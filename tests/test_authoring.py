import tempfile
import unittest
from pathlib import Path

from expertwiki.authoring import (
    audit_bundle,
    bundle_status,
    create_page,
    ingest_source,
    init_bundle,
    list_concepts,
    package_dry_run,
    query_bundle,
    rebuild_indexes,
    show_concept,
)
from expertwiki.linting import lint_bundle


class AuthoringTest(unittest.TestCase):
    def test_init_creates_lintable_wiki(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "my-wiki"

            result = init_bundle(root, title="My Wiki")
            lint_result = lint_bundle(root)

            self.assertIn("AGENTS.md", result.created_files)
            self.assertTrue((root / "raw" / "sources" / "index.md").exists())
            self.assertTrue((root / "wiki" / "topics" / "index.md").exists())
            self.assertTrue((root / "wiki" / "entities" / "experts" / "index.md").exists())
            self.assertTrue((root / "wiki" / "entities" / "projects" / "index.md").exists())
            self.assertTrue((root / "wiki" / "viewpoints" / "index.md").exists())
            agents_text = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("Recommended Agent Loop", agents_text)
            self.assertIn("Page Type Guide", agents_text)
            self.assertIn("wiki/entities/experts/", agents_text)
            self.assertIn("wiki/entities/projects/", agents_text)
            self.assertIn("wiki/synthesis/", agents_text)
            self.assertTrue(lint_result.ok)
            self.assertIn("init | Initialized ExpertWiki bundle", (root / "log.md").read_text())

    def test_init_refuses_non_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "existing.txt").write_text("keep", encoding="utf-8")

            with self.assertRaises(ValueError):
                init_bundle(root)

    def test_ingest_local_file_creates_raw_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "wiki"
            init_bundle(root, title="Wiki")
            source_file = Path(temp_dir) / "note.md"
            source_file.write_text("# Useful Note\n\nImportant source text.", encoding="utf-8")

            result = ingest_source(root, str(source_file), publisher="Tester", slug="note")

            source_path = root / result.source_path
            self.assertEqual(result.source_path, "raw/sources/note.md")
            self.assertTrue(source_path.exists())
            self.assertIn("type: raw_source", source_path.read_text())
            self.assertTrue(lint_bundle(root).ok)

    def test_ingest_rejects_url_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "wiki"
            init_bundle(root, title="Wiki")

            with self.assertRaisesRegex(ValueError, "URL sources are not supported"):
                ingest_source(root, "https://example.com/docs/test", title="Remote Doc", slug="remote")

    def test_ingest_rejects_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "wiki"
            init_bundle(root, title="Wiki")
            source_dir = Path(temp_dir) / "sources"
            source_dir.mkdir()

            with self.assertRaisesRegex(ValueError, "Source must be a local file"):
                ingest_source(root, str(source_dir))

    def test_page_create_writes_wiki_page_with_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_source(Path(temp_dir))

            result = create_page(
                root,
                "wiki/topics/example.md",
                title="Example",
                description="Example page.",
                sources=["example-source"],
                tags=["example"],
            )

            page_text = (root / result.page_path).read_text()
            self.assertIn("type: wiki_page", page_text)
            self.assertIn("entity_type: topic", page_text)
            self.assertIn("quality: unreviewed", page_text)
            self.assertIn("## Human Feedback", page_text)
            self.assertIn("## Counterexamples and Risks", page_text)
            self.assertIn("/raw/sources/example-source.md", page_text)
            self.assertTrue(lint_bundle(root).ok)

    def test_page_create_defaults_description_to_empty_string(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_source(Path(temp_dir))

            create_page(root, "wiki/topics/example.md", title="Example")
            shown = show_concept(root, "topics/example", kind="pages")

            self.assertEqual(shown.concept["metadata"]["description"], "")

    def test_page_create_requires_wiki_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_source(Path(temp_dir))

            with self.assertRaises(ValueError):
                create_page(root, "notes/example.md", title="Example")

    def test_rebuild_indexes_lists_pages_and_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_page(Path(temp_dir))

            result = rebuild_indexes(root)

            self.assertIn("wiki/topics/index.md", result.updated_indexes)
            self.assertIn("Example", (root / "wiki" / "topics" / "index.md").read_text())
            self.assertIn("index | Rebuilt", (root / "log.md").read_text())

    def test_rebuild_indexes_skips_hidden_compiler_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_page(Path(temp_dir))
            drafts = root / ".expertwiki" / "drafts"
            drafts.mkdir(parents=True)
            (drafts / "candidate.md").write_text("draft", encoding="utf-8")

            result = rebuild_indexes(root)

            self.assertFalse((drafts / "index.md").exists())
            self.assertNotIn(".expertwiki/drafts/index.md", result.updated_indexes)

    def test_query_bundle_returns_wiki_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_page(Path(temp_dir))

            result = query_bundle(root, "example page")

            self.assertEqual(len(result.results), 1)
            self.assertEqual(result.results[0]["page"]["id"], "topics/example")
            self.assertIn("query | 'example page'", (root / "log.md").read_text())

    def test_list_and_show_concepts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_page(Path(temp_dir))

            pages = list_concepts(root, kind="pages")
            sources = list_concepts(root, kind="sources")
            shown = show_concept(root, "topics/example", kind="pages")

            self.assertEqual(len(pages.items), 1)
            self.assertEqual(len(sources.items), 1)
            self.assertEqual(shown.concept["metadata"]["title"], "Example")

    def test_status_reports_counts_and_next_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_page(Path(temp_dir))

            result = bundle_status(root)

            self.assertTrue(result.ok)
            self.assertEqual(result.concept_counts["raw_source"], 1)
            self.assertEqual(result.concept_counts["wiki_page"], 1)
            self.assertTrue(result.next_actions)

    def test_audit_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_page(Path(temp_dir))

            result = audit_bundle(root)

            audit_text = (root / result.audit_path).read_text()
            self.assertTrue(result.ok)
            self.assertIn("type: audit_report", audit_text)
            self.assertIn("Wiki pages: 1", audit_text)

    def test_package_dry_run_reports_lint_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _wiki_with_page(Path(temp_dir))

            result = package_dry_run(root)

            self.assertTrue(result.ok)
            self.assertEqual(result.concept_counts["wiki_page"], 1)


def _wiki_with_source(root: Path) -> Path:
    init_bundle(root, title="Example Wiki")
    (root / "raw" / "sources" / "example-source.md").write_text(
        """---
type: raw_source
title: Example Source
description: Source for tests.
resource: https://example.com/source
publisher: Example
retrieved_at: 2026-07-04
---

# Source

Test source.
""",
        encoding="utf-8",
    )
    rebuild_indexes(root)
    return root


def _wiki_with_page(root: Path) -> Path:
    _wiki_with_source(root)
    create_page(
        root,
        "wiki/topics/example.md",
        title="Example",
        description="Example page.",
        sources=["example-source"],
        tags=["example"],
    )
    return root


if __name__ == "__main__":
    unittest.main()
