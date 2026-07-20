import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from expertwiki.authoring import init_bundle
from expertwiki.cli import main
from expertwiki.experience import (
    SuggestedCard,
    add_material,
    approve_suggestion,
    ask_wiki,
    create_suggested_card,
    reject_suggestion,
    review_suggestions,
    start_experience,
)
from expertwiki.linting import lint_bundle


class ExperienceTest(unittest.TestCase):
    def test_start_creates_missing_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "wiki"

            result = start_experience(root, title="Starter Wiki")

            self.assertTrue(result.initialized)
            self.assertEqual(result.source_count, 0)
            self.assertTrue((root / "AGENTS.md").exists())

    def test_add_queues_host_ai_job_without_api_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "wiki"
            init_bundle(root, title="Wiki")
            source = Path(temp_dir) / "note.md"
            source.write_text("# Note\n\nUseful source text.", encoding="utf-8")

            with _without_ai_env():
                result = add_material(root, str(source), publisher="Tester", slug="note")

            self.assertEqual(result.source_path, "raw/sources/note.md")
            self.assertFalse(result.ai_enabled)
            self.assertEqual(result.execution_mode, "host")
            self.assertEqual(result.queued_job_count, 1)
            self.assertEqual(result.draft_paths, [])
            self.assertTrue((root / "raw" / "sources" / "note.md").exists())

    def test_add_does_not_auto_select_configured_api_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "wiki"
            init_bundle(root, title="Wiki")
            source = Path(temp_dir) / "note.md"
            source.write_text("# Note\n\nUseful source text.", encoding="utf-8")

            with mock.patch(
                "expertwiki.experience.client_from_env",
                side_effect=AssertionError("default host mode must not inspect API configuration"),
            ):
                result = add_material(root, str(source), publisher="Tester", slug="note")

            self.assertEqual(result.execution_mode, "host")
            self.assertEqual(result.queued_job_count, 1)

    def test_review_and_approve_suggested_card(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_draft(Path(temp_dir))

            review = review_suggestions(root)
            approved = approve_suggestion(root, "Agent Memory")

            self.assertEqual(len(review.drafts), 1)
            self.assertEqual(approved.page_path, "wiki/topics/agent-memory.md")
            self.assertFalse((root / ".expertwiki" / "drafts" / "agent-memory.md").exists())
            self.assertTrue((root / approved.page_path).exists())
            self.assertTrue(lint_bundle(root).ok)

    def test_reject_suggested_card_preserves_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_draft(Path(temp_dir))

            result = reject_suggestion(root, "agent-memory", feedback="Too generic.")

            rejected_text = (root / result.rejected_path).read_text(encoding="utf-8")
            self.assertIn("draft_status: rejected", rejected_text)
            self.assertIn("Too generic.", rejected_text)
            self.assertEqual(review_suggestions(root).drafts, [])

    def test_ask_without_ai_provider_returns_matching_approved_cards(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_draft(Path(temp_dir))
            approve_suggestion(root, "agent-memory")

            with _without_ai_env():
                result = ask_wiki(root, "agent memory")

            self.assertFalse(result.ai_enabled)
            self.assertEqual(result.used_pages[0]["id"], "topics/agent-memory")
            self.assertIn("invoking host AI", result.answer)

    def test_ask_routes_with_fast_model_then_answers_with_heavy_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_draft(Path(temp_dir))
            approve_suggestion(root, "agent-memory")
            client = _QueryClient()

            with mock.patch("expertwiki.experience.client_from_env", return_value=client):
                result = ask_wiki(root, "How does agent memory help?", backend="api")

            self.assertTrue(result.ai_enabled)
            self.assertEqual(result.answer, "It preserves reusable, approved knowledge.")
            self.assertEqual(result.used_pages[0]["id"], "topics/agent-memory")
            self.assertEqual(client.purposes, ["query-route", "answer"])

    def test_cli_review_and_approve(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_draft(Path(temp_dir))
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                review_code = main(["review", str(root)])
                approve_code = main(["approve", str(root), "agent-memory"])

            self.assertEqual(review_code, 0)
            self.assertEqual(approve_code, 0)
            self.assertIn("Suggested cards: 1", output.getvalue())
            self.assertIn("Approved: Agent Memory", output.getvalue())


def _wiki_with_draft(root: Path) -> Path:
    init_bundle(root, title="Experience Wiki")
    (root / "raw" / "sources" / "source.md").write_text(
        """---
type: raw_source
title: Source
description: Source for tests.
resource: file:///source.md
publisher: Tester
retrieved_at: 2026-07-19
---

# Source

Agent memory turns repeated source-backed knowledge into reusable cards.
""",
        encoding="utf-8",
    )
    create_suggested_card(
        root,
        SuggestedCard(
            title="Agent Memory",
            description="Reusable source-backed knowledge for agents.",
            tags=["agent-memory"],
            body="""# Agent Memory

## Context

Agent memory is useful when source-backed knowledge should be reused.

## Facts

Repeated knowledge can become a stable card.

## Confidence

single_case: based on one test source.

## Sources

- [source](/raw/sources/source.md)
""",
        ),
        sources=["/raw/sources/source.md"],
    )
    return root


def _without_ai_env():
    return mock.patch.dict(
        os.environ,
        {
            "EXPERTWIKI_OPENAI_BASE_URL": "",
            "EXPERTWIKI_OPENAI_MODEL": "",
            "EXPERTWIKI_FAST_MODEL": "",
            "EXPERTWIKI_HEAVY_MODEL": "",
            "EXPERTWIKI_OPENAI_API_KEY": "",
        },
    )


class _QueryClient:
    fast_model = "fast"
    heavy_model = "heavy"

    def __init__(self) -> None:
        self.purposes = []

    def complete_json(self, prompt, *, model, purpose):
        self.purposes.append(purpose)
        if purpose == "query-route":
            return {"page_ids": ["topics/agent-memory"]}
        if purpose == "answer":
            return {"answer": "It preserves reusable, approved knowledge."}
        raise AssertionError(purpose)


if __name__ == "__main__":
    unittest.main()
