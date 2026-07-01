from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


RESERVED_FILENAMES = {"index.md", "log.md"}


@dataclass(frozen=True)
class OkfConcept:
    id: str
    path: str
    metadata: dict[str, Any]
    body: str

    @property
    def type(self) -> str:
        return str(self.metadata["type"])


def load_okf_concepts(bundle_dir: str | Path) -> dict[str, OkfConcept]:
    root = Path(bundle_dir)
    concepts: dict[str, OkfConcept] = {}
    for path in sorted(root.rglob("*.md")):
        if path.name in RESERVED_FILENAMES:
            continue
        concept = parse_okf_concept(root, path)
        concepts[concept.id] = concept
    return concepts


def parse_okf_concept(root: Path, path: Path) -> OkfConcept:
    text = path.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(text, path)
    relative_path = path.relative_to(root).as_posix()
    concept_id = relative_path.removesuffix(".md")
    return OkfConcept(
        id=concept_id,
        path=f"/{relative_path}",
        metadata=metadata,
        body=body.strip(),
    )


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"OKF concept missing frontmatter: {path}")

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
    if end_index is None:
        raise ValueError(f"OKF concept has unterminated frontmatter: {path}")

    metadata = _parse_simple_yaml(lines[1:end_index], path)
    concept_type = metadata.get("type")
    if not isinstance(concept_type, str) or not concept_type:
        raise ValueError(f"OKF concept missing required type field: {path}")

    body = "\n".join(lines[end_index + 1 :])
    return metadata, body


def _parse_simple_yaml(lines: list[str], path: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for line_number, raw_line in enumerate(lines, start=2):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Unsupported frontmatter line in {path}:{line_number}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Empty frontmatter key in {path}:{line_number}")
        metadata[key] = _parse_scalar(raw_value.strip())
    return metadata


def _parse_scalar(value: str) -> Any:
    if value == "":
        return None
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_strip_quotes(item.strip()) for item in inner.split(",")]
    return _strip_quotes(value)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
