import unittest

from expertwiki import KnowledgeStore


class KnowledgeStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = KnowledgeStore("bundles/expertwiki-ai-agent-engineering")

    def test_health_counts_loaded_records(self) -> None:
        self.assertEqual(
            self.store.health(),
            {"status": "ok", "source_count": 5, "claim_count": 5},
        )

    def test_search_returns_verified_claims(self) -> None:
        results = self.store.search("MCP open standard")
        self.assertEqual(results[0]["claim"]["id"], "mcp-open-standard")
        self.assertEqual(results[0]["claim"]["status"], "verified")

    def test_get_claim_includes_source_records(self) -> None:
        claim = self.store.get_claim("openai-file-search-vector-store")
        self.assertIsNotNone(claim)
        assert claim is not None
        self.assertEqual(claim["source_records"][0]["publisher"], "OpenAI Developers")

    def test_missing_claim_returns_none(self) -> None:
        self.assertIsNone(self.store.get_claim("missing"))

    def test_empty_query_returns_no_results(self) -> None:
        self.assertEqual(self.store.search(""), [])


if __name__ == "__main__":
    unittest.main()
