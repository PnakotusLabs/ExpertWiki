from __future__ import annotations

import argparse
import json
import sys

from .authoring import (
    audit_bundle,
    bundle_status,
    create_page,
    ingest_source,
    init_bundle,
    list_concepts,
    package_dry_run,
    query_bundle,
    rebuild_indexes,
    show_concept,
)
from .linting import lint_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="expertwiki")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a local LLM Wiki")
    init_parser.add_argument(
        "bundle_dir",
        nargs="?",
        default="expertwiki",
        help="Bundle directory to create. Defaults to ./expertwiki",
    )
    init_parser.add_argument("--title")
    init_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a local file or URL as a raw source")
    ingest_parser.add_argument("bundle_dir")
    ingest_parser.add_argument("source")
    ingest_parser.add_argument("--title")
    ingest_parser.add_argument("--publisher", default="Unknown")
    ingest_parser.add_argument("--slug")
    ingest_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    page_parser = subparsers.add_parser("page", help="Create or manage wiki pages")
    page_subparsers = page_parser.add_subparsers(dest="page_command", required=True)
    page_create = page_subparsers.add_parser("create", help="Create a wiki page")
    page_create.add_argument("bundle_dir")
    page_create.add_argument("page_path")
    page_create.add_argument("--title", required=True)
    page_create.add_argument("--description")
    page_create.add_argument("--source", action="append", default=[])
    page_create.add_argument("--tag", action="append", default=[])
    page_create.add_argument("--json", action="store_true", help="Emit JSON output")

    list_parser = subparsers.add_parser("list", help="List wiki pages, sources, or audits")
    list_parser.add_argument("bundle_dir")
    list_parser.add_argument("kind", choices=["pages", "sources", "audits"])
    list_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    show_parser = subparsers.add_parser("show", help="Show a wiki page, source, or audit")
    show_parser.add_argument("bundle_dir")
    show_parser.add_argument("ref")
    show_parser.add_argument("--kind", choices=["pages", "sources", "audits"])
    show_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    query_parser = subparsers.add_parser("query", help="Search local wiki pages")
    query_parser.add_argument("bundle_dir")
    query_parser.add_argument("query")
    query_parser.add_argument("--limit", type=int, default=10)
    query_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    lint_parser = subparsers.add_parser("lint", help="Check a local LLM Wiki")
    lint_parser.add_argument("bundle_dir")
    lint_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    status_parser = subparsers.add_parser("status", help="Summarize a wiki for agents")
    status_parser.add_argument("bundle_dir")
    status_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    index_parser = subparsers.add_parser("index", help="Rebuild index.md files")
    index_parser.add_argument("bundle_dir")
    index_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    audit_parser = subparsers.add_parser("audit", help="Write a local audit report")
    audit_parser.add_argument("bundle_dir")
    audit_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    package_parser = subparsers.add_parser("package", help="Run package preflight checks")
    package_parser.add_argument("bundle_dir")
    package_parser.add_argument("--dry-run", action="store_true", required=True)
    package_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            return _run_init(args.bundle_dir, title=args.title, emit_json=args.json)
        if args.command == "ingest":
            return _run_ingest(
                args.bundle_dir,
                args.source,
                title=args.title,
                publisher=args.publisher,
                slug=args.slug,
                emit_json=args.json,
            )
        if args.command == "page" and args.page_command == "create":
            return _run_page_create(
                args.bundle_dir,
                args.page_path,
                title=args.title,
                description=args.description,
                sources=args.source,
                tags=args.tag,
                emit_json=args.json,
            )
        if args.command == "list":
            return _run_list(args.bundle_dir, kind=args.kind, emit_json=args.json)
        if args.command == "show":
            return _run_show(args.bundle_dir, args.ref, kind=args.kind, emit_json=args.json)
        if args.command == "query":
            return _run_query(args.bundle_dir, args.query, limit=args.limit, emit_json=args.json)
        if args.command == "lint":
            return _run_lint(args.bundle_dir, emit_json=args.json)
        if args.command == "status":
            return _run_status(args.bundle_dir, emit_json=args.json)
        if args.command == "index":
            return _run_index(args.bundle_dir, emit_json=args.json)
        if args.command == "audit":
            return _run_audit(args.bundle_dir, emit_json=args.json)
        if args.command == "package":
            return _run_package_dry_run(args.bundle_dir, emit_json=args.json)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_init(bundle_dir: str, *, title: str | None, emit_json: bool) -> int:
    result = init_bundle(bundle_dir, title=title)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Initialized ExpertWiki LLM Wiki at {result.root}")
        for path in result.created_files:
            print(f"created {path}")
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
    result = ingest_source(bundle_dir, source, title=title, publisher=publisher, slug=slug)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Ingested source: {result.source_path}")
    return 0


def _run_page_create(
    bundle_dir: str,
    page_path: str,
    *,
    title: str,
    description: str | None,
    sources: list[str],
    tags: list[str],
    emit_json: bool,
) -> int:
    result = create_page(
        bundle_dir,
        page_path,
        title=title,
        description=description,
        sources=sources,
        tags=tags,
    )
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Created wiki page: {result.page_path}")
    return 0


def _run_list(bundle_dir: str, *, kind: str, emit_json: bool) -> int:
    result = list_concepts(bundle_dir, kind=kind)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"{kind}: {len(result.items)}")
        for item in result.items:
            print(f"- {item['path']}: {item.get('title') or item['id']}")
    return 0


def _run_show(bundle_dir: str, ref: str, *, kind: str | None, emit_json: bool) -> int:
    result = show_concept(bundle_dir, ref, kind=kind)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        metadata = result.concept["metadata"]
        print(result.path)
        print(f"type: {result.concept['type']}")
        print(f"title: {metadata.get('title', '')}")
        print()
        print(result.concept["body"])
    return 0


def _run_query(bundle_dir: str, query: str, *, limit: int, emit_json: bool) -> int:
    result = query_bundle(bundle_dir, query, limit=limit)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Query: {result.query}")
        print(f"Results: {len(result.results)}")
        for item in result.results:
            page = item["page"]
            print(f"- {page['id']}: {page['title']}")
            print(f"  {page['description']}")
    return 0


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
        print(f"ExpertWiki lint {status}: {counts['critical']} critical, {counts['warning']} warning")
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
        print("Concepts:")
        for concept_type, count in sorted(result.concept_counts.items()):
            print(f"  {concept_type}: {count}")
        print(f"Latest audit: {result.latest_audit or 'none'}")
        print("Next actions:")
        for action in result.next_actions:
            print(f"  - {action}")
    return 0 if result.ok else 1


def _run_index(bundle_dir: str, *, emit_json: bool) -> int:
    result = rebuild_indexes(bundle_dir)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Rebuilt {len(result.updated_indexes)} index file(s)")
        for path in result.updated_indexes:
            print(f"updated {path}")
    return 0


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


def _run_package_dry_run(bundle_dir: str, *, emit_json: bool) -> int:
    result = package_dry_run(bundle_dir)
    if emit_json:
        print(
            json.dumps(
                {
                    "root": result.root,
                    "ok": result.ok,
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
        for concept_type, count in sorted(result.concept_counts.items()):
            print(f"{concept_type}: {count}")
        for issue in result.issues:
            location = f" {issue.path}" if issue.path else ""
            print(f"[{issue.severity}]{location}: {issue.message}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
