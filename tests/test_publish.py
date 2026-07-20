import contextlib
import io
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from expertwiki.authoring import create_page, ingest_source, init_bundle
from expertwiki.cli import main
from expertwiki.publish import build_publish_payload, publish_bundle, publish_state_path


class PublishTest(unittest.TestCase):
    def test_build_publish_payload_includes_wiki_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_page(Path(temp_dir))

            payload = build_publish_payload(root)

            self.assertTrue(payload["bundle_title"])
            self.assertEqual(len(payload["pages"]), 1)
            page = payload["pages"][0]
            self.assertEqual(page["id"], "topics/example")
            self.assertEqual(page["title"], "Example")
            self.assertIn("type: wiki_page", page["markdown"])
            self.assertEqual(page["metadata"]["sources"], ["/raw/sources/source.md"])
            self.assertEqual(page["metadata"]["source_records"][0]["title"], "Source")
            self.assertTrue(page["metadata"]["source_records"][0]["resource"])

    def test_publish_dry_run_skips_http_upload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_page(Path(temp_dir))

            result = publish_bundle(
                root,
                endpoint="http://example.test/api/cli/publish",
                token="secret",
                dry_run=True,
            )

            self.assertTrue(result.dry_run)
            self.assertEqual(result.page_count, 1)
            self.assertIsNone(result.status_code)
            self.assertFalse(publish_state_path(root).exists())

    def test_publish_success_records_uploaded_page_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_page(Path(temp_dir))
            server = _PublishTestServer()
            try:
                result = publish_bundle(
                    root,
                    endpoint=server.endpoint,
                    token="secret",
                )
            finally:
                server.close()

            self.assertFalse(result.dry_run)
            self.assertEqual(result.status_code, 200)
            state = json.loads(publish_state_path(root).read_text(encoding="utf-8"))
            self.assertEqual(state["endpoint"], server.endpoint)
            self.assertEqual(state["pages"][0]["path"], "wiki/topics/example.md")
            self.assertTrue(state["pages"][0]["content_hash"])

    def test_cli_publish_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _bundle_with_page(Path(temp_dir))
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "publish",
                        str(root),
                        "--endpoint",
                        "http://example.test/api/cli/publish",
                        "--dry-run",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("Publish dry-run OK", output.getvalue())


def _bundle_with_page(root: Path) -> Path:
    init_bundle(root, title="Publish Wiki")
    source_file = root.parent / "source.md"
    source_file.write_text("# Source\n\nEvidence.", encoding="utf-8")
    ingest_source(root, str(source_file), title="Source", publisher="Tester", slug="source")
    create_page(
        root,
        "wiki/topics/example.md",
        title="Example",
        description="Example page.",
        sources=["source"],
        tags=["example"],
    )
    return root


class _PublishHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        self.server.received_payload = json.loads(self.rfile.read(length).decode("utf-8"))  # type: ignore[attr-defined]
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class _PublishTestServer:
    def __init__(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _PublishHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_address[1]}/api/cli/publish"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
