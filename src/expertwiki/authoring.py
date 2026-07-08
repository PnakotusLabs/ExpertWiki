from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .linting import Issue, lint_bundle
from .okf import RESERVED_FILENAMES, OkfConcept, load_okf_concepts, parse_okf_concept
from .store import KnowledgeStore


@dataclass(frozen=True)
class InitResult:
    root: str
    created_files: list[str]


@dataclass(frozen=True)
class IngestResult:
    root: str
    source_path: str


@dataclass(frozen=True)
class PageResult:
    root: str
    page_path: str


@dataclass(frozen=True)
class IndexResult:
    root: str
    updated_indexes: list[str]


@dataclass(frozen=True)
class QueryResult:
    query: str
    results: list[dict[str, Any]]


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
class AuditResult:
    root: str
    audit_path: str
    ok: bool
    issues: list[Issue]


@dataclass(frozen=True)
class PackageDryRunResult:
    root: str
    ok: bool
    concept_counts: dict[str, int]
    issues: list[Issue]


@dataclass(frozen=True)
class StatusResult:
    root: str
    ok: bool
    concept_counts: dict[str, int]
    latest_audit: str | None
    lint_counts: dict[str, int]
    next_actions: list[str]


def init_bundle(bundle_dir: str | Path, *, title: str | None = None) -> InitResult:
    root = Path(bundle_dir)
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"Refusing to initialize non-empty directory: {root}")

    root.mkdir(parents=True, exist_ok=True)
    wiki_title = title or _title_from_path(root)
    created: list[Path] = []

    for directory in (
        "raw",
        "raw/sources",
        "wiki",
        "wiki/topics",
        "wiki/entities",
        "wiki/comparisons",
        "wiki/synthesis",
        "audits",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)

    created.append(_write(root / "AGENTS.md", _agents_file(wiki_title)))
    created.append(_write(root / "index.md", _root_index(wiki_title)))
    created.append(_write(root / "log.md", "# Wiki Update Log\n"))
    for directory in ("raw", "raw/sources", "wiki", "wiki/topics", "wiki/entities", "wiki/comparisons", "wiki/synthesis", "audits"):
        created.append(_write(root / directory / "index.md", _directory_index(directory)))

    append_log(root, "init", f"Initialized LLM Wiki '{wiki_title}'")
    return InitResult(
        root=str(root),
        created_files=[path.relative_to(root).as_posix() for path in created],
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
    output_path = root / "raw" / "sources" / f"{source_slug}.md"
    if output_path.exists():
        raise ValueError(f"Source already exists: {output_path}")

    resource = source if is_url else str(source_path.resolve())
    content = f"""---
type: raw_source
title: {source_title}
description: Source material ingested into the local LLM Wiki.
resource: {resource}
publisher: {publisher}
retrieved_at: {_today()}
source_kind: {"url" if is_url else "file"}
created_at: {_timestamp()}
---

# Source

{_source_body(source, source_path, is_url)}
"""
    _write(output_path, content)
    rebuild_indexes(root)
    append_log(root, "ingest", f"Ingested {source_title} ({output_path.relative_to(root).as_posix()})")
    return IngestResult(root=str(root), source_path=output_path.relative_to(root).as_posix())


def create_page(
    bundle_dir: str | Path,
    page_path: str,
    *,
    title: str,
    description: str | None = None,
    sources: list[str] | None = None,
    tags: list[str] | None = None,
) -> PageResult:
    root = Path(bundle_dir)
    _ensure_bundle(root)

    relative = Path(page_path)
    if relative.is_absolute():
        raise ValueError("Page path must be relative")
    if relative.suffix != ".md":
        raise ValueError("Page path must end with .md")
    if not relative.parts or relative.parts[0] != "wiki":
        raise ValueError("Page path must live under wiki/")

    output_path = root / relative
    if output_path.exists():
        raise ValueError(f"Page already exists: {output_path}")

    source_paths = [_source_path(root, source_ref) for source_ref in (sources or [])]
    content = _wiki_page(
        title=title,
        description=description or "",
        tags=tags or [],
        sources=source_paths,
    )
    _write(output_path, content)
    rebuild_indexes(root)
    append_log(root, "page", f"Created {output_path.relative_to(root).as_posix()}")
    return PageResult(root=str(root), page_path=output_path.relative_to(root).as_posix())


def list_concepts(bundle_dir: str | Path, *, kind: str) -> ListResult:
    root = Path(bundle_dir)
    _ensure_bundle(root)
    concepts = load_okf_concepts(root)
    expected_type = _kind_to_type(kind)
    items = [
        _concept_summary(concept)
        for concept in concepts.values()
        if concept.type == expected_type
    ]
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


def query_bundle(bundle_dir: str | Path, query: str, *, limit: int = 10) -> QueryResult:
    store = KnowledgeStore(bundle_dir)
    results = store.search(query, limit=limit)
    append_log(bundle_dir, "query", f"{query!r} -> {len(results)} result(s)")
    return QueryResult(query=query, results=results)


def rebuild_indexes(bundle_dir: str | Path) -> IndexResult:
    root = Path(bundle_dir)
    if not root.exists():
        raise ValueError(f"Wiki root does not exist: {root}")
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


def audit_bundle(bundle_dir: str | Path) -> AuditResult:
    root = Path(bundle_dir)
    _ensure_bundle(root)
    lint_result = lint_bundle(root)
    concepts = load_okf_concepts(root)
    page_count = sum(1 for concept in concepts.values() if concept.type == "wiki_page")
    source_count = sum(1 for concept in concepts.values() if concept.type == "raw_source")
    audit_path = root / "audits" / f"audit-{_timestamp_slug()}.md"
    ok = not any(issue.severity == "critical" for issue in lint_result.issues)
    _write(
        audit_path,
        _audit_report(
            ok=ok,
            page_count=page_count,
            source_count=source_count,
            issues=lint_result.issues,
        ),
    )
    rebuild_indexes(root)
    append_log(root, "audit", f"Wrote {audit_path.relative_to(root).as_posix()}")
    return AuditResult(
        root=str(root),
        audit_path=audit_path.relative_to(root).as_posix(),
        ok=ok,
        issues=lint_result.issues,
    )


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

    ok = not any(issue.severity == "critical" for issue in lint_result.issues)
    return PackageDryRunResult(
        root=str(root),
        ok=ok,
        concept_counts=concept_counts,
        issues=lint_result.issues,
    )


def bundle_status(bundle_dir: str | Path) -> StatusResult:
    root = Path(bundle_dir)
    _ensure_bundle(root)
    lint_result = lint_bundle(root)
    concepts = load_okf_concepts(root)
    concept_counts: dict[str, int] = {}
    for concept in concepts.values():
        concept_counts[concept.type] = concept_counts.get(concept.type, 0) + 1

    lint_counts = lint_result.counts()
    return StatusResult(
        root=str(root),
        ok=lint_result.ok,
        concept_counts=concept_counts,
        latest_audit=_latest_audit(root),
        lint_counts=lint_counts,
        next_actions=_next_actions(concept_counts, lint_counts),
    )


def append_log(bundle_dir: str | Path, operation: str, description: str) -> None:
    root = Path(bundle_dir)
    log_path = root / "log.md"
    if not log_path.exists():
        log_path.write_text("# Wiki Update Log\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## [{_today()}] {operation} | {description}\n")


def _ensure_bundle(root: Path) -> None:
    if not root.exists():
        raise ValueError(f"Wiki root does not exist: {root}")
    required = ("AGENTS.md", "index.md", "log.md", "raw", "wiki")
    if not all((root / path).exists() for path in required):
        raise ValueError(f"Not an ExpertWiki LLM Wiki: {root}")


def _agents_file(title: str) -> str:
    return f"""# {title} Agent Instructions

This directory is a local LLM Wiki. Agents maintain it by preserving raw sources,
writing interlinked Markdown pages, updating indexes, and recording changes in
log.md.

## Workflow

1. Read index.md and log.md before editing.
2. Preserve source material under raw/sources/.
3. Write synthesized pages under wiki/.
4. Use Markdown links between related pages.
5. Cite raw sources from each wiki page when source material exists.
6. Run lint after write operations.
7. Run audit before packaging or sharing.
"""


def _root_index(title: str) -> str:
    return f"""# {title}

This is a local LLM Wiki.

## Navigation

* [Raw Sources](raw/)
* [Wiki](wiki/)
* [Audits](audits/)
* [Update Log](log.md)
"""


def _directory_index(directory: str) -> str:
    return f"# {_title_from_path(Path(directory))}\n"


def _wiki_page(
    *,
    title: str,
    description: str,
    tags: list[str],
    sources: list[str],
) -> str:
    return f"""---
type: wiki_page
title: {title}
description: {description}
tags: [{", ".join(tags)}]
sources: [{", ".join(sources)}]
updated_at: {_today()}
---

# {title}

## Summary

TODO: Summarize the topic from the cited sources.

## Key Points

- TODO

## Related Pages

- TODO

## Open Questions

- TODO

## Sources

{_source_list(sources)}
"""


def _source_list(sources: list[str]) -> str:
    if not sources:
        return "- TODO"
    return "\n".join(f"- [{Path(source).stem}]({source})" for source in sources)


def _audit_report(*, ok: bool, page_count: int, source_count: int, issues: list[Issue]) -> str:
    issue_lines = "\n".join(
        f"- [{issue.severity}] {issue.path or 'bundle'}: {issue.message}"
        for issue in issues
    ) or "- No lint issues."
    return f"""---
type: audit_report
title: Audit {_timestamp()}
created_at: {_timestamp()}
---

# Audit

Status: {"OK" if ok else "Needs attention"}

## Counts

- Wiki pages: {page_count}
- Raw sources: {source_count}

## Issues

{issue_lines}
"""


def _should_index(directory: Path) -> bool:
    if directory.name.startswith("."):
        return False
    has_markdown = any(path.suffix == ".md" for path in directory.iterdir() if path.is_file())
    has_child_directory = any(path.is_dir() and not path.name.startswith(".") for path in directory.iterdir())
    return has_markdown or has_child_directory


def _render_index(root: Path, directory: Path) -> str:
    title = root.name if directory == root else _title_from_path(directory)
    lines = [
        f"# {title} Index",
        "",
        f"Last updated: {_today()}",
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
        lines.extend(["## Pages", "", "| File | Type | Description | Updated |", "|---|---|---|---|"])
        for path in concept_files:
            concept = parse_okf_concept(root, path)
            lines.append(_index_row(path, concept))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _index_row(path: Path, concept: OkfConcept) -> str:
    metadata = concept.metadata
    title = str(metadata.get("title") or path.stem)
    description = str(metadata.get("description") or "")
    updated = str(metadata.get("updated_at") or metadata.get("retrieved_at") or metadata.get("created_at") or "")
    return f"| [{title}]({path.name}) | {concept.type} | {_table_cell(description)} | {_table_cell(updated)} |"


def _concept_summary(concept: OkfConcept) -> dict[str, Any]:
    metadata = concept.metadata
    return {
        "id": concept.id,
        "path": concept.path,
        "type": concept.type,
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "updated_at": metadata.get("updated_at") or metadata.get("retrieved_at") or metadata.get("created_at"),
    }


def _kind_to_type(kind: str) -> str:
    mapping = {
        "pages": "wiki_page",
        "sources": "raw_source",
        "audits": "audit_report",
    }
    if kind not in mapping:
        raise ValueError(f"Unknown list kind: {kind}")
    return mapping[kind]


def _resolve_concept_ref(root: Path, ref: str, *, kind: str | None) -> Path:
    raw = ref.strip().removeprefix("/")
    candidates: list[Path] = []
    if raw.endswith(".md"):
        candidates.append(root / raw)
    if kind == "pages" or kind is None:
        candidates.extend(
            [
                root / "wiki" / raw,
                root / "wiki" / f"{raw}.md",
                root / f"{raw}.md",
            ]
        )
    if kind == "sources" or kind is None:
        candidates.extend(
            [
                root / "raw" / "sources" / raw,
                root / "raw" / "sources" / f"{raw}.md",
            ]
        )
    if kind == "audits" or kind is None:
        candidates.extend([root / "audits" / raw, root / "audits" / f"{raw}.md"])

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    raise ValueError(f"Concept reference not found: {ref}")


def _source_path(root: Path, source_ref: str) -> str:
    path = _resolve_concept_ref(root, source_ref, kind="sources")
    return f"/{path.relative_to(root).as_posix()}"


def _latest_audit(root: Path) -> str | None:
    audits_dir = root / "audits"
    if not audits_dir.exists():
        return None
    audits = sorted(
        path for path in audits_dir.glob("*.md")
        if path.name not in RESERVED_FILENAMES
    )
    if not audits:
        return None
    return audits[-1].relative_to(root).as_posix()


def _next_actions(concept_counts: dict[str, int], lint_counts: dict[str, int]) -> list[str]:
    actions: list[str] = []
    if lint_counts.get("critical", 0):
        actions.append("Fix critical lint issues.")
    if concept_counts.get("raw_source", 0) == 0:
        actions.append("Ingest raw sources.")
    if concept_counts.get("wiki_page", 0) == 0:
        actions.append("Create wiki pages from raw sources.")
    if not actions:
        actions.append("Continue linking and maintaining wiki pages.")
    return actions


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _source_title(source: str, source_path: Path | None) -> str:
    if source_path is not None:
        first_heading = _first_markdown_heading(source_path)
        return first_heading or _title_from_path(source_path)
    parsed = urlparse(source)
    return _title_from_path(Path(parsed.path or parsed.netloc))


def _source_body(source: str, source_path: Path | None, is_url: bool) -> str:
    if is_url:
        return (
            f"Source URL: {source}\n\n"
            "Content was not fetched automatically. Add source notes manually before writing wiki pages."
        )
    assert source_path is not None
    return source_path.read_text(encoding="utf-8").strip()


def _first_markdown_heading(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.removeprefix("# ").strip()
    return None


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _title_from_path(path: Path) -> str:
    name = path.stem if path.suffix else path.name
    return re.sub(r"[-_]+", " ", name).strip().title() or "Wiki"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "page"


def _table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
