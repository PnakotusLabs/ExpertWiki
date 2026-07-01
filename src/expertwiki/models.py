from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .okf import OkfConcept


ALLOWED_STATUSES = {"draft", "reviewed", "verified", "disputed", "stale", "rejected"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str
    publisher: str
    published_at: str | None
    retrieved_at: str
    type: str

@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    topic: str
    entities: list[str]
    status: str
    confidence: str
    sources: list[dict[str, Any]]
    reviewers: list[dict[str, Any]]
    last_verified_at: str

    def to_dict(self, source_records: dict[str, Source] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "text": self.text,
            "topic": self.topic,
            "entities": self.entities,
            "status": self.status,
            "confidence": self.confidence,
            "sources": self.sources,
            "reviewers": self.reviewers,
            "last_verified_at": self.last_verified_at,
        }
        if source_records is not None:
            payload["source_records"] = [
                source_records[source_ref["source_id"]].__dict__
                for source_ref in self.sources
                if source_ref.get("source_id") in source_records
            ]
        return payload

    @classmethod
    def from_okf_concept(cls, concept: OkfConcept) -> "Claim":
        if concept.type != "Verified Claim":
            raise ValueError(f"Expected Verified Claim concept, got {concept.type}")

        metadata = concept.metadata
        status = _required_metadata_str(metadata, "status")
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"Unsupported claim status: {status}")

        confidence = _required_metadata_str(metadata, "confidence")
        if confidence not in ALLOWED_CONFIDENCE:
            raise ValueError(f"Unsupported claim confidence: {confidence}")

        source_paths = _required_metadata_list(metadata, "sources")
        reviewers = [
            _parse_reviewer(str(reviewer))
            for reviewer in _required_metadata_list(metadata, "reviewers")
        ]
        if not reviewers:
            raise ValueError("Claim must include at least one reviewer")

        return cls(
            id=concept.id.removeprefix("claims/"),
            text=_extract_claim_text(concept.body),
            topic=_topic_from_metadata(metadata, concept.id),
            entities=[str(tag) for tag in metadata.get("tags", [])],
            status=status,
            confidence=confidence,
            sources=[
                {
                    "source_id": _source_id_from_path(str(source_path)),
                    "url": str(source_path),
                    "locator": "# Citations",
                }
                for source_path in source_paths
            ],
            reviewers=reviewers,
            last_verified_at=_required_metadata_str(metadata, "verified_at"),
        )


def source_from_okf_concept(concept: OkfConcept) -> Source:
    metadata = concept.metadata
    return Source(
        id=_source_id_from_path(concept.path),
        title=_metadata_str(metadata, "title", concept.id),
        url=_metadata_str(metadata, "resource", concept.path),
        publisher=_metadata_str(metadata, "publisher", "Unknown"),
        published_at=_optional_metadata_str(metadata, "published_at"),
        retrieved_at=_metadata_str(metadata, "retrieved_at", ""),
        type=_metadata_str(metadata, "type", "Source"),
    )


def _required_metadata_str(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing required frontmatter string field: {key}")
    return value


def _metadata_str(raw: dict[str, Any], key: str, default: str) -> str:
    value = raw.get(key)
    if value is None:
        return default
    return str(value)


def _optional_metadata_str(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    return str(value)


def _required_metadata_list(raw: dict[str, Any], key: str) -> list[Any]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Missing required frontmatter list field: {key}")
    return value


def _parse_reviewer(value: str) -> dict[str, str]:
    if ":" not in value:
        raise ValueError(f"Reviewer must use id:method format: {value}")
    reviewer_id, method = value.split(":", 1)
    return {"id": reviewer_id, "method": method}


def _extract_claim_text(body: str) -> str:
    lines = body.splitlines()
    in_claim = False
    claim_lines: list[str] = []
    for line in lines:
        if line.startswith("# "):
            if in_claim:
                break
            in_claim = line.strip() == "# Claim"
            continue
        if in_claim:
            claim_lines.append(line)

    text = " ".join(line.strip() for line in claim_lines if line.strip())
    if not text:
        raise ValueError("Verified Claim concept must include a # Claim section")
    return text


def _topic_from_metadata(metadata: dict[str, Any], concept_id: str) -> str:
    tags = metadata.get("tags")
    if isinstance(tags, list) and tags:
        return str(tags[0])
    return concept_id.split("/")[-1]


def _source_id_from_path(path: str) -> str:
    normalized = path.removeprefix("/").removesuffix(".md")
    return normalized.replace("/", "_").replace("-", "_")
