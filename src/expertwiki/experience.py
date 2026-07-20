from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from .authoring import append_log, bundle_status, ingest_source, init_bundle, query_bundle, rebuild_indexes
from .agent_jobs import prepare_agent_jobs
from .compiler import (
    approve_draft,
    compile_bundle,
    compiler_stats,
    list_compiler_drafts,
    reject_draft,
)
from .llm import LLMClient, client_from_env
from .okf import parse_okf_concept, render_frontmatter
from .store import KnowledgeStore


@dataclass(frozen=True)
class StartResult:
    root: str
    initialized: bool
    ok: bool
    source_count: int
    page_count: int
    draft_count: int
    next_actions: list[str]


@dataclass(frozen=True)
class AddResult:
    root: str
    source_path: str
    draft_paths: list[str]
    ai_enabled: bool
    execution_mode: str
    queued_job_count: int
    message: str


@dataclass(frozen=True)
class ReviewResult:
    root: str
    drafts: list[dict[str, Any]]


@dataclass(frozen=True)
class ApproveResult:
    root: str
    draft_path: str
    page_path: str
    title: str


@dataclass(frozen=True)
class RejectResult:
    root: str
    draft_path: str
    rejected_path: str
    title: str
    feedback: str


@dataclass(frozen=True)
class AskResult:
    query: str
    answer: str
    used_pages: list[dict[str, Any]]
    ai_enabled: bool


@dataclass(frozen=True)
class DoctorResult:
    root: str
    ok: bool
    source_count: int
    page_count: int
    draft_count: int
    issues: list[str]
    next_actions: list[str]


@dataclass(frozen=True)
class SuggestedCard:
    title: str
    description: str
    body: str
    tags: list[str]
    entity_type: str = "topic"


def start_experience(bundle_dir: str | Path, *, title: str | None = None) -> StartResult:
    root = Path(bundle_dir)
    initialized = False
    if not root.exists():
        init_bundle(root, title=title)
        initialized = True

    status = bundle_status(root)
    compiler_stats(root)
    return StartResult(
        root=str(root),
        initialized=initialized,
        ok=status.ok,
        source_count=status.concept_counts.get("raw_source", 0),
        page_count=status.concept_counts.get("wiki_page", 0),
        draft_count=len(list_drafts(root)),
        next_actions=_experience_next_actions(root, status.next_actions),
    )


def add_material(
    bundle_dir: str | Path,
    source: str,
    *,
    title: str | None = None,
    publisher: str = "Unknown",
    slug: str | None = None,
    backend: str = "host",
) -> AddResult:
    root = Path(bundle_dir)
    result = ingest_source(root, source, title=title, publisher=publisher, slug=slug)
    if backend == "host":
        prepared = prepare_agent_jobs(root, mode="compile")
        return AddResult(
            root=str(root),
            source_path=result.source_path,
            draft_paths=[],
            ai_enabled=False,
            execution_mode="host",
            queued_job_count=len(prepared.created_jobs),
            message=(
                f"Saved source material and queued {len(prepared.created_jobs)} host-AI job(s). "
                "The invoking AI must process 'expertwiki jobs next' until the queue is empty."
            ),
        )

    if backend != "api":
        raise ValueError(f"Unsupported generation backend: {backend}")
    provider = client_from_env()
    if provider is None:
        raise ValueError(
            "API backend is not configured. Set EXPERTWIKI_OPENAI_BASE_URL, "
            "EXPERTWIKI_FAST_MODEL, and EXPERTWIKI_HEAVY_MODEL."
        )

    compile_result = compile_bundle(root, client=provider)
    draft_paths = compile_result.draft_paths
    if compile_result.errors:
        message = (
            f"Saved source material and created {len(draft_paths)} suggested card(s), "
            f"but {len(compile_result.errors)} compiler error(s) need attention."
        )
    else:
        message = f"Saved source material and created {len(draft_paths)} suggested card(s)."
    return AddResult(
        root=str(root),
        source_path=result.source_path,
        draft_paths=draft_paths,
        ai_enabled=True,
        execution_mode="api",
        queued_job_count=0,
        message=message,
    )


def create_suggested_card(
    bundle_dir: str | Path,
    suggestion: SuggestedCard,
    *,
    sources: list[str],
) -> str:
    root = Path(bundle_dir)
    drafts_dir = _drafts_dir(root)
    drafts_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(suggestion.title)
    path = _next_available(drafts_dir / f"{slug}.md")
    metadata = {
        "type": "draft_page",
        "entity_type": suggestion.entity_type,
        "title": suggestion.title,
        "description": suggestion.description,
        "tags": suggestion.tags,
        "sources": sources,
        "status": "draft",
        "quality": "unreviewed",
        "license": "unknown",
        "source_updated_at": "unknown",
        "last_reviewed_at": "unknown",
        "updated_at": _today(),
        "draft_status": "pending_review",
        "created_at": _timestamp(),
    }
    body = suggestion.body.strip() or _default_card_body(suggestion.title, sources)
    path.write_text(render_frontmatter(metadata, body), encoding="utf-8")
    return path.relative_to(root).as_posix()


def list_drafts(bundle_dir: str | Path) -> list[dict[str, Any]]:
    root = Path(bundle_dir)
    if (root / ".expertwiki" / "state.sqlite").exists():
        managed = list_compiler_drafts(root)
        managed_paths = {str(item["path"]) for item in managed}
    else:
        managed = []
        managed_paths = set()
    drafts_dir = _drafts_dir(root)
    if not drafts_dir.exists():
        return managed

    drafts: list[dict[str, Any]] = list(managed)
    for path in sorted(drafts_dir.glob("*.md")):
        relative = path.relative_to(root).as_posix()
        if relative in managed_paths:
            continue
        concept = parse_okf_concept(root, path)
        metadata = concept.metadata
        drafts.append(
            {
                "path": path.relative_to(root).as_posix(),
                "title": str(metadata.get("title", path.stem)),
                "description": str(metadata.get("description", "")),
                "entity_type": str(metadata.get("entity_type", "topic")),
                "sources": metadata.get("sources", []),
                "created_at": str(metadata.get("created_at", "")),
            }
        )
    return drafts


def review_suggestions(bundle_dir: str | Path) -> ReviewResult:
    root = Path(bundle_dir)
    return ReviewResult(root=str(root), drafts=list_drafts(root))


def approve_suggestion(
    bundle_dir: str | Path,
    draft_ref: str,
    *,
    force: bool = False,
) -> ApproveResult:
    root = Path(bundle_dir)
    draft_path = _resolve_draft(root, draft_ref)
    concept = parse_okf_concept(root, draft_path)
    if concept.metadata.get("concept_id") is not None:
        result = approve_draft(root, draft_ref, force=force)
        return ApproveResult(
            root=result.root,
            draft_path=result.draft_path,
            page_path=result.page_path,
            title=result.title,
        )
    metadata = dict(concept.metadata)
    title = str(metadata.get("title", draft_path.stem))
    entity_type = str(metadata.get("entity_type", "topic"))
    page_dir = _page_dir(root, entity_type)
    page_dir.mkdir(parents=True, exist_ok=True)
    page_path = _next_available(page_dir / f"{_slugify(title)}.md")

    metadata["type"] = "wiki_page"
    metadata["status"] = "published"
    metadata["updated_at"] = _today()
    metadata["last_reviewed_at"] = _today()
    metadata.pop("draft_status", None)
    metadata["approved_at"] = _timestamp()

    page_path.write_text(render_frontmatter(metadata, concept.body), encoding="utf-8")
    draft_path.unlink()
    rebuild_indexes(root)
    append_log(root, "approve", f"Approved {title} ({page_path.relative_to(root).as_posix()})")
    return ApproveResult(
        root=str(root),
        draft_path=draft_path.relative_to(root).as_posix(),
        page_path=page_path.relative_to(root).as_posix(),
        title=title,
    )


def reject_suggestion(bundle_dir: str | Path, draft_ref: str, *, feedback: str) -> RejectResult:
    if not feedback.strip():
        raise ValueError("Rejection feedback is required.")

    root = Path(bundle_dir)
    draft_path = _resolve_draft(root, draft_ref)
    concept = parse_okf_concept(root, draft_path)
    if concept.metadata.get("concept_id") is not None:
        result = reject_draft(root, draft_ref, feedback=feedback)
        return RejectResult(
            root=result.root,
            draft_path=result.draft_path,
            rejected_path=result.rejected_path,
            title=result.title,
            feedback=result.feedback,
        )
    metadata = dict(concept.metadata)
    title = str(metadata.get("title", draft_path.stem))
    metadata["draft_status"] = "rejected"
    metadata["rejection_feedback"] = feedback.strip()
    metadata["rejected_at"] = _timestamp()

    rejected_dir = root / ".expertwiki" / "rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    rejected_path = _next_available(rejected_dir / draft_path.name)
    rejected_path.write_text(render_frontmatter(metadata, concept.body), encoding="utf-8")
    draft_path.unlink()
    append_log(root, "reject", f"Rejected {title}: {feedback.strip()}")
    return RejectResult(
        root=str(root),
        draft_path=draft_path.relative_to(root).as_posix(),
        rejected_path=rejected_path.relative_to(root).as_posix(),
        title=title,
        feedback=feedback.strip(),
    )


def ask_wiki(
    bundle_dir: str | Path,
    query: str,
    *,
    limit: int = 5,
    backend: str = "host",
) -> AskResult:
    if backend == "host":
        result = query_bundle(bundle_dir, query, limit=limit)
        pages = [item["page"] for item in result.results]
        if not pages:
            answer = "No approved card in this ExpertWiki currently supports that question."
        else:
            answer = "Use the invoking host AI to answer from these approved cards."
        return AskResult(query=query, answer=answer, used_pages=pages, ai_enabled=False)

    if backend != "api":
        raise ValueError(f"Unsupported answer backend: {backend}")
    provider = client_from_env()
    if provider is None:
        raise ValueError(
            "API backend is not configured. Set EXPERTWIKI_OPENAI_BASE_URL, "
            "EXPERTWIKI_FAST_MODEL, and EXPERTWIKI_HEAVY_MODEL."
        )

    store = KnowledgeStore(bundle_dir)
    pages = _route_approved_pages(store, query, provider, limit=limit)
    if not pages:
        return AskResult(
            query=query,
            answer="No approved card in this ExpertWiki currently supports that question.",
            used_pages=[],
            ai_enabled=True,
        )

    answer = _request_grounded_answer(query, pages, provider)
    append_log(bundle_dir, "ask", f"{query!r} -> {len(pages)} approved card(s)")
    return AskResult(query=query, answer=answer, used_pages=pages, ai_enabled=True)


def doctor_experience(bundle_dir: str | Path) -> DoctorResult:
    root = Path(bundle_dir)
    status = bundle_status(root)
    drafts = list_drafts(root)
    issues: list[str] = []
    compiler = compiler_stats(root)
    if drafts:
        issues.append(f"{len(drafts)} suggested card(s) need review.")
    if compiler["frozen_concepts"]:
        issues.append(f"{compiler['frozen_concepts']} concept(s) are frozen after source deletion.")
    if compiler["orphaned_concepts"]:
        issues.append(f"{compiler['orphaned_concepts']} concept(s) no longer have an active source.")
    if compiler["failed_agent_jobs"]:
        issues.append(f"{compiler['failed_agent_jobs']} host-AI job(s) failed and need retry or repair.")
    return DoctorResult(
        root=str(root),
        ok=status.ok and not issues,
        source_count=status.concept_counts.get("raw_source", 0),
        page_count=status.concept_counts.get("wiki_page", 0),
        draft_count=len(drafts),
        issues=issues,
        next_actions=_experience_next_actions(root, status.next_actions),
    )


def _experience_next_actions(root: Path, status_actions: list[str]) -> list[str]:
    drafts = list_drafts(root)
    if drafts:
        return ["Review suggested cards with `expertwiki review`."]
    compiler = compiler_stats(root)
    if compiler["pending_agent_jobs"]:
        return ["Continue host-AI generation with `expertwiki jobs next --json`."]
    if compiler["failed_agent_jobs"]:
        return ["Inspect failed host-AI work with `expertwiki jobs status --json`."]
    return status_actions


def _route_approved_pages(
    store: KnowledgeStore,
    query: str,
    provider: LLMClient,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    manifest = [
        {
            "id": page.id,
            "title": page.title,
            "description": page.description,
            "tags": page.tags,
            "entity_type": page.entity_type,
        }
        for page in sorted(store.pages.values(), key=lambda item: item.id)
    ]
    prompt = (
        "Route this question to 1-5 approved ExpertWiki pages. Return JSON only as "
        '{"page_ids":["..."]}. Select only ids from the manifest. Return an empty list '
        "when no page supports the question.\n\n"
        f"Question: {query}\n\nManifest:\n"
        f"{json.dumps(manifest, ensure_ascii=False, separators=(',', ':'))}"
    )
    payload = provider.complete_json(prompt, model=provider.fast_model, purpose="query-route")
    raw_ids = payload.get("page_ids")
    if not isinstance(raw_ids, list) or any(not isinstance(value, str) for value in raw_ids):
        raise ValueError("Query router response must include a page_ids string list.")
    pages: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page_id in raw_ids:
        if page_id in seen:
            continue
        page = store.get_page(page_id)
        if page is None:
            raise ValueError(f"Query router selected an unknown approved page: {page_id}")
        seen.add(page_id)
        pages.append(page)
        if len(pages) >= min(limit, 5):
            break
    return pages


def _request_grounded_answer(
    query: str,
    pages: list[dict[str, Any]],
    provider: LLMClient,
) -> str:
    context = "\n\n---\n\n".join(
        f"# {page['title']}\n\n{page['body'][:6000]}" for page in pages[:5]
    )
    prompt = (
        "Answer the user question using only these approved ExpertWiki cards. "
        "If the cards do not support an answer, say so. Return JSON only with shape: "
        '{"answer":"markdown answer"}.\n\n'
        f"Question: {query}\n\nApproved cards:\n{context}"
    )
    payload = provider.complete_json(prompt, model=provider.heavy_model, purpose="answer")
    answer = payload.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("AI response did not include an answer.")
    return answer.strip()


def _resolve_draft(root: Path, draft_ref: str) -> Path:
    raw = draft_ref.strip()
    candidates = [
        root / raw,
        _drafts_dir(root) / raw,
        _drafts_dir(root) / f"{raw}.md",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    lowered = raw.casefold()
    for draft in list_drafts(root):
        if draft["title"].casefold() == lowered or Path(draft["path"]).stem.casefold() == lowered:
            return root / draft["path"]
    raise ValueError(f"Suggested card not found: {draft_ref}")


def _drafts_dir(root: Path) -> Path:
    return root / ".expertwiki" / "drafts"


def _page_dir(root: Path, entity_type: str) -> Path:
    if entity_type == "expert":
        return root / "wiki" / "entities" / "experts"
    if entity_type == "project":
        return root / "wiki" / "entities" / "projects"
    if entity_type == "viewpoint":
        return root / "wiki" / "viewpoints"
    if entity_type == "comparison":
        return root / "wiki" / "comparisons"
    if entity_type == "synthesis":
        return root / "wiki" / "synthesis"
    return root / "wiki" / "topics"


def _default_card_body(title: str, sources: list[str]) -> str:
    source_lines = "\n".join(f"- [{Path(source).stem}]({source})" for source in sources)
    return f"""# {title}

## Context

TODO: Review the source material and record the reusable context.

## Facts

TODO: Record source-backed facts.

## Confidence

TODO: Explain whether this card is single_case, multiple_confirmed, verified, stale, or disputed.

## Sources

{source_lines}
"""


def _next_available(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise ValueError(f"No available path for {path}")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "card"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
