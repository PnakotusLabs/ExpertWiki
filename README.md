# ExpertWiki

ExpertWiki is a local-first authoring CLI for LLM Wikis.

An ExpertWiki bundle is a directory of Markdown files that an agent can read,
edit, link, lint, query, audit, and package. The durable knowledge unit is a
wiki page. Raw sources are preserved under `raw/`; synthesized pages live under
`wiki/`; navigation is maintained through `index.md`, `log.md`, and Markdown
links.

The project follows the LLM Wiki idea:
https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## Project Shape

- Local authoring CLI first.
- Markdown pages first.
- Raw sources preserved before synthesis.
- Interlinked wiki pages under `wiki/`.
- `AGENTS.md`, `index.md`, and `log.md` as the agent operating surface.
- Local API and MCP adapters after the file contract is stable.

## Bundle Layout

```text
my-wiki/
  AGENTS.md
  index.md
  log.md

  raw/
    index.md
    sources/
      notes.md

  wiki/
    index.md
    topics/
      oauth.md
    entities/
    comparisons/
    synthesis/

  audits/
    index.md
```

## Quick Start

Install the local CLI from a checkout:

```bash
python3 -m pip install -e .
```

If your shell cannot find the installed `expertwiki` script, run the same
commands as `python3 -m expertwiki.cli ...`.

Create a wiki:

```bash
expertwiki init my-wiki --title "Engineering Notes"
expertwiki ingest my-wiki ./notes.md --publisher "Me" --slug notes
expertwiki page create my-wiki wiki/topics/notes.md \
  --title "Notes" \
  --source notes
expertwiki lint my-wiki
expertwiki query my-wiki "notes"
```

Run from source without installing:

```bash
PYTHONPATH=src python3 -m expertwiki.cli status bundles/expertwiki-ai-agent-engineering --json
```

Run the local API:

```bash
PYTHONPATH=src python3 -m expertwiki.server \
  --data-dir bundles/expertwiki-ai-agent-engineering \
  --port 8765
```

Query it:

```bash
curl "http://127.0.0.1:8765/search?q=LLM%20Wiki"
curl "http://127.0.0.1:8765/pages/topics/llm-wiki"
```

## CLI

```bash
expertwiki init <wiki> --title "<title>"
expertwiki ingest <wiki> <file-or-url> --publisher "<publisher>" --slug <slug>
expertwiki page create <wiki> wiki/topics/<page>.md --title "<title>" --source <source-ref>
expertwiki list <wiki> pages
expertwiki show <wiki> wiki/topics/<page>.md
expertwiki query <wiki> "<query>"
expertwiki lint <wiki>
expertwiki audit <wiki>
expertwiki package <wiki> --dry-run
```

## Repository Layout

```text
bundles/              Example LLM Wiki bundles
docs/                 Architecture, CLI, and agent workflow notes
src/expertwiki/       Dependency-free local CLI and API
tests/                Unit tests for authoring, linting, and search
```

## Status

This is an early implementation focused on the file contract, CLI ergonomics,
and agent-maintained Markdown wiki workflow.
