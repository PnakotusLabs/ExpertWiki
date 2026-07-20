from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import sqlite3
from typing import Any
from urllib.parse import parse_qs, urlparse
import webbrowser

from .compiler import approve_draft as approve_compiler_draft
from .compiler import reject_draft as reject_compiler_draft
from .compiler import return_article_to_draft as return_compiler_article_to_draft
from .compiler import return_rejected_to_draft as return_compiler_rejected_to_draft
from .okf import OkfConcept, RESERVED_FILENAMES, parse_okf_concept
from .publish import markdown_hash, published_page_hashes


ASSET_DIR = Path(__file__).with_name("viewer_assets")
CITATION_MARKER_PATTERN = re.compile(r"\^\[([^\]]+)\]")
CITATION_ENTRY_PATTERN = re.compile(r"([^,\[\]]+?\.md):(\d+)-(\d+)")
DRAFT_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
MAX_JSON_BODY_BYTES = 32_768
ASSETS = {
    "/assets/viewer.css": (ASSET_DIR / "viewer.css", "text/css"),
    "/assets/viewer.js": (ASSET_DIR / "viewer.js", "text/javascript"),
    "/assets/vendor/cytoscape.min.js": (
        ASSET_DIR / "vendor" / "cytoscape.min.js",
        "text/javascript",
    ),
}


class ViewerNotFoundError(ValueError):
    pass


class ViewerStore:
    """Local projection of an ExpertWiki bundle for the viewer."""

    def __init__(self, bundle_dir: str | Path) -> None:
        self.root = Path(bundle_dir).expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError(f"ExpertWiki bundle does not exist: {self.root}")

    def summary(self) -> dict[str, Any]:
        documents = self._documents()
        graph = self.graph()
        return {
            "title": _bundle_title(self.root),
            "root": str(self.root),
            "source_count": sum(1 for item in documents.values() if item.type == "raw_source"),
            "draft_count": len(self._drafts()),
            "approved_count": len(self._approved()),
            "published_count": len(self._published()),
            "rejected_count": len(self._rejected()),
            "concept_count": graph["counts"]["concepts"],
            "graph_edge_count": graph["counts"]["edges"],
        }

    def list_documents(self, kind: str) -> list[dict[str, Any]]:
        concepts = self._concepts_for_kind(kind)
        output = [_document_summary(concept, kind) for concept in concepts]
        return sorted(output, key=lambda item: (str(item["title"]).casefold(), str(item["id"])))

    def get_document(self, kind: str, document_id: str) -> dict[str, Any]:
        concept = self._find_document(kind, document_id)
        payload = _document_summary(concept, kind)
        payload["body"] = concept.body
        payload["metadata"] = concept.metadata
        payload["citations"] = _citations(concept.body)
        return payload

    def approve_draft(self, document_id: str, *, force: bool = False) -> dict[str, Any]:
        self._find_document("draft", document_id)
        result = approve_compiler_draft(self.root, document_id, force=force)
        return {
            "action": "approved",
            "id": document_id,
            "title": result.title,
            "draft_path": result.draft_path,
            "page_path": result.page_path,
            "approved_id": result.page_path.removeprefix("wiki/").removesuffix(".md"),
            "summary": self.summary(),
        }

    def reject_draft(self, document_id: str, *, feedback: str) -> dict[str, Any]:
        self._find_document("draft", document_id)
        result = reject_compiler_draft(self.root, document_id, feedback=feedback)
        return {
            "action": "rejected",
            "id": document_id,
            "title": result.title,
            "draft_path": result.draft_path,
            "rejected_path": result.rejected_path,
            "rejected_id": result.rejected_path.removeprefix(".expertwiki/rejected/").removesuffix(".md"),
            "blocked": result.blocked,
            "summary": self.summary(),
        }

    def return_approved_to_draft(self, document_id: str) -> dict[str, Any]:
        self._find_document("approved", document_id)
        result = return_compiler_article_to_draft(self.root, document_id)
        return {
            "action": "drafted",
            "id": document_id,
            "title": result.title,
            "page_path": result.page_path,
            "draft_path": result.draft_path,
            "draft_id": result.draft_path.removeprefix(".expertwiki/drafts/").removesuffix(".md"),
            "summary": self.summary(),
        }

    def return_rejected_to_draft(self, document_id: str) -> dict[str, Any]:
        self._find_document("rejected", document_id)
        result = return_compiler_rejected_to_draft(self.root, document_id)
        return {
            "action": "drafted",
            "id": document_id,
            "title": result.title,
            "rejected_path": result.page_path,
            "draft_path": result.draft_path,
            "draft_id": result.draft_path.removeprefix(".expertwiki/drafts/").removesuffix(".md"),
            "summary": self.summary(),
        }

    def source_excerpt(self, source_path: str, start: int, end: int) -> dict[str, Any]:
        if start < 1 or end < start or end - start > 199:
            raise ValueError("Source range must be positive, ordered, and no longer than 200 lines.")
        normalized, path = self._safe_source_path(source_path)
        lines = path.read_text(encoding="utf-8").splitlines()
        if start > len(lines) or end > len(lines):
            raise ValueError(f"Source range {start}-{end} exceeds {len(lines)} lines.")
        concept = parse_okf_concept(self.root, path)
        return {
            "path": normalized,
            "title": str(concept.metadata.get("title", path.stem)),
            "start": start,
            "end": end,
            "line_count": len(lines),
            "lines": [
                {"number": number, "text": lines[number - 1]}
                for number in range(start, end + 1)
            ],
        }

    def graph(self, focus: str | None = None) -> dict[str, Any]:
        state_path = self.root / ".expertwiki" / "state.sqlite"
        if not state_path.is_file():
            return {"nodes": [], "edges": [], "counts": {"sources": 0, "concepts": 0, "edges": 0}}

        connection = sqlite3.connect(state_path.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            source_rows = connection.execute(
                "SELECT path, title, status FROM sources WHERE status != 'deleted' ORDER BY path"
            ).fetchall()
            concept_rows = connection.execute(
                """
                SELECT id, name, slug, summary, tags_json, confidence, status
                FROM concepts ORDER BY name_key
                """
            ).fetchall()
            relation_rows = connection.execute(
                """
                SELECT sc.source_path, sc.concept_id, sc.source_ranges_json, sc.confidence
                FROM source_concepts sc
                JOIN sources s ON s.path = sc.source_path
                WHERE s.status != 'deleted'
                ORDER BY sc.source_path, sc.concept_id
                """
            ).fetchall()
            draft_ids = {
                int(row["concept_id"])
                for row in connection.execute(
                    "SELECT concept_id FROM drafts WHERE status = 'pending_review'"
                )
            }
            article_paths = {
                int(row["concept_id"]): str(row["path"])
                for row in connection.execute(
                    "SELECT concept_id, path FROM articles WHERE status IN ('published', 'stale')"
                )
            }
        finally:
            connection.close()

        source_counts: dict[int, int] = {}
        for row in relation_rows:
            concept_id = int(row["concept_id"])
            source_counts[concept_id] = source_counts.get(concept_id, 0) + 1

        nodes = [
            {
                "id": f"source:{row['path']}",
                "type": "source",
                "label": str(row["title"]),
                "path": str(row["path"]),
                "status": str(row["status"]),
            }
            for row in source_rows
        ]
        for row in concept_rows:
            concept_id = int(row["id"])
            if concept_id in article_paths:
                document_id = article_paths[concept_id].removeprefix("wiki/").removesuffix(".md")
                if self._path_is_published(article_paths[concept_id]):
                    artifact_status = "published"
                    document_kind = "published"
                else:
                    artifact_status = "approved"
                    document_kind = "approved"
            elif concept_id in draft_ids:
                artifact_status = "pending_review"
                document_kind = "draft"
                document_id = str(row["slug"])
            else:
                artifact_status = str(row["status"])
                document_kind = None
                document_id = None
            nodes.append(
                {
                    "id": f"concept:{concept_id}",
                    "type": "concept",
                    "label": str(row["name"]),
                    "slug": str(row["slug"]),
                    "summary": str(row["summary"]),
                    "tags": _json_list(row["tags_json"]),
                    "confidence": float(row["confidence"]),
                    "status": artifact_status,
                    "document_kind": document_kind,
                    "document_id": document_id,
                    "source_count": source_counts.get(concept_id, 0),
                }
            )

        edges = []
        for row in relation_rows:
            concept_id = int(row["concept_id"])
            source_path = str(row["source_path"])
            edges.append(
                {
                    "id": f"supports:{source_path}:{concept_id}",
                    "source": f"source:{source_path}",
                    "target": f"concept:{concept_id}",
                    "type": "supports",
                    "source_path": source_path,
                    "source_ranges": _json_list(row["source_ranges_json"]),
                    "confidence": float(row["confidence"]),
                }
            )

        if focus:
            node_ids = {str(node["id"]) for node in nodes}
            if focus not in node_ids:
                raise ViewerNotFoundError(f"Graph node not found: {focus}")
            focused_edges = [
                edge for edge in edges if focus in {str(edge["source"]), str(edge["target"])}
            ]
            visible_ids = {focus}
            for edge in focused_edges:
                visible_ids.update({str(edge["source"]), str(edge["target"])})
            nodes = [node for node in nodes if str(node["id"]) in visible_ids]
            edges = focused_edges

        return {
            "nodes": nodes,
            "edges": edges,
            "counts": {
                "sources": sum(1 for node in nodes if node["type"] == "source"),
                "concepts": sum(1 for node in nodes if node["type"] == "concept"),
                "edges": len(edges),
            },
        }

    def _documents(self) -> dict[str, OkfConcept]:
        concepts: dict[str, OkfConcept] = {}
        for directory in (self.root / "raw" / "sources", self.root / "wiki"):
            for path in self._safe_markdown_files(directory):
                if path.name in RESERVED_FILENAMES:
                    continue
                concept = parse_okf_concept(self.root, path)
                concepts[concept.id] = concept
        return concepts

    def _drafts(self) -> list[OkfConcept]:
        draft_dir = self.root / ".expertwiki" / "drafts"
        return [parse_okf_concept(self.root, path) for path in self._safe_markdown_files(draft_dir)]

    def _approved(self) -> list[OkfConcept]:
        return [
            concept
            for concept in self._wiki_pages()
            if not self._path_is_published(concept.path.removeprefix("/"))
        ]

    def _published(self) -> list[OkfConcept]:
        return [
            concept
            for concept in self._wiki_pages()
            if self._path_is_published(concept.path.removeprefix("/"))
        ]

    def _rejected(self) -> list[OkfConcept]:
        rejected_dir = self.root / ".expertwiki" / "rejected"
        return [
            parse_okf_concept(self.root, path)
            for path in self._safe_markdown_files(rejected_dir)
        ]

    def _wiki_pages(self) -> list[OkfConcept]:
        return [concept for concept in self._documents().values() if concept.type == "wiki_page"]

    def _path_is_published(self, relative_path: str) -> bool:
        expected_hash = published_page_hashes(self.root).get(relative_path)
        if not expected_hash:
            return False
        path = self.root / relative_path
        if not path.is_file():
            return False
        return markdown_hash(path.read_text(encoding="utf-8")) == expected_hash

    def _safe_markdown_files(self, directory: Path) -> list[Path]:
        if not directory.is_dir():
            return []
        resolved_directory = directory.resolve()
        output = []
        for path in sorted(directory.rglob("*.md")):
            try:
                path.resolve().relative_to(resolved_directory)
            except ValueError as exc:
                raise ValueError(f"Markdown path escapes bundle directory: {path}") from exc
            output.append(path)
        return output

    def _concepts_for_kind(self, kind: str) -> list[OkfConcept]:
        if kind == "draft":
            return self._drafts()
        if kind == "approved":
            return self._approved()
        if kind == "published":
            return self._published()
        if kind == "rejected":
            return self._rejected()
        raise ValueError("Document kind must be 'draft', 'approved', 'published', or 'rejected'.")

    def _find_document(self, kind: str, document_id: str) -> OkfConcept:
        if kind in {"draft", "rejected"} and not DRAFT_ID_PATTERN.fullmatch(document_id):
            raise ValueError(f"Invalid {kind} id.")
        for concept in self._concepts_for_kind(kind):
            if _document_id(concept, kind) == document_id:
                return concept
        raise ViewerNotFoundError(f"{kind.title()} document not found: {document_id}")

    def _safe_source_path(self, source_path: str) -> tuple[str, Path]:
        normalized = source_path.removeprefix("/")
        if not normalized.startswith("raw/sources/") or not normalized.endswith(".md"):
            raise ValueError("Source path must point to raw/sources/*.md.")
        source_root = (self.root / "raw" / "sources").resolve()
        candidate = (self.root / normalized).resolve()
        try:
            candidate.relative_to(source_root)
        except ValueError as exc:
            raise ValueError("Source path escapes raw/sources/.") from exc
        if not candidate.is_file():
            raise ViewerNotFoundError(f"Source not found: {normalized}")
        return normalized, candidate


class ExpertWikiViewerHandler(BaseHTTPRequestHandler):
    store: ViewerStore

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self._file(ASSET_DIR / "index.html", "text/html")
                return
            if parsed.path == "/favicon.ico":
                self._respond(
                    HTTPStatus.NO_CONTENT,
                    b"",
                    "image/x-icon",
                    cache="public, max-age=86400",
                )
                return
            if parsed.path in ASSETS:
                path, content_type = ASSETS[parsed.path]
                self._file(path, content_type)
                return
            if parsed.path == "/health":
                self._json(HTTPStatus.OK, {"status": "ok", "root": str(self.store.root)})
                return
            if parsed.path == "/api/summary":
                self._json(HTTPStatus.OK, self.store.summary())
                return
            if parsed.path == "/api/documents":
                params = parse_qs(parsed.query)
                kind = params.get("kind", ["draft"])[0]
                self._json(HTTPStatus.OK, {"kind": kind, "documents": self.store.list_documents(kind)})
                return
            if parsed.path == "/api/document":
                params = parse_qs(parsed.query)
                kind = _required_param(params, "kind")
                document_id = _required_param(params, "id")
                self._json(HTTPStatus.OK, self.store.get_document(kind, document_id))
                return
            if parsed.path == "/api/source":
                params = parse_qs(parsed.query)
                source_path = _required_param(params, "path")
                start = _positive_int(_required_param(params, "start"), "start")
                end = _positive_int(_required_param(params, "end"), "end")
                self._json(HTTPStatus.OK, self.store.source_excerpt(source_path, start, end))
                return
            if parsed.path == "/api/graph":
                params = parse_qs(parsed.query)
                focus = params.get("focus", [None])[0]
                self._json(HTTPStatus.OK, self.store.graph(focus))
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        except ViewerNotFoundError as exc:
            self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except (OSError, sqlite3.Error) as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Viewer read failed: {exc}"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/draft/approve":
                payload = _read_json_body(self)
                document_id = _json_string(payload, "id")
                force = _json_bool(payload, "force", default=False)
                self._json(HTTPStatus.OK, self.store.approve_draft(document_id, force=force))
                return
            if parsed.path == "/api/draft/reject":
                payload = _read_json_body(self)
                document_id = _json_string(payload, "id")
                feedback = _json_string(payload, "feedback")
                self._json(HTTPStatus.OK, self.store.reject_draft(document_id, feedback=feedback))
                return
            if parsed.path in {"/api/approved/draft", "/api/published/draft"}:
                payload = _read_json_body(self)
                document_id = _json_string(payload, "id")
                self._json(HTTPStatus.OK, self.store.return_approved_to_draft(document_id))
                return
            if parsed.path == "/api/rejected/draft":
                payload = _read_json_body(self)
                document_id = _json_string(payload, "id")
                self._json(HTTPStatus.OK, self.store.return_rejected_to_draft(document_id))
                return
            self._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "viewer_is_read_only"})
        except ViewerNotFoundError as exc:
            self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except (OSError, sqlite3.Error) as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Viewer write failed: {exc}"})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self._json(HTTPStatus.NOT_FOUND, {"error": "asset_not_found"})
            return
        payload = path.read_bytes()
        self._respond(HTTPStatus.OK, payload, f"{content_type}; charset=utf-8", cache="no-store")

    def _json(self, status: HTTPStatus, payload: Any) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._respond(status, encoded, "application/json; charset=utf-8", cache="no-store")

    def _respond(
        self,
        status: HTTPStatus,
        payload: bytes,
        content_type: str,
        *,
        cache: str,
    ) -> None:
        self.send_response(status.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(payload)


def create_viewer_server(
    bundle_dir: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    store = ViewerStore(bundle_dir)
    handler = type(
        "ConfiguredExpertWikiViewerHandler",
        (ExpertWikiViewerHandler,),
        {"store": store},
    )
    return ThreadingHTTPServer((host, port), handler)


def serve_viewer(
    bundle_dir: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    server = create_viewer_server(bundle_dir, host=host, port=port)
    actual_port = int(server.server_address[1])
    url = f"http://{host}:{actual_port}"
    print(f"ExpertWiki Viewer: {url}")
    print(f"Bundle: {Path(bundle_dir).expanduser().resolve()}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _document_summary(concept: OkfConcept, kind: str) -> dict[str, Any]:
    metadata = concept.metadata
    tags = metadata.get("tags", [])
    sources = metadata.get("sources", [])
    return {
        "id": _document_id(concept, kind),
        "path": concept.path.removeprefix("/"),
        "kind": kind,
        "title": str(metadata.get("title", Path(concept.path).stem)),
        "description": str(metadata.get("description", "")),
        "entity_type": str(metadata.get("entity_type", "topic")),
        "status": str(
            metadata.get("draft_status", "rejected" if kind == "rejected" else "pending_review")
            if kind in {"draft", "rejected"}
            else ("approved" if kind == "approved" else metadata.get("status", "published"))
        ),
        "tags": [str(value) for value in tags] if isinstance(tags, list) else [],
        "sources": [str(value).removeprefix("/") for value in sources]
        if isinstance(sources, list)
        else [],
        "updated_at": str(metadata.get("updated_at", metadata.get("compiled_at", ""))),
    }


def _document_id(concept: OkfConcept, kind: str) -> str:
    if kind in {"draft", "rejected"}:
        return Path(concept.path).stem
    return concept.id.removeprefix("wiki/")


def _citations(body: str) -> list[dict[str, Any]]:
    output = []
    seen_markers: set[str] = set()
    for marker_match in CITATION_MARKER_PATTERN.finditer(body):
        marker = marker_match.group(0)
        if marker in seen_markers:
            continue
        seen_markers.add(marker)
        for entry_match in CITATION_ENTRY_PATTERN.finditer(marker_match.group(1)):
            output.append(
                {
                    "id": f"citation-{len(output) + 1}",
                    "marker": marker,
                    "path": entry_match.group(1).strip().removeprefix("/"),
                    "start": int(entry_match.group(2)),
                    "end": int(entry_match.group(3)),
                }
            )
    return output


def _json_list(raw: Any) -> list[Any]:
    try:
        value = json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def _required_param(params: dict[str, list[str]], name: str) -> str:
    value = params.get(name, [""])[0].strip()
    if not value:
        raise ValueError(f"Missing query parameter: {name}")
    return value


def _positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"Query parameter {name} must be an integer.") from exc
    if parsed < 1:
        raise ValueError(f"Query parameter {name} must be positive.")
    return parsed


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    raw_length = handler.headers.get("Content-Length", "0")
    try:
        length = int(raw_length)
    except ValueError as exc:
        raise ValueError("Content-Length must be an integer.") from exc
    if length < 0:
        raise ValueError("Content-Length must be non-negative.")
    if length > MAX_JSON_BODY_BYTES:
        raise ValueError("JSON request body is too large.")
    raw_body = handler.rfile.read(length)
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Request body must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON request body must be an object.")
    return payload


def _json_string(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name, "")
    if not isinstance(value, str):
        raise ValueError(f"JSON field {name} must be a string.")
    value = value.strip()
    if not value:
        raise ValueError(f"Missing JSON field: {name}")
    return value


def _json_bool(payload: dict[str, Any], name: str, *, default: bool) -> bool:
    value = payload.get(name, default)
    if not isinstance(value, bool):
        raise ValueError(f"JSON field {name} must be a boolean.")
    return value


def _bundle_title(root: Path) -> str:
    instructions = root / "AGENTS.md"
    if instructions.is_file():
        for line in instructions.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].removesuffix(" Agent Instructions").strip()
    return root.name


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the local ExpertWiki Viewer")
    parser.add_argument("bundle_dir", nargs="?", default=str(Path.home() / ".expertwiki"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    arguments = parser.parse_args()
    serve_viewer(
        arguments.bundle_dir,
        host=arguments.host,
        port=arguments.port,
        open_browser=not arguments.no_open,
    )
