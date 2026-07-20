from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


RESERVED_FILENAMES = {"AGENTS.md", "index.md", "log.md"}


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
        if any(part.startswith(".") for part in path.relative_to(root).parts[:-1]):
            continue
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
        raise ValueError(f"Markdown concept missing frontmatter: {path}")

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
    if end_index is None:
        raise ValueError(f"Markdown concept has unterminated frontmatter: {path}")

    metadata = _parse_simple_yaml(lines[1:end_index], path)
    concept_type = metadata.get("type")
    if not isinstance(concept_type, str) or not concept_type:
        raise ValueError(f"Markdown concept missing required type field: {path}")

    body = "\n".join(lines[end_index + 1 :])
    return metadata, body


def render_frontmatter(metadata: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        lines.extend(_render_field(key, value))
    lines.append("---")
    lines.append("")
    lines.append(body.strip())
    lines.append("")
    return "\n".join(lines)


def _render_field(key: str, value: Any) -> list[str]:
    if isinstance(value, list):
        if not value:
            return [f"{key}: []"]
        rendered = [f"{key}:"]
        rendered.extend(f"  - {_render_scalar(item)}" for item in value)
        return rendered
    return [f"{key}: {_render_scalar(value)}"]


def _render_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    if not text:
        return ""
    if any(char in text for char in [":", "#", "[", "]", "{", "}", "\n"]) or text != text.strip():
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def _parse_simple_yaml(lines: list[str], path: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    current_key: str | None = None
    for line_number, raw_line in enumerate(lines, start=2):
        if raw_line.startswith("  - ") and current_key:
            current_value = metadata.setdefault(current_key, [])
            if current_value == "":
                current_value = []
                metadata[current_key] = current_value
            if not isinstance(current_value, list):
                raise ValueError(
                    f"Frontmatter field is not a list in {path}:{line_number}"
                )
            current_value.append(_parse_scalar(raw_line[4:].strip()))
            continue

        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Unsupported frontmatter line in {path}:{line_number}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Empty frontmatter key in {path}:{line_number}")
        current_key = key
        metadata[key] = _parse_scalar(raw_value.strip())
    return metadata


def _parse_scalar(value: str) -> Any:
    if value == "":
        return ""
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in _split_inline_list(inner)]
    return _strip_quotes(value)


def _split_inline_list(value: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    for char in value:
        if char in {"'", '"'}:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            current.append(char)
            continue
        if char == "," and quote is None:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    parts.append("".join(current).strip())
    return parts


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
        return str(parsed)
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return value
