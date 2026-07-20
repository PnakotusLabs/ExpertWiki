from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


EXTRACTION_PROMPT_VERSION = "expertwiki-extract-v1"
ARTICLE_PROMPT_VERSION = "expertwiki-article-v1"
ANSWER_PROMPT_VERSION = "expertwiki-answer-v1"


@dataclass(frozen=True)
class ModelConfig:
    base_url: str
    fast_model: str
    heavy_model: str
    api_key: str = ""


@dataclass(frozen=True)
class ExtractedConcept:
    name: str
    aliases: list[str]
    summary: str
    tags: list[str]
    confidence: float
    provenance_state: str
    source_ranges: list[str]
    contradicted_by: list[str]


@dataclass(frozen=True)
class AnalysisResult:
    summary: str
    concepts: list[ExtractedConcept]
    suggested_topics: list[str]
    named_references: list[str]
    quality: str
    language: str | None


@dataclass(frozen=True)
class ArticleResult:
    title: str
    description: str
    tags: list[str]
    entity_type: str
    body: str


class LLMClient(Protocol):
    @property
    def fast_model(self) -> str: ...

    @property
    def heavy_model(self) -> str: ...

    def complete_json(self, prompt: str, *, model: str, purpose: str) -> dict[str, Any]: ...


class OpenAICompatibleClient:
    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    @property
    def fast_model(self) -> str:
        return self.config.fast_model

    @property
    def heavy_model(self) -> str:
        return self.config.heavy_model

    def complete_json(self, prompt: str, *, model: str, purpose: str) -> dict[str, Any]:
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        request = Request(
            url,
            data=json.dumps(
                {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                }
            ).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"{purpose} model failed with HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise ValueError(f"{purpose} model failed: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"{purpose} model returned invalid response JSON.") from exc

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"{purpose} model response did not include message content.") from exc
        if not isinstance(content, str):
            raise ValueError(f"{purpose} model message content must be a JSON string.")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{purpose} model message content was not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{purpose} model JSON response must be an object.")
        return parsed


def client_from_env() -> OpenAICompatibleClient | None:
    base_url = os.environ.get("EXPERTWIKI_OPENAI_BASE_URL", "").strip()
    legacy_model = os.environ.get("EXPERTWIKI_OPENAI_MODEL", "").strip()
    fast_model = os.environ.get("EXPERTWIKI_FAST_MODEL", "").strip() or legacy_model
    heavy_model = os.environ.get("EXPERTWIKI_HEAVY_MODEL", "").strip() or legacy_model
    if not base_url or not fast_model or not heavy_model:
        return None
    return OpenAICompatibleClient(
        ModelConfig(
            base_url=base_url,
            fast_model=fast_model,
            heavy_model=heavy_model,
            api_key=os.environ.get("EXPERTWIKI_OPENAI_API_KEY", ""),
        )
    )


def build_extraction_prompt(
    *,
    source_path: str,
    numbered_content: str,
    existing_concepts: list[dict[str, Any]],
) -> str:
    existing = json.dumps(existing_concepts[:300], ensure_ascii=False, separators=(",", ":"))
    return f"""You are the fast extraction stage of a local, review-gated wiki compiler.
Extract 3-8 durable standalone concepts from the numbered source. Do not extract trivial details.
Reuse an existing canonical concept when its title or alias clearly matches. Aliases must be surface
forms actually present in this source. Named references must be exact names copied from the source.
For each concept, source_ranges must be a flat list such as ["12-18", "31-34"]. Use only line
numbers shown below. confidence is 0..1. provenance_state is one of extracted, merged, inferred,
ambiguous. Keep the schema small and return JSON only.

Required response shape:
{{"summary":"2-3 sentences","quality":"high|medium|low","language":"ISO code or null",
"suggested_topics":["..."],"named_references":["..."],"concepts":[{{"name":"...",
"aliases":["..."],"summary":"...","tags":["..."],"confidence":0.8,
"provenance_state":"extracted","source_ranges":["12-18"],
"contradicted_by":["other-concept-slug"]}}]}}

Existing concepts and aliases:
{existing}

--- SOURCE: {source_path} ---
{numbered_content}
"""


def build_article_prompt(
    *,
    concept_name: str,
    aliases: list[str],
    source_material: str,
    existing_page: str,
    related_pages: list[dict[str, str]],
    rejection_feedback: list[str],
) -> str:
    existing_section = existing_page.strip() or "(none; this is a new page)"
    related = json.dumps(related_pages[:50], ensure_ascii=False, separators=(",", ":"))
    feedback = "\n".join(f"- {item}" for item in rejection_feedback) or "(none)"
    return f"""You are the heavy writing stage of a local, human-reviewed wiki compiler.
Write one evidence-backed page for the canonical concept {concept_name!r}. Use facts only from the
provided numbered source material. Preserve useful existing content only when the current sources
still support it. Do not claim human confirmation unless a source explicitly contains it.

Return JSON only with this shape:
{{"title":"...","description":"...","tags":["..."],
"entity_type":"expert|project|viewpoint|topic|comparison|synthesis","body":"markdown"}}

The body must start with '# {concept_name}' and use these sections when applicable: Context, Facts,
Human Feedback, Experience Rules, Counterexamples and Risks, Confidence, Sources, Related Pages.
Append citations to prose paragraphs in the exact form ^[raw/sources/file.md:START-END]. Multiple
sources may appear in one marker separated by commas. Never cite frontmatter. Leave genuine model
inferences uncited so review can see them. Use [[Canonical Title]] only for a title in Related pages.
Do not emit YAML frontmatter; the compiler owns metadata.

Canonical aliases: {json.dumps(aliases, ensure_ascii=False)}

Recent rejection feedback that must be addressed:
{feedback}

Existing published page:
{existing_section}

Related pages:
{related}

--- NUMBERED SOURCE MATERIAL ---
{source_material}
"""


def parse_analysis(payload: dict[str, Any]) -> AnalysisResult:
    summary = _required_string(payload, "summary")
    quality = _required_string(payload, "quality").lower()
    if quality not in {"high", "medium", "low"}:
        raise ValueError("Analysis quality must be high, medium, or low.")
    language_raw = payload.get("language")
    if language_raw is not None and not isinstance(language_raw, str):
        raise ValueError("Analysis language must be a string or null.")
    concepts_raw = payload.get("concepts")
    if not isinstance(concepts_raw, list):
        raise ValueError("Analysis concepts must be a list.")
    concepts: list[ExtractedConcept] = []
    for raw in concepts_raw[:8]:
        if not isinstance(raw, dict):
            raise ValueError("Every extracted concept must be an object.")
        confidence = raw.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise ValueError("Concept confidence must be a number.")
        confidence_value = float(confidence)
        if not 0 <= confidence_value <= 1:
            raise ValueError("Concept confidence must be between 0 and 1.")
        provenance = str(raw.get("provenance_state", "extracted"))
        if provenance not in {"extracted", "merged", "inferred", "ambiguous"}:
            raise ValueError(f"Unsupported concept provenance state: {provenance}")
        source_ranges = _string_list(raw.get("source_ranges", []), "source_ranges", limit=20)
        for value in source_ranges:
            if not re.fullmatch(r"\d+(?:-\d+)?", value):
                raise ValueError(f"Invalid source range: {value}")
        concepts.append(
            ExtractedConcept(
                name=_required_string(raw, "name"),
                aliases=_string_list(raw.get("aliases", []), "aliases", limit=8),
                summary=_required_string(raw, "summary"),
                tags=_string_list(raw.get("tags", []), "tags", limit=8),
                confidence=confidence_value,
                provenance_state=provenance,
                source_ranges=source_ranges,
                contradicted_by=_string_list(
                    raw.get("contradicted_by", []), "contradicted_by", limit=8
                ),
            )
        )
    if not concepts:
        raise ValueError("Analysis did not include any usable concepts.")
    return AnalysisResult(
        summary=summary,
        concepts=concepts,
        suggested_topics=_string_list(
            payload.get("suggested_topics", []), "suggested_topics", limit=8
        ),
        named_references=_string_list(
            payload.get("named_references", []), "named_references", limit=12
        ),
        quality=quality,
        language=language_raw.strip() if isinstance(language_raw, str) else None,
    )


def parse_article(payload: dict[str, Any]) -> ArticleResult:
    entity_type = _required_string(payload, "entity_type").lower()
    if entity_type not in {"expert", "project", "viewpoint", "topic", "comparison", "synthesis"}:
        raise ValueError(f"Unsupported article entity_type: {entity_type}")
    body = _required_string(payload, "body")
    if not body.lstrip().startswith("# "):
        raise ValueError("Article body must start with an H1 heading.")
    return ArticleResult(
        title=_required_string(payload, "title"),
        description=_required_string(payload, "description"),
        tags=_string_list(payload.get("tags", []), "tags", limit=8),
        entity_type=entity_type,
        body=body.strip(),
    )


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"LLM response field {key!r} must be a non-empty string.")
    return value.strip()


def _string_list(value: Any, field: str, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"LLM response field {field!r} must be a list.")
    output: list[str] = []
    seen: set[str] = set()
    for item in value[:limit]:
        if not isinstance(item, str):
            raise ValueError(f"LLM response field {field!r} must contain only strings.")
        clean = item.strip()
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            output.append(clean)
    return output
