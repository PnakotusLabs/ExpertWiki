from __future__ import annotations

import argparse
import json
import sys

from .authoring import (
    audit_bundle,
    bundle_status,
    compile_claim_draft,
    ingest_source,
    init_bundle,
    list_concepts,
    mark_claim,
    package_dry_run,
    query_bundle,
    rebuild_indexes,
    show_concept,
    verify_claim,
)
from .linting import lint_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="expertwiki")
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint_parser = subparsers.add_parser("lint", help="Check an OKF bundle")
    lint_parser.add_argument("bundle_dir")
    lint_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    status_parser = subparsers.add_parser("status", help="Summarize a bundle for agents")
    status_parser.add_argument("bundle_dir")
    status_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    init_parser = subparsers.add_parser("init", help="Create a new OKF bundle")
    init_parser.add_argument("bundle_dir")
    init_parser.add_argument("--title")
    init_parser.add_argument(
        "--access-mode",
        choices=["open", "gated", "remote_only", "enterprise_private"],
        default="open",
    )
    init_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    index_parser = subparsers.add_parser("index", help="Rebuild bundle index.md files")
    index_parser.add_argument("bundle_dir")
    index_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a local file or record a URL as a Source")
    ingest_parser.add_argument("bundle_dir")
    ingest_parser.add_argument("source")
    ingest_parser.add_argument("--title")
    ingest_parser.add_argument("--publisher", default="Unknown")
    ingest_parser.add_argument("--slug")
    ingest_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    compile_parser = subparsers.add_parser("compile", help="Create a draft claim from a Source")
    compile_parser.add_argument("bundle_dir")
    compile_parser.add_argument("source_ref")
    compile_parser.add_argument("--title")
    compile_parser.add_argument("--claim")
    compile_parser.add_argument("--slug")
    compile_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    verify_parser = subparsers.add_parser("verify", help="Mark a draft claim as reviewed or verified")
    verify_parser.add_argument("bundle_dir")
    verify_parser.add_argument("claim_ref")
    verify_parser.add_argument("--reviewer", required=True)
    verify_parser.add_argument("--method", default="source_audit")
    verify_parser.add_argument("--confidence", choices=["high", "medium", "low"], default="high")
    verify_parser.add_argument("--status", choices=["reviewed", "verified"], default="verified")
    verify_parser.add_argument("--verified-at")
    verify_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    mark_parser = subparsers.add_parser("mark", help="Update a claim lifecycle status")
    mark_parser.add_argument("bundle_dir")
    mark_parser.add_argument("claim_ref")
    mark_parser.add_argument(
        "--status",
        required=True,
        choices=["draft", "reviewed", "verified", "disputed", "stale", "rejected"],
    )
    mark_parser.add_argument("--reason")
    mark_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    list_parser = subparsers.add_parser("list", help="List bundle concepts")
    list_parser.add_argument("bundle_dir")
    list_parser.add_argument("kind", choices=["claims", "sources", "reviews", "audits"])
    list_parser.add_argument("--status")
    list_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    show_parser = subparsers.add_parser("show", help="Show a bundle concept")
    show_parser.add_argument("bundle_dir")
    show_parser.add_argument("ref")
    show_parser.add_argument("--kind", choices=["claims", "sources", "reviews", "audits"])
    show_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    query_parser = subparsers.add_parser("query", help="Query local verified claims")
    query_parser.add_argument("bundle_dir")
    query_parser.add_argument("query")
    query_parser.add_argument("--limit", type=int, default=10)
    query_parser.add_argument("--status", default="verified")
    query_parser.add_argument("--all-statuses", action="store_true")
    query_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    package_parser = subparsers.add_parser("package", help="Run package preflight checks")
    package_parser.add_argument("bundle_dir")
    package_parser.add_argument("--dry-run", action="store_true", required=True)
    package_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    audit_parser = subparsers.add_parser("audit", help="Write a local audit report")
    audit_parser.add_argument("bundle_dir")
    audit_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    args = parser.parse_args(argv)
    if args.command == "lint":
        return _run_lint(args.bundle_dir, emit_json=args.json)
    if args.command == "status":
        return _run_status(args.bundle_dir, emit_json=args.json)
    if args.command == "init":
        return _run_init(
            args.bundle_dir,
            title=args.title,
            access_mode=args.access_mode,
            emit_json=args.json,
        )
    if args.command == "index":
        return _run_index(args.bundle_dir, emit_json=args.json)
    if args.command == "ingest":
        return _run_ingest(
            args.bundle_dir,
            args.source,
            title=args.title,
            publisher=args.publisher,
            slug=args.slug,
            emit_json=args.json,
        )
    if args.command == "compile":
        return _run_compile(
            args.bundle_dir,
            args.source_ref,
            title=args.title,
            claim=args.claim,
            slug=args.slug,
            emit_json=args.json,
        )
    if args.command == "verify":
        return _run_verify(
            args.bundle_dir,
            args.claim_ref,
            reviewer=args.reviewer,
            method=args.method,
            confidence=args.confidence,
            status=args.status,
            verified_at=args.verified_at,
            emit_json=args.json,
        )
    if args.command == "mark":
        return _run_mark(
            args.bundle_dir,
            args.claim_ref,
            status=args.status,
            reason=args.reason,
            emit_json=args.json,
        )
    if args.command == "list":
        return _run_list(
            args.bundle_dir,
            kind=args.kind,
            status=args.status,
            emit_json=args.json,
        )
    if args.command == "show":
        return _run_show(
            args.bundle_dir,
            args.ref,
            kind=args.kind,
            emit_json=args.json,
        )
    if args.command == "query":
        status = None if args.all_statuses else args.status
        return _run_query(
            args.bundle_dir,
            args.query,
            status=status,
            limit=args.limit,
            emit_json=args.json,
        )
    if args.command == "package":
        return _run_package_dry_run(args.bundle_dir, emit_json=args.json)
    if args.command == "audit":
        return _run_audit(args.bundle_dir, emit_json=args.json)

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_lint(bundle_dir: str, *, emit_json: bool) -> int:
    result = lint_bundle(bundle_dir)
    if emit_json:
        print(
            json.dumps(
                {
                    "root": result.root,
                    "ok": result.ok,
                    "counts": result.counts(),
                    "issues": [issue.__dict__ for issue in result.issues],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        counts = result.counts()
        status = "OK" if result.ok else "FAILED"
        print(
            "ExpertWiki lint "
            f"{status}: {counts['critical']} critical, "
            f"{counts['warning']} warning, {counts['suggestion']} suggestion"
        )
        for issue in result.issues:
            location = f" {issue.path}" if issue.path else ""
            print(f"[{issue.severity}]{location}: {issue.message}")
    return 0 if result.ok else 1


def _run_status(bundle_dir: str, *, emit_json: bool) -> int:
    result = bundle_status(bundle_dir)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        status = "OK" if result.ok else "NEEDS ATTENTION"
        print(f"ExpertWiki status {status}")
        print(f"Access mode: {result.access_mode or 'missing'}")
        print("Concepts:")
        for concept_type, count in sorted(result.concept_counts.items()):
            print(f"  {concept_type}: {count}")
        print("Claims:")
        for claim_status, count in sorted(result.claim_status_counts.items()):
            if count:
                print(f"  {claim_status}: {count}")
        print(f"Latest audit: {result.latest_audit or 'none'}")
        print("Next actions:")
        for action in result.next_actions:
            print(f"  - {action}")
    return 0 if result.ok else 1


def _run_init(
    bundle_dir: str,
    *,
    title: str | None,
    access_mode: str,
    emit_json: bool,
) -> int:
    result = init_bundle(bundle_dir, title=title, access_mode=access_mode)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Initialized ExpertWiki bundle at {result.root}")
        for path in result.created_files:
            print(f"created {path}")
    return 0


def _run_index(bundle_dir: str, *, emit_json: bool) -> int:
    result = rebuild_indexes(bundle_dir)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Rebuilt {len(result.updated_indexes)} index file(s)")
        for path in result.updated_indexes:
            print(f"updated {path}")
    return 0


def _run_ingest(
    bundle_dir: str,
    source: str,
    *,
    title: str | None,
    publisher: str,
    slug: str | None,
    emit_json: bool,
) -> int:
    result = ingest_source(
        bundle_dir,
        source,
        title=title,
        publisher=publisher,
        slug=slug,
    )
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Ingested source: {result.source_path}")
    return 0


def _run_compile(
    bundle_dir: str,
    source_ref: str,
    *,
    title: str | None,
    claim: str | None,
    slug: str | None,
    emit_json: bool,
) -> int:
    result = compile_claim_draft(
        bundle_dir,
        source_ref,
        title=title,
        claim=claim,
        slug=slug,
    )
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Created draft claim: {result.claim_path}")
    return 0


def _run_verify(
    bundle_dir: str,
    claim_ref: str,
    *,
    reviewer: str,
    method: str,
    confidence: str,
    status: str,
    verified_at: str | None,
    emit_json: bool,
) -> int:
    result = verify_claim(
        bundle_dir,
        claim_ref,
        reviewer=reviewer,
        method=method,
        confidence=confidence,
        status=status,
        verified_at=verified_at,
    )
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Updated claim: {result.claim_path} -> {result.status}")
    return 0


def _run_mark(
    bundle_dir: str,
    claim_ref: str,
    *,
    status: str,
    reason: str | None,
    emit_json: bool,
) -> int:
    result = mark_claim(bundle_dir, claim_ref, status=status, reason=reason)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Marked claim: {result.claim_path} -> {result.status}")
    return 0


def _run_list(
    bundle_dir: str,
    *,
    kind: str,
    status: str | None,
    emit_json: bool,
) -> int:
    result = list_concepts(bundle_dir, kind=kind, status=status)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"{kind}: {len(result.items)}")
        for item in result.items:
            status_text = f" [{item['status']}]" if item.get("status") else ""
            print(f"- {item['path']}{status_text}: {item.get('title') or item['id']}")
    return 0


def _run_show(
    bundle_dir: str,
    ref: str,
    *,
    kind: str | None,
    emit_json: bool,
) -> int:
    result = show_concept(bundle_dir, ref, kind=kind)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        metadata = result.concept["metadata"]
        print(f"{result.path}")
        print(f"type: {result.concept['type']}")
        print(f"title: {metadata.get('title', '')}")
        if metadata.get("status"):
            print(f"status: {metadata['status']}")
        print()
        print(result.concept["body"])
    return 0


def _run_query(
    bundle_dir: str,
    query: str,
    *,
    status: str | None,
    limit: int,
    emit_json: bool,
) -> int:
    result = query_bundle(bundle_dir, query, status=status, limit=limit)
    if emit_json:
        print(
            json.dumps(
                {
                    "query": result.query,
                    "status": result.status,
                    "results": result.results,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"Query: {result.query}")
        print(f"Results: {len(result.results)}")
        for item in result.results:
            claim = item["claim"]
            print(f"- {claim['id']} [{claim['confidence']}, {claim['status']}]")
            print(f"  {claim['text']}")
            for source in claim.get("source_records", []):
                print(f"  Source: {source['title']} ({source['url']})")
    return 0


def _run_package_dry_run(bundle_dir: str, *, emit_json: bool) -> int:
    result = package_dry_run(bundle_dir)
    if emit_json:
        print(
            json.dumps(
                {
                    "root": result.root,
                    "ok": result.ok,
                    "access_mode": result.access_mode,
                    "concept_counts": result.concept_counts,
                    "issues": [issue.__dict__ for issue in result.issues],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        status = "OK" if result.ok else "FAILED"
        print(f"Package dry-run {status}")
        print(f"Access mode: {result.access_mode or 'missing'}")
        for concept_type, count in sorted(result.concept_counts.items()):
            print(f"{concept_type}: {count}")
        for issue in result.issues:
            location = f" {issue.path}" if issue.path else ""
            print(f"[{issue.severity}]{location}: {issue.message}")
    return 0 if result.ok else 1


def _run_audit(bundle_dir: str, *, emit_json: bool) -> int:
    result = audit_bundle(bundle_dir)
    if emit_json:
        print(
            json.dumps(
                {
                    "root": result.root,
                    "audit_path": result.audit_path,
                    "ok": result.ok,
                    "issues": [issue.__dict__ for issue in result.issues],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        status = "OK" if result.ok else "FAILED"
        print(f"Audit {status}: {result.audit_path}")
        for issue in result.issues:
            location = f" {issue.path}" if issue.path else ""
            print(f"[{issue.severity}]{location}: {issue.message}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
