#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
CITATION_RE = re.compile(r"\^\[([^\]]+)\]")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle")
    parser.add_argument("run_dir")
    parser.add_argument("--phase", required=True)
    parser.add_argument("--ordinal", type=int, required=True)
    args = parser.parse_args()

    bundle = Path(args.bundle).resolve()
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    previous = _read_json(run_dir / "metrics-state.json") or {}
    snapshot, state = collect_metrics(bundle, previous, args.phase, args.ordinal)
    _write_json(run_dir / "metrics-state.json", state)
    with (run_dir / "metrics.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n")
    _append_markdown(run_dir / "metrics.log", snapshot)
    print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def collect_metrics(
    bundle: Path,
    previous: dict[str, Any],
    phase: str,
    ordinal: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    database = bundle / ".expertwiki" / "state.sqlite"
    if not database.exists():
        current = _empty_state()
    else:
        current = _read_compiler_state(database)
    artifacts = _artifact_inventory(bundle)
    graph = _graph_metrics(bundle, artifacts)
    citations = _citation_metrics(bundle, artifacts, set(current["sources"]))

    old_sources = previous.get("sources", {})
    new_sources = sorted(set(current["sources"]) - set(old_sources))
    deleted_sources = sorted(set(old_sources) - set(current["sources"]))
    changed_sources = sorted(
        path for path in set(current["sources"]) & set(old_sources)
        if current["sources"][path] != old_sources[path]
    )
    unchanged_sources = sorted(
        path for path in set(current["sources"]) & set(old_sources)
        if current["sources"][path] == old_sources[path]
    )
    direct = set(new_sources) | set(changed_sources) | set(deleted_sources)
    touched_concepts: set[int] = set()
    for path in direct:
        touched_concepts.update(current["source_concepts"].get(path, []))
        touched_concepts.update(previous.get("source_concepts", {}).get(path, []))
    affected = {
        path
        for path, concept_ids in current["source_concepts"].items()
        if path not in direct and touched_concepts.intersection(concept_ids)
    }

    active_direct = set(new_sources) | set(changed_sources)
    mentions = sum(
        len(current["source_concepts"].get(path, [])) for path in active_direct
    )
    touched_current = {
        concept_id
        for path in active_direct
        for concept_id in current["source_concepts"].get(path, [])
    }
    old_concepts = set(previous.get("concept_ids", []))
    new_canonical = touched_current - old_concepts
    merge_count = max(0, mentions - len(new_canonical))

    contributor_counts: dict[int, int] = {}
    for concept_ids in current["source_concepts"].values():
        for concept_id in concept_ids:
            contributor_counts[concept_id] = contributor_counts.get(concept_id, 0) + 1
    shared_count = sum(1 for count in contributor_counts.values() if count >= 2)
    avg_sources = (
        sum(contributor_counts.values()) / len(contributor_counts)
        if contributor_counts else 0.0
    )

    old_artifacts = previous.get("artifacts", {})
    created_artifacts = set(artifacts) - set(old_artifacts)
    updated_artifacts = {
        path for path in set(artifacts) & set(old_artifacts)
        if artifacts[path]["hash"] != old_artifacts[path]["hash"]
    }
    unchanged_artifacts = {
        path for path in set(artifacts) & set(old_artifacts)
        if artifacts[path]["hash"] == old_artifacts[path]["hash"]
    }

    scanned = len(set(current["sources"]) | set(old_sources))
    durations = current["job_durations"]
    snapshot = {
        "protocol": "expertwiki.metrics-snapshot/v1",
        "timestamp": _timestamp(),
        "phase": phase,
        "ordinal": ordinal,
        "incremental_input": {
            "sources_new": len(new_sources),
            "sources_changed": len(changed_sources),
            "sources_deleted": len(deleted_sources),
            "sources_unchanged": len(unchanged_sources),
            "sources_scanned": scanned,
        },
        "incremental_efficiency": {
            "incremental_skip_rate": _ratio(len(unchanged_sources), scanned),
        },
        "dependency_spread": {
            "affected_source_count": len(affected),
            "dependency_amplification": (
                round((len(direct) + len(affected)) / len(direct), 4) if direct else 0.0
            ),
        },
        "concept_extraction": {"concept_mentions_extracted": mentions},
        "concept_deduplication": {
            "canonical_concepts_touched": len(touched_current),
            "new_canonical_concepts": len(new_canonical),
            "concept_merge_count": merge_count,
            "merge_rate": _ratio(merge_count, mentions),
        },
        "concept_sharing": {
            "shared_concept_count": shared_count,
            "avg_sources_per_concept": round(avg_sources, 4),
            "source_concept_edges": sum(contributor_counts.values()),
        },
        "page_artifacts": {
            "pages_created": len(created_artifacts),
            "pages_updated": len(updated_artifacts),
            "pages_unchanged": len(unchanged_artifacts),
            "pages_failed": current["failed_compile_jobs"],
            "pages_held": current["pending_drafts"],
            "drafts_total": current["pending_drafts"],
            "published_total": current["published_articles"],
        },
        "review": {
            "pending": current["pending_drafts"],
            "approved": current["approved_articles"],
            "rejected": current["rejections"],
            "approval_latency_seconds": current["approval_latency_seconds"],
        },
        "knowledge_graph": graph,
        "citation_quality": citations["quality"],
        "source_utilization": citations["utilization"],
        "freshness": {
            "stale_pages": current["stale_articles"],
            "frozen_pages": current["frozen_concepts"],
            "orphaned_pages": current["orphaned_concepts"],
        },
        "reliability": {
            "jobs_completed": current["job_statuses"].get("completed", 0),
            "jobs_failed": current["job_statuses"].get("failed", 0),
            "jobs_stale": current["job_statuses"].get("stale", 0),
            "jobs_retried": current["retried_jobs"],
            "duration_p95_seconds": _percentile(durations, 0.95),
        },
        "totals": {
            "sources": len(current["sources"]),
            "canonical_concepts": len(current["concept_ids"]),
            "artifacts": len(artifacts),
        },
    }
    state = {
        "sources": current["sources"],
        "source_concepts": current["source_concepts"],
        "concept_ids": current["concept_ids"],
        "artifacts": artifacts,
    }
    return snapshot, state


def _read_compiler_state(database: Path) -> dict[str, Any]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    sources = {
        str(row["path"]): str(row["content_hash"])
        for row in connection.execute("SELECT path, content_hash FROM sources WHERE status != 'deleted'")
    }
    source_concepts: dict[str, list[int]] = {path: [] for path in sources}
    for row in connection.execute(
        """SELECT sc.source_path, sc.concept_id FROM source_concepts sc
        JOIN sources s ON s.path = sc.source_path WHERE s.status != 'deleted'"""
    ):
        source_concepts.setdefault(str(row["source_path"]), []).append(int(row["concept_id"]))
    for values in source_concepts.values():
        values.sort()
    concept_ids = [int(row[0]) for row in connection.execute("SELECT id FROM concepts")]
    job_statuses = {
        str(row[0]): int(row[1])
        for row in connection.execute("SELECT status, COUNT(*) FROM agent_jobs GROUP BY status")
    }
    durations: list[float] = []
    for row in connection.execute(
        "SELECT claimed_at, completed_at FROM agent_jobs WHERE claimed_at IS NOT NULL AND completed_at IS NOT NULL"
    ):
        start = _parse_time(row[0])
        end = _parse_time(row[1])
        if start and end and end >= start:
            durations.append((end - start).total_seconds())
    latencies: list[float] = []
    for row in connection.execute(
        "SELECT compiled_at, approved_at FROM articles WHERE compiled_at IS NOT NULL AND approved_at IS NOT NULL"
    ):
        start = _parse_time(row[0])
        end = _parse_time(row[1])
        if start and end and end >= start:
            latencies.append((end - start).total_seconds())
    result = {
        "sources": sources,
        "source_concepts": source_concepts,
        "concept_ids": concept_ids,
        "pending_drafts": _count(connection, "drafts", "status = 'pending_review'"),
        "published_articles": _count(connection, "articles", "status = 'published'"),
        "approved_articles": _count(connection, "articles", "approved_at IS NOT NULL"),
        "stale_articles": _count(connection, "articles", "status = 'stale'"),
        "rejections": _count(connection, "rejections"),
        "frozen_concepts": _count(connection, "concepts", "status = 'frozen'"),
        "orphaned_concepts": _count(connection, "concepts", "status = 'orphaned'"),
        "failed_compile_jobs": _count(
            connection, "agent_jobs", "kind = 'compile_concept' AND status = 'failed'"
        ),
        "job_statuses": job_statuses,
        "retried_jobs": int(connection.execute(
            "SELECT COUNT(*) FROM agent_jobs WHERE attempts > 1"
        ).fetchone()[0]),
        "job_durations": durations,
        "approval_latency_seconds": round(sum(latencies) / len(latencies), 3) if latencies else None,
    }
    connection.close()
    return result


def _artifact_inventory(bundle: Path) -> dict[str, dict[str, str]]:
    paths = list((bundle / ".expertwiki" / "drafts").glob("*.md"))
    paths.extend(
        path for path in (bundle / "wiki").rglob("*.md")
        if path.name != "index.md" and not any(part.startswith(".") for part in path.parts)
    )
    return {
        path.relative_to(bundle).as_posix(): {
            "hash": hashlib.sha256(path.read_bytes()).hexdigest(),
            "title": _frontmatter_title(path.read_text(encoding="utf-8")) or path.stem,
        }
        for path in sorted(set(paths))
    }


def _graph_metrics(bundle: Path, artifacts: dict[str, dict[str, str]]) -> dict[str, Any]:
    title_to_path = {data["title"].casefold(): path for path, data in artifacts.items()}
    adjacency = {path: set() for path in artifacts}
    dangling: set[str] = set()
    for path in artifacts:
        text = (bundle / path).read_text(encoding="utf-8")
        for raw_target in WIKILINK_RE.findall(text):
            target = title_to_path.get(raw_target.strip().casefold())
            if target:
                adjacency[path].add(target)
            else:
                dangling.add(raw_target.strip())
    edges = {(source, target) for source, targets in adjacency.items() for target in targets}
    indegree = {path: 0 for path in artifacts}
    for _, target in edges:
        indegree[target] += 1
    components = _component_count(adjacency)
    return {
        "resolved_edges": len(edges),
        "avg_indegree": round(len(edges) / len(artifacts), 4) if artifacts else 0.0,
        "components": components,
        "dangling_links": len(dangling),
        "unreferenced_pages": sum(1 for value in indegree.values() if value == 0),
    }


def _citation_metrics(
    bundle: Path,
    artifacts: dict[str, dict[str, str]],
    active_sources: set[str],
) -> dict[str, Any]:
    total_prose = cited_prose = total = valid = claim_level = 0
    cited_sources: set[str] = set()
    for path in artifacts:
        text = _body((bundle / path).read_text(encoding="utf-8"))
        for paragraph in re.split(r"\n\s*\n", text):
            clean = paragraph.strip()
            if not clean or clean.startswith(("#", "- ", "* ", ">", "```")):
                continue
            total_prose += 1
            markers = CITATION_RE.findall(clean)
            if markers:
                cited_prose += 1
            for marker in markers:
                for raw in [part.strip() for part in marker.split(",") if part.strip()]:
                    total += 1
                    match = re.fullmatch(r"(.+?\.md)(?::(\d+)(?:-(\d+))?)?", raw)
                    if not match:
                        continue
                    source_path = match.group(1).removeprefix("/")
                    start = int(match.group(2)) if match.group(2) else None
                    end = int(match.group(3) or match.group(2)) if match.group(2) else None
                    source_file = bundle / source_path
                    line_count = len(source_file.read_text(encoding="utf-8").splitlines()) if source_file.exists() else 0
                    if source_path in active_sources and source_file.exists() and (
                        start is None or (1 <= start <= (end or 0) <= line_count)
                    ):
                        valid += 1
                        cited_sources.add(source_path)
                    if start is not None:
                        claim_level += 1
    return {
        "quality": {
            "citation_coverage": _ratio(cited_prose, total_prose),
            "citation_precision": _ratio(valid, total),
            "claim_level_rate": _ratio(claim_level, total),
            "total_citations": total,
        },
        "utilization": {
            "source_utilization_rate": _ratio(len(cited_sources), len(active_sources)),
            "uncited_sources": len(active_sources - cited_sources),
        },
    }


def _component_count(adjacency: dict[str, set[str]]) -> int:
    undirected = {node: set(targets) for node, targets in adjacency.items()}
    for source, targets in adjacency.items():
        for target in targets:
            undirected.setdefault(target, set()).add(source)
    seen: set[str] = set()
    count = 0
    for node in undirected:
        if node in seen:
            continue
        count += 1
        stack = [node]
        seen.add(node)
        while stack:
            for neighbor in undirected.get(stack.pop(), set()):
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
    return count


def _append_markdown(path: Path, snapshot: dict[str, Any]) -> None:
    if not path.exists():
        path.write_text(
            "# ExpertWiki Metric Checkpoints\n\n"
            "| Ordinal | Phase | Sources | Concepts | Merge rate | Artifacts | Pending | Edges | Citation coverage | Source utilization | Failed jobs |\n"
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n",
            encoding="utf-8",
        )
    row = (
        f"| {snapshot['ordinal']} | {snapshot['phase']} | {snapshot['totals']['sources']} | "
        f"{snapshot['totals']['canonical_concepts']} | {snapshot['concept_deduplication']['merge_rate']:.3f} | "
        f"{snapshot['totals']['artifacts']} | {snapshot['review']['pending']} | "
        f"{snapshot['knowledge_graph']['resolved_edges']} | {snapshot['citation_quality']['citation_coverage']:.3f} | "
        f"{snapshot['source_utilization']['source_utilization_rate']:.3f} | {snapshot['reliability']['jobs_failed']} |\n"
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(row)


def _frontmatter_title(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    match = re.search(r"^title:\s*(.+)$", text[4:end], re.MULTILINE)
    return match.group(1).strip().strip('"\'') if match else None


def _body(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            return text[end + 5:]
    return text


def _count(connection: sqlite3.Connection, table: str, where: str | None = None) -> int:
    sql = f"SELECT COUNT(*) FROM {table}"
    if where:
        sql += f" WHERE {where}"
    return int(connection.execute(sql).fetchone()[0])


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * percentile + 0.999999)))
    return round(ordered[index], 3)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else None


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _empty_state() -> dict[str, Any]:
    return {
        "sources": {}, "source_concepts": {}, "concept_ids": [],
        "pending_drafts": 0, "published_articles": 0, "approved_articles": 0,
        "stale_articles": 0, "rejections": 0, "frozen_concepts": 0,
        "orphaned_concepts": 0, "failed_compile_jobs": 0, "job_statuses": {},
        "retried_jobs": 0, "job_durations": [], "approval_latency_seconds": None,
    }


if __name__ == "__main__":
    raise SystemExit(main())
