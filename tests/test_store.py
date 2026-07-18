import unittest

from expertwiki import KnowledgeStore


class KnowledgeStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = KnowledgeStore("bundles/expertwiki-ai-agent-engineering")

    def test_health_counts_loaded_records(self) -> None:
        self.assertEqual(
            self.store.health(),
            {"status": "ok", "source_count": 3, "page_count": 6},
        )

    def test_search_returns_wiki_pages(self) -> None:
        results = self.store.search("agent knowledge bundles")
        self.assertEqual(results[0]["page"]["id"], "topics/agent-knowledge-bundles")

    def test_get_page_includes_source_records(self) -> None:
        page = self.store.get_page("entities/experts/andrej-karpathy")
        self.assertIsNotNone(page)
        assert page is not None
        self.assertEqual(page["source_records"][0]["publisher"], "Andrej Karpathy / GitHub Gist")

    def test_missing_page_returns_none(self) -> None:
        self.assertIsNone(self.store.get_page("missing"))

    def test_empty_query_returns_no_results(self) -> None:
        self.assertEqual(self.store.search(""), [])

    def test_graph_contains_page_source_edges(self) -> None:
        graph = self.store.graph()
        self.assertTrue(any(edge["type"] == "cites" for edge in graph["edges"]))
        self.assertTrue(any(node["type"] == "source" for node in graph["nodes"]))

    def test_llms_txt_lists_agent_readable_pages(self) -> None:
        text = self.store.llms_txt()
        self.assertTrue(text.startswith("# AI Agent Engineering Wiki\n\n"))
        self.assertIn("> Source-backed expert and project knowledge for AI agents.", text)
        self.assertIn("## Pages", text)
        self.assertIn("/pages/entities/experts/andrej-karpathy.md", text)
        self.assertIn("## Optional", text)

    def test_get_page_markdown_returns_source_markdown(self) -> None:
        markdown = self.store.get_page_markdown("entities/experts/andrej-karpathy")
        self.assertIsNotNone(markdown)
        assert markdown is not None
        self.assertTrue(markdown.startswith("---\ntype: wiki_page\n"))
        self.assertIn("# Andrej Karpathy", markdown)


if __name__ == "__main__":
    unittest.main()
