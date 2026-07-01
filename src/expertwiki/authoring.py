from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .linting import Issue, lint_bundle
from .models import ALLOWED_CONFIDENCE, ALLOWED_STATUSES
from .okf import (
    RESERVED_FILENAMES,
    OkfConcept,
    load_okf_concepts,
    parse_frontmatter,
    parse_okf_concept,
    render_frontmatter,
)
from .store import KnowledgeStore


ACCESS_MODES = {"open", "gated", "remote_only", "enterprise_private"}
DOWNLOAD_BY_MODE = {
    "open": "allowed",
    "gated": "denied",
    "remote_only": "denied",
    "enterprise_private": "denied",
}
QUERY_BY_MODE = {
    "open": "local",
    "gated": "remote",
    "remote_only": "remote",
    "enterprise_private": "remote",
}


@dataclass(frozen=True)
class InitResult:
    root: str
    created_files: list[str]


@dataclass(frozen=True)
class IndexResult:
    root: str
    updated_indexes: list[str]


@dataclass(frozen=True)
class QueryResult:
    query: str
    status: str | None
    results: list[dict[str, Any]]


@dataclass(frozen=True)
class IngestResult:
    root: str
    source_path: str


@dataclass(frozen=True)
class CompileResult:
    root: str
    claim_path: str


@dataclass(frozen=True)
class AuditResult:
    root: str
    audit_path: str
    ok: bool
    issues: list[Issue]


@dataclass(frozen=True)
class VerifyResult:
    root: str
    claim_path: str
    status: str


@dataclass(frozen=True)
class MarkResult:
    root: str
    claim_path: str
    status: str


@dataclass(frozen=True)
class ListResult:
    root: str
    kind: str
    items: list[dict[str, Any]]


@dataclass(frozen=True)
class ShowResult:
    root: str
    path: str
    concept: dict[str, Any]


@dataclass(frozen=True)
class PackageDryRunResult:
    root: str
    ok: bool
    access_mode: str | None
    concept_counts: dict[str, int]
    issues: list[Issue]


@dataclass(frozen=True)
class StatusResult:
    root: str
    ok: bool
    access_mode: str | None
    concept_counts: dict[str, int]
    claim_status_counts: dict[str, int]
    latest_audit: str | None
    lint_counts: dict[str, int]
    next_actions: list[str]


def init_bundle(
    bundle_dir: str | Path,
    *,
    title: str | None = None,
    access_mode: str = "open",
) -> InitResult:
    if access_mode not in ACCESS_MODES:
        raise ValueError(f"Invalid access mode: {access_mode}")

    root = Path(bundle_dir)
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"Refusing to initialize non-empty directory: {root}")

    root.mkdir(parents=True, exist_ok=True)
    bundle_title = title or _title_from_path(root)
    today = _today()
    timestamp = _timestamp()
    created_files: list[Path] = []

    for directory in ("claims", "sources", "reviews", "audits"):
        (root / directory).mkdir(exist_ok=True)

    created_files.append(_write(root / "index.md", _root_index(bundle_title, today)))
    created_files.append(_write(root / "log.md", "# Bundle Update Log\n"))
    created_files.append(_write(root / "claims" / "index.md", _directory_index("Claims", today)))
    created_files.append(_write(root / "sources" / "index.md", _directory_index("Sources", today)))
    created_files.append(_write(root / "reviews" / "index.md", _directory_index("Reviews", today)))
    created_files.append(_write(root / "audits" / "index.md", _directory_index("Audits", today)))
    created_files.append(
        _write(
            root / "access.md",
            _access_policy(bundle_title, access_mode, timestamp),
        )
    )

    append_log(root, "init", f"Initialized bundle '{bundle_title}'")
    return InitResult(
        root=str(root),
        created_files=[path.relative_to(root).as_posix() for path in created_files],
    )


def ingest_source(
    bundle_dir: str | Path,
    source: str,
    *,
    title: str | None = None,
    publisher: str = "Unknown",
    slug: str | None = None,
) -> IngestResult:
    root = Path(bundle_dir)
    _ensure_bundle(root)

    is_url = _is_url(source)
    source_path = None if is_url else Path(source)
    if source_path is not None and not source_path.exists():
        raise ValueError(f"Source file does not exist: {source}")

    source_title = title or _source_title(source, source_path)
    source_slug = slug or _slugify(source_title)
    output_path = root / "sources" / f"{source_slug}.md"
    if output_path.exists():
        raise ValueError(f"Source already exists: {output_path}")

    body = _source_body(source, source_path, is_url)
    resource = source if is_url else str(source_path.resolve())
    content = f"""---
type: Source
title: {source_title}
description: Source ingested into ExpertWiki.
resource: {resource}
publisher: {publisher}
published_at:
retrieved_at: {_today()}
source_kind: {"url" if is_url else "file"}
timestamp: {_timestamp()}
---

# Source

{body}
"""
    _write(output_path, content)
    rebuild_indexes(root)
    append_log(root, "ingest", f"Ingested {source_title} ({output_path.relative_to(root).as_posix()})")
    return IngestResult(root=str(root), source_path=output_path.relative_to(root).as_posix())


def compile_claim_draft(
    bundle_dir: str | Path,
    source_ref: str,
    *,
    title: str | None = None,
    claim: str | None = None,
    slug: str | None = None,
) -> CompileResult:
    root = Path(bundle_dir)
    _ensure_bundle(root)
    source_path = _resolve_source_ref(root, source_ref)
    source_concept = parse_okf_concept(root, source_path)
    if source_concept.type != "Source":
        raise ValueError(f"Compile source must be a Source concept: {source_ref}")

    claim_title = title or f"Draft Claim From {source_concept.metadata.get('title', source_path.stem)}"
    claim_slug = slug or _slugify(claim_title)
    output_path = root / "claims" / f"{claim_slug}.md"
    if output_path.exists():
        raise ValueError(f"Claim already exists: {output_path}")

    claim_text = claim or "TODO: Replace this draft with one source-backed claim."
    source_link = f"/{source_path.relative_to(root).as_posix()}"
    content = f"""---
type: Verified Claim
title: {claim_title}
description: Draft claim generated from a source; requires human review before verification.
tags: [draft]
status: draft
confidence: low
reviewers: []
sources: [{source_link}]
timestamp: {_timestamp()}
---

# Claim

{claim_text}

# Review Notes

This is a draft. A human reviewer must check the claim against the cited source,
set the correct confidence, add reviewer metadata, and set `verified_at` before
this claim can be treated as verified knowledge.

# Citations

[1] [{source_concept.metadata.get('title', source_path.stem)}]({source_link})
"""
    _write(output_path, content)
    rebuild_indexes(root)
    append_log(root, "compile", f"Created draft claim {output_path.relative_to(root).as_posix()}")
    return CompileResult(root=str(root), claim_path=output_path.relative_to(root).as_posix())


def verify_claim(
    bundle_dir: str | Path,
    claim_ref: str,
    *,
    reviewer: str,
    method: str = "source_audit",
    confidence: str = "high",
    status: str = "verified",
    verified_at: str | None = None,
) -> VerifyResult:
    root = Path(bundle_dir)
    _ensure_bundle(root)
    if status not in {"reviewed", "verified"}:
        raise ValueError("verify only supports reviewed or verified status")
    if confidence not in ALLOWED_CONFIDENCE:
        raise ValueError(f"Invalid confidence: {confidence}")
    claim_path = _resolve_claim_ref(root, claim_ref)
    metadata, body = parse_frontmatter(claim_path.read_text(encoding="utf-8"), claim_path)
    if metadata.get("type") != "Verified Claim":
        raise ValueError(f"Not a Verified Claim: {claim_ref}")

    metadata["status"] = status
    metadata["confidence"] = confidence
    metadata["reviewers"] = [f"{reviewer}:{method}"]
    if status == "verified":
        metadata["verified_at"] = verified_at or _today()
    elif verified_at:
        metadata["verified_at"] = verified_at

    claim_path.write_text(render_frontmatter(metadata, body), encoding="utf-8")
    rebuild_indexes(root)
    append_log(root, "verify", f"{claim_path.relative_to(root).as_posix()} -> {status}")
    return VerifyResult(
        root=str(root),
        claim_path=claim_path.relative_to(root).as_posix(),
        status=status,
    )


def mark_claim(
    bundle_dir: str | Path,
    claim_ref: str,
    *,
    status: str,
    reason: str | None = None,
) -> MarkResult:
    root = Path(bundle_dir)
    _ensure_bundle(root)
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid claim status: {status}")
    claim_path = _resolve_claim_ref(root, claim_ref)
    metadata, body = parse_frontmatter(claim_path.read_text(encoding="utf-8"), claim_path)
    if metadata.get("type") != "Verified Claim":
        raise ValueError(f"Not a Verified Claim: {claim_ref}")

    metadata["status"] = status
    metadata["status_updated_at"] = _today()
    if reason:
        metadata["status_reason"] = reason
    claim_path.write_text(render_frontmatter(metadata, body), encoding="utf-8")
    rebuild_indexes(root)
    append_log(root, "mark", f"{claim_path.relative_to(root).as_posix()} -> {status}")
    return MarkResult(
        root=str(root),
        claim_path=claim_path.relative_to(root).as_posix(),
        status=status,
    )


def list_concepts(
    bundle_dir: str | Path,
    *,
    kind: str,
    status: str | None = None,
) -> ListResult:
    root = Path(bundle_dir)
    _ensure_bundle(root)
    concepts = load_okf_concepts(root)
    expected_type = _kind_to_type(kind)
    items: list[dict[str, Any]] = []
    for concept in concepts.values():
        if concept.type != expected_type:
            continue
        concept_status = concept.metadata.get("status")
        if status is not None and concept_status != status:
            continue
        items.append(_concept_summary(concept))
    items.sort(key=lambda item: item["path"])
    return ListResult(root=str(root), kind=kind, items=items)


def show_concept(bundle_dir: str | Path, ref: str, *, kind: str | None = None) -> ShowResult:
    root = Path(bundle_dir)
    _ensure_bundle(root)
    path = _resolve_concept_ref(root, ref, kind=kind)
    concept = parse_okf_concept(root, path)
    return ShowResult(
        root=str(root),
        path=path.relative_to(root).as_posix(),
        concept={
            "id": concept.id,
            "path": concept.path,
            "type": concept.type,
            "metadata": concept.metadata,
            "body": concept.body,
        },
    )


def append_log(bundle_dir: str | Path, operation: str, description: str) -> None:
    root = Path(bundle_dir)
    log_path = root / "log.md"
    if not log_path.exists():
        log_path.write_text("# Bundle Update Log\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## [{_today()}] {operation} | {description}\n")


def rebuild_indexes(bundle_dir: str | Path) -> IndexResult:
    root = Path(bundle_dir)
    if not root.exists():
        raise ValueError(f"Bundle root does not exist: {root}")

    # Fail fast on invalid concepts before rewriting indexes.
    load_okf_concepts(root)

    updated: list[Path] = []
    directories = [root, *sorted(path for path in root.rglob("*") if path.is_dir())]
    for directory in directories:
        if _should_index(directory):
            updated.append(_write(directory / "index.md", _render_index(root, directory)))

    append_log(root, "index", f"Rebuilt {len(updated)} index file(s)")
    return IndexResult(
        root=str(root),
        updated_indexes=[path.relative_to(root).as_posix() for path in updated],
    )


def query_bundle(
    bundle_dir: str | Path,
    query: str,
    *,
    status: str | None = "verified",
    limit: int = 10,
) -> QueryResult:
    store = KnowledgeStore(bundle_dir)
    results = store.search(query, status=status, limit=limit)
    append_log(bundle_dir, "query", f"{query!r} -> {len(results)} result(s)")
    return QueryResult(query=query, status=status, results=results)


def package_dry_run(bundle_dir: str | Path) -> PackageDryRunResult:
    root = Path(bundle_dir)
    lint_result = lint_bundle(root)
    try:
        concepts = load_okf_concepts(root) if root.exists() else {}
    except ValueError:
        concepts = {}
    concept_counts: dict[str, int] = {}
    for concept in concepts.values():
        concept_counts[concept.type] = concept_counts.get(concept.type, 0) + 1

    issues = list(lint_result.issues)
    access_mode = _access_mode(root)
    if access_mode is None:
        issues.append(
            Issue(
                "critical",
                "Package requires access.md with a valid access mode",
                "access.md",
            )
        )

    ok = not any(issue.severity == "critical" for issue in issues)
    return PackageDryRunResult(
        root=str(root),
        ok=ok,
        access_mode=access_mode,
        concept_counts=concept_counts,
        issues=sorted(issues, key=lambda issue: issue.sort_key()),
    )


def bundle_status(bundle_dir: str | Path) -> StatusResult:
    root = Path(bundle_dir)
    _ensure_bundle(root)
    lint_result = lint_bundle(root)
    concepts = load_okf_concepts(root)
    concept_counts: dict[str, int] = {}
    claim_status_counts: dict[str, int] = {
        status: 0 for status in sorted(ALLOWED_STATUSES)
    }
    for concept in concepts.values():
        concept_counts[concept.type] = concept_counts.get(concept.type, 0) + 1
        if concept.type == "Verified Claim":
            status = str(concept.metadata.get("status", "unknown"))
            claim_status_counts[status] = claim_status_counts.get(status, 0) + 1

    latest_audit = _latest_audit(root)
    lint_counts = lint_result.counts()
    next_actions = _next_actions(concept_counts, claim_status_counts, lint_counts)
    return StatusResult(
        root=str(root),
        ok=lint_result.ok,
        access_mode=_access_mode(root),
        concept_counts=concept_counts,
        claim_status_counts=claim_status_counts,
        latest_audit=latest_audit,
        lint_counts=lint_counts,
        next_actions=next_actions,
    )


def audit_bundle(bundle_dir: str | Path) -> AuditResult:
    root = Path(bundle_dir)
    _ensure_bundle(root)
    lint_result = lint_bundle(root)
    concepts = load_okf_concepts(root)
    draft_claims = [
        concept for concept in concepts.values()
        if concept.type == "Verified Claim" and concept.metadata.get("status") == "draft"
    ]
    stale_claims = [
        concept for concept in concepts.values()
        if concept.type == "Verified Claim" and concept.metadata.get("status") == "stale"
    ]
    disputed_claims = [
        concept for concept in concepts.values()
        if concept.type == "Verified Claim" and concept.metadata.get("status") == "disputed"
    ]
    issues = list(lint_result.issues)
    audit_slug = f"audit-{_timestamp_slug()}"
    audit_path = root / "audits" / f"{audit_slug}.md"
    ok = not any(issue.severity == "critical" for issue in issues)
    _write(
        audit_path,
        _audit_report(
            title=f"Audit {_timestamp()}",
            ok=ok,
            issues=issues,
            draft_count=len(draft_claims),
            stale_count=len(stale_claims),
            disputed_count=len(disputed_claims),
        ),
    )
    rebuild_indexes(root)
    append_log(root, "audit", f"Wrote {audit_path.relative_to(root).as_posix()}")
    return AuditResult(
        root=str(root),
        audit_path=audit_path.relative_to(root).as_posix(),
        ok=ok,
        issues=issues,
    )


def _ensure_bundle(root: Path) -> None:
    if not root.exists():
        raise ValueError(f"Bundle root does not exist: {root}")
    if not (root / "index.md").exists() or not (root / "log.md").exists():
        raise ValueError(f"Not an ExpertWiki bundle: {root}")


def _should_index(directory: Path) -> bool:
    if directory.name.startswith("."):
        return False
    has_markdown = any(path.suffix == ".md" for path in directory.iterdir() if path.is_file())
    has_child_directory = any(path.is_dir() and not path.name.startswith(".") for path in directory.iterdir())
    return has_markdown or has_child_directory


def _render_index(root: Path, directory: Path) -> str:
    title = "Bundle" if directory == root else _title_from_path(directory)
    today = _today()
    lines = [
        f"# {title} Index",
        "",
        f"Last updated: {today}",
        "",
    ]

    child_dirs = sorted(path for path in directory.iterdir() if path.is_dir() and not path.name.startswith("."))
    if child_dirs:
        lines.extend(["## Directories", ""])
        for child in child_dirs:
            lines.append(f"* [{_title_from_path(child)}]({child.name}/)")
        lines.append("")

    concept_files = [
        path
        for path in sorted(directory.glob("*.md"))
        if path.name not in RESERVED_FILENAMES
    ]
    if concept_files:
        lines.extend(
            [
                "## Contents",
                "",
                "| File | Type | Summary | Tags | Updated |",
                "|---|---|---|---|---|",
            ]
        )
        for path in concept_files:
            concept = parse_okf_concept(root, path)
            lines.append(_index_row(path, concept))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _index_row(path: Path, concept: OkfConcept) -> str:
    metadata = concept.metadata
    title = str(metadata.get("title") or path.stem)
    summary = str(metadata.get("description") or metadata.get("summary") or "")
    tags = metadata.get("tags")
    tags_text = ", ".join(str(tag) for tag in tags) if isinstance(tags, list) else ""
    updated = str(metadata.get("verified_at") or metadata.get("retrieved_at") or metadata.get("timestamp") or "")
    return (
        f"| [{title}]({path.name}) | {concept.type} | "
        f"{_table_cell(summary)} | {_table_cell(tags_text)} | {_table_cell(updated)} |"
    )


def _table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _access_mode(root: Path) -> str | None:
    access_path = root / "access.md"
    if not access_path.exists():
        return None
    try:
        concept = parse_okf_concept(root, access_path)
    except ValueError:
        return None
    mode = concept.metadata.get("mode")
    if isinstance(mode, str) and mode in ACCESS_MODES:
        return mode
    return None


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _resolve_source_ref(root: Path, source_ref: str) -> Path:
    candidates: list[Path] = []
    raw = source_ref.strip()
    if raw.startswith("/"):
        candidates.append(root / raw.removeprefix("/"))
    else:
        candidates.append(root / raw)
        candidates.append(root / "sources" / raw)
        if not raw.endswith(".md"):
            candidates.append(root / "sources" / f"{raw}.md")

    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise ValueError(f"Source reference not found: {source_ref}")


def _resolve_claim_ref(root: Path, claim_ref: str) -> Path:
    return _resolve_concept_ref(root, claim_ref, kind="claims")


def _resolve_concept_ref(root: Path, ref: str, *, kind: str | None = None) -> Path:
    raw = ref.strip()
    candidates: list[Path] = []
    if raw.startswith("/"):
        candidates.append(root / raw.removeprefix("/"))
    else:
        candidates.append(root / raw)
        if kind is not None:
            candidates.append(root / kind / raw)
            if not raw.endswith(".md"):
                candidates.append(root / kind / f"{raw}.md")
        elif not raw.endswith(".md"):
            candidates.extend(
                [
                    root / "claims" / f"{raw}.md",
                    root / "sources" / f"{raw}.md",
                    root / "reviews" / f"{raw}.md",
                    root / "audits" / f"{raw}.md",
                ]
            )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise ValueError(f"Concept reference not found: {ref}")


def _kind_to_type(kind: str) -> str:
    mapping = {
        "claims": "Verified Claim",
        "sources": "Source",
        "reviews": "Review",
        "audits": "Audit Report",
    }
    if kind not in mapping:
        raise ValueError(f"Invalid kind: {kind}")
    return mapping[kind]


def _concept_summary(concept: OkfConcept) -> dict[str, Any]:
    return {
        "id": concept.id,
        "path": concept.path,
        "type": concept.type,
        "title": concept.metadata.get("title"),
        "description": concept.metadata.get("description"),
        "status": concept.metadata.get("status"),
        "confidence": concept.metadata.get("confidence"),
        "verified_at": concept.metadata.get("verified_at"),
    }


def _latest_audit(root: Path) -> str | None:
    audit_dir = root / "audits"
    if not audit_dir.exists():
        return None
    audits = sorted(
        (path for path in audit_dir.glob("*.md") if path.name not in RESERVED_FILENAMES),
        key=lambda path: path.name,
    )
    if not audits:
        return None
    return audits[-1].relative_to(root).as_posix()


def _next_actions(
    concept_counts: dict[str, int],
    claim_status_counts: dict[str, int],
    lint_counts: dict[str, int],
) -> list[str]:
    actions: list[str] = []
    if lint_counts.get("critical", 0):
        actions.append("Fix critical lint issues before continuing.")
    elif lint_counts.get("warning", 0):
        actions.append("Review lint warnings.")

    if concept_counts.get("Source", 0) == 0:
        actions.append("Ingest at least one source.")
    if claim_status_counts.get("draft", 0):
        actions.append("Review draft claims and run verify only after human approval.")
    if claim_status_counts.get("stale", 0):
        actions.append("Refresh or reject stale claims.")
    if claim_status_counts.get("disputed", 0):
        actions.append("Resolve disputed claims.")
    if concept_counts.get("Verified Claim", 0) and claim_status_counts.get("verified", 0) == 0:
        actions.append("Verify reviewed claims before relying on query results.")
    if concept_counts.get("Audit Report", 0) == 0:
        actions.append("Run audit before packaging or sharing the bundle.")
    if not actions:
        actions.append("Bundle is ready for local query or package dry-run.")
    return actions


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _source_title(source: str, source_path: Path | None) -> str:
    if source_path is not None:
        text = source_path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped.removeprefix("# ").strip()
        return _title_from_path(source_path)

    parsed = urlparse(source)
    name = Path(parsed.path).stem or parsed.netloc
    return _title_from_path(Path(name))


def _source_body(source: str, source_path: Path | None, is_url: bool) -> str:
    if is_url:
        return (
            f"Recorded URL: [{source}]({source})\n\n"
            "Content was not fetched automatically. Add source notes manually before compiling claims."
        )
    assert source_path is not None
    text = source_path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return "Empty source file."
    return text


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def _audit_report(
    *,
    title: str,
    ok: bool,
    issues: list[Issue],
    draft_count: int,
    stale_count: int,
    disputed_count: int,
) -> str:
    status = "pass" if ok else "fail"
    issue_lines = "\n".join(
        f"- **{issue.severity}** {issue.path or ''}: {issue.message}".strip()
        for issue in issues
    ) or "- No lint issues."
    return f"""---
type: Audit Report
title: {title}
description: Local ExpertWiki audit report.
status: {status}
timestamp: {_timestamp()}
---

# Audit Report

Status: **{status}**

# Claim Status Summary

- Draft claims: {draft_count}
- Stale claims: {stale_count}
- Disputed claims: {disputed_count}

# Issues

{issue_lines}
"""


def _root_index(title: str, today: str) -> str:
    return f"""# {title} Index

Last updated: {today}

## Directories

* [Claims](claims/)
* [Sources](sources/)
* [Reviews](reviews/)
* [Audits](audits/)

## Contents

| File | Type | Summary | Tags | Updated |
|---|---|---|---|---|
| [Access Policy](access.md) | Access Policy | Bundle access policy |  |  |
"""


def _directory_index(title: str, today: str) -> str:
    return f"""# {title} Index

Last updated: {today}
"""


def _access_policy(title: str, access_mode: str, timestamp: str) -> str:
    download = DOWNLOAD_BY_MODE[access_mode]
    query = QUERY_BY_MODE[access_mode]
    return f"""---
type: Access Policy
title: {title} Access Policy
description: Access policy for {title}.
mode: {access_mode}
download: {download}
query: {query}
raw_sources: {"visible" if access_mode == "open" else "restricted"}
citation_detail: {"full" if access_mode == "open" else "limited"}
timestamp: {timestamp}
---

# Access Policy

This bundle uses `{access_mode}` access.
"""


def _title_from_path(path: Path) -> str:
    words = re.split(r"[-_\s]+", path.name.strip())
    return " ".join(word.capitalize() for word in words if word) or "ExpertWiki"


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
