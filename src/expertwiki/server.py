from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .store import KnowledgeStore


class ExpertWikiHandler(BaseHTTPRequestHandler):
    store: KnowledgeStore

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json(HTTPStatus.OK, self.store.health())
            return

        if parsed.path == "/search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            status = params.get("status", ["verified"])[0]
            limit = _parse_limit(params.get("limit", ["10"])[0])
            self._json(
                HTTPStatus.OK,
                {
                    "query": query,
                    "status": status,
                    "results": self.store.search(query, status=status, limit=limit),
                },
            )
            return

        if parsed.path.startswith("/claims/"):
            claim_id = parsed.path.removeprefix("/claims/")
            claim = self.store.get_claim(claim_id)
            if claim is None:
                self._json(HTTPStatus.NOT_FOUND, {"error": "claim_not_found"})
                return
            self._json(HTTPStatus.OK, claim)
            return

        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def create_server(host: str, port: int, store: KnowledgeStore) -> ThreadingHTTPServer:
    handler = type("ConfiguredExpertWikiHandler", (ExpertWikiHandler,), {"store": store})
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ExpertWiki prototype API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args()

    store = KnowledgeStore(args.data_dir)
    server = create_server(args.host, args.port, store)
    print(f"ExpertWiki API listening on http://{args.host}:{args.port}")
    server.serve_forever()


def _parse_limit(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        return 10
    return max(1, min(parsed, 50))


if __name__ == "__main__":
    main()
