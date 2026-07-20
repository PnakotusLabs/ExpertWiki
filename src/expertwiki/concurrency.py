from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
import uuid


class BundleLockedError(RuntimeError):
    pass


class BundleLock(AbstractContextManager["BundleLock"]):
    """Single-writer lock with dead-process reclamation."""

    def __init__(self, bundle_dir: str | Path, *, timeout: float = 10.0) -> None:
        self.root = Path(bundle_dir).resolve()
        self.path = self.root / ".expertwiki" / "compiler.lock"
        self.timeout = timeout
        self.token = uuid.uuid4().hex
        self._acquired = False

    def __enter__(self) -> "BundleLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout
        while True:
            payload = json.dumps(
                {"pid": os.getpid(), "token": self.token, "created_at": _timestamp()},
                sort_keys=True,
            )
            try:
                descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                self._acquired = True
                return self
            except FileExistsError:
                if self._reclaim_dead_owner():
                    continue
                if time.monotonic() >= deadline:
                    owner = _read_lock(self.path)
                    raise BundleLockedError(f"ExpertWiki compiler is already running: {owner}")
                time.sleep(0.05)

    def _reclaim_dead_owner(self) -> bool:
        owner = _read_lock(self.path)
        pid = owner.get("pid") if isinstance(owner, dict) else None
        if not isinstance(pid, int) or _pid_is_alive(pid):
            return False
        reclaim = self.path.with_suffix(".reclaim")
        try:
            descriptor = os.open(reclaim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
        except FileExistsError:
            return False
        try:
            current = _read_lock(self.path)
            if current != owner:
                return False
            self.path.unlink(missing_ok=True)
            return True
        finally:
            reclaim.unlink(missing_ok=True)

    def __exit__(self, *_: object) -> None:
        if not self._acquired:
            return
        owner = _read_lock(self.path)
        if isinstance(owner, dict) and owner.get("token") == self.token:
            self.path.unlink(missing_ok=True)
        self._acquired = False


@dataclass
class _JournalEntry:
    path: str
    absent: bool
    content: str | None


class FileMutationBatch(AbstractContextManager["FileMutationBatch"]):
    """Pre-state journal for a small batch of Markdown mutations."""

    def __init__(self, bundle_dir: str | Path, operation: str) -> None:
        self.root = Path(bundle_dir).resolve()
        self.operation = operation
        self.batch_id = f"{int(time.time() * 1000)}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self.journal_dir = self.root / ".expertwiki" / "journal"
        self.journal_path = self.journal_dir / f"{self.batch_id}.json"
        self.entries: list[_JournalEntry] = []
        self._committed = False

    def __enter__(self) -> "FileMutationBatch":
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self._persist()
        return self

    def capture(self, path: str | Path) -> None:
        target = _confined_path(self.root, path)
        relative = target.relative_to(self.root).as_posix()
        if any(entry.path == relative for entry in self.entries):
            return
        if target.is_symlink():
            raise ValueError(f"Refusing to mutate symlinked file: {target}")
        if target.exists() and not target.is_file():
            raise ValueError(f"Refusing to mutate non-file target: {target}")
        content = target.read_text(encoding="utf-8") if target.exists() else None
        self.entries.append(_JournalEntry(relative, content is None, content))
        self._persist()

    def write_text(self, path: str | Path, content: str) -> None:
        target = _confined_path(self.root, path)
        self.capture(target)
        atomic_write_text(target, content)

    def unlink(self, path: str | Path) -> None:
        target = _confined_path(self.root, path)
        self.capture(target)
        target.unlink(missing_ok=True)

    def commit(self) -> None:
        self._committed = True
        self.journal_path.unlink(missing_ok=True)

    def rollback(self) -> None:
        for entry in reversed(self.entries):
            target = _confined_path(self.root, entry.path)
            if entry.absent:
                target.unlink(missing_ok=True)
            else:
                assert entry.content is not None
                atomic_write_text(target, entry.content)
        self.journal_path.unlink(missing_ok=True)

    def __exit__(self, exc_type: object, *_: object) -> None:
        if exc_type is not None or not self._committed:
            self.rollback()

    def _persist(self) -> None:
        payload = {
            "batch_id": self.batch_id,
            "operation": self.operation,
            "status": "pending",
            "entries": [entry.__dict__ for entry in self.entries],
        }
        atomic_write_text(self.journal_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def recover_file_journals(bundle_dir: str | Path) -> list[str]:
    root = Path(bundle_dir).resolve()
    journal_dir = root / ".expertwiki" / "journal"
    if not journal_dir.exists():
        return []
    recovered: list[str] = []
    for path in sorted(journal_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            entries = payload["entries"]
            if not isinstance(entries, list):
                raise ValueError("entries must be a list")
            for raw in reversed(entries):
                target = _confined_path(root, str(raw["path"]))
                if bool(raw["absent"]):
                    target.unlink(missing_ok=True)
                else:
                    content = raw.get("content")
                    if not isinstance(content, str):
                        raise ValueError("journal content must be text")
                    atomic_write_text(target, content)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot safely recover file journal {path}: {exc}") from exc
        path.unlink()
        recovered.append(path.name)
    return recovered


def atomic_write_text(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _confined_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Mutation target escapes ExpertWiki bundle: {candidate}") from exc
    return candidate


def _read_lock(path: Path) -> dict[str, object]:
    try:
        if path.is_symlink() or not path.is_file():
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
