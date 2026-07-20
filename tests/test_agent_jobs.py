from __future__ import annotations

from pathlib import Path

import pytest

from expertwiki.agent_jobs import (
    agent_job_status,
    fail_agent_job,
    next_agent_job,
    prepare_agent_jobs,
    retry_agent_job,
    submit_agent_job,
)
from expertwiki.authoring import ingest_source, init_bundle
from expertwiki.compiler import list_compiler_drafts


def test_host_ai_jobs_analyze_then_compile_to_review_draft(tmp_path: Path) -> None:
    bundle = _bundle_with_source(tmp_path)

    prepared = prepare_agent_jobs(bundle)
    analysis_job = next_agent_job(bundle)

    assert len(prepared.created_jobs) == 1
    assert analysis_job is not None
    assert analysis_job.kind == "analyze_source"
    assert analysis_job.payload["source"]["path"] == "raw/sources/note.md"

    analyzed = submit_agent_job(
        bundle,
        analysis_job.id,
        _analysis_result(),
        generator="codex",
    )
    compile_job = next_agent_job(bundle)

    assert analyzed.affected_concepts == ["Shared Compiler"]
    assert compile_job is not None
    assert compile_job.kind == "compile_concept"
    assert compile_job.payload["sources"][0]["path"] == "raw/sources/note.md"

    compiled = submit_agent_job(
        bundle,
        compile_job.id,
        _article_result(),
        generator="codex",
    )

    assert compiled.output_path == ".expertwiki/drafts/shared-compiler.md"
    assert len(list_compiler_drafts(bundle)) == 1
    assert not (bundle / "wiki" / "topics" / "shared-compiler.md").exists()
    assert agent_job_status(bundle)["counts"]["completed"] == 2


def test_changed_source_invalidates_claimed_analysis_result(tmp_path: Path) -> None:
    bundle = _bundle_with_source(tmp_path)
    job = next_agent_job(bundle)
    assert job is not None
    source = bundle / "raw" / "sources" / "note.md"
    source.write_text(source.read_text(encoding="utf-8") + "\nChanged after claim.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="inputs changed"):
        submit_agent_job(bundle, job.id, _analysis_result(), generator="codex")

    replacement = next_agent_job(bundle)
    assert replacement is not None
    assert replacement.id != job.id
    statuses = agent_job_status(bundle)["counts"]
    assert statuses["stale"] == 1
    assert statuses["claimed"] == 1


def test_changed_source_stales_pending_compile_before_next_claim(tmp_path: Path) -> None:
    bundle = _bundle_with_source(tmp_path)
    analysis_job = next_agent_job(bundle)
    assert analysis_job is not None
    submit_agent_job(bundle, analysis_job.id, _analysis_result(), generator="codex")
    source = bundle / "raw" / "sources" / "note.md"
    source.write_text(
        source.read_text(encoding="utf-8") + "\nA new constraint changes the evidence.\n",
        encoding="utf-8",
    )

    next_job = next_agent_job(bundle)

    assert next_job is not None
    assert next_job.kind == "analyze_source"
    statuses = agent_job_status(bundle)["counts"]
    assert statuses["stale"] == 1
    assert statuses["claimed"] == 1


def test_failed_host_job_requires_explicit_retry(tmp_path: Path) -> None:
    bundle = _bundle_with_source(tmp_path)
    job = next_agent_job(bundle)
    assert job is not None

    failed = fail_agent_job(bundle, job.id, "Host context window exhausted.")
    assert failed.status == "failed"
    assert next_agent_job(bundle) is None

    retried = retry_agent_job(bundle, job.id)
    assert retried.status == "pending"
    claimed = next_agent_job(bundle)
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.attempts == 2


def _bundle_with_source(tmp_path: Path) -> Path:
    bundle = tmp_path / "wiki"
    init_bundle(bundle, title="Host AI Wiki")
    source = tmp_path / "note.md"
    source.write_text(
        "# Note\n\nA shared compiler aggregates every contributing source into one concept page.\n"
        "It preserves source citations and requires human review.\n",
        encoding="utf-8",
    )
    ingest_source(bundle, str(source), publisher="Tester", slug="note")
    return bundle


def _analysis_result() -> dict[str, object]:
    return {
        "summary": "The source describes a review-gated shared compiler.",
        "quality": "high",
        "language": "en",
        "suggested_topics": ["knowledge compiler"],
        "named_references": [],
        "concepts": [
            {
                "name": "Shared Compiler",
                "aliases": ["shared compiler"],
                "summary": "Aggregates contributing sources into a cited concept page.",
                "tags": ["compiler", "knowledge"],
                "confidence": 0.9,
                "provenance_state": "extracted",
                "source_ranges": ["3-4"],
                "contradicted_by": [],
            }
        ],
    }


def _article_result() -> dict[str, object]:
    return {
        "title": "Shared Compiler",
        "description": "A compiler that aggregates source-backed knowledge.",
        "tags": ["compiler", "knowledge"],
        "entity_type": "topic",
        "body": """# Shared Compiler

## Context

A shared compiler combines all contributing evidence. ^[raw/sources/note.md:3-3]

## Facts

It preserves citations and requires human review. ^[raw/sources/note.md:4-4]

## Confidence

single_case: supported by one source.

## Sources

- [note](/raw/sources/note.md)
""",
    }
