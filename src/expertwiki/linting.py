from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import ALLOWED_CONFIDENCE, ALLOWED_STATUSES
from .okf import RESERVED_FILENAMES, OkfConcept, load_okf_concepts, parse_okf_concept


ALLOWED_CONCEPT_TYPES = {
    "Access Policy",
    "Source",
    "Verified Claim",
    "Review",
    "Audit Report",
    "Dispute",
}
ALLOWED_ACCESS_MODES = {"open", "gated", "remote_only", "enterprise_private"}
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

    _check_root_files(context, root)
    concept_paths = _parse_concepts(context, root)
    if not concept_paths:
        return context.result()

    concepts = load_okf_concepts(root)
    _check_concepts(context, concepts)
    _check_source_references(context, concepts)
    _check_index_consistency(context, root)
    _check_markdown_links(context, root)
    _check_access_policy(context, root)
    return context.result()


def _check_root_files(context: LintContext, root: Path) -> None:
    if not root.exists():
        context.issue("critical", "Bundle root does not exist", root)
        return
    if not root.is_dir():
        context.issue("critical", "Bundle root is not a directory", root)
        return
    for filename in ("index.md", "log.md"):
        path = root / filename
        if not path.exists():
            context.issue("critical", f"Missing required {filename}", path)


def _parse_concepts(context: LintContext, root: Path) -> list[Path]:
    concept_paths: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        if path.name in RESERVED_FILENAMES:
            continue
        concept_paths.append(path)
        try:
            parse_okf_concept(root, path)
        except ValueError as exc:
            context.issue("critical", str(exc), path)
    return concept_paths


def _check_concepts(context: LintContext, concepts: dict[str, OkfConcept]) -> None:
    for concept in concepts.values():
        concept_type = concept.type
        if concept_type not in ALLOWED_CONCEPT_TYPES:
            context.issue("warning", f"Unknown concept type: {concept_type}", concept.path)

        if concept_type == "Source":
            _check_required_fields(
                context,
                concept,
                ("title", "resource", "publisher", "retrieved_at"),
            )
            continue

        if concept_type == "Verified Claim":
            _check_verified_claim(context, concept)


def _check_verified_claim(context: LintContext, concept: OkfConcept) -> None:
    _check_required_fields(
        context,
        concept,
        ("title", "status", "confidence", "sources"),
    )

    status = concept.metadata.get("status")
    if status is not None and status not in ALLOWED_STATUSES:
        context.issue("critical", f"Invalid claim status: {status}", concept.path)

    confidence = concept.metadata.get("confidence")
    if confidence is not None and confidence not in ALLOWED_CONFIDENCE:
        context.issue("critical", f"Invalid claim confidence: {confidence}", concept.path)

    reviewers = concept.metadata.get("reviewers")
    if status in {"reviewed", "verified"} and not _is_non_empty_list(reviewers):
        context.issue(
            "critical",
            "Reviewed and verified claims must include at least one reviewer",
            concept.path,
        )

    verified_at = concept.metadata.get("verified_at")
    if status == "verified" and not isinstance(verified_at, str):
        context.issue("critical", "Verified claims must include verified_at", concept.path)

    sources = concept.metadata.get("sources")
    if sources is not None and not _is_non_empty_list(sources):
        context.issue("critical", "Verified Claim sources must be a non-empty list", concept.path)

    if "# Claim" not in concept.body:
        context.issue("critical", "Verified Claim must include a # Claim section", concept.path)


def _check_required_fields(
    context: LintContext,
    concept: OkfConcept,
    fields: tuple[str, ...],
) -> None:
    for field in fields:
        value = concept.metadata.get(field)
        if value in (None, "", []):
            context.issue("critical", f"Missing required frontmatter field: {field}", concept.path)


def _check_source_references(
    context: LintContext,
    concepts: dict[str, OkfConcept],
) -> None:
    available_paths = {concept.path for concept in concepts.values() if concept.type == "Source"}
    for concept in concepts.values():
        if concept.type != "Verified Claim":
            continue
        for source_path in concept.metadata.get("sources", []):
            if str(source_path) not in available_paths:
                context.issue(
                    "critical",
                    f"Claim references missing source: {source_path}",
                    concept.path,
                )


def _check_index_consistency(context: LintContext, root: Path) -> None:
    for directory in sorted(path for path in root.rglob("*") if path.is_dir()):
        markdown_files = [
            path
            for path in directory.glob("*.md")
            if path.name not in RESERVED_FILENAMES
        ]
        if not markdown_files:
            continue

        index_path = directory / "index.md"
        if not index_path.exists():
            context.issue("critical", "Directory with concepts is missing index.md", index_path)
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


def _check_access_policy(context: LintContext, root: Path) -> None:
    access_path = root / "access.md"
    if not access_path.exists():
        context.issue(
            "suggestion",
            "Bundle has no access.md policy; required before marketplace publishing",
            access_path,
        )
        return

    try:
        access_concept = parse_okf_concept(root, access_path)
    except ValueError as exc:
        context.issue("critical", str(exc), access_path)
        return

    mode = access_concept.metadata.get("mode")
    if mode not in ALLOWED_ACCESS_MODES:
        context.issue("critical", f"Invalid access mode: {mode}", access_path)
        return

    if mode in {"gated", "remote_only", "enterprise_private"}:
        download = access_concept.metadata.get("download")
        if download == "allowed":
            context.issue(
                "critical",
                f"{mode} bundle cannot allow full download by default",
                access_path,
            )


def _is_non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _is_external_link(target: str) -> bool:
    return target.startswith(("http://", "https://", "mailto:"))


def _resolve_link(root: Path, source: Path, target: str) -> Path:
    if target.startswith("/"):
        return root / target.removeprefix("/")

    target_without_anchor = target.split("#", 1)[0]
    if not target_without_anchor:
        return source
    return (source.parent / target_without_anchor).resolve()
