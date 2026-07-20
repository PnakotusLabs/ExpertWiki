from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from .okf import RESERVED_FILENAMES, OkfConcept, load_okf_concepts, parse_okf_concept


ALLOWED_CONCEPT_TYPES = {"raw_source", "wiki_page", "draft_page", "audit_report"}
ALLOWED_ENTITY_TYPES = {"expert", "project", "viewpoint", "topic", "comparison", "synthesis"}
ALLOWED_QUALITY_STATES = {"unreviewed", "reviewed", "verified", "stale", "disputed", "rejected"}
SEVERITY_ORDER = {"critical": 0, "warning": 1, "suggestion": 2, "info": 3}
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
CITATION_PATTERN = re.compile(r"\^\[([^\]]+)\]")


@dataclass(frozen=True)
class Issue:
    severity: str
    message: str
    path: str | None = None

    def sort_key(self) -> tuple[int, str, str]:
        return (
            SEVERITY_ORDER.get(self.severity, 99),
            self.path or "",
            self.message,
        )


@dataclass(frozen=True)
class LintResult:
    root: str
    issues: list[Issue]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "critical" for issue in self.issues)

    def counts(self) -> dict[str, int]:
        counts = {"critical": 0, "warning": 0, "suggestion": 0, "info": 0}
        for issue in self.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return counts


class LintContext:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.issues: list[Issue] = []

    def issue(self, severity: str, message: str, path: str | Path | None = None) -> None:
        self.issues.append(Issue(severity, message, self._display_path(path)))

    def result(self) -> LintResult:
        return LintResult(
            root=str(self.root),
            issues=sorted(self.issues, key=lambda issue: issue.sort_key()),
        )

    def _display_path(self, path: str | Path | None) -> str | None:
        if path is None:
            return None
        path_obj = Path(path)
        try:
            return path_obj.relative_to(self.root).as_posix()
        except ValueError:
            return str(path)


def lint_bundle(bundle_dir: str | Path) -> LintResult:
    context = LintContext(bundle_dir)
    root = Path(bundle_dir)

    _check_root(context, root)
    if not root.exists() or not root.is_dir():
        return context.result()

    _parse_concepts(context, root)
    try:
        concepts = load_okf_concepts(root)
    except ValueError:
        return context.result()

    _check_concepts(context, concepts)
    _check_source_references(context, concepts)
    _check_citations(context, root, concepts)
    _check_index_consistency(context, root)
    _check_markdown_links(context, root)
    _check_compiler_state(context, root)
    return context.result()


def _check_root(context: LintContext, root: Path) -> None:
    if not root.exists():
        context.issue("critical", "Wiki root does not exist", root)
        return
    if not root.is_dir():
        context.issue("critical", "Wiki root is not a directory", root)
        return

    for filename in ("AGENTS.md", "index.md", "log.md"):
        path = root / filename
        if not path.exists():
            context.issue("critical", f"Missing required {filename}", path)

    for dirname in ("raw", "wiki"):
        path = root / dirname
        if not path.is_dir():
            context.issue("critical", f"Missing required {dirname}/ directory", path)


def _parse_concepts(context: LintContext, root: Path) -> None:
    for path in sorted(root.rglob("*.md")):
        if path.name in RESERVED_FILENAMES:
            continue
        try:
            parse_okf_concept(root, path)
        except ValueError as exc:
            context.issue("critical", str(exc), path)


def _check_concepts(context: LintContext, concepts: dict[str, OkfConcept]) -> None:
    for concept in concepts.values():
        if concept.type not in ALLOWED_CONCEPT_TYPES:
            context.issue("warning", f"Unknown concept type: {concept.type}", concept.path)
            continue

        if concept.type == "raw_source":
            _check_required_fields(context, concept, ("title", "resource", "publisher", "retrieved_at"))
            if not concept.path.startswith("/raw/sources/"):
                context.issue("warning", "raw_source should live under raw/sources/", concept.path)
            continue

        if concept.type == "wiki_page":
            _check_required_fields(context, concept, ("title",))
            if not concept.path.startswith("/wiki/"):
                context.issue("warning", "wiki_page should live under wiki/", concept.path)
            entity_type = concept.metadata.get("entity_type")
            if entity_type not in ALLOWED_ENTITY_TYPES:
                context.issue("warning", "wiki_page should declare a valid entity_type", concept.path)
            quality = concept.metadata.get("quality")
            if quality not in ALLOWED_QUALITY_STATES:
                context.issue("warning", "wiki_page should declare a valid quality state", concept.path)
            for field in ("license", "source_updated_at", "last_reviewed_at"):
                if field not in concept.metadata:
                    context.issue("suggestion", f"wiki_page has no {field} field", concept.path)
            sources = concept.metadata.get("sources")
            if sources is None:
                context.issue("suggestion", "wiki_page has no sources list", concept.path)
            elif not isinstance(sources, list):
                context.issue("critical", "wiki_page sources must be a list", concept.path)
            continue

        if concept.type == "draft_page":
            _check_required_fields(context, concept, ("title",))
            if not concept.path.startswith(("/.expertwiki/drafts/", "/.expertwiki/rejected/")):
                context.issue(
                    "warning",
                    "draft_page should live under .expertwiki/drafts/ or .expertwiki/rejected/",
                    concept.path,
                )
            sources = concept.metadata.get("sources")
            if sources is None:
                context.issue("suggestion", "draft_page has no sources list", concept.path)
            elif not isinstance(sources, list):
                context.issue("critical", "draft_page sources must be a list", concept.path)
            continue

        if concept.type == "audit_report":
            _check_required_fields(context, concept, ("title", "created_at"))


def _check_required_fields(
    context: LintContext,
    concept: OkfConcept,
    fields: tuple[str, ...],
) -> None:
    for field in fields:
        value = concept.metadata.get(field)
        if value in (None, "", []):
            context.issue("critical", f"Missing required frontmatter field: {field}", concept.path)


def _check_source_references(context: LintContext, concepts: dict[str, OkfConcept]) -> None:
    available_paths = {concept.path for concept in concepts.values() if concept.type == "raw_source"}
    for concept in concepts.values():
        if concept.type not in {"wiki_page", "draft_page"}:
            continue
        sources = concept.metadata.get("sources")
        if not isinstance(sources, list):
            continue
        for source_path in sources:
            if str(source_path) not in available_paths:
                context.issue(
                    "critical",
                    f"{concept.type} references missing source: {source_path}",
                    concept.path,
                )


def _check_citations(
    context: LintContext,
    root: Path,
    concepts: dict[str, OkfConcept],
) -> None:
    source_lines = {
        concept.path.removeprefix("/"): len((root / concept.path.removeprefix("/")).read_text(encoding="utf-8").splitlines())
        for concept in concepts.values()
        if concept.type == "raw_source"
    }
    basename_map: dict[str, list[str]] = {}
    for source_path in source_lines:
        basename_map.setdefault(Path(source_path).name, []).append(source_path)
    for concept in concepts.values():
        if concept.type not in {"wiki_page", "draft_page"}:
            continue
        for marker in CITATION_PATTERN.findall(concept.body):
            for raw_ref in [part.strip() for part in marker.split(",") if part.strip()]:
                match = re.fullmatch(r"(.+?\.md)(?::(\d+)(?:-(\d+))?)?", raw_ref)
                if not match:
                    context.issue("critical", f"Malformed source citation: ^[{raw_ref}]", concept.path)
                    continue
                raw_path, start_raw, end_raw = match.groups()
                source_path = raw_path.removeprefix("/")
                if source_path not in source_lines:
                    matches = basename_map.get(Path(source_path).name, [])
                    if len(matches) == 1:
                        source_path = matches[0]
                    else:
                        context.issue(
                            "critical",
                            f"Citation references an unknown source: {raw_path}",
                            concept.path,
                        )
                        continue
                if start_raw:
                    start = int(start_raw)
                    end = int(end_raw or start_raw)
                    if start < 1 or end < start or end > source_lines[source_path]:
                        context.issue(
                            "critical",
                            f"Citation range is outside {source_path}: {start}-{end}",
                            concept.path,
                        )


def _check_index_consistency(context: LintContext, root: Path) -> None:
    for directory in sorted(path for path in root.rglob("*") if path.is_dir()):
        if any(part.startswith(".") for part in directory.relative_to(root).parts):
            continue
        markdown_files = [
            path
            for path in directory.glob("*.md")
            if path.name not in RESERVED_FILENAMES
        ]
        child_dirs = [path for path in directory.iterdir() if path.is_dir() and not path.name.startswith(".")]
        if not markdown_files and not child_dirs:
            continue

        index_path = directory / "index.md"
        if not index_path.exists():
            context.issue("critical", "Directory with wiki content is missing index.md", index_path)
            continue

        index_text = index_path.read_text(encoding="utf-8")
        for markdown_file in markdown_files:
            if markdown_file.name not in index_text:
                context.issue(
                    "warning",
                    f"index.md does not reference {markdown_file.name}",
                    index_path,
                )


def _check_markdown_links(context: LintContext, root: Path) -> None:
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK_PATTERN.findall(text):
            cleaned = target.strip("<>")
            if _is_external_link(cleaned) or cleaned.startswith("#"):
                continue
            target_path = _resolve_link(root, path, cleaned)
            if not target_path.exists():
                context.issue("warning", f"Broken markdown link: {target}", path)


def _check_compiler_state(context: LintContext, root: Path) -> None:
    journal_dir = root / ".expertwiki" / "journal"
    pending_journals = sorted(journal_dir.glob("*.json")) if journal_dir.exists() else []
    for path in pending_journals:
        context.issue(
            "critical",
            "Pending compiler journal requires recovery before the bundle is trusted",
            path,
        )

    database = root / ".expertwiki" / "state.sqlite"
    if not database.exists():
        return
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        required = {"sources", "concepts", "articles", "drafts"}
        if not required.issubset(tables):
            context.issue("critical", "Compiler state database is missing required tables", database)
            return
        for row in connection.execute("SELECT path, content_hash, status FROM sources"):
            path = root / str(row["path"])
            if row["status"] == "deleted":
                if path.exists():
                    context.issue("warning", "Deleted source exists again and needs analysis", path)
                continue
            if not path.exists():
                context.issue("critical", "Compiler state references a missing source", path)
                continue
            if _content_hash(path) != str(row["content_hash"]):
                context.issue("warning", "Source changed since its last compiler scan", path)
        for row in connection.execute("SELECT path, content_hash FROM drafts WHERE status = 'pending_review'"):
            path = root / str(row["path"])
            if not path.exists():
                context.issue("critical", "Compiler state references a missing draft", path)
            elif _content_hash(path) != str(row["content_hash"]):
                context.issue("warning", "Draft was edited after compilation", path)
        for row in connection.execute("SELECT path, content_hash FROM articles"):
            path = root / str(row["path"])
            if not path.exists():
                context.issue("critical", "Compiler state references a missing published page", path)
            elif _content_hash(path) != str(row["content_hash"]):
                context.issue("warning", "Published page has a manual edit not recorded in state", path)
        for row in connection.execute(
            "SELECT name, status FROM concepts WHERE status IN ('frozen', 'orphaned', 'blocked')"
        ):
            severity = "warning" if row["status"] in {"frozen", "orphaned"} else "info"
            context.issue(severity, f"Compiler concept {row['name']!r} is {row['status']}", database)
    except sqlite3.DatabaseError as exc:
        context.issue("critical", f"Compiler state database cannot be read: {exc}", database)
    finally:
        if connection is not None:
            connection.close()


def _content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_external_link(target: str) -> bool:
    return "://" in target or target.startswith("mailto:")


def _resolve_link(root: Path, current_path: Path, target: str) -> Path:
    target = target.split("#", 1)[0]
    if target.startswith("/"):
        return root / target.removeprefix("/")
    return (current_path.parent / target).resolve()
