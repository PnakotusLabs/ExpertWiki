from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .okf import RESERVED_FILENAMES, OkfConcept, load_okf_concepts, parse_okf_concept


ALLOWED_CONCEPT_TYPES = {"raw_source", "wiki_page", "audit_report"}
SEVERITY_ORDER = {"critical": 0, "warning": 1, "suggestion": 2, "info": 3}
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


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
    _check_index_consistency(context, root)
    _check_markdown_links(context, root)
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
            sources = concept.metadata.get("sources")
            if sources is None:
                context.issue("suggestion", "wiki_page has no sources list", concept.path)
            elif not isinstance(sources, list):
                context.issue("critical", "wiki_page sources must be a list", concept.path)
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
        if concept.type != "wiki_page":
            continue
        sources = concept.metadata.get("sources")
        if not isinstance(sources, list):
            continue
        for source_path in sources:
            if str(source_path) not in available_paths:
                context.issue(
                    "critical",
                    f"wiki_page references missing source: {source_path}",
                    concept.path,
                )


def _check_index_consistency(context: LintContext, root: Path) -> None:
    for directory in sorted(path for path in root.rglob("*") if path.is_dir()):
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


def _is_external_link(target: str) -> bool:
    return "://" in target or target.startswith("mailto:")


def _resolve_link(root: Path, current_path: Path, target: str) -> Path:
    target = target.split("#", 1)[0]
    if target.startswith("/"):
        return root / target.removeprefix("/")
    return (current_path.parent / target).resolve()
