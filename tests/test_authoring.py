import tempfile
import unittest
from pathlib import Path

from expertwiki.authoring import (
    audit_bundle,
    bundle_status,
    compile_claim_draft,
    ingest_source,
    init_bundle,
    list_concepts,
    mark_claim,
    package_dry_run,
    query_bundle,
    rebuild_indexes,
    show_concept,
    verify_claim,
)
from expertwiki.linting import lint_bundle


class AuthoringTest(unittest.TestCase):
    def test_init_creates_lintable_open_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "my-wiki"

            result = init_bundle(root, title="My Wiki")
            lint_result = lint_bundle(root)

            self.assertIn("access.md", result.created_files)
            self.assertTrue((root / "claims" / "index.md").exists())
            self.assertTrue((root / "sources" / "index.md").exists())
            self.assertTrue(lint_result.ok)
            self.assertIn("init | Initialized bundle", (root / "log.md").read_text())

    def test_init_refuses_non_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "existing.txt").write_text("keep", encoding="utf-8")

            with self.assertRaises(ValueError):
                init_bundle(root)

    def test_rebuild_indexes_lists_claims_and_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_claim(Path(temp_dir))

            result = rebuild_indexes(root)

            self.assertIn("claims/index.md", result.updated_indexes)
            self.assertIn("Example Claim", (root / "claims" / "index.md").read_text())
            self.assertIn("index | Rebuilt", (root / "log.md").read_text())

    def test_query_bundle_returns_verified_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_claim(Path(temp_dir))

            result = query_bundle(root, "example claim")

            self.assertEqual(len(result.results), 1)
            self.assertEqual(result.results[0]["claim"]["id"], "example-claim")
            self.assertIn("query | 'example claim'", (root / "log.md").read_text())

    def test_package_dry_run_requires_access_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_claim(Path(temp_dir))
            (root / "access.md").unlink()

            result = package_dry_run(root)

            self.assertFalse(result.ok)
            self.assertTrue(any("Package requires access.md" in issue.message for issue in result.issues))

    def test_ingest_local_file_creates_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "bundle"
            init_bundle(root, title="Bundle")
            source_file = Path(temp_dir) / "note.md"
            source_file.write_text("# Useful Note\n\nImportant source text.", encoding="utf-8")

            result = ingest_source(root, str(source_file), publisher="Tester")

            source_path = root / result.source_path
            self.assertTrue(source_path.exists())
            self.assertIn("title: Useful Note", source_path.read_text())
            self.assertIn("ingest | Ingested Useful Note", (root / "log.md").read_text())
            self.assertTrue(lint_bundle(root).ok)

    def test_ingest_url_records_metadata_without_fetching(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "bundle"
            init_bundle(root, title="Bundle")

            result = ingest_source(root, "https://example.com/docs/test", title="Remote Doc")

            text = (root / result.source_path).read_text()
            self.assertIn("resource: https://example.com/docs/test", text)
            self.assertIn("Content was not fetched automatically", text)

    def test_compile_creates_draft_claim_from_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_claim(Path(temp_dir))

            result = compile_claim_draft(
                root,
                "example-source",
                title="Draft Example",
                claim="Draft source-backed claim.",
            )

            claim_text = (root / result.claim_path).read_text()
            self.assertIn("status: draft", claim_text)
            self.assertIn("Draft source-backed claim.", claim_text)
            self.assertTrue(lint_bundle(root).ok)
            self.assertIn("compile | Created draft claim", (root / "log.md").read_text())

    def test_draft_claims_are_not_returned_by_default_query(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_claim(Path(temp_dir))
            compile_claim_draft(
                root,
                "example-source",
                title="Draft Example",
                claim="Draft source-backed claim.",
            )

            result = query_bundle(root, "draft source")

            self.assertEqual(result.results, [])

    def test_verify_promotes_draft_claim_to_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_claim(Path(temp_dir))
            draft = compile_claim_draft(
                root,
                "example-source",
                title="Draft Example",
                claim="Draft source-backed claim.",
            )

            result = verify_claim(
                root,
                draft.claim_path,
                reviewer="tester",
                method="source_audit",
                confidence="medium",
                verified_at="2026-07-01",
            )
            query_result = query_bundle(root, "draft source")

            self.assertEqual(result.status, "verified")
            self.assertEqual(query_result.results[0]["claim"]["id"], "draft-example")
            text = (root / draft.claim_path).read_text()
            self.assertIn("status: verified", text)
            self.assertIn("reviewers:", text)
            self.assertIn("verified_at: 2026-07-01", text)

    def test_mark_claim_updates_status_and_hides_from_default_query(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_claim(Path(temp_dir))

            result = mark_claim(root, "example-claim", status="stale", reason="Needs review")
            query_result = query_bundle(root, "example claim")

            self.assertEqual(result.status, "stale")
            self.assertEqual(query_result.results, [])
            text = (root / result.claim_path).read_text()
            self.assertIn("status: stale", text)
            self.assertIn("status_reason: Needs review", text)

    def test_list_and_show_concepts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_claim(Path(temp_dir))

            claims = list_concepts(root, kind="claims")
            sources = list_concepts(root, kind="sources")
            shown = show_concept(root, "example-claim", kind="claims")

            self.assertEqual(len(claims.items), 1)
            self.assertEqual(len(sources.items), 1)
            self.assertEqual(shown.concept["metadata"]["title"], "Example Claim")

    def test_status_reports_counts_and_next_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_claim(Path(temp_dir))
            compile_claim_draft(root, "example-source", title="Draft Example")

            result = bundle_status(root)

            self.assertTrue(result.ok)
            self.assertEqual(result.concept_counts["Source"], 1)
            self.assertEqual(result.claim_status_counts["draft"], 1)
            self.assertEqual(result.claim_status_counts["verified"], 1)
            self.assertTrue(
                any("Review draft claims" in action for action in result.next_actions)
            )

    def test_status_ignores_audit_index_as_latest_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "bundle"
            init_bundle(root, title="Bundle")

            result = bundle_status(root)

            self.assertIsNone(result.latest_audit)

    def test_audit_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_claim(Path(temp_dir))
            compile_claim_draft(root, "example-source", title="Draft Example")

            result = audit_bundle(root)

            audit_text = (root / result.audit_path).read_text()
            self.assertTrue(result.ok)
            self.assertIn("type: Audit Report", audit_text)
            self.assertIn("Draft claims: 1", audit_text)
            self.assertIn("audit | Wrote", (root / "log.md").read_text())


def _bundle_with_claim(root: Path) -> Path:
    init_bundle(root, title="Example Bundle")
    (root / "sources" / "example-source.md").write_text(
        """---
type: Source
title: Example Source
description: Source for tests.
resource: https://example.com/source
publisher: Example
retrieved_at: 2026-07-01
---

# Source

Test source.
""",
        encoding="utf-8",
    )
    (root / "claims" / "example-claim.md").write_text(
        """---
type: Verified Claim
title: Example Claim
description: Claim for tests.
tags: [example]
status: verified
confidence: high
reviewers: [tester:source_audit]
verified_at: 2026-07-01
sources: [/sources/example-source.md]
---

# Claim

This example claim is used by tests.

# Citations

[1] [Example Source](/sources/example-source.md)
""",
        encoding="utf-8",
    )
    rebuild_indexes(root)
    return root


if __name__ == "__main__":
    unittest.main()
