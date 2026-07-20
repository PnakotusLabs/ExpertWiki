from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from expertwiki.authoring import init_bundle
from expertwiki.okf import render_frontmatter
from expertwiki.publish import markdown_hash, publish_state_path
from expertwiki.state import StateDB
from expertwiki.viewer import ViewerNotFoundError, ViewerStore, create_viewer_server


class ViewerStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "wiki"
        _create_viewer_bundle(self.root)
        self.store = ViewerStore(self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_summary_and_document_views_include_drafts_and_published_pages(self) -> None:
        summary = self.store.summary()

        self.assertEqual(summary["source_count"], 1)
        self.assertEqual(summary["draft_count"], 1)
        self.assertEqual(summary["approved_count"], 1)
        self.assertEqual(summary["published_count"], 0)
        self.assertEqual(summary["rejected_count"], 0)
        self.assertEqual(summary["concept_count"], 2)
        self.assertEqual(summary["graph_edge_count"], 2)
        self.assertEqual(self.store.list_documents("draft")[0]["title"], "Shared Concept")
        self.assertEqual(
            self.store.list_documents("approved")[0]["title"], "Published Concept"
        )
        self.assertEqual(self.store.list_documents("published"), [])
        self.assertEqual(self.store.list_documents("rejected"), [])

    def test_document_exposes_body_metadata_and_line_citations(self) -> None:
        document = self.store.get_document("draft", "shared-concept")

        self.assertIn("Source-backed sentence", document["body"])
        self.assertEqual(document["metadata"]["concept_id"], "1")
        self.assertEqual(len(document["citations"]), 2)
        self.assertEqual(
            [(item["path"], item["start"], item["end"]) for item in document["citations"]],
            [
                ("raw/sources/note.md", 11, 11),
                ("raw/sources/note.md", 13, 14),
            ],
        )
        self.assertEqual(
            document["citations"][0]["marker"],
            "^[raw/sources/note.md:11-11, raw/sources/note.md:13-14]",
        )

    def test_source_excerpt_returns_exact_numbered_lines(self) -> None:
        excerpt = self.store.source_excerpt("raw/sources/note.md", 13, 14)

        self.assertEqual(excerpt["start"], 13)
        self.assertEqual(excerpt["end"], 14)
        self.assertEqual(
            excerpt["lines"],
            [
                {"number": 13, "text": "Evidence line one."},
                {"number": 14, "text": "Evidence line two."},
            ],
        )

    def test_source_excerpt_rejects_path_traversal_and_out_of_bounds_ranges(self) -> None:
        with self.assertRaisesRegex(ValueError, "raw/sources"):
            self.store.source_excerpt("raw/sources/../../AGENTS.md", 1, 1)
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.store.source_excerpt("raw/sources/note.md", 13, 99)

    def test_graph_contains_compiler_nodes_edges_and_focused_neighborhood(self) -> None:
        graph = self.store.graph()

        self.assertEqual(graph["counts"], {"sources": 1, "concepts": 2, "edges": 2})
        draft_node = next(node for node in graph["nodes"] if node["id"] == "concept:1")
        published_node = next(node for node in graph["nodes"] if node["id"] == "concept:2")
        self.assertEqual(draft_node["status"], "pending_review")
        self.assertEqual(draft_node["document_id"], "shared-concept")
        self.assertEqual(published_node["status"], "approved")
        self.assertEqual(published_node["document_id"], "topics/published-concept")

        focused = self.store.graph("concept:1")
        self.assertEqual(focused["counts"], {"sources": 1, "concepts": 1, "edges": 1})
        with self.assertRaises(ViewerNotFoundError):
            self.store.graph("concept:404")

    def test_invalid_document_kind_and_id_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Document kind"):
            self.store.list_documents("archived")
        with self.assertRaisesRegex(ValueError, "Invalid draft id"):
            self.store.get_document("draft", "../shared-concept")
        with self.assertRaisesRegex(ValueError, "Invalid rejected id"):
            self.store.get_document("rejected", "../shared-concept")

    def test_draft_symlink_cannot_escape_bundle(self) -> None:
        outside = Path(self.temp_dir.name) / "outside.md"
        outside.write_text("---\ntype: draft_page\n---\n\n# Outside\n", encoding="utf-8")
        (self.root / ".expertwiki" / "drafts" / "outside.md").symlink_to(outside)

        with self.assertRaisesRegex(ValueError, "escapes bundle"):
            self.store.list_documents("draft")


class ViewerHttpTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "wiki"
        _create_viewer_bundle(self.root)
        self.server = create_viewer_server(self.root, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def test_index_and_assets_are_local_and_security_hardened(self) -> None:
        with urlopen(self.base_url + "/", timeout=2) as response:
            body = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertIn("ExpertWiki Viewer", body)
            self.assertIn("Approved", body)
            self.assertIn("Published", body)
            self.assertIn("Rejected", body)
            self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
            self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")

        with urlopen(self.base_url + "/assets/vendor/cytoscape.min.js", timeout=2) as response:
            self.assertGreater(len(response.read()), 100_000)

    def test_json_endpoints(self) -> None:
        summary = _get_json(self.base_url + "/api/summary")
        documents = _get_json(self.base_url + "/api/documents?kind=draft")
        graph = _get_json(self.base_url + "/api/graph?focus=concept%3A1")
        source = _get_json(
            self.base_url + "/api/source?path=raw%2Fsources%2Fnote.md&start=13&end=14"
        )

        self.assertEqual(summary["draft_count"], 1)
        self.assertEqual(summary["approved_count"], 1)
        self.assertEqual(summary["published_count"], 0)
        self.assertEqual(documents["documents"][0]["id"], "shared-concept")
        self.assertEqual(graph["counts"]["edges"], 1)
        self.assertEqual(source["lines"][0]["number"], 13)

        request = Request(self.base_url + "/api/document", method="POST", data=b"{}")
        with self.assertRaises(HTTPError) as context:
            urlopen(request, timeout=2)
        self.assertEqual(context.exception.code, 405)
        self.assertIn("viewer_is_read_only", context.exception.read().decode("utf-8"))

    def test_approve_draft_endpoint_publishes_selected_draft(self) -> None:
        result = _post_json(self.base_url + "/api/draft/approve", {"id": "shared-concept"})

        self.assertEqual(result["action"], "approved")
        self.assertEqual(result["approved_id"], "topics/shared-concept")
        self.assertEqual(result["summary"]["draft_count"], 0)
        self.assertEqual(result["summary"]["approved_count"], 2)
        self.assertEqual(result["summary"]["published_count"], 0)
        self.assertFalse((self.root / ".expertwiki" / "drafts" / "shared-concept.md").exists())
        self.assertTrue((self.root / "wiki" / "topics" / "shared-concept.md").is_file())

        approved = _get_json(
            self.base_url + "/api/document?kind=approved&id=topics%2Fshared-concept"
        )
        self.assertEqual(approved["title"], "Shared Concept")
        self.assertEqual(approved["status"], "approved")

    def test_reject_draft_endpoint_moves_selected_draft_to_rejected(self) -> None:
        result = _post_json(
            self.base_url + "/api/draft/reject",
            {"id": "shared-concept", "feedback": "Needs clearer evidence."},
        )

        self.assertEqual(result["action"], "rejected")
        self.assertEqual(result["rejected_path"], ".expertwiki/rejected/shared-concept.md")
        self.assertEqual(result["rejected_id"], "shared-concept")
        self.assertEqual(result["summary"]["draft_count"], 0)
        self.assertEqual(result["summary"]["rejected_count"], 1)
        self.assertFalse((self.root / ".expertwiki" / "drafts" / "shared-concept.md").exists())
        self.assertTrue((self.root / ".expertwiki" / "rejected" / "shared-concept.md").is_file())

        rejected = _get_json(self.base_url + "/api/document?kind=rejected&id=shared-concept")
        self.assertEqual(rejected["title"], "Shared Concept")
        self.assertEqual(rejected["status"], "rejected")

    def test_reject_draft_endpoint_requires_feedback(self) -> None:
        with self.assertRaises(HTTPError) as context:
            _post_json(self.base_url + "/api/draft/reject", {"id": "shared-concept"})

        self.assertEqual(context.exception.code, 400)
        self.assertIn("Missing JSON field: feedback", context.exception.read().decode("utf-8"))

    def test_approved_draft_endpoint_moves_page_back_to_drafts(self) -> None:
        result = _post_json(
            self.base_url + "/api/approved/draft",
            {"id": "topics/published-concept"},
        )

        self.assertEqual(result["action"], "drafted")
        self.assertEqual(result["draft_id"], "published-concept")
        self.assertEqual(result["summary"]["draft_count"], 2)
        self.assertEqual(result["summary"]["approved_count"], 0)
        self.assertEqual(result["summary"]["published_count"], 0)
        self.assertFalse((self.root / "wiki" / "topics" / "published-concept.md").exists())
        self.assertTrue((self.root / ".expertwiki" / "drafts" / "published-concept.md").is_file())

        draft = _get_json(self.base_url + "/api/document?kind=draft&id=published-concept")
        self.assertEqual(draft["title"], "Published Concept")
        self.assertEqual(draft["status"], "pending_review")

    def test_publish_state_moves_current_approved_page_to_published_tab(self) -> None:
        page_path = self.root / "wiki" / "topics" / "published-concept.md"
        _write_publish_state(self.root, page_path)
        store = ViewerStore(self.root)

        summary = store.summary()

        self.assertEqual(summary["approved_count"], 0)
        self.assertEqual(summary["published_count"], 1)
        self.assertEqual(store.list_documents("approved"), [])
        self.assertEqual(store.list_documents("published")[0]["title"], "Published Concept")

        page_path.write_text(page_path.read_text(encoding="utf-8") + "\nLocal edit.\n", encoding="utf-8")
        self.assertEqual(store.summary()["approved_count"], 1)
        self.assertEqual(store.summary()["published_count"], 0)

    def test_rejected_draft_endpoint_moves_rejected_page_back_to_drafts(self) -> None:
        rejected = _post_json(
            self.base_url + "/api/draft/reject",
            {"id": "shared-concept", "feedback": "Needs clearer evidence."},
        )

        result = _post_json(
            self.base_url + "/api/rejected/draft",
            {"id": rejected["rejected_id"]},
        )

        self.assertEqual(result["action"], "drafted")
        self.assertEqual(result["draft_id"], "shared-concept")
        self.assertEqual(result["summary"]["draft_count"], 1)
        self.assertEqual(result["summary"]["rejected_count"], 0)
        self.assertFalse((self.root / ".expertwiki" / "rejected" / "shared-concept.md").exists())
        self.assertTrue((self.root / ".expertwiki" / "drafts" / "shared-concept.md").is_file())

        draft = _get_json(self.base_url + "/api/document?kind=draft&id=shared-concept")
        self.assertEqual(draft["title"], "Shared Concept")
        self.assertEqual(draft["status"], "pending_review")
        self.assertNotIn("rejection_feedback", draft["metadata"])

    def test_invalid_source_path_returns_bad_request(self) -> None:
        with self.assertRaises(HTTPError) as context:
            urlopen(
                self.base_url
                + "/api/source?path=raw%2Fsources%2F..%2F..%2FAGENTS.md&start=1&end=1",
                timeout=2,
            )
        self.assertEqual(context.exception.code, 400)


def _get_json(url: str) -> dict[str, object]:
    with urlopen(url, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        method="POST",
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def _write_publish_state(root: Path, page_path: Path) -> None:
    relative = page_path.relative_to(root).as_posix()
    path = publish_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "endpoint": "http://example.test/api/cli/publish",
                "bundle_title": "Viewer Test Wiki",
                "published_at": "2026-07-20T00:00:00Z",
                "response": {},
                "pages": [
                    {
                        "id": relative.removesuffix(".md"),
                        "path": relative,
                        "title": "Published Concept",
                        "content_hash": markdown_hash(page_path.read_text(encoding="utf-8")),
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _create_viewer_bundle(root: Path) -> None:
    init_bundle(root, title="Viewer Test Wiki")
    source_path = root / "raw" / "sources" / "note.md"
    source_path.write_text(
        render_frontmatter(
            {
                "type": "raw_source",
                "title": "Test Source",
                "resource": "local-note.md",
                "publisher": "Test",
                "retrieved_at": "2026-07-19",
            },
            "# Source\n\nContext line.\n\nEvidence line one.\nEvidence line two.\n",
        ),
        encoding="utf-8",
    )
    source_lines = source_path.read_text(encoding="utf-8").splitlines()

    draft_dir = root / ".expertwiki" / "drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / "shared-concept.md"
    draft_body = (
        "# Shared Concept\n\n"
        "Source-backed sentence.^[raw/sources/note.md:11-11, raw/sources/note.md:13-14]\n"
    )
    draft_text = render_frontmatter(
        {
            "type": "draft_page",
            "concept_id": "1",
            "title": "Shared Concept",
            "description": "A concept supported by a local source.",
            "entity_type": "topic",
            "tags": ["compiler", "knowledge"],
            "sources": ["/raw/sources/note.md"],
            "draft_status": "pending_review",
        },
        draft_body,
    )
    draft_path.write_text(draft_text, encoding="utf-8")

    page_path = root / "wiki" / "topics" / "published-concept.md"
    page_path.write_text(
        render_frontmatter(
            {
                "type": "wiki_page",
                "title": "Published Concept",
                "description": "An approved page.",
                "entity_type": "topic",
                "tags": ["published"],
                "sources": ["/raw/sources/note.md"],
                "status": "published",
            },
            "# Published Concept\n\nApproved knowledge.\n",
        ),
        encoding="utf-8",
    )

    state_path = root / ".expertwiki" / "state.sqlite"
    with StateDB(state_path) as state:
        state.upsert_source(
            path="raw/sources/note.md",
            title="Test Source",
            resource="local-note.md",
            publisher="Test",
            content_hash=hashlib.sha256(source_path.read_bytes()).hexdigest(),
            line_count=len(source_lines),
            status="preserved",
        )
        state.record_analysis(
            source_path="raw/sources/note.md",
            summary="Test source summary.",
            quality="high",
            language="en",
            suggested_topics=["knowledge"],
            named_references=[],
            extractor_version="test",
            prompt_version="test",
            concepts=[
                {
                    "name": "Shared Concept",
                    "aliases": [],
                    "summary": "A concept supported by a local source.",
                    "tags": ["compiler", "knowledge"],
                    "confidence": 0.9,
                    "provenance_state": "extracted",
                    "source_ranges": ["13-14"],
                    "contradicted_by": [],
                    "extraction_hash": "shared-extraction",
                }
            ],
        )
        shared = state.get_concept("Shared Concept")
        assert shared is not None
        state.upsert_draft(
            concept_id=shared.id,
            path=".expertwiki/drafts/shared-concept.md",
            content_hash=hashlib.sha256(draft_text.encode("utf-8")).hexdigest(),
            source_hashes={"raw/sources/note.md": "source-hash"},
            prompt_hash="prompt-hash",
            model="test",
        )
        published = state.ensure_concept(
            "Published Concept",
            summary="An approved page.",
            tags=["published"],
            status="clean",
        )
        state.import_source_concept("raw/sources/note.md", published.id)
        page_text = page_path.read_text(encoding="utf-8")
        state.upsert_article(
            concept_id=published.id,
            path="wiki/topics/published-concept.md",
            content_hash=hashlib.sha256(page_text.encode("utf-8")).hexdigest(),
            source_hashes={"raw/sources/note.md": "source-hash"},
            status="published",
            managed=True,
            compiled_at="2026-07-19T00:00:00Z",
            approved_at="2026-07-19T00:00:00Z",
        )
