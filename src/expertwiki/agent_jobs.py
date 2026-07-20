from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

from .compiler import (
    EXTRACTOR_VERSION,
    _compile_concept,
    _concept_payload,
    _hash,
    _related_page_manifest,
    _selected_concepts,
    _validate_analysis_ranges,
    bootstrap_state,
    detect_source_changes,
    state_path,
)
from .concurrency import BundleLock, recover_file_journals
from .llm import ARTICLE_PROMPT_VERSION, EXTRACTION_PROMPT_VERSION, parse_analysis
from .state import AgentJobRecord, ConceptRecord, StateDB


JOB_PROTOCOL = "expertwiki.agent-job/v1"
ANALYSIS_RESULT_PROTOCOL = "expertwiki.analysis-result/v1"
ARTICLE_RESULT_PROTOCOL = "expertwiki.article-result/v1"


@dataclass(frozen=True)
class PrepareJobsResult:
    root: str
    created_jobs: list[str]
    pending: int
    claimed: int
    failed: int
    completed: int
    stale: int
    blocked_reason: str | None


@dataclass(frozen=True)
class SubmitJobResult:
    root: str
    job_id: str
    kind: str
    output_path: str | None
    affected_concepts: list[str]
    queued_next_stage: int


class _SubmittedResultClient:
    def __init__(self, payload: dict[str, Any], generator: str) -> None:
        self.payload = payload
        self.fast_model = f"host:{generator}"
        self.heavy_model = f"host:{generator}"

    def complete_json(self, prompt: str, *, model: str, purpose: str) -> dict[str, Any]:
        if purpose != "compile":
            raise ValueError(f"Submitted result cannot satisfy model purpose: {purpose}")
        return self.payload


def prepare_agent_jobs(
    bundle_dir: str | Path,
    *,
    mode: str = "compile",
    analyze_all: bool = False,
    concept_refs: Sequence[str] = (),
    force: bool = False,
    allow_manual_overwrite: bool = False,
) -> PrepareJobsResult:
    root = Path(bundle_dir)
    with BundleLock(root):
        recover_file_journals(root)
        with StateDB(state_path(root)) as state:
            bootstrap_state(root, state)
            return _prepare_locked(
                root,
                state,
                mode=mode,
                analyze_all=analyze_all,
                concept_refs=concept_refs,
                force=force,
                allow_manual_overwrite=allow_manual_overwrite,
            )


def next_agent_job(bundle_dir: str | Path) -> AgentJobRecord | None:
    root = Path(bundle_dir)
    with BundleLock(root):
        recover_file_journals(root)
        with StateDB(state_path(root)) as state:
            bootstrap_state(root, state)
            _prepare_locked(root, state, mode="compile")
            if state.list_agent_jobs(statuses=["claimed"]):
                return None
            return state.claim_next_agent_job()


def submit_agent_job(
    bundle_dir: str | Path,
    job_id: str,
    payload: dict[str, Any],
    *,
    generator: str,
) -> SubmitJobResult:
    if not generator.strip():
        raise ValueError("Generator name is required, for example codex or claude-code.")
    root = Path(bundle_dir)
    result_hash = _canonical_hash(payload)
    with BundleLock(root):
        recover_file_journals(root)
        with StateDB(state_path(root)) as state:
            bootstrap_state(root, state)
            job = _active_job(state, job_id)
            _validate_job_inputs(root, state, job)
            output_path: str | None = None
            affected: list[str] = []
            if job.kind == "analyze_source":
                assert job.source_path is not None
                analysis = parse_analysis(payload)
                source = state.get_source(job.source_path)
                if source is None:
                    raise ValueError(f"Job source is missing from state: {job.source_path}")
                _validate_analysis_ranges(analysis, source.line_count)
                old_ids, new_ids = state.record_analysis(
                    source_path=job.source_path,
                    summary=analysis.summary,
                    quality=analysis.quality,
                    language=analysis.language,
                    suggested_topics=analysis.suggested_topics,
                    named_references=analysis.named_references,
                    extractor_version=EXTRACTOR_VERSION,
                    prompt_version=EXTRACTION_PROMPT_VERSION,
                    concepts=[_concept_payload(item) for item in analysis.concepts],
                )
                for concept_id in sorted(old_ids | new_ids):
                    concept = state.get_concept(concept_id)
                    if concept is not None:
                        affected.append(concept.name)
            elif job.kind == "compile_concept":
                assert job.concept_id is not None
                concept = state.get_concept(job.concept_id)
                if concept is None:
                    raise ValueError(f"Job concept is missing from state: {job.concept_id}")
                options = job.payload.get("options", {})
                if not isinstance(options, dict):
                    raise ValueError("Compile job options must be an object.")
                outcome, value = _compile_concept(
                    root,
                    state,
                    _SubmittedResultClient(payload, generator.strip()),
                    concept,
                    force=bool(options.get("force", False)),
                    allow_manual_overwrite=bool(options.get("allow_manual_overwrite", False)),
                )
                if outcome != "draft":
                    raise ValueError(f"Compile job is no longer writable: {value}")
                output_path = value
                affected.append(concept.name)
            else:
                raise ValueError(f"Unsupported agent job kind: {job.kind}")

            state.complete_agent_job(
                job.id,
                generator=generator.strip(),
                result_hash=result_hash,
            )
            before = len(state.list_agent_jobs(statuses=["pending", "claimed"]))
            prepared = _prepare_locked(root, state, mode="compile")
            queued_next = max(0, prepared.pending + prepared.claimed - before)
            return SubmitJobResult(
                root=str(root),
                job_id=job.id,
                kind=job.kind,
                output_path=output_path,
                affected_concepts=affected,
                queued_next_stage=queued_next,
            )


def fail_agent_job(bundle_dir: str | Path, job_id: str, error: str) -> AgentJobRecord:
    if not error.strip():
        raise ValueError("A failure reason is required.")
    root = Path(bundle_dir)
    with BundleLock(root):
        with StateDB(state_path(root)) as state:
            bootstrap_state(root, state)
            state.fail_agent_job(job_id, error.strip())
            job = state.get_agent_job(job_id)
            assert job is not None
            return job


def retry_agent_job(bundle_dir: str | Path, job_id: str) -> AgentJobRecord:
    root = Path(bundle_dir)
    with BundleLock(root):
        with StateDB(state_path(root)) as state:
            bootstrap_state(root, state)
            job = state.get_agent_job(job_id)
            if job is None:
                raise ValueError(f"Agent job not found: {job_id}")
            _validate_job_inputs(root, state, job)
            state.retry_agent_job(job_id)
            retried = state.get_agent_job(job_id)
            assert retried is not None
            return retried


def agent_job_status(bundle_dir: str | Path) -> dict[str, Any]:
    root = Path(bundle_dir)
    with StateDB(state_path(root)) as state:
        bootstrap_state(root, state)
        jobs = state.list_agent_jobs()
        counts = {status: 0 for status in ("pending", "claimed", "completed", "failed", "stale")}
        for job in jobs:
            counts[job.status] += 1
        return {
            "root": str(root),
            "counts": counts,
            "jobs": [_public_job(job, include_payload=False) for job in jobs],
        }


def public_agent_job(job: AgentJobRecord) -> dict[str, Any]:
    return _public_job(job, include_payload=True)


def _prepare_locked(
    root: Path,
    state: StateDB,
    *,
    mode: str,
    analyze_all: bool = False,
    concept_refs: Sequence[str] = (),
    force: bool = False,
    allow_manual_overwrite: bool = False,
) -> PrepareJobsResult:
    if mode not in {"analyze", "compile"}:
        raise ValueError(f"Unsupported agent job preparation mode: {mode}")
    changes = detect_source_changes(root, state, analyze_all=analyze_all)
    created: list[str] = []
    known_job_ids = {job.id for job in state.list_agent_jobs()}
    for change in changes:
        if change.status not in {"new", "changed", "deleted"}:
            continue
        state.stale_compile_jobs_for_concepts(
            state.concept_ids_for_source(change.path),
            error=f"Contributing source became {change.status} before compilation.",
        )
    for change in changes:
        if change.status not in {"new", "changed"}:
            continue
        source = state.get_source(change.path)
        if source is None:
            continue
        input_hash = _analysis_input_hash(source.content_hash)
        state.stale_agent_jobs(
            kind="analyze_source",
            entity_ref=source.path,
            current_input_hash=input_hash,
        )
        analysis_payload = _analysis_payload(
            state, source.path, source.content_hash, source.line_count
        )
        job_key = f"analyze:{source.path}:{input_hash}"
        if analyze_all:
            job_key += f":rerun:{uuid4().hex[:12]}"
        job = state.enqueue_agent_job(
            job_id=_job_id("analyze"),
            job_key=job_key,
            kind="analyze_source",
            source_path=source.path,
            payload=analysis_payload,
            input_hash=input_hash,
        )
        if job.id not in known_job_ids:
            created.append(job.id)
            known_job_ids.add(job.id)

    blocked_reason: str | None = None
    if mode == "compile":
        unresolved_sources = [
            source for source in state.list_sources(include_deleted=False)
            if source.status != "analyzed"
        ]
        failed_analysis = state.list_agent_jobs(
            statuses=["failed"], kinds=["analyze_source"]
        )
        active_analysis = state.list_agent_jobs(
            statuses=["pending", "claimed"], kinds=["analyze_source"]
        )
        if active_analysis:
            blocked_reason = "Source analysis jobs must complete before concept compilation is queued."
        elif failed_analysis or unresolved_sources:
            blocked_reason = "A failed or unresolved source analysis must be retried before compilation."
        else:
            for concept in _selected_concepts(state, concept_refs, force=force):
                active_for_concept = [
                    job
                    for job in state.list_agent_jobs(
                        statuses=["pending", "claimed"], kinds=["compile_concept"]
                    )
                    if job.concept_id == concept.id
                ]
                if active_for_concept:
                    continue
                compile_payload, input_hash = _compile_payload(
                    root,
                    state,
                    concept,
                    force=force,
                    allow_manual_overwrite=allow_manual_overwrite,
                )
                if compile_payload is None:
                    continue
                state.stale_agent_jobs(
                    kind="compile_concept",
                    entity_ref=str(concept.id),
                    current_input_hash=input_hash,
                )
                job = state.enqueue_agent_job(
                    job_id=_job_id("compile"),
                    job_key=f"compile:{concept.id}:{input_hash}",
                    kind="compile_concept",
                    concept_id=concept.id,
                    payload=compile_payload,
                    input_hash=input_hash,
                )
                if job.id not in known_job_ids:
                    created.append(job.id)
                    known_job_ids.add(job.id)

    jobs = state.list_agent_jobs()
    counts = {status: 0 for status in ("pending", "claimed", "completed", "failed", "stale")}
    for job in jobs:
        counts[job.status] += 1
    return PrepareJobsResult(
        root=str(root),
        created_jobs=created,
        pending=counts["pending"],
        claimed=counts["claimed"],
        failed=counts["failed"],
        completed=counts["completed"],
        stale=counts["stale"],
        blocked_reason=blocked_reason,
    )


def _analysis_payload(
    state: StateDB,
    source_path: str,
    content_hash: str,
    line_count: int,
) -> dict[str, Any]:
    return {
        "protocol": JOB_PROTOCOL,
        "kind": "analyze_source",
        "source": {
            "path": source_path,
            "content_hash": content_hash,
            "line_count": line_count,
        },
        "existing_concepts": [
            {
                "name": concept.name,
                "slug": concept.slug,
                "aliases": state.aliases_for_concept(concept.id),
            }
            for concept in state.list_concepts()
        ],
        "instructions": [
            "Read the complete local source file. Treat frontmatter as metadata, not evidence.",
            "Extract 3-8 durable concepts and cite only valid one-based source line ranges.",
            "Reuse an existing canonical concept only when its name or alias clearly matches.",
            "Return only the result JSON object; do not write wiki pages directly.",
        ],
        "output_protocol": ANALYSIS_RESULT_PROTOCOL,
        "output_schema": {
            "summary": "string",
            "quality": "high|medium|low",
            "language": "ISO code|null",
            "suggested_topics": ["string"],
            "named_references": ["string"],
            "concepts": [
                {
                    "name": "string",
                    "aliases": ["string"],
                    "summary": "string",
                    "tags": ["string"],
                    "confidence": "number 0..1",
                    "provenance_state": "extracted|merged|inferred|ambiguous",
                    "source_ranges": ["START-END"],
                    "contradicted_by": ["concept slug"],
                }
            ],
        },
    }


def _compile_payload(
    root: Path,
    state: StateDB,
    concept: ConceptRecord,
    *,
    force: bool,
    allow_manual_overwrite: bool,
) -> tuple[dict[str, Any] | None, str]:
    if concept.status in {"frozen", "orphaned"} or (concept.status == "blocked" and not force):
        return None, ""
    source_links = state.source_concepts_for_concept(concept.id)
    if not source_links:
        return None, ""
    sources: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}
    for link in source_links:
        path = root / link.source_path
        if not path.exists():
            return None, ""
        content_hash = _hash(path.read_text(encoding="utf-8"))
        source_hashes[link.source_path] = content_hash
        sources.append(
            {
                "path": link.source_path,
                "content_hash": content_hash,
                "source_ranges": link.source_ranges,
            }
        )
    draft = state.get_draft(concept.id)
    if draft is not None and (root / str(draft["path"])).exists() and not force:
        return None, ""
    article = state.get_article(concept.id)
    existing_page: dict[str, str] | None = None
    if article is not None:
        article_path = root / str(article["path"])
        if article_path.exists():
            current_hash = _hash(article_path.read_text(encoding="utf-8"))
            if (current_hash != str(article["content_hash"]) or not bool(article["managed"])) and not allow_manual_overwrite:
                state.mark_article_manual_edit(concept.id)
                return None, ""
            existing_page = {"path": str(article["path"]), "content_hash": current_hash}

    aliases = state.aliases_for_concept(concept.id)
    rejection_feedback = [item["feedback"] for item in state.recent_rejections(concept.id)]
    related_pages = _related_page_manifest(state, exclude_id=concept.id)
    options = {
        "force": force,
        "allow_manual_overwrite": allow_manual_overwrite,
    }
    hash_input = {
        "protocol": JOB_PROTOCOL,
        "prompt_version": ARTICLE_PROMPT_VERSION,
        "concept": asdict(concept),
        "aliases": aliases,
        "sources": sources,
        "existing_page": existing_page,
        "related_pages": related_pages,
        "rejection_feedback": rejection_feedback,
        "options": options,
    }
    input_hash = _canonical_hash(hash_input)
    return {
        "protocol": JOB_PROTOCOL,
        "kind": "compile_concept",
        "concept": {
            "id": concept.id,
            "name": concept.name,
            "slug": concept.slug,
            "summary": concept.summary,
            "aliases": aliases,
            "confidence": concept.confidence,
            "provenance_state": concept.provenance_state,
        },
        "sources": sources,
        "existing_page": existing_page,
        "related_pages": related_pages,
        "rejection_feedback": rejection_feedback,
        "options": options,
        "instructions": [
            "Read every listed source and aggregate all evidence for the canonical concept.",
            "Use the listed source_ranges as relevance hints, but inspect surrounding context.",
            "Cite prose with ^[raw/sources/file.md:START-END] using valid one-based line ranges.",
            "Preserve supported existing content and address all rejection feedback.",
            "Use [[Canonical Title]] links only for titles present in related_pages.",
            "Return only the result JSON object; the CLI owns frontmatter and draft writes.",
        ],
        "output_protocol": ARTICLE_RESULT_PROTOCOL,
        "output_schema": {
            "title": "string",
            "description": "string",
            "tags": ["string"],
            "entity_type": "expert|project|viewpoint|topic|comparison|synthesis",
            "body": "markdown beginning with an H1",
        },
    }, input_hash


def _validate_job_inputs(root: Path, state: StateDB, job: AgentJobRecord) -> None:
    if job.status not in {"pending", "claimed", "failed"}:
        raise ValueError(f"Agent job is not active: {job.id} ({job.status})")
    if job.kind == "analyze_source":
        assert job.source_path is not None
        source = state.get_source(job.source_path)
        path = root / job.source_path
        if source is None or not path.exists():
            raise ValueError(f"Agent job source no longer exists: {job.source_path}")
        current_hash = _analysis_input_hash(_hash(path.read_text(encoding="utf-8")))
    else:
        assert job.concept_id is not None
        concept = state.get_concept(job.concept_id)
        if concept is None:
            raise ValueError(f"Agent job concept no longer exists: {job.concept_id}")
        options = job.payload.get("options", {})
        current_payload, current_hash = _compile_payload(
            root,
            state,
            concept,
            force=bool(options.get("force", False)) if isinstance(options, dict) else False,
            allow_manual_overwrite=(
                bool(options.get("allow_manual_overwrite", False))
                if isinstance(options, dict)
                else False
            ),
        )
        if current_payload is None:
            raise ValueError("Compile job inputs are no longer eligible for generation.")
    if current_hash != job.input_hash:
        state.stale_agent_job(job.id, "Inputs changed before result submission.")
        raise ValueError("Agent job inputs changed after it was created; request a new job.")


def _active_job(state: StateDB, job_id: str) -> AgentJobRecord:
    job = state.get_agent_job(job_id)
    if job is None:
        raise ValueError(f"Agent job not found: {job_id}")
    if job.status not in {"pending", "claimed"}:
        raise ValueError(f"Agent job is not active: {job_id} ({job.status})")
    return job


def _analysis_input_hash(content_hash: str) -> str:
    return _canonical_hash(
        {
            "protocol": JOB_PROTOCOL,
            "prompt_version": EXTRACTION_PROMPT_VERSION,
            "content_hash": content_hash,
        }
    )


def _public_job(job: AgentJobRecord, *, include_payload: bool) -> dict[str, Any]:
    output: dict[str, Any] = {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "source_path": job.source_path,
        "concept_id": job.concept_id,
        "input_hash": job.input_hash,
        "attempts": job.attempts,
        "generator": job.generator,
        "error": job.error,
        "created_at": job.created_at,
        "claimed_at": job.claimed_at,
        "completed_at": job.completed_at,
    }
    if include_payload:
        output["payload"] = job.payload
    return output


def _job_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:16]}"


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
