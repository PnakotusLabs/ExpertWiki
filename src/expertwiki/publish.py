from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .authoring import package_dry_run
from .concurrency import atomic_write_text
from .linting import lint_bundle
from .models import RawSource, WikiPage
from .okf import load_okf_concepts


PUBLISH_STATE_RELATIVE_PATH = ".expertwiki/publish-state.json"


@dataclass(frozen=True)
class PublishResult:
    endpoint: str
    bundle_title: str
    page_count: int
    status_code: int | None
    response: dict[str, Any] | None
    dry_run: bool


def build_publish_payload(bundle_dir: str | Path) -> dict[str, Any]:
    root = Path(bundle_dir)
    concepts = load_okf_concepts(root)
    sources = {
        RawSource.from_concept(concept).id: RawSource.from_concept(concept)
        for concept in concepts.values()
        if concept.type == "raw_source"
    }
    pages: list[dict[str, Any]] = []

    for concept in concepts.values():
        if concept.type != "wiki_page":
            continue

        page = WikiPage.from_concept(concept)
        raw_markdown = (root / concept.path.removeprefix("/")).read_text(encoding="utf-8")
        source_records = [
            sources[source_id].to_dict()
            for source_id in page.sources
            if source_id in sources
        ]
        pages.append(
            {
                "id": page.id,
                "path": page.path,
                "title": page.title,
                "description": page.description,
                "body": page.body,
                "markdown": raw_markdown,
                "metadata": {
                    "entity_type": page.entity_type,
                    "tags": page.tags,
                    "sources": [f"/raw/sources/{source}.md" for source in page.sources],
                    "source_records": source_records,
                    "status": page.status,
                    "quality": page.quality,
                    "license": page.license,
                    "source_updated_at": page.source_updated_at,
                    "last_reviewed_at": page.last_reviewed_at,
                    "updated_at": page.updated_at,
                },
            }
        )

    return {
        "bundle_title": _bundle_title(root),
        "pages": pages,
    }


def publish_bundle(
    bundle_dir: str | Path,
    *,
    endpoint: str,
    token: str,
    dry_run: bool = False,
) -> PublishResult:
    lint_result = lint_bundle(bundle_dir)
    if not lint_result.ok:
        raise ValueError("Cannot publish bundle with lint issues.")

    package_result = package_dry_run(bundle_dir)
    if not package_result.ok:
        raise ValueError("Cannot publish bundle that fails package preflight.")

    payload = build_publish_payload(bundle_dir)
    page_count = len(payload["pages"])
    if page_count == 0:
        raise ValueError("Cannot publish bundle with no wiki pages.")

    if dry_run:
        return PublishResult(
            endpoint=endpoint,
            bundle_title=payload["bundle_title"],
            page_count=page_count,
            status_code=None,
            response=None,
            dry_run=True,
        )

    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "expertwiki-cli/0.1.0",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            parsed_response = json.loads(response_body) if response_body else {}
            _write_publish_state(
                bundle_dir,
                endpoint=endpoint,
                bundle_title=payload["bundle_title"],
                response=parsed_response,
                pages=payload["pages"],
            )
            return PublishResult(
                endpoint=endpoint,
                bundle_title=payload["bundle_title"],
                page_count=page_count,
                status_code=response.status,
                response=parsed_response,
                dry_run=False,
            )
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"Publish failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise ValueError(f"Publish failed: {exc.reason}") from exc


def _bundle_title(root: Path) -> str:
    index_path = root / "index.md"
    if not index_path.exists():
        return "ExpertWiki"
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip() or "ExpertWiki"
    return "ExpertWiki"


def publish_state_path(bundle_dir: str | Path) -> Path:
    return Path(bundle_dir) / PUBLISH_STATE_RELATIVE_PATH


def read_publish_state(bundle_dir: str | Path) -> dict[str, Any]:
    path = publish_state_path(bundle_dir)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Publish state is invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Publish state must be a JSON object: {path}")
    return payload


def published_page_hashes(bundle_dir: str | Path) -> dict[str, str]:
    payload = read_publish_state(bundle_dir)
    pages = payload.get("pages", [])
    if not isinstance(pages, list):
        return {}
    output: dict[str, str] = {}
    for item in pages:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        content_hash = item.get("content_hash")
        if isinstance(path, str) and isinstance(content_hash, str):
            output[path] = content_hash
    return output


def markdown_hash(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def _write_publish_state(
    bundle_dir: str | Path,
    *,
    endpoint: str,
    bundle_title: str,
    response: dict[str, Any],
    pages: list[dict[str, Any]],
) -> None:
    records = []
    for page in pages:
        markdown = page.get("markdown")
        path = page.get("path")
        if not isinstance(markdown, str) or not isinstance(path, str):
            continue
        normalized_path = path.removeprefix("/")
        records.append(
            {
                "id": str(page.get("id", "")),
                "path": normalized_path,
                "title": str(page.get("title", "")),
                "content_hash": markdown_hash(markdown),
            }
        )
    payload = {
        "version": 1,
        "endpoint": endpoint,
        "bundle_title": bundle_title,
        "published_at": _timestamp(),
        "response": response,
        "pages": records,
    }
    atomic_write_text(
        publish_state_path(bundle_dir),
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
