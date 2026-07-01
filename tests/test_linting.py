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

    def test_missing_claim_source_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_bundle(root)
            (root / "claims" / "broken.md").write_text(
                """---
type: Verified Claim
title: Broken Claim
description: Broken source reference.
tags: [broken]
status: verified
confidence: high
reviewers: [reviewer:source_audit]
verified_at: 2026-07-01
sources: [/sources/missing.md]
---

# Claim

This claim points at a missing source.
""",
                encoding="utf-8",
            )

            result = lint_bundle(root)

        self.assertFalse(result.ok)
        self.assertTrue(
            any("missing source" in issue.message for issue in result.issues)
        )

    def test_remote_only_bundle_cannot_allow_full_download(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_bundle(root)
            (root / "access.md").write_text(
                """---
type: Access Policy
title: Remote Policy
description: Invalid remote-only policy.
mode: remote_only
download: allowed
query: remote
---

# Access Policy

Invalid.
""",
                encoding="utf-8",
            )

            result = lint_bundle(root)

        self.assertFalse(result.ok)
        self.assertTrue(
            any("cannot allow full download" in issue.message for issue in result.issues)
        )


def _write_minimal_bundle(root: Path) -> None:
    (root / "claims").mkdir(parents=True)
    (root / "sources").mkdir(parents=True)
    (root / "index.md").write_text("# Test Bundle\n", encoding="utf-8")
    (root / "log.md").write_text("# Log\n", encoding="utf-8")
    (root / "claims" / "index.md").write_text("# Claims\n", encoding="utf-8")
    (root / "sources" / "index.md").write_text("# Sources\n", encoding="utf-8")
    (root / "access.md").write_text(
        """---
type: Access Policy
title: Open Policy
description: Valid open policy.
mode: open
download: allowed
query: local
---

# Access Policy

Valid.
""",
        encoding="utf-8",
    )
    (root / "sources" / "source.md").write_text(
        """---
type: Source
title: Source
description: Test source.
resource: https://example.com/source
publisher: Example
retrieved_at: 2026-07-01
---

# Source

Test.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
