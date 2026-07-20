from __future__ import annotations

from pathlib import Path
import sqlite3

from expertwiki.state import SCHEMA_VERSION, StateDB


def test_state_db_migrates_v1_source_metadata_columns(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE schema_version (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL
        );
        INSERT INTO schema_version (id, version) VALUES (1, 1);
        CREATE TABLE sources (
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
            prompt_version TEXT
        );
        """
    )
    connection.close()

    with StateDB(database) as state:
        columns = {
            row[1] for row in state._conn.execute("PRAGMA table_info(sources)").fetchall()
        }
        version = state._conn.execute(
            "SELECT version FROM schema_version WHERE id = 1"
        ).fetchone()[0]

    assert version == SCHEMA_VERSION
    assert "suggested_topics_json" in columns
    assert "named_references_json" in columns

    connection = sqlite3.connect(database)
    job_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(agent_jobs)").fetchall()
    }
    connection.close()
    assert {"job_key", "payload_json", "input_hash", "status"} <= job_columns


def test_analysis_merges_aliases_that_resolve_to_one_source_concept(tmp_path: Path) -> None:
    with StateDB(tmp_path / "state.sqlite") as state:
        state.upsert_source(
            path="raw/sources/source.md",
            title="Source",
            resource="source.md",
            publisher="Test",
            content_hash="hash",
            line_count=20,
            status="preserved",
        )
        state.record_analysis(
            source_path="raw/sources/source.md",
            summary="Summary",
            quality="high",
            language="en",
            suggested_topics=[],
            named_references=[],
            extractor_version="test",
            prompt_version="test",
            concepts=[
                {
                    "name": "Retrieval Augmented Generation",
                    "aliases": ["RAG"],
                    "summary": "Long form.",
                    "tags": [],
                    "confidence": 0.8,
                    "provenance_state": "extracted",
                    "source_ranges": ["1-3"],
                    "contradicted_by": [],
                    "extraction_hash": "a",
                },
                {
                    "name": "RAG",
                    "aliases": ["Retrieval Augmented Generation"],
                    "summary": "Short form.",
                    "tags": [],
                    "confidence": 0.9,
                    "provenance_state": "extracted",
                    "source_ranges": ["8-10"],
                    "contradicted_by": [],
                    "extraction_hash": "b",
                },
            ],
        )

        concept = state.get_concept("RAG")
        assert concept is not None
        links = state.source_concepts_for_concept(concept.id)

    assert len(links) == 1
    assert links[0].source_ranges == ["1-3", "8-10"]
    assert links[0].confidence == 0.9
