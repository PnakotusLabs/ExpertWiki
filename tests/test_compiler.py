from __future__ import annotations

from pathlib import Path
from typing import Any

from expertwiki.authoring import ingest_source, init_bundle
from expertwiki.compiler import (
    _assemble_source_material,
    approve_draft,
    compile_bundle,
    compiler_stats,
    reject_draft,
    state_path,
)
from expertwiki.state import StateDB


class FakeLLM:
    fast_model = "fake-fast"
    heavy_model = "fake-heavy"

    def __init__(self) -> None:
        self.analysis_prompts: list[str] = []
        self.compile_prompts: list[str] = []

    def complete_json(self, prompt: str, *, model: str, purpose: str) -> dict[str, Any]:
        if purpose == "analysis":
            self.analysis_prompts.append(prompt)
            return {
                "summary": "The source explains shared incremental compilation.",
                "quality": "high",
                "language": "en",
                "suggested_topics": ["Shared Concept"],
                "named_references": [],
                "concepts": [
                    {
                        "name": "Shared Concept",
                        "aliases": ["shared compiler"],
                        "summary": "A concept supported by multiple sources.",
                        "tags": ["compiler", "knowledge"],
                        "confidence": 0.9,
                        "provenance_state": "extracted",
                        "source_ranges": ["1-3"],
                        "contradicted_by": [],
                    }
                ],
            }
        if purpose == "compile":
            self.compile_prompts.append(prompt)
            return {
                "title": "Shared Concept",
                "description": "A source-backed shared concept.",
                "tags": ["compiler", "knowledge"],
                "entity_type": "topic",
                "body": (
                    "# Shared Concept\n\n"
                    "## Context\n\n"
                    "This concept is compiled from preserved source material. "
                    "^[raw/sources/source-a.md:1-3]\n\n"
                    "## Facts\n\n"
                    "The compiler aggregates every active contributor. "
                    "^[raw/sources/source-a.md:1-3]\n\n"
                    "## Confidence\n\n"
                    "The claim is directly extracted.\n\n"
                    "## Sources\n\n"
                    "- [Source A](/raw/sources/source-a.md)"
                ),
            }
        raise AssertionError(f"Unexpected purpose: {purpose}")


class BadCitationLLM(FakeLLM):
    def complete_json(self, prompt: str, *, model: str, purpose: str) -> dict[str, Any]:
        payload = super().complete_json(prompt, model=model, purpose=purpose)
        if purpose == "compile":
            payload["body"] = "# Shared Concept\n\nUnsupported. ^[raw/sources/source-a.md:999-1000]"
        return payload


def _bundle_with_two_sources(tmp_path: Path) -> Path:
    bundle = tmp_path / "bundle"
    init_bundle(bundle, title="Compiler Test")
    source_a = tmp_path / "source-a.txt"
    source_b = tmp_path / "source-b.txt"
    source_a.write_text("Shared compilers aggregate evidence.\nA second line.\nA third line.\n")
    source_b.write_text("Shared compilers preserve context.\nAnother line.\nFinal line.\n")
    ingest_source(bundle, str(source_a), publisher="Test")
    ingest_source(bundle, str(source_b), publisher="Test")
    return bundle


def test_incremental_compile_aggregates_all_contributing_sources(tmp_path: Path) -> None:
    bundle = _bundle_with_two_sources(tmp_path)
    client = FakeLLM()

    first = compile_bundle(bundle, client=client)

    assert first.errors == []
    assert first.draft_paths == [".expertwiki/drafts/shared-concept.md"]
    assert len(client.analysis_prompts) == 2
    assert len(client.compile_prompts) == 1
    assert "--- SOURCE: raw/sources/source-a.md ---" in client.compile_prompts[0]
    assert "--- SOURCE: raw/sources/source-b.md ---" in client.compile_prompts[0]

    second = compile_bundle(bundle, client=client)

    assert second.changes == []
    assert second.draft_paths == []
    assert len(client.analysis_prompts) == 2
    assert len(client.compile_prompts) == 1


def test_changed_source_recompiles_shared_concept_with_unchanged_contributor(
    tmp_path: Path,
) -> None:
    bundle = _bundle_with_two_sources(tmp_path)
    client = FakeLLM()
    first = compile_bundle(bundle, client=client)
    approve_draft(bundle, first.draft_paths[0])
    source_a = bundle / "raw" / "sources" / "source-a.md"
    source_a.write_text(source_a.read_text() + "\nA new observation.\n")

    result = compile_bundle(bundle, client=client)

    assert [change.status for change in result.changes] == ["changed"]
    assert result.draft_paths == [".expertwiki/drafts/shared-concept.md"]
    assert "--- SOURCE: raw/sources/source-a.md ---" in client.compile_prompts[-1]
    assert "--- SOURCE: raw/sources/source-b.md ---" in client.compile_prompts[-1]


def test_deleted_shared_source_freezes_existing_synthesis(tmp_path: Path) -> None:
    bundle = _bundle_with_two_sources(tmp_path)
    client = FakeLLM()
    first = compile_bundle(bundle, client=client)
    approved = approve_draft(bundle, first.draft_paths[0])
    published = bundle / approved.page_path
    published_before = published.read_text()
    (bundle / "raw" / "sources" / "source-b.md").unlink()

    result = compile_bundle(bundle, client=client)

    assert result.draft_paths == []
    assert result.frozen_concepts == ["Shared Concept"]
    assert published.read_text() == published_before
    assert len(client.compile_prompts) == 1


def test_manual_page_edit_is_not_overwritten(tmp_path: Path) -> None:
    bundle = _bundle_with_two_sources(tmp_path)
    client = FakeLLM()
    first = compile_bundle(bundle, client=client)
    approved = approve_draft(bundle, first.draft_paths[0])
    page = bundle / approved.page_path
    page.write_text(page.read_text() + "\nManual note.\n")
    source_a = bundle / "raw" / "sources" / "source-a.md"
    source_a.write_text(source_a.read_text() + "\nChanged evidence.\n")

    result = compile_bundle(bundle, client=client)

    assert result.draft_paths == []
    assert result.skipped == [
        {
            "concept": "Shared Concept",
            "reason": "Published page is user-owned or manually edited; refusing to overwrite it.",
        }
    ]
    assert page.read_text().endswith("Manual note.\n")


def test_rejection_feedback_is_injected_into_forced_recompile(tmp_path: Path) -> None:
    bundle = _bundle_with_two_sources(tmp_path)
    client = FakeLLM()
    first = compile_bundle(bundle, client=client)

    rejected = reject_draft(
        bundle,
        first.draft_paths[0],
        feedback="Explain the cross-source dependency explicitly.",
    )
    assert rejected.blocked is False

    result = compile_bundle(bundle, client=client, force=True)

    assert result.draft_paths == [".expertwiki/drafts/shared-concept.md"]
    assert "Explain the cross-source dependency explicitly." in client.compile_prompts[-1]


def test_compiler_state_records_dependency_and_citation_contract(tmp_path: Path) -> None:
    bundle = _bundle_with_two_sources(tmp_path)
    client = FakeLLM()
    compile_bundle(bundle, client=client)

    stats = compiler_stats(bundle)
    assert stats["sources"] == 2
    assert stats["concepts"] == 1
    assert stats["drafts"] == 1

    with StateDB(state_path(bundle)) as state:
        concept = state.get_concept("shared compiler")
        assert concept is not None
        contributors = state.source_concepts_for_concept(concept.id)
        assert [item.source_path for item in contributors] == [
            "raw/sources/source-a.md",
            "raw/sources/source-b.md",
        ]


def test_invalid_citation_fails_visible_without_writing_draft(tmp_path: Path) -> None:
    bundle = _bundle_with_two_sources(tmp_path)

    result = compile_bundle(bundle, client=BadCitationLLM())

    assert result.draft_paths == []
    assert "Citation range is outside" in result.errors[0]
    assert not (bundle / ".expertwiki" / "drafts" / "shared-concept.md").exists()


def test_compiler_state_rebuilds_pending_draft_from_markdown(tmp_path: Path) -> None:
    bundle = _bundle_with_two_sources(tmp_path)
    compile_bundle(bundle, client=FakeLLM())
    database = state_path(bundle)
    database.unlink()
    database.with_name(database.name + "-wal").unlink(missing_ok=True)
    database.with_name(database.name + "-shm").unlink(missing_ok=True)

    stats = compiler_stats(bundle)

    assert stats["drafts"] == 1
    with StateDB(database) as state:
        concept = state.get_concept("Shared Concept")
        assert concept is not None
        assert len(state.source_concepts_for_concept(concept.id)) == 2


def test_context_budget_keeps_extracted_ranges_from_end_of_long_source() -> None:
    text = "\n".join(f"line {index} " + ("x" * 80) for index in range(1, 501))

    material = _assemble_source_material(
        [("raw/sources/long.md", text, ["490-492"])],
        max_chars=2_000,
    )

    assert "   490 | line 490" in material
    assert "   492 | line 492" in material
    assert "lines omitted by deterministic context budget" in material
