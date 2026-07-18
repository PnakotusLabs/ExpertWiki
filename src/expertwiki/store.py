from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import RawSource, WikiPage
from .okf import load_okf_concepts


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class KnowledgeStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.sources, self.pages = self._load_bundle()

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "source_count": len(self.sources),
            "page_count": len(self.pages),
        }

    def get_page(self, page_id: str) -> dict[str, Any] | None:
        page = self.pages.get(page_id)
        if page is None:
            return None
        return page.to_dict(self.sources)

    def get_page_markdown(self, page_id: str) -> str | None:
        page = self.pages.get(page_id)
        if page is None:
            return None
        path = self.data_dir / page.path.removeprefix("/")
        return path.read_text(encoding="utf-8")

    def graph(self) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, str]] = []
        for page in self.pages.values():
            nodes.append(
                {
                    "id": page.id,
                    "type": "page",
                    "title": page.title,
                    "entity_type": page.entity_type,
                    "quality": page.quality,
                }
            )
            for source_id in page.sources:
                edges.append({"from": page.id, "to": source_id, "type": "cites"})
        for source in self.sources.values():
            nodes.append({"id": source.id, "type": "source", "title": source.title})
        return {"nodes": nodes, "edges": edges}

    def llms_txt(self) -> str:
        lines = [
            f"# {_bundle_title(self.data_dir)}",
            "",
            "> Source-backed expert and project knowledge for AI agents.",
            "",
            "This file indexes the Markdown knowledge cards in this bundle. Read the linked Markdown pages for the source-backed details.",
            "",
            "## Pages",
            "",
        ]
        for page in sorted(self.pages.values(), key=lambda item: item.id):
            lines.append(
                f"- [{page.title}](/pages/{page.id}.md): {page.description} "
                f"Type: {page.entity_type}; quality: {page.quality}."
            )
        lines.extend(
            [
                "",
                "## Optional",
                "",
                "- [Knowledge graph](/graph): JSON graph of knowledge cards, sources, and citation edges.",
            ]
        )
        return "\n".join(lines) + "\n"

    def search(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        scored: list[tuple[int, WikiPage]] = []
        for page in self.pages.values():
            score = _score_page(query, query_tokens, page)
            if score:
                scored.append((score, page))

        scored.sort(key=lambda item: (-item[0], item[1].id))
        return [
            {"score": score, "page": page.to_dict(self.sources)}
            for score, page in scored[:limit]
        ]

    def _load_bundle(self) -> tuple[dict[str, RawSource], dict[str, WikiPage]]:
        concepts = load_okf_concepts(self.data_dir)
        sources = {
            source.id: source
            for source in (
                RawSource.from_concept(concept)
                for concept in concepts.values()
                if concept.type == "raw_source"
            )
        }
        pages = {
            page.id: page
            for page in (
                WikiPage.from_concept(concept)
                for concept in concepts.values()
                if concept.type == "wiki_page"
            )
        }
        _validate_page_sources(sources, pages)
        return sources, pages


def _validate_page_sources(
    sources: dict[str, RawSource],
    pages: dict[str, WikiPage],
) -> None:
    missing_refs: list[str] = []
    for page in pages.values():
        for source_id in page.sources:
            if source_id not in sources:
                missing_refs.append(f"{page.id}:{source_id}")
    if missing_refs:
        joined = ", ".join(missing_refs)
        raise ValueError(f"Pages reference missing sources: {joined}")


def _tokens(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(text.lower()))


def _score_page(query: str, query_tokens: set[str], page: WikiPage) -> int:
    title_tokens = _tokens(page.title)
    id_tokens = _tokens(page.id)
    haystack = " ".join([page.title, page.description, page.body, *page.tags])
    score = len(query_tokens & _tokens(haystack))

    if query.strip().lower() == page.title.strip().lower():
        score += 10
    if query_tokens <= title_tokens:
        score += 5
    if query_tokens <= id_tokens:
        score += 3

    return score


def _bundle_title(root: Path) -> str:
    instructions = root / "AGENTS.md"
    if instructions.exists():
        for line in instructions.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].removesuffix(" Agent Instructions").strip()

    return root.name
