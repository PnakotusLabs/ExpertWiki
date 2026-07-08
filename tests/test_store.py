import unittest

from expertwiki import KnowledgeStore


class KnowledgeStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = KnowledgeStore("bundles/expertwiki-ai-agent-engineering")

    def test_health_counts_loaded_records(self) -> None:
        self.assertEqual(
            self.store.health(),
            {"status": "ok", "source_count": 3, "page_count": 3},
        )

    def test_search_returns_wiki_pages(self) -> None:
        results = self.store.search("LLM Wiki")
        self.assertEqual(results[0]["page"]["id"], "topics/llm-wiki")

    def test_get_page_includes_source_records(self) -> None:
        page = self.store.get_page("topics/llm-wiki")
        self.assertIsNotNone(page)
        assert page is not None
        self.assertEqual(page["source_records"][0]["publisher"], "Andrej Karpathy / GitHub Gist")

    def test_missing_page_returns_none(self) -> None:
        self.assertIsNone(self.store.get_page("missing"))

    def test_empty_query_returns_no_results(self) -> None:
        self.assertEqual(self.store.search(""), [])


if __name__ == "__main__":
    unittest.main()
