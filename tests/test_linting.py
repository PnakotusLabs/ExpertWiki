import tempfile
import unittest
from pathlib import Path

from expertwiki.linting import lint_bundle


VALID_BUNDLE = Path("bundles/expertwiki-ai-agent-engineering")


class BundleLintTest(unittest.TestCase):
    def test_seed_bundle_has_no_critical_issues(self) -> None:
        result = lint_bundle(VALID_BUNDLE)

        self.assertTrue(result.ok)
        self.assertEqual(result.counts()["critical"], 0)

    def test_missing_page_source_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_wiki(root)
            (root / "wiki" / "topics" / "broken.md").write_text(
                """---
type: wiki_page
title: Broken Page
sources: [/raw/sources/missing.md]
updated_at: 2026-07-04
---

# Broken Page
""",
                encoding="utf-8",
            )

            result = lint_bundle(root)

        self.assertFalse(result.ok)
        self.assertTrue(any("missing source" in issue.message for issue in result.issues))

    def test_broken_markdown_link_is_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_wiki(root)
            (root / "wiki" / "topics" / "page.md").write_text(
                """---
type: wiki_page
title: Page
sources: []
updated_at: 2026-07-04
---

# Page

[Missing](missing.md)
""",
                encoding="utf-8",
            )

            result = lint_bundle(root)

        self.assertTrue(result.ok)
        self.assertTrue(any("Broken markdown link" in issue.message for issue in result.issues))

    def test_out_of_range_source_citation_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_wiki(root)
            (root / "wiki" / "topics" / "cited.md").write_text(
                """---
type: wiki_page
entity_type: topic
title: Cited Page
quality: reviewed
license: unknown
source_updated_at: 2026-07-19
last_reviewed_at: 2026-07-19
sources: [/raw/sources/source.md]
---

# Cited Page

This range does not exist. ^[raw/sources/source.md:500-510]
""",
                encoding="utf-8",
            )

            result = lint_bundle(root)

        self.assertFalse(result.ok)
        self.assertTrue(any("Citation range is outside" in issue.message for issue in result.issues))


def _write_minimal_wiki(root: Path) -> None:
    (root / "raw" / "sources").mkdir(parents=True)
    (root / "wiki" / "topics").mkdir(parents=True)
    (root / "audits").mkdir()
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / "index.md").write_text("# Wiki\n", encoding="utf-8")
    (root / "log.md").write_text("# Log\n", encoding="utf-8")
    (root / "raw" / "index.md").write_text("# Raw\n", encoding="utf-8")
    (root / "raw" / "sources" / "index.md").write_text("# Sources\n", encoding="utf-8")
    (root / "wiki" / "index.md").write_text("# Wiki\n", encoding="utf-8")
    (root / "wiki" / "topics" / "index.md").write_text("# Topics\n", encoding="utf-8")
    (root / "audits" / "index.md").write_text("# Audits\n", encoding="utf-8")
    (root / "raw" / "sources" / "source.md").write_text(
        """---
type: raw_source
title: Source
resource: https://example.com/source
publisher: Example
retrieved_at: 2026-07-04
---

# Source
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
