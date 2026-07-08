# ExpertWiki MVP

## Decision

Build a local-first authoring CLI and local wiki runtime for creating,
maintaining, querying, auditing, and packaging LLM Wiki bundles.

## Target Users

- Agent developers.
- Teams building internal agents.
- Researchers and analysts maintaining research notes.
- Advanced AI users organizing durable local knowledge.

## Product Promise

Users and their agents can turn source material into an interlinked Markdown
wiki that remains readable, portable, and useful across sessions.

## MVP Features

1. Initialize a local LLM Wiki.
2. Ingest local files and URLs as raw source records.
3. Create wiki pages under `wiki/`.
4. Search wiki pages locally.
5. List and show pages, sources, and audits.
6. Rebuild directory indexes.
7. Lint required files, frontmatter, source references, and Markdown links.
8. Write local audit reports.
9. Run package preflight checks.
10. Serve local search and page lookup over HTTP.

## Success Criteria

- A user can create a wiki from source material in one local workflow.
- A coding agent can inspect `AGENTS.md`, run CLI commands, and maintain pages.
- Search returns useful wiki pages with source metadata.
- Lint catches broken structure and broken links.
