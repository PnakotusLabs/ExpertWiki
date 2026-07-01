from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import Claim, Source, source_from_okf_concept
from .okf import load_okf_concepts


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class KnowledgeStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.sources, self.claims = self._load_okf_bundle()

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "source_count": len(self.sources),
            "claim_count": len(self.claims),
        }

    def get_claim(self, claim_id: str) -> dict[str, Any] | None:
        claim = self.claims.get(claim_id)
        if claim is None:
            return None
        return claim.to_dict(self.sources)

    def search(
        self,
        query: str,
        *,
        status: str | None = "verified",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        scored: list[tuple[int, Claim]] = []
        for claim in self.claims.values():
            if status is not None and claim.status != status:
                continue
            haystack = " ".join([claim.text, claim.topic, *claim.entities])
            score = _score(query_tokens, _tokens(haystack))
            if score:
                scored.append((score, claim))

        scored.sort(key=lambda item: (-item[0], item[1].id))
        return [
            {"score": score, "claim": claim.to_dict(self.sources)}
            for score, claim in scored[:limit]
        ]

    def _load_okf_bundle(self) -> tuple[dict[str, Source], dict[str, Claim]]:
        concepts = load_okf_concepts(self.data_dir)
        sources = {
            source_from_okf_concept(concept).id: source_from_okf_concept(concept)
            for concept in concepts.values()
            if concept.type == "Source"
        }
        claims = {
            claim.id: claim
            for claim in (
                Claim.from_okf_concept(concept)
                for concept in concepts.values()
                if concept.type == "Verified Claim"
            )
        }
        self.sources = sources
        self._validate_claim_sources(claims)
        return sources, claims

    def _validate_claim_sources(self, claims: dict[str, Claim]) -> None:
        missing_refs: list[str] = []
        for claim in claims.values():
            for source_ref in claim.sources:
                source_id = source_ref.get("source_id")
                if source_id not in self.sources:
                    missing_refs.append(f"{claim.id}:{source_id}")
        if missing_refs:
            joined = ", ".join(missing_refs)
            raise ValueError(f"Claims reference missing sources: {joined}")


def _tokens(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(text.lower()))


def _score(query_tokens: set[str], document_tokens: set[str]) -> int:
    return len(query_tokens & document_tokens)
