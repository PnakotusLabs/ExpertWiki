from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Sequence


SCHEMA_VERSION = 3


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    path TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    resource TEXT NOT NULL,
    publisher TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    line_count INTEGER NOT NULL,
    status TEXT NOT NULL,
    summary TEXT,
    quality TEXT,
    language TEXT,
    ingested_at TEXT NOT NULL,
    analyzed_at TEXT,
    deleted_at TEXT,
    last_error TEXT,
    extractor_version TEXT,
    prompt_version TEXT,
    suggested_topics_json TEXT NOT NULL DEFAULT '[]',
    named_references_json TEXT NOT NULL DEFAULT '[]',
    CHECK (status IN ('preserved', 'changed', 'analyzed', 'failed', 'deleted'))
);

CREATE TABLE IF NOT EXISTS concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    summary TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 0.5,
    provenance_state TEXT NOT NULL DEFAULT 'extracted',
    status TEXT NOT NULL DEFAULT 'dirty',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (status IN ('dirty', 'clean', 'frozen', 'orphaned', 'blocked'))
);

CREATE TABLE IF NOT EXISTS source_concepts (
    source_path TEXT NOT NULL REFERENCES sources(path),
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    source_ranges_json TEXT NOT NULL DEFAULT '[]',
    extract_summary TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.5,
    extraction_hash TEXT NOT NULL,
    PRIMARY KEY (source_path, concept_id)
);

CREATE TABLE IF NOT EXISTS concept_aliases (
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    alias TEXT NOT NULL,
    alias_key TEXT NOT NULL,
    source_path TEXT NOT NULL REFERENCES sources(path),
    observed_at TEXT NOT NULL,
    PRIMARY KEY (concept_id, alias_key, source_path)
);

CREATE TABLE IF NOT EXISTS articles (
    concept_id INTEGER PRIMARY KEY REFERENCES concepts(id),
    path TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL,
    source_hashes_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    managed INTEGER NOT NULL DEFAULT 1,
    manual_edit_state TEXT NOT NULL DEFAULT 'clean',
    compiled_at TEXT,
    approved_at TEXT,
    updated_at TEXT NOT NULL,
    CHECK (status IN ('published', 'stale', 'orphaned', 'deferred_manual_edit')),
    CHECK (manual_edit_state IN ('clean', 'modified'))
);

CREATE TABLE IF NOT EXISTS drafts (
    concept_id INTEGER PRIMARY KEY REFERENCES concepts(id),
    path TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL,
    source_hashes_json TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    model TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_review',
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (status IN ('pending_review', 'failed', 'deferred_draft'))
);

CREATE TABLE IF NOT EXISTS rejections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    feedback TEXT NOT NULL,
    rejected_body TEXT NOT NULL,
    rejected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS citation_spans (
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    paragraph_index INTEGER NOT NULL,
    source_path TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    PRIMARY KEY (concept_id, paragraph_index, source_path, start_line, end_line)
);

CREATE TABLE IF NOT EXISTS concept_contradictions (
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    source_path TEXT NOT NULL REFERENCES sources(path),
    target_ref TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    PRIMARY KEY (concept_id, source_path, target_ref)
);

CREATE TABLE IF NOT EXISTS frozen_concepts (
    concept_id INTEGER PRIMARY KEY REFERENCES concepts(id),
    reason TEXT NOT NULL,
    frozen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS compile_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    changed_sources_json TEXT NOT NULL DEFAULT '[]',
    analyzed_count INTEGER NOT NULL DEFAULT 0,
    compiled_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS agent_jobs (
    id TEXT PRIMARY KEY,
    job_key TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    source_path TEXT REFERENCES sources(path),
    concept_id INTEGER REFERENCES concepts(id),
    payload_json TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    generator TEXT,
    result_hash TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    claimed_at TEXT,
    completed_at TEXT,
    CHECK (kind IN ('analyze_source', 'compile_concept')),
    CHECK (status IN ('pending', 'claimed', 'completed', 'failed', 'stale'))
);

CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);
CREATE INDEX IF NOT EXISTS idx_concepts_status ON concepts(status);
CREATE INDEX IF NOT EXISTS idx_source_concepts_concept ON source_concepts(concept_id);
CREATE INDEX IF NOT EXISTS idx_alias_key ON concept_aliases(alias_key);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status);
CREATE INDEX IF NOT EXISTS idx_rejections_concept ON rejections(concept_id, rejected_at);
CREATE INDEX IF NOT EXISTS idx_citations_source ON citation_spans(source_path);
CREATE INDEX IF NOT EXISTS idx_contradictions_concept ON concept_contradictions(concept_id);
CREATE INDEX IF NOT EXISTS idx_agent_jobs_status ON agent_jobs(status, kind, created_at);
"""


MIGRATIONS: dict[int, tuple[str, ...]] = {
    2: (
        "ALTER TABLE sources ADD COLUMN suggested_topics_json TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE sources ADD COLUMN named_references_json TEXT NOT NULL DEFAULT '[]'",
        """
        CREATE TABLE IF NOT EXISTS concept_contradictions (
            concept_id INTEGER NOT NULL REFERENCES concepts(id),
            source_path TEXT NOT NULL REFERENCES sources(path),
            target_ref TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            PRIMARY KEY (concept_id, source_path, target_ref)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_contradictions_concept ON concept_contradictions(concept_id)",
    ),
    3: (
        """
        CREATE TABLE IF NOT EXISTS agent_jobs (
            id TEXT PRIMARY KEY,
            job_key TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            source_path TEXT REFERENCES sources(path),
            concept_id INTEGER REFERENCES concepts(id),
            payload_json TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            generator TEXT,
            result_hash TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            claimed_at TEXT,
            completed_at TEXT,
            CHECK (kind IN ('analyze_source', 'compile_concept')),
            CHECK (status IN ('pending', 'claimed', 'completed', 'failed', 'stale'))
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_agent_jobs_status ON agent_jobs(status, kind, created_at)",
    ),
}


@dataclass(frozen=True)
class SourceRecord:
    path: str
    title: str
    resource: str
    publisher: str
    content_hash: str
    line_count: int
    status: str
    summary: str | None
    quality: str | None
    language: str | None
    analyzed_at: str | None
    deleted_at: str | None
    last_error: str | None
    suggested_topics: list[str]
    named_references: list[str]


@dataclass(frozen=True)
class ConceptRecord:
    id: int
    name: str
    slug: str
    summary: str
    tags: list[str]
    confidence: float
    provenance_state: str
    status: str


@dataclass(frozen=True)
class SourceConceptRecord:
    source_path: str
    concept_id: int
    source_ranges: list[str]
    extract_summary: str
    confidence: float
    extraction_hash: str


@dataclass(frozen=True)
class AgentJobRecord:
    id: str
    job_key: str
    kind: str
    status: str
    source_path: str | None
    concept_id: int | None
    payload: dict[str, Any]
    input_hash: str
    attempts: int
    generator: str | None
    result_hash: str | None
    error: str | None
    created_at: str
    claimed_at: str | None
    completed_at: str | None


class StateDB:
    """SQLite compiler state; Markdown remains the user-owned knowledge store."""

    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA busy_timeout = 10000")
        self._initialize()

    def _initialize(self) -> None:
        self._conn.executescript(SCHEMA)
        row = self._conn.execute(
            "SELECT version FROM schema_version WHERE id = 1"
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO schema_version (id, version) VALUES (1, ?)",
                (SCHEMA_VERSION,),
            )
            return
        version = int(row["version"])
        if version > SCHEMA_VERSION:
            raise ValueError(
                f"Compiler state schema {version} is newer than supported version {SCHEMA_VERSION}."
            )
        while version < SCHEMA_VERSION:
            target = version + 1
            statements = MIGRATIONS.get(target)
            if statements is None:
                raise ValueError(f"No migration path from compiler state schema {version}.")
            with self.transaction():
                for statement in statements:
                    try:
                        self._conn.execute(statement)
                    except sqlite3.OperationalError as exc:
                        if "duplicate column" not in str(exc).lower():
                            raise
                self._conn.execute(
                    "UPDATE schema_version SET version = ? WHERE id = 1", (target,)
                )
            version = target

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "StateDB":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except Exception:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    def get_source(self, path: str) -> SourceRecord | None:
        row = self._conn.execute("SELECT * FROM sources WHERE path = ?", (path,)).fetchone()
        return _source_record(row) if row else None

    def list_sources(self, *, include_deleted: bool = True) -> list[SourceRecord]:
        sql = "SELECT * FROM sources"
        params: tuple[Any, ...] = ()
        if not include_deleted:
            sql += " WHERE status != ?"
            params = ("deleted",)
        rows = self._conn.execute(sql + " ORDER BY path", params).fetchall()
        return [_source_record(row) for row in rows]

    def upsert_source(
        self,
        *,
        path: str,
        title: str,
        resource: str,
        publisher: str,
        content_hash: str,
        line_count: int,
        status: str,
    ) -> None:
        now = _timestamp()
        self._conn.execute(
            """
            INSERT INTO sources (
                path, title, resource, publisher, content_hash, line_count,
                status, ingested_at, deleted_at, last_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
            ON CONFLICT(path) DO UPDATE SET
                title = excluded.title,
                resource = excluded.resource,
                publisher = excluded.publisher,
                content_hash = excluded.content_hash,
                line_count = excluded.line_count,
                status = excluded.status,
                deleted_at = NULL,
                last_error = NULL
            """,
            (path, title, resource, publisher, content_hash, line_count, status, now),
        )

    def mark_source_deleted(self, path: str) -> None:
        self._conn.execute(
            "UPDATE sources SET status = 'deleted', deleted_at = ?, last_error = NULL WHERE path = ?",
            (_timestamp(), path),
        )

    def mark_source_failed(self, path: str, error: str) -> None:
        self._conn.execute(
            "UPDATE sources SET status = 'failed', last_error = ? WHERE path = ?",
            (error, path),
        )

    def record_analysis(
        self,
        *,
        source_path: str,
        summary: str,
        quality: str,
        language: str | None,
        suggested_topics: Sequence[str],
        named_references: Sequence[str],
        extractor_version: str,
        prompt_version: str,
        concepts: Sequence[dict[str, Any]],
    ) -> tuple[set[int], set[int]]:
        """Replace one source's extraction and return old/new concept id sets."""
        now = _timestamp()
        with self.transaction():
            old_ids = set(self.concept_ids_for_source(source_path))
            self._conn.execute("DELETE FROM concept_aliases WHERE source_path = ?", (source_path,))
            self._conn.execute(
                "DELETE FROM concept_contradictions WHERE source_path = ?", (source_path,)
            )
            self._conn.execute("DELETE FROM source_concepts WHERE source_path = ?", (source_path,))
            new_ids: set[int] = set()
            for raw in concepts:
                concept_id = self._resolve_or_create_concept(raw, now)
                new_ids.add(concept_id)
                existing_link = self._conn.execute(
                    """
                    SELECT source_ranges_json, extract_summary, confidence, extraction_hash
                    FROM source_concepts WHERE source_path = ? AND concept_id = ?
                    """,
                    (source_path, concept_id),
                ).fetchone()
                ranges = _dedupe_strings(
                    [
                        *(
                            json.loads(str(existing_link["source_ranges_json"]))
                            if existing_link
                            else []
                        ),
                        *[str(value) for value in raw.get("source_ranges", [])],
                    ]
                )
                summaries = _dedupe_strings(
                    [
                        str(existing_link["extract_summary"]) if existing_link else "",
                        str(raw.get("summary", "")),
                    ]
                )
                confidence = max(
                    float(existing_link["confidence"]) if existing_link else 0.0,
                    float(raw.get("confidence", 0.5)),
                )
                extraction_hash = hashlib.sha256(
                    "\n".join(
                        sorted(
                            value
                            for value in [
                                str(existing_link["extraction_hash"]) if existing_link else "",
                                str(raw["extraction_hash"]),
                            ]
                            if value
                        )
                    ).encode("utf-8")
                )
                extraction_digest = extraction_hash.hexdigest()
                self._conn.execute(
                    """
                    INSERT INTO source_concepts (
                        source_path, concept_id, source_ranges_json, extract_summary,
                        confidence, extraction_hash
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_path, concept_id) DO UPDATE SET
                        source_ranges_json = excluded.source_ranges_json,
                        extract_summary = excluded.extract_summary,
                        confidence = excluded.confidence,
                        extraction_hash = excluded.extraction_hash
                    """,
                    (
                        source_path,
                        concept_id,
                        _json(ranges),
                        " ".join(summaries),
                        confidence,
                        extraction_digest,
                    ),
                )
                aliases = _dedupe_strings([str(raw["name"]), *raw.get("aliases", [])])
                for alias in aliases:
                    self._conn.execute(
                        """
                        INSERT OR IGNORE INTO concept_aliases (
                            concept_id, alias, alias_key, source_path, observed_at
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (concept_id, alias, _normalize_name(alias), source_path, now),
                    )
                for target_ref in _dedupe_strings(
                    [str(value) for value in raw.get("contradicted_by", [])]
                ):
                    self._conn.execute(
                        """
                        INSERT OR IGNORE INTO concept_contradictions (
                            concept_id, source_path, target_ref, observed_at
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (concept_id, source_path, target_ref, now),
                    )
            self._conn.execute(
                """
                UPDATE sources SET
                    status = 'analyzed', summary = ?, quality = ?, language = ?,
                    analyzed_at = ?, deleted_at = NULL, last_error = NULL,
                    extractor_version = ?, prompt_version = ?,
                    suggested_topics_json = ?, named_references_json = ?
                WHERE path = ?
                """,
                (
                    summary,
                    quality,
                    language,
                    now,
                    extractor_version,
                    prompt_version,
                    _json(_dedupe_strings(list(suggested_topics))),
                    _json(_dedupe_strings(list(named_references))),
                    source_path,
                ),
            )
            affected = old_ids | new_ids
            if affected:
                placeholders = ",".join("?" for _ in affected)
                self._conn.execute(
                    f"UPDATE concepts SET status = 'dirty', updated_at = ? "
                    f"WHERE id IN ({placeholders}) AND status != 'blocked'",
                    (now, *sorted(affected)),
                )
            self._refresh_orphan_and_frozen_states(affected, now)
        return old_ids, new_ids

    def _resolve_or_create_concept(self, raw: dict[str, Any], now: str) -> int:
        name = str(raw["name"]).strip()
        candidates = _dedupe_strings([name, *raw.get("aliases", [])])
        concept_id = self.resolve_concept_id(name)
        if concept_id is None:
            for alias in candidates:
                concept_id = self.resolve_concept_id(alias)
                if concept_id is not None:
                    break
        tags = _dedupe_strings([str(tag) for tag in raw.get("tags", [])])
        if concept_id is None:
            cursor = self._conn.execute(
                """
                INSERT INTO concepts (
                    name, name_key, slug, summary, tags_json, confidence,
                    provenance_state, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'dirty', ?, ?)
                """,
                (
                    name,
                    _normalize_name(name),
                    self._available_slug(_slugify(name)),
                    str(raw.get("summary", "")),
                    _json(tags),
                    float(raw.get("confidence", 0.5)),
                    str(raw.get("provenance_state", "extracted")),
                    now,
                    now,
                ),
            )
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

        current = self.get_concept(concept_id)
        assert current is not None
        merged_tags = _dedupe_strings([*current.tags, *tags])
        confidence = max(current.confidence, float(raw.get("confidence", 0.5)))
        summary = current.summary or str(raw.get("summary", ""))
        self._conn.execute(
            """
            UPDATE concepts SET summary = ?, tags_json = ?, confidence = ?, updated_at = ?
            WHERE id = ?
            """,
            (summary, _json(merged_tags), confidence, now, concept_id),
        )
        return concept_id

    def _available_slug(self, preferred: str) -> str:
        slug = preferred
        suffix = 2
        while self._conn.execute("SELECT 1 FROM concepts WHERE slug = ?", (slug,)).fetchone():
            slug = f"{preferred}-{suffix}"
            suffix += 1
        return slug

    def resolve_concept_id(self, value: str) -> int | None:
        key = _normalize_name(value)
        row = self._conn.execute(
            "SELECT id FROM concepts WHERE name_key = ? OR slug = ? ORDER BY id LIMIT 1",
            (key, _slugify(value)),
        ).fetchone()
        if row:
            return int(row["id"])
        rows = self._conn.execute(
            "SELECT DISTINCT concept_id FROM concept_aliases WHERE alias_key = ? ORDER BY concept_id",
            (key,),
        ).fetchall()
        if len(rows) == 1:
            return int(rows[0]["concept_id"])
        return None

    def get_concept(self, concept: int | str) -> ConceptRecord | None:
        if isinstance(concept, int):
            row = self._conn.execute("SELECT * FROM concepts WHERE id = ?", (concept,)).fetchone()
        else:
            concept_id = self.resolve_concept_id(concept)
            if concept_id is None:
                return None
            row = self._conn.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,)).fetchone()
        return _concept_record(row) if row else None

    def ensure_concept(
        self,
        name: str,
        *,
        summary: str = "",
        tags: Sequence[str] = (),
        status: str = "dirty",
    ) -> ConceptRecord:
        existing = self.get_concept(name)
        if existing is not None:
            return existing
        now = _timestamp()
        cursor = self._conn.execute(
            """
            INSERT INTO concepts (
                name, name_key, slug, summary, tags_json, confidence,
                provenance_state, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 0.5, 'extracted', ?, ?, ?)
            """,
            (
                name.strip(),
                _normalize_name(name),
                self._available_slug(_slugify(name)),
                summary.strip(),
                _json(_dedupe_strings(list(tags))),
                status,
                now,
                now,
            ),
        )
        assert cursor.lastrowid is not None
        created = self.get_concept(int(cursor.lastrowid))
        assert created is not None
        return created

    def list_concepts(self, *, statuses: Sequence[str] | None = None) -> list[ConceptRecord]:
        sql = "SELECT * FROM concepts"
        params: tuple[Any, ...] = ()
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            sql += f" WHERE status IN ({placeholders})"
            params = tuple(statuses)
        rows = self._conn.execute(sql + " ORDER BY name_key", params).fetchall()
        return [_concept_record(row) for row in rows]

    def concept_ids_for_source(self, source_path: str) -> list[int]:
        rows = self._conn.execute(
            "SELECT concept_id FROM source_concepts WHERE source_path = ? ORDER BY concept_id",
            (source_path,),
        ).fetchall()
        return [int(row["concept_id"]) for row in rows]

    def import_source_concept(self, source_path: str, concept_id: int) -> None:
        """Restore a minimal dependency from Markdown metadata before re-analysis."""
        self._conn.execute(
            """
            INSERT INTO source_concepts (
                source_path, concept_id, source_ranges_json, extract_summary,
                confidence, extraction_hash
            ) VALUES (?, ?, '[]', '', 0.5, 'imported')
            ON CONFLICT(source_path, concept_id) DO NOTHING
            """,
            (source_path, concept_id),
        )

    def source_concepts_for_concept(self, concept_id: int) -> list[SourceConceptRecord]:
        rows = self._conn.execute(
            """
            SELECT sc.* FROM source_concepts sc
            JOIN sources s ON s.path = sc.source_path
            WHERE sc.concept_id = ? AND s.status != 'deleted'
            ORDER BY sc.source_path
            """,
            (concept_id,),
        ).fetchall()
        return [_source_concept_record(row) for row in rows]

    def aliases_for_concept(self, concept_id: int) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT alias FROM concept_aliases WHERE concept_id = ? ORDER BY alias_key",
            (concept_id,),
        ).fetchall()
        return [str(row["alias"]) for row in rows]

    def deleted_sources_for_concept(self, concept_id: int) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT sc.source_path FROM source_concepts sc
            JOIN sources s ON s.path = sc.source_path
            WHERE sc.concept_id = ? AND s.status = 'deleted'
            ORDER BY sc.source_path
            """,
            (concept_id,),
        ).fetchall()
        return [str(row["source_path"]) for row in rows]

    def mark_concepts_after_source_deletion(self, source_path: str) -> list[int]:
        concept_ids = self.concept_ids_for_source(source_path)
        now = _timestamp()
        with self.transaction():
            self.mark_source_deleted(source_path)
            self._refresh_orphan_and_frozen_states(set(concept_ids), now)
        return concept_ids

    def _refresh_orphan_and_frozen_states(self, concept_ids: set[int], now: str) -> None:
        for concept_id in concept_ids:
            active_count = int(
                self._conn.execute(
                    """
                    SELECT COUNT(*) AS count FROM source_concepts sc
                    JOIN sources s ON s.path = sc.source_path
                    WHERE sc.concept_id = ? AND s.status != 'deleted'
                    """,
                    (concept_id,),
                ).fetchone()["count"]
            )
            deleted_count = int(
                self._conn.execute(
                    """
                    SELECT COUNT(*) AS count FROM source_concepts sc
                    JOIN sources s ON s.path = sc.source_path
                    WHERE sc.concept_id = ? AND s.status = 'deleted'
                    """,
                    (concept_id,),
                ).fetchone()["count"]
            )
            current = self.get_concept(concept_id)
            if current is None or current.status == "blocked":
                continue
            if active_count == 0:
                status = "orphaned"
                self._conn.execute("DELETE FROM frozen_concepts WHERE concept_id = ?", (concept_id,))
            elif deleted_count > 0:
                status = "frozen"
                self._conn.execute(
                    """
                    INSERT INTO frozen_concepts (concept_id, reason, frozen_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(concept_id) DO UPDATE SET reason = excluded.reason
                    """,
                    (concept_id, "A contributing source was deleted; preserving the last synthesis.", now),
                )
            else:
                status = "dirty"
                self._conn.execute("DELETE FROM frozen_concepts WHERE concept_id = ?", (concept_id,))
            self._conn.execute(
                "UPDATE concepts SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, concept_id),
            )
            article_status = "orphaned" if status == "orphaned" else "stale"
            if status in {"orphaned", "frozen"}:
                self._conn.execute(
                    "UPDATE articles SET status = ?, updated_at = ? WHERE concept_id = ?",
                    (article_status, now, concept_id),
                )

    def mark_concept_status(self, concept_id: int, status: str) -> None:
        self._conn.execute(
            "UPDATE concepts SET status = ?, updated_at = ? WHERE id = ?",
            (status, _timestamp(), concept_id),
        )

    def get_article(self, concept_id: int) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM articles WHERE concept_id = ?", (concept_id,)
        ).fetchone()

    def list_articles(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM articles ORDER BY path"
        ).fetchall()

    def find_article_by_path(self, path: str) -> sqlite3.Row | None:
        return self._conn.execute("SELECT * FROM articles WHERE path = ?", (path,)).fetchone()

    def upsert_article(
        self,
        *,
        concept_id: int,
        path: str,
        content_hash: str,
        source_hashes: dict[str, str],
        status: str,
        managed: bool,
        compiled_at: str | None,
        approved_at: str | None,
        manual_edit_state: str = "clean",
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO articles (
                concept_id, path, content_hash, source_hashes_json, status, managed,
                manual_edit_state, compiled_at, approved_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(concept_id) DO UPDATE SET
                path = excluded.path,
                content_hash = excluded.content_hash,
                source_hashes_json = excluded.source_hashes_json,
                status = excluded.status,
                managed = excluded.managed,
                manual_edit_state = excluded.manual_edit_state,
                compiled_at = excluded.compiled_at,
                approved_at = excluded.approved_at,
                updated_at = excluded.updated_at
            """,
            (
                concept_id,
                path,
                content_hash,
                _json(source_hashes),
                status,
                1 if managed else 0,
                manual_edit_state,
                compiled_at,
                approved_at,
                _timestamp(),
            ),
        )

    def mark_article_manual_edit(self, concept_id: int) -> None:
        self._conn.execute(
            """
            UPDATE articles SET status = 'deferred_manual_edit', manual_edit_state = 'modified',
                updated_at = ? WHERE concept_id = ?
            """,
            (_timestamp(), concept_id),
        )

    def delete_article(self, concept_id: int) -> None:
        self._conn.execute("DELETE FROM articles WHERE concept_id = ?", (concept_id,))

    def get_draft(self, concept_id: int) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM drafts WHERE concept_id = ?", (concept_id,)
        ).fetchone()

    def find_draft_by_path(self, path: str) -> sqlite3.Row | None:
        return self._conn.execute("SELECT * FROM drafts WHERE path = ?", (path,)).fetchone()

    def list_drafts(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            """
            SELECT d.*, c.name, c.slug, c.summary, c.status AS concept_status
            FROM drafts d JOIN concepts c ON c.id = d.concept_id
            WHERE d.status = 'pending_review'
            ORDER BY d.created_at, c.name_key
            """
        ).fetchall()

    def upsert_draft(
        self,
        *,
        concept_id: int,
        path: str,
        content_hash: str,
        source_hashes: dict[str, str],
        prompt_hash: str,
        model: str,
        status: str = "pending_review",
        last_error: str | None = None,
    ) -> None:
        now = _timestamp()
        self._conn.execute(
            """
            INSERT INTO drafts (
                concept_id, path, content_hash, source_hashes_json, prompt_hash,
                model, status, last_error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(concept_id) DO UPDATE SET
                path = excluded.path,
                content_hash = excluded.content_hash,
                source_hashes_json = excluded.source_hashes_json,
                prompt_hash = excluded.prompt_hash,
                model = excluded.model,
                status = excluded.status,
                last_error = excluded.last_error,
                updated_at = excluded.updated_at
            """,
            (
                concept_id,
                path,
                content_hash,
                _json(source_hashes),
                prompt_hash,
                model,
                status,
                last_error,
                now,
                now,
            ),
        )

    def delete_draft(self, concept_id: int) -> None:
        self._conn.execute("DELETE FROM drafts WHERE concept_id = ?", (concept_id,))

    def add_rejection(self, concept_id: int, feedback: str, body: str) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO rejections (concept_id, feedback, rejected_body, rejected_at)
            VALUES (?, ?, ?, ?)
            """,
            (concept_id, feedback, body, _timestamp()),
        )
        assert cursor.lastrowid is not None
        return int(cursor.lastrowid)

    def recent_rejections(self, concept_id: int, *, limit: int = 3) -> list[dict[str, str]]:
        rows = self._conn.execute(
            """
            SELECT feedback, rejected_at FROM rejections
            WHERE concept_id = ? ORDER BY id DESC LIMIT ?
            """,
            (concept_id, limit),
        ).fetchall()
        return [
            {"feedback": str(row["feedback"]), "rejected_at": str(row["rejected_at"])}
            for row in rows
        ]

    def rejection_count(self, concept_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM rejections WHERE concept_id = ?", (concept_id,)
        ).fetchone()
        return int(row["count"])

    def replace_citations(self, concept_id: int, citations: Sequence[dict[str, Any]]) -> None:
        self._conn.execute("DELETE FROM citation_spans WHERE concept_id = ?", (concept_id,))
        for citation in citations:
            self._conn.execute(
                """
                INSERT INTO citation_spans (
                    concept_id, paragraph_index, source_path, start_line, end_line
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    concept_id,
                    int(citation["paragraph_index"]),
                    str(citation["source_path"]),
                    citation.get("start_line"),
                    citation.get("end_line"),
                ),
            )

    def enqueue_agent_job(
        self,
        *,
        job_id: str,
        job_key: str,
        kind: str,
        payload: dict[str, Any],
        input_hash: str,
        source_path: str | None = None,
        concept_id: int | None = None,
    ) -> AgentJobRecord:
        self._conn.execute(
            """
            INSERT INTO agent_jobs (
                id, job_key, kind, status, source_path, concept_id, payload_json,
                input_hash, created_at
            ) VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?)
            ON CONFLICT(job_key) DO NOTHING
            """,
            (
                job_id,
                job_key,
                kind,
                source_path,
                concept_id,
                _json(payload),
                input_hash,
                _timestamp(),
            ),
        )
        row = self._conn.execute(
            "SELECT * FROM agent_jobs WHERE job_key = ?", (job_key,)
        ).fetchone()
        assert row is not None
        return _agent_job_record(row)

    def get_agent_job(self, job_id: str) -> AgentJobRecord | None:
        row = self._conn.execute(
            "SELECT * FROM agent_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return _agent_job_record(row) if row else None

    def list_agent_jobs(
        self,
        *,
        statuses: Sequence[str] | None = None,
        kinds: Sequence[str] | None = None,
    ) -> list[AgentJobRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if statuses:
            clauses.append("status IN (" + ",".join("?" for _ in statuses) + ")")
            params.extend(statuses)
        if kinds:
            clauses.append("kind IN (" + ",".join("?" for _ in kinds) + ")")
            params.extend(kinds)
        sql = "SELECT * FROM agent_jobs"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY CASE kind WHEN 'analyze_source' THEN 0 ELSE 1 END, created_at, id"
        rows = self._conn.execute(sql, tuple(params)).fetchall()
        return [_agent_job_record(row) for row in rows]

    def claim_next_agent_job(self) -> AgentJobRecord | None:
        with self.transaction():
            row = self._conn.execute(
                """
                SELECT * FROM agent_jobs
                WHERE status = 'pending'
                ORDER BY CASE kind WHEN 'analyze_source' THEN 0 ELSE 1 END, created_at, id
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            self._conn.execute(
                """
                UPDATE agent_jobs SET status = 'claimed', claimed_at = ?, attempts = attempts + 1,
                    error = NULL WHERE id = ? AND status = 'pending'
                """,
                (_timestamp(), str(row["id"])),
            )
            claimed = self._conn.execute(
                "SELECT * FROM agent_jobs WHERE id = ?", (str(row["id"]),)
            ).fetchone()
            assert claimed is not None
            return _agent_job_record(claimed)

    def complete_agent_job(self, job_id: str, *, generator: str, result_hash: str) -> None:
        cursor = self._conn.execute(
            """
            UPDATE agent_jobs SET status = 'completed', generator = ?, result_hash = ?,
                completed_at = ?, error = NULL WHERE id = ? AND status IN ('pending', 'claimed')
            """,
            (generator, result_hash, _timestamp(), job_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"Agent job is not active: {job_id}")

    def fail_agent_job(self, job_id: str, error: str) -> None:
        cursor = self._conn.execute(
            """
            UPDATE agent_jobs SET status = 'failed', error = ?, completed_at = ?
            WHERE id = ? AND status IN ('pending', 'claimed')
            """,
            (error, _timestamp(), job_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"Agent job is not active: {job_id}")

    def stale_agent_job(self, job_id: str, error: str) -> None:
        cursor = self._conn.execute(
            """
            UPDATE agent_jobs SET status = 'stale', error = ?, completed_at = ?
            WHERE id = ? AND status IN ('pending', 'claimed', 'failed')
            """,
            (error, _timestamp(), job_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"Agent job cannot be marked stale: {job_id}")

    def retry_agent_job(self, job_id: str) -> None:
        cursor = self._conn.execute(
            """
            UPDATE agent_jobs SET status = 'pending', claimed_at = NULL, completed_at = NULL,
                error = NULL WHERE id = ? AND status = 'failed'
            """,
            (job_id,),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"Only failed agent jobs can be retried: {job_id}")

    def stale_agent_jobs(self, *, kind: str, entity_ref: str, current_input_hash: str) -> int:
        column = "source_path" if kind == "analyze_source" else "concept_id"
        cursor = self._conn.execute(
            f"""
            UPDATE agent_jobs SET status = 'stale', completed_at = ?,
                error = 'Inputs changed before completion.'
            WHERE kind = ? AND {column} = ? AND input_hash != ?
                AND status IN ('pending', 'claimed', 'failed')
            """,
            (_timestamp(), kind, entity_ref, current_input_hash),
        )
        return int(cursor.rowcount)

    def stale_compile_jobs_for_concepts(
        self,
        concept_ids: Sequence[int],
        *,
        error: str,
    ) -> int:
        if not concept_ids:
            return 0
        placeholders = ",".join("?" for _ in concept_ids)
        cursor = self._conn.execute(
            f"""
            UPDATE agent_jobs SET status = 'stale', completed_at = ?, error = ?
            WHERE kind = 'compile_concept' AND concept_id IN ({placeholders})
                AND status IN ('pending', 'claimed', 'failed')
            """,
            (_timestamp(), error, *concept_ids),
        )
        return int(cursor.rowcount)

    def begin_run(self) -> int:
        cursor = self._conn.execute(
            "INSERT INTO compile_runs (status, started_at) VALUES ('running', ?)",
            (_timestamp(),),
        )
        assert cursor.lastrowid is not None
        return int(cursor.lastrowid)

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        changed_sources: Sequence[str],
        analyzed_count: int,
        compiled_count: int,
        skipped_count: int,
        error: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE compile_runs SET
                status = ?, finished_at = ?, changed_sources_json = ?,
                analyzed_count = ?, compiled_count = ?, skipped_count = ?, error = ?
            WHERE id = ?
            """,
            (
                status,
                _timestamp(),
                _json(list(changed_sources)),
                analyzed_count,
                compiled_count,
                skipped_count,
                error,
                run_id,
            ),
        )

    def stats(self) -> dict[str, int]:
        return {
            "sources": _count(self._conn, "sources", "status != 'deleted'"),
            "deleted_sources": _count(self._conn, "sources", "status = 'deleted'"),
            "concepts": _count(self._conn, "concepts"),
            "dirty_concepts": _count(self._conn, "concepts", "status = 'dirty'"),
            "frozen_concepts": _count(self._conn, "concepts", "status = 'frozen'"),
            "orphaned_concepts": _count(self._conn, "concepts", "status = 'orphaned'"),
            "drafts": _count(self._conn, "drafts", "status = 'pending_review'"),
            "articles": _count(self._conn, "articles"),
            "pending_agent_jobs": _count(
                self._conn, "agent_jobs", "status IN ('pending', 'claimed')"
            ),
            "failed_agent_jobs": _count(self._conn, "agent_jobs", "status = 'failed'"),
        }


def _source_record(row: sqlite3.Row) -> SourceRecord:
    return SourceRecord(
        path=str(row["path"]),
        title=str(row["title"]),
        resource=str(row["resource"]),
        publisher=str(row["publisher"]),
        content_hash=str(row["content_hash"]),
        line_count=int(row["line_count"]),
        status=str(row["status"]),
        summary=row["summary"],
        quality=row["quality"],
        language=row["language"],
        analyzed_at=row["analyzed_at"],
        deleted_at=row["deleted_at"],
        last_error=row["last_error"],
        suggested_topics=[
            str(value) for value in json.loads(str(row["suggested_topics_json"]))
        ],
        named_references=[
            str(value) for value in json.loads(str(row["named_references_json"]))
        ],
    )


def _concept_record(row: sqlite3.Row) -> ConceptRecord:
    tags = json.loads(str(row["tags_json"]))
    return ConceptRecord(
        id=int(row["id"]),
        name=str(row["name"]),
        slug=str(row["slug"]),
        summary=str(row["summary"]),
        tags=[str(tag) for tag in tags],
        confidence=float(row["confidence"]),
        provenance_state=str(row["provenance_state"]),
        status=str(row["status"]),
    )


def _source_concept_record(row: sqlite3.Row) -> SourceConceptRecord:
    return SourceConceptRecord(
        source_path=str(row["source_path"]),
        concept_id=int(row["concept_id"]),
        source_ranges=[str(value) for value in json.loads(str(row["source_ranges_json"]))],
        extract_summary=str(row["extract_summary"]),
        confidence=float(row["confidence"]),
        extraction_hash=str(row["extraction_hash"]),
    )


def _agent_job_record(row: sqlite3.Row) -> AgentJobRecord:
    payload = json.loads(str(row["payload_json"]))
    if not isinstance(payload, dict):
        raise ValueError(f"Agent job payload must be an object: {row['id']}")
    return AgentJobRecord(
        id=str(row["id"]),
        job_key=str(row["job_key"]),
        kind=str(row["kind"]),
        status=str(row["status"]),
        source_path=str(row["source_path"]) if row["source_path"] is not None else None,
        concept_id=int(row["concept_id"]) if row["concept_id"] is not None else None,
        payload=payload,
        input_hash=str(row["input_hash"]),
        attempts=int(row["attempts"]),
        generator=str(row["generator"]) if row["generator"] is not None else None,
        result_hash=str(row["result_hash"]) if row["result_hash"] is not None else None,
        error=str(row["error"]) if row["error"] is not None else None,
        created_at=str(row["created_at"]),
        claimed_at=str(row["claimed_at"]) if row["claimed_at"] is not None else None,
        completed_at=str(row["completed_at"]) if row["completed_at"] is not None else None,
    )


def _count(conn: sqlite3.Connection, table: str, where: str | None = None) -> int:
    sql = f"SELECT COUNT(*) AS count FROM {table}"
    if where:
        sql += f" WHERE {where}"
    return int(conn.execute(sql).fetchone()["count"])


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip()
        key = _normalize_name(clean)
        if not clean or key in seen:
            continue
        seen.add(key)
        output.append(clean)
    return output


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def _slugify(value: str) -> str:
    import re

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "concept"


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
