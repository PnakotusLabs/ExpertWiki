from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .okf import OkfConcept


@dataclass(frozen=True)
class RawSource:
    id: str
    path: str
    title: str
    resource: str
    publisher: str
    retrieved_at: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "title": self.title,
            "resource": self.resource,
            "publisher": self.publisher,
            "retrieved_at": self.retrieved_at,
        }

    @classmethod
    def from_concept(cls, concept: OkfConcept) -> "RawSource":
        if concept.type != "raw_source":
            raise ValueError(f"Expected raw_source concept, got {concept.type}")
        metadata = concept.metadata
        return cls(
            id=concept.id.removeprefix("raw/sources/"),
            path=concept.path,
            title=_metadata_str(metadata, "title", concept.id),
            resource=_metadata_str(metadata, "resource", concept.path),
            publisher=_metadata_str(metadata, "publisher", "Unknown"),
            retrieved_at=_metadata_str(metadata, "retrieved_at", ""),
            body=concept.body,
        )


@dataclass(frozen=True)
class WikiPage:
    id: str
    path: str
    title: str
    description: str
    tags: list[str]
    sources: list[str]
    body: str
    updated_at: str

    def to_dict(self, sources: dict[str, RawSource] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "path": self.path,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "sources": self.sources,
            "updated_at": self.updated_at,
            "body": self.body,
        }
        if sources is not None:
            payload["source_records"] = [
                sources[source_id].to_dict()
                for source_id in self.sources
                if source_id in sources
            ]
        return payload

    @classmethod
    def from_concept(cls, concept: OkfConcept) -> "WikiPage":
        if concept.type != "wiki_page":
            raise ValueError(f"Expected wiki_page concept, got {concept.type}")
        metadata = concept.metadata
        return cls(
            id=concept.id.removeprefix("wiki/"),
            path=concept.path,
            title=_metadata_str(metadata, "title", concept.id),
            description=_metadata_str(metadata, "description", ""),
            tags=[str(tag) for tag in _metadata_list(metadata, "tags")],
            sources=[_source_id_from_path(str(path)) for path in _metadata_list(metadata, "sources")],
            body=concept.body,
            updated_at=_metadata_str(metadata, "updated_at", ""),
        )


def _metadata_str(raw: dict[str, Any], key: str, default: str) -> str:
    value = raw.get(key)
    if value is None:
        return default
    return str(value)


def _metadata_list(raw: dict[str, Any], key: str) -> list[Any]:
    value = raw.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Frontmatter field must be a list: {key}")
    return value


def _source_id_from_path(path: str) -> str:
    normalized = path.removeprefix("/").removesuffix(".md")
    return normalized.removeprefix("raw/sources/")
