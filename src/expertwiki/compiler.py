from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Sequence

from .authoring import append_log, rebuild_indexes
from .concurrency import BundleLock, FileMutationBatch, recover_file_journals
from .llm import (
    ARTICLE_PROMPT_VERSION,
    EXTRACTION_PROMPT_VERSION,
    AnalysisResult,
    ExtractedConcept,
    LLMClient,
    build_article_prompt,
    build_extraction_prompt,
    client_from_env,
    parse_analysis,
    parse_article,
)
from .okf import RESERVED_FILENAMES, load_okf_concepts, parse_okf_concept, render_frontmatter
from .state import ConceptRecord, SourceRecord, StateDB


EXTRACTOR_VERSION = "expertwiki-compiler-v1"
DEFAULT_ANALYSIS_CHARS = 14_000
DEFAULT_COMPILE_CONTEXT_CHARS = 56_000
REJECTION_BLOCK_THRESHOLD = 3


@dataclass(frozen=True)
class SourceChange:
    path: str
    status: str


@dataclass(frozen=True)
class AnalyzeBundleResult:
    root: str
    changes: list[SourceChange]
    analyzed_sources: list[str]
    affected_concepts: list[str]
    errors: list[str]


@dataclass(frozen=True)
class CompileBundleResult:
    root: str
    run_id: int
    changes: list[SourceChange]
    analyzed_sources: list[str]
    draft_paths: list[str]
    skipped: list[dict[str, str]]
    frozen_concepts: list[str]
    orphaned_concepts: list[str]
    errors: list[str]


@dataclass(frozen=True)
class ApprovedDraftResult:
    root: str
    draft_path: str
    page_path: str
    title: str


@dataclass(frozen=True)
class RejectedDraftResult:
    root: str
    draft_path: str
    rejected_path: str
    title: str
    feedback: str
    blocked: bool


@dataclass(frozen=True)
class ReturnedDraftResult:
    root: str
    page_path: str
    draft_path: str
    title: str


def state_path(bundle_dir: str | Path) -> Path:
    return Path(bundle_dir) / ".expertwiki" / "state.sqlite"


def compiler_stats(
    bundle_dir: str | Path,
    *,
    initialize: bool = True,
) -> dict[str, Any]:
    root = Path(bundle_dir)
    database = state_path(root)
    if not database.exists() and not initialize:
        concepts = load_okf_concepts(root)
        return {
            "initialized": False,
            "database": database.relative_to(root).as_posix(),
            "sources": sum(1 for item in concepts.values() if item.type == "raw_source"),
            "articles": sum(1 for item in concepts.values() if item.type == "wiki_page"),
            "drafts": len(list((root / ".expertwiki" / "drafts").glob("*.md"))),
        }
    with StateDB(database) as state:
        bootstrap_state(root, state)
        stats: dict[str, Any] = state.stats()
        stats["initialized"] = True
        stats["database"] = database.relative_to(root).as_posix()
        return stats


def analyze_bundle(
    bundle_dir: str | Path,
    *,
    client: LLMClient | None = None,
    analyze_all: bool = False,
) -> AnalyzeBundleResult:
    root = Path(bundle_dir)
    model = _require_client(client)
    with BundleLock(root):
        recover_file_journals(root)
        with StateDB(state_path(root)) as state:
            bootstrap_state(root, state)
            changes = detect_source_changes(root, state, analyze_all=analyze_all)
            paths = [change.path for change in changes if change.status in {"new", "changed"}]
            analyzed, affected, errors = _analyze_paths(root, state, model, paths)
            append_log(
                root,
                "analyze",
                f"Analyzed {len(analyzed)} source(s); {len(errors)} failed",
            )
            return AnalyzeBundleResult(
                root=str(root),
                changes=changes,
                analyzed_sources=analyzed,
                affected_concepts=sorted(affected),
                errors=errors,
            )


def compile_bundle(
    bundle_dir: str | Path,
    *,
    client: LLMClient | None = None,
    concept_refs: Sequence[str] = (),
    analyze_changes: bool = True,
    force: bool = False,
    allow_manual_overwrite: bool = False,
) -> CompileBundleResult:
    root = Path(bundle_dir)
    model = _require_client(client)
    with BundleLock(root):
        recover_file_journals(root)
        with StateDB(state_path(root)) as state:
            bootstrap_state(root, state)
            run_id = state.begin_run()
            changes: list[SourceChange] = []
            analyzed: list[str] = []
            errors: list[str] = []
            draft_paths: list[str] = []
            skipped: list[dict[str, str]] = []
            try:
                changes = detect_source_changes(root, state)
                if analyze_changes:
                    paths = [
                        change.path
                        for change in changes
                        if change.status in {"new", "changed"}
                    ]
                    analyzed, _, analyze_errors = _analyze_paths(root, state, model, paths)
                    errors.extend(analyze_errors)
                elif any(change.status in {"new", "changed"} for change in changes):
                    skipped.append(
                        {
                            "concept": "*",
                            "reason": "Changed sources require analysis; rerun without --no-analyze.",
                        }
                    )

                concepts = _selected_concepts(state, concept_refs, force=force)
                for concept in concepts:
                    try:
                        outcome, value = _compile_concept(
                            root,
                            state,
                            model,
                            concept,
                            force=force,
                            allow_manual_overwrite=allow_manual_overwrite,
                        )
                    except Exception as exc:
                        state.mark_concept_status(concept.id, "dirty")
                        errors.append(f"{concept.name}: {exc}")
                        continue
                    if outcome == "draft":
                        draft_paths.append(value)
                    else:
                        skipped.append({"concept": concept.name, "reason": value})

                frozen = [item.name for item in state.list_concepts(statuses=["frozen"])]
                orphaned = [item.name for item in state.list_concepts(statuses=["orphaned"])]
                status = "failed" if errors else "completed"
                state.finish_run(
                    run_id,
                    status=status,
                    changed_sources=[change.path for change in changes],
                    analyzed_count=len(analyzed),
                    compiled_count=len(draft_paths),
                    skipped_count=len(skipped),
                    error="\n".join(errors) if errors else None,
                )
                append_log(
                    root,
                    "compile",
                    f"Run {run_id}: {len(draft_paths)} draft(s), {len(skipped)} skipped, "
                    f"{len(errors)} error(s)",
                )
                return CompileBundleResult(
                    root=str(root),
                    run_id=run_id,
                    changes=changes,
                    analyzed_sources=analyzed,
                    draft_paths=draft_paths,
                    skipped=skipped,
                    frozen_concepts=frozen,
                    orphaned_concepts=orphaned,
                    errors=errors,
                )
            except Exception as exc:
                state.finish_run(
                    run_id,
                    status="failed",
                    changed_sources=[change.path for change in changes],
                    analyzed_count=len(analyzed),
                    compiled_count=len(draft_paths),
                    skipped_count=len(skipped),
                    error=str(exc),
                )
                raise


def bootstrap_state(root: Path, state: StateDB) -> None:
    """Import durable Markdown artifacts without treating imported pages as compiler-owned."""
    if not (root / "AGENTS.md").exists():
        raise ValueError(f"Not an ExpertWiki bundle: {root}")
    for path in _source_files(root):
        relative = path.relative_to(root).as_posix()
        if state.get_source(relative) is not None:
            continue
        concept = parse_okf_concept(root, path)
        text = path.read_text(encoding="utf-8")
        state.upsert_source(
            path=relative,
            title=str(concept.metadata.get("title", path.stem)),
            resource=str(concept.metadata.get("resource", relative)),
            publisher=str(concept.metadata.get("publisher", "Unknown")),
            content_hash=_hash(text),
            line_count=len(text.splitlines()),
            status="preserved",
        )

    known_article_paths = {str(row["path"]) for row in state.list_articles()}
    for path in sorted((root / "wiki").rglob("*.md")):
        if path.name in RESERVED_FILENAMES or any(part.startswith(".") for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if relative in known_article_paths:
            continue
        concept = parse_okf_concept(root, path)
        if concept.type != "wiki_page":
            continue
        title = str(concept.metadata.get("title", path.stem))
        record = state.ensure_concept(
            title,
            summary=str(concept.metadata.get("description", "")),
            tags=_as_string_list(concept.metadata.get("tags", [])),
            status="clean",
        )
        text = path.read_text(encoding="utf-8")
        managed = str(concept.metadata.get("generator", "")) == EXTRACTOR_VERSION
        source_hashes = _json_object(concept.metadata.get("source_hashes", "{}"))
        state.upsert_article(
            concept_id=record.id,
            path=relative,
            content_hash=_hash(text),
            source_hashes=source_hashes,
            status="published",
            managed=managed,
            compiled_at=str(concept.metadata.get("compiled_at", "")) or None,
            approved_at=str(concept.metadata.get("approved_at", "")) or None,
        )
        _import_source_dependencies(state, record.id, concept.metadata)

    drafts_dir = root / ".expertwiki" / "drafts"
    if drafts_dir.exists():
        for path in sorted(drafts_dir.glob("*.md")):
            candidate = parse_okf_concept(root, path)
            if candidate.type != "draft_page":
                continue
            title = str(candidate.metadata.get("title", path.stem))
            draft_concept = state.get_concept(title) or state.ensure_concept(
                title,
                summary=str(candidate.metadata.get("description", "")),
                tags=_as_string_list(candidate.metadata.get("tags", [])),
                status="clean",
            )
            if state.get_draft(draft_concept.id) is None:
                text = path.read_text(encoding="utf-8")
                state.upsert_draft(
                    concept_id=draft_concept.id,
                    path=path.relative_to(root).as_posix(),
                    content_hash=_hash(text),
                    source_hashes=_json_object(candidate.metadata.get("source_hashes", "{}")),
                    prompt_hash=str(candidate.metadata.get("prompt_hash", _hash(candidate.body))),
                    model=str(candidate.metadata.get("model", "unknown")),
                )
                state.mark_concept_status(draft_concept.id, "clean")
            _import_source_dependencies(state, draft_concept.id, candidate.metadata)

    _reconcile_missing_drafts(root, state)


def detect_source_changes(
    root: Path,
    state: StateDB,
    *,
    analyze_all: bool = False,
) -> list[SourceChange]:
    changes: list[SourceChange] = []
    on_disk: set[str] = set()
    for path in _source_files(root):
        relative = path.relative_to(root).as_posix()
        on_disk.add(relative)
        text = path.read_text(encoding="utf-8")
        content_hash = _hash(text)
        concept = parse_okf_concept(root, path)
        previous = state.get_source(relative)
        if previous is None or previous.analyzed_at is None:
            status = "new"
        elif (
            analyze_all
            or previous.content_hash != content_hash
            or previous.status in {"deleted", "failed", "changed", "preserved"}
        ):
            status = "changed"
        else:
            continue
        state.upsert_source(
            path=relative,
            title=str(concept.metadata.get("title", path.stem)),
            resource=str(concept.metadata.get("resource", relative)),
            publisher=str(concept.metadata.get("publisher", "Unknown")),
            content_hash=content_hash,
            line_count=len(text.splitlines()),
            status="changed" if status == "changed" else "preserved",
        )
        changes.append(SourceChange(relative, status))

    for source in state.list_sources(include_deleted=False):
        if source.path in on_disk:
            continue
        state.mark_concepts_after_source_deletion(source.path)
        changes.append(SourceChange(source.path, "deleted"))
    changes.sort(key=lambda item: item.path)
    return changes


def approve_draft(
    bundle_dir: str | Path,
    draft_ref: str,
    *,
    force: bool = False,
) -> ApprovedDraftResult:
    root = Path(bundle_dir)
    with BundleLock(root):
        recover_file_journals(root)
        with StateDB(state_path(root)) as state:
            bootstrap_state(root, state)
            draft_path = _resolve_draft(root, state, draft_ref)
            candidate = parse_okf_concept(root, draft_path)
            concept_id = _draft_concept_id(candidate.metadata, state, draft_path)
            concept = state.get_concept(concept_id)
            if concept is None:
                raise ValueError(f"Draft concept is missing from compiler state: {draft_path}")
            article = state.get_article(concept_id)
            if article:
                page_path = root / str(article["path"])
                if page_path.exists() and _hash(page_path.read_text(encoding="utf-8")) != str(
                    article["content_hash"]
                ):
                    state.mark_article_manual_edit(concept_id)
                    if not force:
                        raise ValueError(
                            "Published page was edited manually; rerun approve with --force to replace it."
                        )
            else:
                page_path = _page_path(root, str(candidate.metadata.get("entity_type", "topic")), concept.slug)

            metadata = dict(candidate.metadata)
            metadata["type"] = "wiki_page"
            metadata["status"] = "published"
            metadata["quality"] = "reviewed"
            metadata["approved_at"] = _timestamp()
            metadata["last_reviewed_at"] = _today()
            metadata["updated_at"] = _today()
            metadata.pop("draft_status", None)
            rendered = render_frontmatter(metadata, candidate.body)
            indexes = list(root.rglob("index.md"))
            with FileMutationBatch(root, "approve") as batch:
                batch.write_text(page_path, rendered)
                batch.unlink(draft_path)
                for index in indexes:
                    batch.capture(index)
                with state.transaction():
                    source_hashes = _json_object(candidate.metadata.get("source_hashes", "{}"))
                    state.upsert_article(
                        concept_id=concept_id,
                        path=page_path.relative_to(root).as_posix(),
                        content_hash=_hash(rendered),
                        source_hashes=source_hashes,
                        status="published",
                        managed=True,
                        compiled_at=str(candidate.metadata.get("compiled_at", "")) or None,
                        approved_at=str(metadata["approved_at"]),
                    )
                    state.delete_draft(concept_id)
                    state.mark_concept_status(concept_id, "clean")
                rebuild_indexes(root)
                batch.commit()
            append_log(root, "approve", f"Approved {concept.name} ({page_path.relative_to(root)})")
            return ApprovedDraftResult(
                root=str(root),
                draft_path=draft_path.relative_to(root).as_posix(),
                page_path=page_path.relative_to(root).as_posix(),
                title=concept.name,
            )


def reject_draft(
    bundle_dir: str | Path,
    draft_ref: str,
    *,
    feedback: str,
) -> RejectedDraftResult:
    if not feedback.strip():
        raise ValueError("Rejection feedback is required.")
    root = Path(bundle_dir)
    with BundleLock(root):
        recover_file_journals(root)
        with StateDB(state_path(root)) as state:
            bootstrap_state(root, state)
            draft_path = _resolve_draft(root, state, draft_ref)
            candidate = parse_okf_concept(root, draft_path)
            concept_id = _draft_concept_id(candidate.metadata, state, draft_path)
            concept = state.get_concept(concept_id)
            if concept is None:
                raise ValueError(f"Draft concept is missing from compiler state: {draft_path}")
            metadata = dict(candidate.metadata)
            metadata["draft_status"] = "rejected"
            metadata["rejection_feedback"] = feedback.strip()
            metadata["rejected_at"] = _timestamp()
            rejected_dir = root / ".expertwiki" / "rejected"
            rejected_dir.mkdir(parents=True, exist_ok=True)
            rejected_path = _available_path(rejected_dir / draft_path.name)
            rendered = render_frontmatter(metadata, candidate.body)
            with FileMutationBatch(root, "reject") as batch:
                batch.write_text(rejected_path, rendered)
                batch.unlink(draft_path)
                with state.transaction():
                    state.add_rejection(concept_id, feedback.strip(), candidate.body)
                    state.delete_draft(concept_id)
                    blocked = state.rejection_count(concept_id) >= REJECTION_BLOCK_THRESHOLD
                    state.mark_concept_status(concept_id, "blocked" if blocked else "dirty")
                batch.commit()
            append_log(root, "reject", f"Rejected {concept.name}: {feedback.strip()}")
            return RejectedDraftResult(
                root=str(root),
                draft_path=draft_path.relative_to(root).as_posix(),
                rejected_path=rejected_path.relative_to(root).as_posix(),
                title=concept.name,
                feedback=feedback.strip(),
                blocked=blocked,
            )


def return_article_to_draft(
    bundle_dir: str | Path,
    page_ref: str,
) -> ReturnedDraftResult:
    root = Path(bundle_dir)
    with BundleLock(root):
        recover_file_journals(root)
        with StateDB(state_path(root)) as state:
            bootstrap_state(root, state)
            page_path = _resolve_article(root, state, page_ref)
            article = state.find_article_by_path(page_path.relative_to(root).as_posix())
            if article is None:
                raise ValueError(f"Published page is missing from compiler state: {page_path}")
            concept_id = int(article["concept_id"])
            concept = state.get_concept(concept_id)
            if concept is None:
                raise ValueError(f"Published concept is missing from compiler state: {page_path}")
            candidate = parse_okf_concept(root, page_path)
            metadata = dict(candidate.metadata)
            metadata["type"] = "draft_page"
            metadata["concept_id"] = str(concept_id)
            metadata["status"] = "draft"
            metadata["draft_status"] = "pending_review"
            metadata["returned_to_draft_at"] = _timestamp()
            metadata.pop("quality", None)
            metadata.pop("approved_at", None)
            metadata.pop("last_reviewed_at", None)
            metadata.pop("updated_at", None)
            draft_path = _available_path(root / ".expertwiki" / "drafts" / f"{concept.slug}.md")
            rendered = render_frontmatter(metadata, candidate.body)
            indexes = list(root.rglob("index.md"))
            with FileMutationBatch(root, "return-to-draft") as batch:
                batch.write_text(draft_path, rendered)
                batch.unlink(page_path)
                for index in indexes:
                    batch.capture(index)
                with state.transaction():
                    state.upsert_draft(
                        concept_id=concept_id,
                        path=draft_path.relative_to(root).as_posix(),
                        content_hash=_hash(rendered),
                        source_hashes=_json_object(article["source_hashes_json"]),
                        prompt_hash="manual-return-to-draft",
                        model="manual",
                    )
                    state.delete_article(concept_id)
                    state.mark_concept_status(concept_id, "dirty")
                rebuild_indexes(root)
                batch.commit()
            append_log(root, "draft", f"Returned {concept.name} to draft ({draft_path.relative_to(root)})")
            return ReturnedDraftResult(
                root=str(root),
                page_path=page_path.relative_to(root).as_posix(),
                draft_path=draft_path.relative_to(root).as_posix(),
                title=concept.name,
            )


def return_rejected_to_draft(
    bundle_dir: str | Path,
    rejected_ref: str,
) -> ReturnedDraftResult:
    root = Path(bundle_dir)
    with BundleLock(root):
        recover_file_journals(root)
        with StateDB(state_path(root)) as state:
            bootstrap_state(root, state)
            rejected_path = _resolve_rejected(root, state, rejected_ref)
            candidate = parse_okf_concept(root, rejected_path)
            concept_id = _draft_concept_id(candidate.metadata, state, rejected_path)
            concept = state.get_concept(concept_id)
            if concept is None:
                raise ValueError(f"Rejected concept is missing from compiler state: {rejected_path}")
            metadata = dict(candidate.metadata)
            metadata["type"] = "draft_page"
            metadata["concept_id"] = str(concept_id)
            metadata["status"] = "draft"
            metadata["draft_status"] = "pending_review"
            metadata["returned_to_draft_at"] = _timestamp()
            metadata.pop("rejected_at", None)
            metadata.pop("rejection_feedback", None)
            draft_path = _available_path(root / ".expertwiki" / "drafts" / f"{concept.slug}.md")
            rendered = render_frontmatter(metadata, candidate.body)
            with FileMutationBatch(root, "return-rejected-to-draft") as batch:
                batch.write_text(draft_path, rendered)
                batch.unlink(rejected_path)
                with state.transaction():
                    state.upsert_draft(
                        concept_id=concept_id,
                        path=draft_path.relative_to(root).as_posix(),
                        content_hash=_hash(rendered),
                        source_hashes=_source_hashes_from_metadata(metadata),
                        prompt_hash="manual-return-to-draft",
                        model="manual",
                    )
                    state.mark_concept_status(concept_id, "dirty")
                batch.commit()
            append_log(root, "draft", f"Returned rejected {concept.name} to draft ({draft_path.relative_to(root)})")
            return ReturnedDraftResult(
                root=str(root),
                page_path=rejected_path.relative_to(root).as_posix(),
                draft_path=draft_path.relative_to(root).as_posix(),
                title=concept.name,
            )


def list_compiler_drafts(bundle_dir: str | Path) -> list[dict[str, Any]]:
    root = Path(bundle_dir)
    with StateDB(state_path(root)) as state:
        bootstrap_state(root, state)
        output: list[dict[str, Any]] = []
        for row in state.list_drafts():
            path = root / str(row["path"])
            if not path.exists():
                continue
            concept = parse_okf_concept(root, path)
            output.append(
                {
                    "path": str(row["path"]),
                    "title": str(row["name"]),
                    "description": str(concept.metadata.get("description", row["summary"])),
                    "entity_type": str(concept.metadata.get("entity_type", "topic")),
                    "sources": _as_string_list(concept.metadata.get("sources", [])),
                    "created_at": str(row["created_at"]),
                    "source_hashes": _json_object(row["source_hashes_json"]),
                }
            )
        return output


def _analyze_paths(
    root: Path,
    state: StateDB,
    client: LLMClient,
    paths: Sequence[str],
) -> tuple[list[str], set[str], list[str]]:
    analyzed: list[str] = []
    affected_names: set[str] = set()
    errors: list[str] = []
    for source_path in paths:
        try:
            analysis = _analyze_source(root, state, client, source_path)
            records = [_concept_payload(concept) for concept in analysis.concepts]
            old_ids, new_ids = state.record_analysis(
                source_path=source_path,
                summary=analysis.summary,
                quality=analysis.quality,
                language=analysis.language,
                extractor_version=EXTRACTOR_VERSION,
                prompt_version=EXTRACTION_PROMPT_VERSION,
                suggested_topics=analysis.suggested_topics,
                named_references=analysis.named_references,
                concepts=records,
            )
            for concept_id in old_ids | new_ids:
                concept = state.get_concept(concept_id)
                if concept:
                    affected_names.add(concept.name)
            analyzed.append(source_path)
        except Exception as exc:
            state.mark_source_failed(source_path, str(exc))
            errors.append(f"{source_path}: {exc}")
    return analyzed, affected_names, errors


def _analyze_source(
    root: Path,
    state: StateDB,
    client: LLMClient,
    source_path: str,
) -> AnalysisResult:
    path = root / source_path
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    existing = [
        {
            "name": concept.name,
            "slug": concept.slug,
            "aliases": state.aliases_for_concept(concept.id),
        }
        for concept in state.list_concepts()
    ]
    chunks = _numbered_chunks(lines, DEFAULT_ANALYSIS_CHARS)
    partials: list[AnalysisResult] = []
    for chunk in chunks:
        prompt = build_extraction_prompt(
            source_path=source_path,
            numbered_content=chunk,
            existing_concepts=existing,
        )
        payload = client.complete_json(prompt, model=client.fast_model, purpose="analysis")
        partial = parse_analysis(payload)
        _validate_analysis_ranges(partial, len(lines))
        partials.append(partial)
    return _merge_analyses(partials)


def _selected_concepts(
    state: StateDB,
    concept_refs: Sequence[str],
    *,
    force: bool,
) -> list[ConceptRecord]:
    if concept_refs:
        output: list[ConceptRecord] = []
        for ref in concept_refs:
            concept = state.get_concept(ref)
            if concept is None:
                raise ValueError(f"Concept not found: {ref}")
            output.append(concept)
        return output
    statuses = ["dirty"]
    if force:
        statuses.append("blocked")
    return state.list_concepts(statuses=statuses)


def _compile_concept(
    root: Path,
    state: StateDB,
    client: LLMClient,
    concept: ConceptRecord,
    *,
    force: bool,
    allow_manual_overwrite: bool,
) -> tuple[str, str]:
    if concept.status == "frozen":
        return "skip", "A contributing source was deleted; the previous synthesis is frozen."
    if concept.status == "orphaned":
        return "skip", "No active source supports this concept."
    if concept.status == "blocked" and not force:
        return "skip", "Three rejected drafts blocked automatic retries."

    source_links = state.source_concepts_for_concept(concept.id)
    if not source_links:
        return "skip", "No analyzed source supports this concept."
    source_hashes: dict[str, str] = {}
    source_texts: list[tuple[str, str, list[str]]] = []
    for link in source_links:
        path = root / link.source_path
        if not path.exists():
            return "skip", f"Contributing source is missing: {link.source_path}"
        text = path.read_text(encoding="utf-8")
        source_hashes[link.source_path] = _hash(text)
        source_texts.append((link.source_path, text, link.source_ranges))

    draft_row = state.get_draft(concept.id)
    if draft_row:
        draft_path = root / str(draft_row["path"])
        if draft_path.exists() and not force:
            recorded = _json_object(draft_row["source_hashes_json"])
            reason = "An unreviewed draft already exists."
            if recorded != source_hashes:
                reason += " Its sources changed; use --force to regenerate it."
            return "skip", reason

    article = state.get_article(concept.id)
    existing_page = ""
    if article:
        article_path = root / str(article["path"])
        if article_path.exists():
            text = article_path.read_text(encoding="utf-8")
            changed_manually = _hash(text) != str(article["content_hash"])
            imported = not bool(article["managed"])
            if (changed_manually or imported) and not allow_manual_overwrite:
                state.mark_article_manual_edit(concept.id)
                reason = "Published page is user-owned or manually edited; refusing to overwrite it."
                return "skip", reason
            existing_page = text

    material = _assemble_source_material(source_texts, DEFAULT_COMPILE_CONTEXT_CHARS)
    related = _related_page_manifest(state, exclude_id=concept.id)
    feedback = [item["feedback"] for item in state.recent_rejections(concept.id)]
    prompt = build_article_prompt(
        concept_name=concept.name,
        aliases=state.aliases_for_concept(concept.id),
        source_material=material,
        existing_page=existing_page,
        related_pages=related,
        rejection_feedback=feedback,
    )
    payload = client.complete_json(prompt, model=client.heavy_model, purpose="compile")
    article_result = parse_article(payload)
    body = _resolve_wikilinks(article_result.body, state)
    citations = _parse_and_validate_citations(body, state, concept.id)
    sources = [f"/{path}" for path in sorted(source_hashes)]
    prompt_hash = _hash(prompt)
    metadata = {
        "type": "draft_page",
        "concept_id": concept.id,
        "concept_slug": concept.slug,
        "entity_type": article_result.entity_type,
        "title": article_result.title,
        "aliases": [alias for alias in state.aliases_for_concept(concept.id) if alias != concept.name],
        "description": article_result.description,
        "tags": article_result.tags,
        "sources": sources,
        "source_hashes": json.dumps(source_hashes, sort_keys=True, separators=(",", ":")),
        "status": "draft",
        "quality": "unreviewed",
        "confidence": f"{concept.confidence:.2f}",
        "provenance_state": concept.provenance_state,
        "license": "unknown",
        "source_updated_at": _today(),
        "last_reviewed_at": "unknown",
        "updated_at": _today(),
        "compiled_at": _timestamp(),
        "generator": EXTRACTOR_VERSION,
        "prompt_version": ARTICLE_PROMPT_VERSION,
        "prompt_hash": prompt_hash,
        "model": client.heavy_model,
        "draft_status": "pending_review",
    }
    rendered = render_frontmatter(metadata, body)
    draft_path = root / ".expertwiki" / "drafts" / f"{concept.slug}.md"
    with FileMutationBatch(root, "compile-draft") as batch:
        batch.write_text(draft_path, rendered)
        with state.transaction():
            state.upsert_draft(
                concept_id=concept.id,
                path=draft_path.relative_to(root).as_posix(),
                content_hash=_hash(rendered),
                source_hashes=source_hashes,
                prompt_hash=prompt_hash,
                model=client.heavy_model,
            )
            state.replace_citations(concept.id, citations)
            state.mark_concept_status(concept.id, "clean")
        batch.commit()
    return "draft", draft_path.relative_to(root).as_posix()


def _merge_analyses(results: Sequence[AnalysisResult]) -> AnalysisResult:
    if not results:
        raise ValueError("Analysis produced no chunk results.")
    quality_rank = {"high": 2, "medium": 1, "low": 0}
    quality = min((result.quality for result in results), key=lambda value: quality_rank[value])
    summaries = _dedupe([result.summary for result in results])
    concepts: dict[str, ExtractedConcept] = {}
    for result in results:
        for item in result.concepts:
            key = _normalize(item.name)
            previous = concepts.get(key)
            if previous is None:
                concepts[key] = item
                continue
            concepts[key] = ExtractedConcept(
                name=previous.name,
                aliases=_dedupe([*previous.aliases, *item.aliases]),
                summary=previous.summary or item.summary,
                tags=_dedupe([*previous.tags, *item.tags]),
                confidence=max(previous.confidence, item.confidence),
                provenance_state=(
                    "merged" if previous.provenance_state != item.provenance_state else previous.provenance_state
                ),
                source_ranges=_dedupe([*previous.source_ranges, *item.source_ranges]),
                contradicted_by=_dedupe([*previous.contradicted_by, *item.contradicted_by]),
            )
    return AnalysisResult(
        summary=" ".join(summaries),
        concepts=list(concepts.values())[:8],
        suggested_topics=_dedupe(
            item for result in results for item in result.suggested_topics
        )[:8],
        named_references=_dedupe(
            item for result in results for item in result.named_references
        )[:12],
        quality=quality,
        language=next((result.language for result in results if result.language), None),
    )


def _concept_payload(concept: ExtractedConcept) -> dict[str, Any]:
    payload = {
        "name": concept.name,
        "aliases": concept.aliases,
        "summary": concept.summary,
        "tags": concept.tags,
        "confidence": concept.confidence,
        "provenance_state": concept.provenance_state,
        "source_ranges": concept.source_ranges,
        "contradicted_by": concept.contradicted_by,
    }
    payload["extraction_hash"] = _hash(
        json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    )
    return payload


def _numbered_chunks(lines: Sequence[str], max_chars: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for index, line in enumerate(lines, start=1):
        numbered = f"{index:6d} | {line}"
        if current and current_size + len(numbered) + 1 > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_size = 0
        current.append(numbered)
        current_size += len(numbered) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks or [""]


def _assemble_source_material(
    sources: Sequence[tuple[str, str, list[str]]],
    max_chars: int,
) -> str:
    if not sources:
        raise ValueError("Cannot compile without source material.")
    per_source = max(2_000, max_chars // len(sources))
    sections: list[str] = []
    for path, text, source_ranges in sources:
        lines = text.splitlines()
        numbered = _select_numbered_lines(lines, source_ranges, per_source)
        sections.append(f"--- SOURCE: {path} ---\n" + "\n".join(numbered))
    material = "\n\n".join(sections)
    if len(material) > max_chars + len(sources) * 200:
        raise ValueError("Source material exceeds the configured compile context budget.")
    return material


def _select_numbered_lines(
    lines: Sequence[str],
    source_ranges: Sequence[str],
    budget: int,
) -> list[str]:
    preferred: set[int] = set()
    for source_range in source_ranges:
        start_raw, _, end_raw = source_range.partition("-")
        if not start_raw.isdigit() or (end_raw and not end_raw.isdigit()):
            continue
        start = max(1, int(start_raw) - 2)
        end = min(len(lines), int(end_raw or start_raw) + 2)
        preferred.update(range(start, end + 1))

    selected: set[int] = set()
    size = 0
    for line_number in [*sorted(preferred), *range(1, len(lines) + 1)]:
        if line_number in selected:
            continue
        value = f"{line_number:6d} | {lines[line_number - 1]}"
        if size + len(value) + 1 > budget:
            continue
        selected.add(line_number)
        size += len(value) + 1

    output: list[str] = []
    previous = 0
    for line_number in sorted(selected):
        if previous and line_number > previous + 1:
            output.append("       | [lines omitted by deterministic context budget]")
        output.append(f"{line_number:6d} | {lines[line_number - 1]}")
        previous = line_number
    if selected and max(selected) < len(lines):
        output.append("       | [lines omitted by deterministic context budget]")
    return output or ["       | [source exceeded context budget]"]


def _parse_and_validate_citations(
    body: str,
    state: StateDB,
    concept_id: int,
) -> list[dict[str, Any]]:
    sources = state.source_concepts_for_concept(concept_id)
    records: dict[str, SourceRecord] = {}
    basename_map: dict[str, list[str]] = {}
    for link in sources:
        record = state.get_source(link.source_path)
        if record is None:
            continue
        records[link.source_path] = record
        basename_map.setdefault(Path(link.source_path).name, []).append(link.source_path)
    citations: list[dict[str, Any]] = []
    paragraphs = re.split(r"\n\s*\n", body)
    for paragraph_index, paragraph in enumerate(paragraphs):
        for marker in re.findall(r"\^\[([^\]]+)\]", paragraph):
            for raw_ref in [part.strip() for part in marker.split(",") if part.strip()]:
                match = re.fullmatch(r"(.+?\.md)(?::(\d+)(?:-(\d+))?)?", raw_ref)
                if not match:
                    raise ValueError(f"Malformed citation: ^[{raw_ref}]")
                raw_path, start_raw, end_raw = match.groups()
                source_path = raw_path.removeprefix("/")
                if source_path not in records:
                    matches = basename_map.get(Path(source_path).name, [])
                    if len(matches) == 1:
                        source_path = matches[0]
                    else:
                        raise ValueError(f"Citation does not reference a contributing source: {raw_path}")
                start = int(start_raw) if start_raw else None
                end = int(end_raw or start_raw) if start_raw else None
                if start is not None:
                    line_count = records[source_path].line_count
                    if start < 1 or end is None or end < start or end > line_count:
                        raise ValueError(
                            f"Citation range is outside {source_path} (1-{line_count}): {start}-{end}"
                        )
                citations.append(
                    {
                        "paragraph_index": paragraph_index,
                        "source_path": source_path,
                        "start_line": start,
                        "end_line": end,
                    }
                )
    return citations


def _resolve_wikilinks(body: str, state: StateDB) -> str:
    def replace(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        concept_id = state.resolve_concept_id(label)
        if concept_id is None:
            return label
        article = state.get_article(concept_id)
        concept = state.get_concept(concept_id)
        if article is None or concept is None:
            return label
        return f"[{concept.name}](/{article['path']})"

    return re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", replace, body)


def _related_page_manifest(state: StateDB, *, exclude_id: int) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for row in state.list_articles():
        concept_id = int(row["concept_id"])
        if concept_id == exclude_id:
            continue
        concept = state.get_concept(concept_id)
        if concept:
            output.append({"title": concept.name, "path": str(row["path"])})
    return output


def _resolve_draft(root: Path, state: StateDB, draft_ref: str) -> Path:
    raw = draft_ref.strip()
    candidates = [root / raw, root / ".expertwiki" / "drafts" / raw]
    if not raw.endswith(".md"):
        candidates.append(root / ".expertwiki" / "drafts" / f"{raw}.md")
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    concept = state.get_concept(raw)
    if concept:
        row = state.get_draft(concept.id)
        if row:
            candidate = root / str(row["path"])
            if candidate.exists():
                return candidate
    raise ValueError(f"Suggested card not found: {draft_ref}")


def _resolve_article(root: Path, state: StateDB, page_ref: str) -> Path:
    raw = page_ref.strip().removeprefix("/")
    candidates = [root / raw, root / "wiki" / raw]
    if not raw.endswith(".md"):
        candidates.extend([path.with_suffix(".md") for path in list(candidates)])
    resolved_root = root.resolve()
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
            relative = resolved.relative_to(resolved_root).as_posix()
        except (FileNotFoundError, ValueError):
            continue
        if state.find_article_by_path(relative) is not None:
            return resolved
    lowered = _normalize(raw.removesuffix(".md").removeprefix("wiki/"))
    for row in state.list_articles():
        concept = state.get_concept(int(row["concept_id"]))
        normalized_path = _normalize(str(row["path"]).removesuffix(".md").removeprefix("wiki/"))
        if normalized_path == lowered or (concept is not None and _normalize(concept.name) == lowered):
            path = root / str(row["path"])
            if path.exists():
                return path
    raise ValueError(f"Published page not found: {page_ref}")


def _resolve_rejected(root: Path, state: StateDB, rejected_ref: str) -> Path:
    raw = rejected_ref.strip().removeprefix("/")
    candidates = [root / raw, root / ".expertwiki" / "rejected" / raw]
    if not raw.endswith(".md"):
        candidates.append(root / ".expertwiki" / "rejected" / f"{raw}.md")
    rejected_root = (root / ".expertwiki" / "rejected").resolve()
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(rejected_root)
        except (FileNotFoundError, ValueError):
            continue
        return resolved
    lowered = _normalize(raw.removesuffix(".md"))
    rejected_dir = root / ".expertwiki" / "rejected"
    if rejected_dir.is_dir():
        for path in sorted(rejected_dir.glob("*.md")):
            candidate = parse_okf_concept(root, path)
            title = str(candidate.metadata.get("title", path.stem))
            if _normalize(path.stem) == lowered or _normalize(title) == lowered:
                return path
    raise ValueError(f"Rejected card not found: {rejected_ref}")


def _draft_concept_id(metadata: dict[str, Any], state: StateDB, path: Path) -> int:
    raw_id = metadata.get("concept_id")
    if raw_id is not None:
        try:
            concept_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid draft concept_id in {path}: {raw_id}") from exc
        concept = state.get_concept(concept_id)
        title = str(metadata.get("title", path.stem))
        if concept is not None and _normalize(concept.name) == _normalize(title):
            return concept_id
    title = str(metadata.get("title", path.stem))
    concept = state.get_concept(title)
    if concept is None:
        concept = state.ensure_concept(title)
    return concept.id


def _source_hashes_from_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    hashes = _json_object(metadata.get("source_hashes", "{}"))
    if hashes:
        return hashes
    return {source.removeprefix("/"): "" for source in _as_string_list(metadata.get("sources", []))}


def _reconcile_missing_drafts(root: Path, state: StateDB) -> None:
    for row in state.list_drafts():
        if not (root / str(row["path"])).exists():
            state.delete_draft(int(row["concept_id"]))


def _import_source_dependencies(
    state: StateDB,
    concept_id: int,
    metadata: dict[str, Any],
) -> None:
    for raw_path in _as_string_list(metadata.get("sources", [])):
        source_path = raw_path.removeprefix("/")
        if state.get_source(source_path) is not None:
            state.import_source_concept(source_path, concept_id)


def _validate_analysis_ranges(analysis: AnalysisResult, line_count: int) -> None:
    for concept in analysis.concepts:
        for source_range in concept.source_ranges:
            start_raw, _, end_raw = source_range.partition("-")
            start = int(start_raw)
            end = int(end_raw or start_raw)
            if start < 1 or end < start or end > line_count:
                raise ValueError(
                    f"Analysis range {source_range} is outside the source (1-{line_count})."
                )


def _source_files(root: Path) -> list[Path]:
    directory = root / "raw" / "sources"
    if not directory.exists():
        return []
    return [
        path
        for path in sorted(directory.rglob("*.md"))
        if path.name not in RESERVED_FILENAMES
    ]


def _page_path(root: Path, entity_type: str, slug: str) -> Path:
    directories = {
        "expert": "wiki/entities/experts",
        "project": "wiki/entities/projects",
        "viewpoint": "wiki/viewpoints",
        "comparison": "wiki/comparisons",
        "synthesis": "wiki/synthesis",
        "topic": "wiki/topics",
    }
    return root / directories.get(entity_type, "wiki/topics") / f"{slug}.md"


def _available_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise ValueError(f"No available path for {path}")


def _require_client(client: LLMClient | None) -> LLMClient:
    resolved = client or client_from_env()
    if resolved is None:
        raise ValueError(
            "AI provider is not configured. Set EXPERTWIKI_OPENAI_BASE_URL, "
            "EXPERTWIKI_FAST_MODEL, and EXPERTWIKI_HEAVY_MODEL."
        )
    return resolved


def _json_object(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items()}
    if not isinstance(value, str) or not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object.")
    return {str(key): str(item) for key, item in parsed.items()}


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _dedupe(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip()
        key = _normalize(clean)
        if clean and key not in seen:
            seen.add(key)
            output.append(clean)
    return output


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
