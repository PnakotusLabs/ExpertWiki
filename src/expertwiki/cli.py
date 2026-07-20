from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
import sys
from pathlib import Path

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
from .agent_jobs import (
    agent_job_status,
    fail_agent_job,
    next_agent_job,
    prepare_agent_jobs,
    public_agent_job,
    retry_agent_job,
    submit_agent_job,
)
from .experience import (
    add_material,
    approve_suggestion,
    ask_wiki,
    doctor_experience,
    reject_suggestion,
    review_suggestions,
    start_experience,
)
from .compiler import analyze_bundle, compile_bundle, compiler_stats
from .concurrency import BundleLockedError
from .linting import lint_bundle
from .publish import publish_bundle
from .viewer import serve_viewer


def _default_bundle_dir() -> str:
    return str(Path.home() / ".expertwiki")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="expertwiki")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a local ExpertWiki knowledge bundle")
    init_parser.add_argument(
        "bundle_dir",
        nargs="?",
        default=_default_bundle_dir(),
        help="Bundle directory to create. Defaults to ~/.expertwiki",
    )
    init_parser.add_argument("--title")
    init_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    start_parser = subparsers.add_parser("start", help="Set up or summarize the default ExpertWiki")
    start_parser.add_argument("bundle_dir", nargs="?", default=_default_bundle_dir())
    start_parser.add_argument("--title")
    start_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    add_parser = subparsers.add_parser("add", help="Add material and queue host-AI generation jobs")
    add_parser.add_argument("paths", nargs="+", help="Either <source> or <bundle_dir> <source>")
    add_parser.add_argument("--title")
    add_parser.add_argument("--publisher", default="Unknown")
    add_parser.add_argument("--slug")
    add_parser.add_argument("--backend", choices=["host", "api"], default="host")
    add_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    analyze_parser = subparsers.add_parser(
        "analyze", help="Extract concepts and dependencies from changed raw sources"
    )
    analyze_parser.add_argument("bundle_dir", nargs="?", default=_default_bundle_dir())
    analyze_parser.add_argument("--all", action="store_true", dest="analyze_all")
    analyze_parser.add_argument("--backend", choices=["host", "api"], default="host")
    analyze_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    compile_parser = subparsers.add_parser(
        "compile", help="Incrementally analyze sources and compile concept drafts"
    )
    compile_parser.add_argument("bundle_dir", nargs="?", default=_default_bundle_dir())
    compile_parser.add_argument("--concept", action="append", default=[])
    compile_parser.add_argument("--no-analyze", action="store_true")
    compile_parser.add_argument("--force", action="store_true")
    compile_parser.add_argument("--allow-manual-overwrite", action="store_true")
    compile_parser.add_argument("--backend", choices=["host", "api"], default="host")
    compile_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    review_parser = subparsers.add_parser("review", help="Review suggested cards")
    review_parser.add_argument("bundle_dir", nargs="?", default=_default_bundle_dir())
    review_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    approve_parser = subparsers.add_parser("approve", help="Approve a suggested card into the wiki")
    approve_parser.add_argument("refs", nargs="+", help="Either <card> or <bundle_dir> <card>")
    approve_parser.add_argument("--force", action="store_true")
    approve_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    reject_parser = subparsers.add_parser("reject", help="Reject a suggested card with feedback")
    reject_parser.add_argument("refs", nargs="+", help="Either <card> or <bundle_dir> <card>")
    reject_parser.add_argument("--feedback", required=True)
    reject_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    ask_parser = subparsers.add_parser("ask", help="Ask the approved wiki")
    ask_parser.add_argument("parts", nargs="+", help="Either <question> or <bundle_dir> <question>")
    ask_parser.add_argument("--limit", type=int, default=5)
    ask_parser.add_argument("--backend", choices=["host", "api"], default="host")
    ask_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    doctor_parser = subparsers.add_parser("doctor", help="Explain what needs attention")
    doctor_parser.add_argument("bundle_dir", nargs="?", default=_default_bundle_dir())
    doctor_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    view_parser = subparsers.add_parser("view", help="Open the local read-only wiki viewer")
    view_parser.add_argument("bundle_dir", nargs="?", default=_default_bundle_dir())
    view_parser.add_argument("--host", default="127.0.0.1")
    view_parser.add_argument("--port", type=int, default=8765)
    view_parser.add_argument("--no-open", action="store_true", help="Do not open a browser")

    jobs_parser = subparsers.add_parser("jobs", help="Exchange generation jobs with the host AI")
    jobs_subparsers = jobs_parser.add_subparsers(dest="jobs_command", required=True)
    jobs_next = jobs_subparsers.add_parser("next", help="Claim the next host-AI job")
    jobs_next.add_argument("bundle_dir", nargs="?", default=_default_bundle_dir())
    jobs_next.add_argument("--json", action="store_true", help="Emit JSON output")
    jobs_submit = jobs_subparsers.add_parser("submit", help="Validate and apply a host-AI result")
    jobs_submit.add_argument("bundle_dir")
    jobs_submit.add_argument("job_id")
    jobs_submit.add_argument("--result", required=True, help="Result JSON path, or - for stdin")
    jobs_submit.add_argument("--generator", required=True, help="Host AI name, such as codex")
    jobs_submit.add_argument("--json", action="store_true", help="Emit JSON output")
    jobs_fail = jobs_subparsers.add_parser("fail", help="Record a host-AI job failure")
    jobs_fail.add_argument("bundle_dir")
    jobs_fail.add_argument("job_id")
    jobs_fail.add_argument("--error", required=True)
    jobs_fail.add_argument("--json", action="store_true", help="Emit JSON output")
    jobs_retry = jobs_subparsers.add_parser("retry", help="Retry a failed host-AI job")
    jobs_retry.add_argument("bundle_dir")
    jobs_retry.add_argument("job_id")
    jobs_retry.add_argument("--json", action="store_true", help="Emit JSON output")
    jobs_status = jobs_subparsers.add_parser("status", help="List host-AI job state")
    jobs_status.add_argument("bundle_dir", nargs="?", default=_default_bundle_dir())
    jobs_status.add_argument("--json", action="store_true", help="Emit JSON output")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a local file as a raw source")
    ingest_parser.add_argument("bundle_dir")
    ingest_parser.add_argument("source", help="Local text file to preserve as a raw source")
    ingest_parser.add_argument("--title")
    ingest_parser.add_argument("--publisher", default="Unknown")
    ingest_parser.add_argument("--slug")
    ingest_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    page_parser = subparsers.add_parser("page", help="Create or manage knowledge cards")
    page_subparsers = page_parser.add_subparsers(dest="page_command", required=True)
    page_create = page_subparsers.add_parser("create", help="Create a knowledge card")
    page_create.add_argument("bundle_dir")
    page_create.add_argument("page_path")
    page_create.add_argument("--title", required=True)
    page_create.add_argument("--description")
    page_create.add_argument("--source", action="append", default=[])
    page_create.add_argument("--tag", action="append", default=[])
    page_create.add_argument(
        "--entity-type",
        choices=["expert", "project", "viewpoint", "topic", "comparison", "synthesis"],
        default="topic",
        help="Knowledge card type written into frontmatter",
    )
    page_create.add_argument("--json", action="store_true", help="Emit JSON output")

    list_parser = subparsers.add_parser("list", help="List knowledge cards, sources, or audits")
    list_parser.add_argument("bundle_dir")
    list_parser.add_argument("kind", choices=["pages", "sources", "audits"])
    list_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    show_parser = subparsers.add_parser("show", help="Show a knowledge card, source, or audit")
    show_parser.add_argument("bundle_dir")
    show_parser.add_argument("ref")
    show_parser.add_argument("--kind", choices=["pages", "sources", "audits"])
    show_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    query_parser = subparsers.add_parser("query", help="Search local expert knowledge")
    query_parser.add_argument("bundle_dir")
    query_parser.add_argument("query")
    query_parser.add_argument("--limit", type=int, default=10)
    query_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    lint_parser = subparsers.add_parser("lint", help="Check a local ExpertWiki knowledge bundle")
    lint_parser.add_argument("bundle_dir")
    lint_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    status_parser = subparsers.add_parser("status", help="Summarize a knowledge bundle for agents")
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

    publish_parser = subparsers.add_parser("publish", help="Publish wiki pages to ExpertWikiSaaS")
    publish_parser.add_argument("bundle_dir")
    publish_parser.add_argument(
        "--endpoint",
        default=os.environ.get("EXPERTWIKI_PUBLISH_ENDPOINT"),
        help="Publish API endpoint. Can also be set with EXPERTWIKI_PUBLISH_ENDPOINT.",
    )
    publish_parser.add_argument(
        "--token",
        default=os.environ.get("EXPERTWIKI_PUBLISH_TOKEN"),
        help="Publish token. Can also be set with EXPERTWIKI_PUBLISH_TOKEN.",
    )
    publish_parser.add_argument("--dry-run", action="store_true", help="Run publish preflight without HTTP upload")
    publish_parser.add_argument("--json", action="store_true", help="Emit JSON output")

    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            return _run_init(args.bundle_dir, title=args.title, emit_json=args.json)
        if args.command == "start":
            return _run_start(args.bundle_dir, title=args.title, emit_json=args.json)
        if args.command == "add":
            bundle_dir, source = _resolve_bundle_and_value(args.paths, value_name="source")
            return _run_add(
                bundle_dir,
                source,
                title=args.title,
                publisher=args.publisher,
                slug=args.slug,
                backend=args.backend,
                emit_json=args.json,
            )
        if args.command == "analyze":
            return _run_analyze(
                args.bundle_dir,
                analyze_all=args.analyze_all,
                backend=args.backend,
                emit_json=args.json,
            )
        if args.command == "compile":
            return _run_compile(
                args.bundle_dir,
                concept_refs=args.concept,
                analyze_changes=not args.no_analyze,
                force=args.force,
                allow_manual_overwrite=args.allow_manual_overwrite,
                backend=args.backend,
                emit_json=args.json,
            )
        if args.command == "review":
            return _run_review(args.bundle_dir, emit_json=args.json)
        if args.command == "approve":
            bundle_dir, draft_ref = _resolve_bundle_and_value(args.refs, value_name="card")
            return _run_approve(bundle_dir, draft_ref, force=args.force, emit_json=args.json)
        if args.command == "reject":
            bundle_dir, draft_ref = _resolve_bundle_and_value(args.refs, value_name="card")
            return _run_reject(
                bundle_dir,
                draft_ref,
                feedback=args.feedback,
                emit_json=args.json,
            )
        if args.command == "ask":
            bundle_dir, question = _resolve_bundle_and_query(args.parts)
            return _run_ask(
                bundle_dir,
                question,
                limit=args.limit,
                backend=args.backend,
                emit_json=args.json,
            )
        if args.command == "doctor":
            return _run_doctor(args.bundle_dir, emit_json=args.json)
        if args.command == "view":
            return _run_view(
                args.bundle_dir,
                host=args.host,
                port=args.port,
                open_browser=not args.no_open,
            )
        if args.command == "jobs":
            return _run_jobs(args)
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
                entity_type=args.entity_type,
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
        if args.command == "publish":
            return _run_publish(
                args.bundle_dir,
                endpoint=args.endpoint,
                token=args.token,
                dry_run=args.dry_run,
                emit_json=args.json,
            )
    except (ValueError, BundleLockedError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _resolve_bundle_and_value(parts: list[str], *, value_name: str) -> tuple[str, str]:
    if len(parts) == 1:
        return _default_bundle_dir(), parts[0]
    if len(parts) == 2:
        return parts[0], parts[1]
    raise ValueError(f"Expected either <{value_name}> or <bundle_dir> <{value_name}>.")


def _resolve_bundle_and_query(parts: list[str]) -> tuple[str, str]:
    if len(parts) == 1:
        return _default_bundle_dir(), parts[0]
    first = Path(parts[0])
    if first.exists() or "/" in parts[0] or parts[0] in {".", ".."} or parts[0].startswith("~"):
        return parts[0], " ".join(parts[1:])
    return _default_bundle_dir(), " ".join(parts)


def _run_init(bundle_dir: str, *, title: str | None, emit_json: bool) -> int:
    result = init_bundle(bundle_dir, title=title)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Initialized ExpertWiki bundle at {result.root}")
        for path in result.created_files:
            print(f"created {path}")
    return 0


def _run_start(bundle_dir: str, *, title: str | None, emit_json: bool) -> int:
    result = start_experience(bundle_dir, title=title)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        if result.initialized:
            print(f"Initialized ExpertWiki at {result.root}")
        else:
            print(f"ExpertWiki: {result.root}")
        print(f"Sources: {result.source_count}")
        print(f"Approved cards: {result.page_count}")
        print(f"Suggested cards: {result.draft_count}")
        print("Next actions:")
        for action in result.next_actions:
            print(f"  - {action}")
    return 0 if result.ok else 1


def _run_add(
    bundle_dir: str,
    source: str,
    *,
    title: str | None,
    publisher: str,
    slug: str | None,
    backend: str,
    emit_json: bool,
) -> int:
    result = add_material(
        bundle_dir,
        source,
        title=title,
        publisher=publisher,
        slug=slug,
        backend=backend,
    )
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Saved source: {result.source_path}")
        print(result.message)
        for draft_path in result.draft_paths:
            print(f"Suggested card: {draft_path}")
        if result.draft_paths:
            print("Review them with: expertwiki review")
    return 0


def _run_review(bundle_dir: str, *, emit_json: bool) -> int:
    result = review_suggestions(bundle_dir)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Suggested cards: {len(result.drafts)}")
        for index, draft in enumerate(result.drafts, start=1):
            print(f"[{index}] {draft['title']}")
            if draft["description"]:
                print(f"    {draft['description']}")
            print(f"    Path: {draft['path']}")
            if draft["sources"]:
                print(f"    Sources: {', '.join(str(source) for source in draft['sources'])}")
    return 0


def _run_view(
    bundle_dir: str,
    *,
    host: str,
    port: int,
    open_browser: bool,
) -> int:
    try:
        serve_viewer(
            bundle_dir,
            host=host,
            port=port,
            open_browser=open_browser,
        )
    except OSError as exc:
        raise ValueError(f"Could not start viewer: {exc}") from exc
    return 0


def _run_analyze(
    bundle_dir: str,
    *,
    analyze_all: bool,
    backend: str,
    emit_json: bool,
) -> int:
    if backend == "host":
        host_result = prepare_agent_jobs(bundle_dir, mode="analyze", analyze_all=analyze_all)
        payload = asdict(host_result)
        if emit_json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"Queued host-AI jobs: {len(host_result.created_jobs)}")
            print(
                f"Pending: {host_result.pending}; claimed: {host_result.claimed}; "
                f"failed: {host_result.failed}"
            )
            print("Run 'expertwiki jobs next <bundle> --json' from the invoking AI workflow.")
        return 1 if host_result.failed else 0

    api_result = analyze_bundle(bundle_dir, analyze_all=analyze_all)
    payload = asdict(api_result)
    if emit_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Analyzed sources: {len(api_result.analyzed_sources)}")
        print(f"Affected concepts: {len(api_result.affected_concepts)}")
        for error in api_result.errors:
            print(f"error: {error}")
    return 1 if api_result.errors else 0


def _run_compile(
    bundle_dir: str,
    *,
    concept_refs: list[str],
    analyze_changes: bool,
    force: bool,
    allow_manual_overwrite: bool,
    backend: str,
    emit_json: bool,
) -> int:
    if backend == "host":
        if not analyze_changes:
            raise ValueError("Host backend always analyzes changed sources before compilation.")
        host_result = prepare_agent_jobs(
            bundle_dir,
            mode="compile",
            concept_refs=concept_refs,
            force=force,
            allow_manual_overwrite=allow_manual_overwrite,
        )
        payload = asdict(host_result)
        if emit_json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"Queued host-AI jobs: {len(host_result.created_jobs)}")
            print(
                f"Pending: {host_result.pending}; claimed: {host_result.claimed}; "
                f"failed: {host_result.failed}"
            )
            if host_result.blocked_reason:
                print(f"Waiting: {host_result.blocked_reason}")
            print("Run 'expertwiki jobs next <bundle> --json' from the invoking AI workflow.")
        return 1 if host_result.failed else 0

    api_result = compile_bundle(
        bundle_dir,
        concept_refs=concept_refs,
        analyze_changes=analyze_changes,
        force=force,
        allow_manual_overwrite=allow_manual_overwrite,
    )
    payload = asdict(api_result)
    if emit_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Compile run: {api_result.run_id}")
        print(f"Analyzed sources: {len(api_result.analyzed_sources)}")
        print(f"Created drafts: {len(api_result.draft_paths)}")
        for path in api_result.draft_paths:
            print(f"draft {path}")
        for item in api_result.skipped:
            print(f"skipped {item['concept']}: {item['reason']}")
        for error in api_result.errors:
            print(f"error: {error}")
    return 1 if api_result.errors else 0


def _run_jobs(args: argparse.Namespace) -> int:
    if args.jobs_command == "next":
        next_job = next_agent_job(args.bundle_dir)
        next_payload = {
            "job": public_agent_job(next_job) if next_job is not None else None
        }
        if args.json:
            print(json.dumps(next_payload, indent=2, sort_keys=True))
        elif next_job is None:
            print("No pending host-AI jobs.")
        else:
            print(f"Claimed {next_job.kind} job: {next_job.id}")
            print(json.dumps(next_job.payload, indent=2, sort_keys=True))
        return 0
    if args.jobs_command == "submit":
        result_payload = _read_result_json(args.result)
        submit_result = submit_agent_job(
            args.bundle_dir,
            args.job_id,
            result_payload,
            generator=args.generator,
        )
        output = asdict(submit_result)
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print(f"Completed {submit_result.kind} job: {submit_result.job_id}")
            if submit_result.output_path:
                print(f"Suggested card: {submit_result.output_path}")
            if submit_result.affected_concepts:
                print(f"Affected concepts: {', '.join(submit_result.affected_concepts)}")
        return 0
    if args.jobs_command == "fail":
        failed_job = fail_agent_job(args.bundle_dir, args.job_id, args.error)
        failed_payload = public_agent_job(failed_job)
        if args.json:
            print(json.dumps(failed_payload, indent=2, sort_keys=True))
        else:
            print(f"Failed job: {failed_job.id}")
            print(f"Reason: {failed_job.error}")
        return 0
    if args.jobs_command == "retry":
        retried_job = retry_agent_job(args.bundle_dir, args.job_id)
        retried_payload = public_agent_job(retried_job)
        if args.json:
            print(json.dumps(retried_payload, indent=2, sort_keys=True))
        else:
            print(f"Queued retry: {retried_job.id}")
        return 0
    if args.jobs_command == "status":
        status_payload = agent_job_status(args.bundle_dir)
        if args.json:
            print(json.dumps(status_payload, indent=2, sort_keys=True))
        else:
            counts = status_payload["counts"]
            print(
                "Host-AI jobs: "
                + ", ".join(f"{key}={value}" for key, value in counts.items())
            )
            for status_job in status_payload["jobs"]:
                target = status_job["source_path"] or status_job["concept_id"]
                print(
                    f"- {status_job['status']} {status_job['kind']} "
                    f"{status_job['id']} ({target})"
                )
        return 0
    raise ValueError(f"Unknown jobs command: {args.jobs_command}")


def _read_result_json(path: str) -> dict[str, object]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Result file is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Result JSON must be an object.")
    return payload


def _run_approve(bundle_dir: str, draft_ref: str, *, force: bool, emit_json: bool) -> int:
    result = approve_suggestion(bundle_dir, draft_ref, force=force)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Approved: {result.title}")
        print(f"Saved to: {result.page_path}")
    return 0


def _run_reject(bundle_dir: str, draft_ref: str, *, feedback: str, emit_json: bool) -> int:
    result = reject_suggestion(bundle_dir, draft_ref, feedback=feedback)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print(f"Rejected: {result.title}")
        print(f"Saved feedback to: {result.rejected_path}")
    return 0


def _run_ask(
    bundle_dir: str,
    question: str,
    *,
    limit: int,
    backend: str,
    emit_json: bool,
) -> int:
    result = ask_wiki(bundle_dir, question, limit=limit, backend=backend)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        print("Answer")
        print(result.answer)
        if result.used_pages:
            print()
            print("Used cards")
            for page in result.used_pages:
                print(f"- {page['id']}: {page['title']}")
    return 0


def _run_doctor(bundle_dir: str, *, emit_json: bool) -> int:
    result = doctor_experience(bundle_dir)
    if emit_json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    else:
        status = "OK" if result.ok else "NEEDS ATTENTION"
        print(f"ExpertWiki doctor {status}")
        print(f"Sources: {result.source_count}")
        print(f"Approved cards: {result.page_count}")
        print(f"Suggested cards: {result.draft_count}")
        for issue in result.issues:
            print(f"- {issue}")
        if result.next_actions:
            print("Next actions:")
            for action in result.next_actions:
                print(f"  - {action}")
    return 0 if result.ok else 1


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
    entity_type: str,
    emit_json: bool,
) -> int:
    result = create_page(
        bundle_dir,
        page_path,
        title=title,
        description=description,
        sources=sources,
        tags=tags,
        entity_type=entity_type,
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
        payload = dict(result.__dict__)
        payload["compiler"] = compiler_stats(bundle_dir, initialize=False)
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        status = "OK" if result.ok else "NEEDS ATTENTION"
        print(f"ExpertWiki status {status}")
        print("Concepts:")
        for concept_type, count in sorted(result.concept_counts.items()):
            print(f"  {concept_type}: {count}")
        compiler = compiler_stats(bundle_dir, initialize=False)
        print("Compiler:")
        for key, value in sorted(compiler.items()):
            print(f"  {key}: {value}")
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


def _run_publish(
    bundle_dir: str,
    *,
    endpoint: str | None,
    token: str | None,
    dry_run: bool,
    emit_json: bool,
) -> int:
    if not endpoint:
        raise ValueError("Missing publish endpoint. Use --endpoint or EXPERTWIKI_PUBLISH_ENDPOINT.")
    if not token and not dry_run:
        raise ValueError("Missing publish token. Use --token or EXPERTWIKI_PUBLISH_TOKEN.")

    result = publish_bundle(
        bundle_dir,
        endpoint=endpoint,
        token=token or "",
        dry_run=dry_run,
    )
    payload = {
        "endpoint": result.endpoint,
        "bundle_title": result.bundle_title,
        "page_count": result.page_count,
        "status_code": result.status_code,
        "response": result.response,
        "dry_run": result.dry_run,
    }
    if emit_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif dry_run:
        print(f"Publish dry-run OK: {result.page_count} page(s) ready for {result.endpoint}")
    else:
        print(f"Published {result.page_count} page(s) to {result.endpoint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
