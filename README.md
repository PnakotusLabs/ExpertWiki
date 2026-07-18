# ExpertWiki

ExpertWiki is a local-first expert encyclopedia and professional knowledge
bundle system for AI agents.

It turns human-confirmed source material into structured, citable Markdown
knowledge cards so agents can answer with clearer provenance:

- who said what
- what evidence supports it
- when the source was updated or reviewed
- which credentials, conflicts, and context matter
- whether a claim is verified, stale, disputed, or based on a single case

The first vertical is global open-source AI, agent infrastructure, and developer
tooling. The same file contract can later support legal, medical, financial,
enterprise, and other expert domains.

## Why It Exists

Agent developers and AI application teams need stable professional knowledge
that is easier to inspect than a vector-store blob and more structured than a
folder of notes.

ExpertWiki keeps the source trail local and explicit:

```text
local files and expert/project source material
  -> preserved raw source records
  -> expert, project, topic, viewpoint, comparison, and synthesis cards
  -> local search, JSON graph, llms.txt, audit reports, and package checks
  -> coding agents, business agents, workflow apps, and future hosted APIs
```

The local CLI is the authoring substrate. MCP servers, hosted Context7-like
delivery, ExpertContext APIs, licensing, metering, payout, and expert claiming
are future distribution and business layers.

## What You Can Do Today

- Initialize an ExpertWiki bundle, defaulting to `~/.expertwiki`.
- Preserve local source files under `raw/sources/`.
- Create source-backed Markdown cards under `wiki/`.
- Model experts, projects, viewpoints, topics, comparisons, and synthesis pages.
- Query only the synthesized `wiki/` layer.
- Rebuild indexes and maintain `log.md`.
- Lint structure, frontmatter, source references, and Markdown links.
- Write audit reports and run package preflight checks.
- Serve a local reader API with search, page lookup, Markdown export, graph
  export, and `llms.txt`.
- Install a Codex Skill that knows the ExpertWiki admission gate and authoring
  workflow.

## Current Boundaries

- `ingest` accepts local files only.
- URLs are not fetched or ingested by the CLI.
- Directories are not bulk-ingested.
- The Codex Skill processes candidate files one at a time and applies an
  admission gate before preserving sources or writing cards.
- Unconfirmed AI summaries, chat filler, unsupported assertions, templates,
  automatic logs, and context-free prompt tricks are not treated as knowledge.
- Query searches generated `wiki/` pages, not raw sources.
- The project does not yet provide remote access control, expert page claiming,
  hosted MCP, billing, payout, or enterprise permissioning.

## Installation

ExpertWiki is a zero-runtime-dependency Python package.

Requirements:

- Python 3.9+
- `pytest` for running the test suite

Install from a checkout:

```bash
python3 -m pip install -e .
```

If your shell cannot find the installed command, run from source:

```bash
PYTHONPATH=src python3 -m expertwiki.cli --help
```

## Quick Start

Create the default user-level bundle:

```bash
expertwiki init --title "Open Source AI Experts"
```

That creates:

```text
~/.expertwiki/
  AGENTS.md
  index.md
  log.md
  raw/
    sources/
  wiki/
    topics/
    entities/
      experts/
      projects/
    viewpoints/
    comparisons/
    synthesis/
  audits/
```

Add a local source file. Replace `<local-file>` with a real file on disk; the
CLI does not fetch URLs.

```bash
expertwiki ingest ~/.expertwiki <local-file> \
  --publisher "GitHub" \
  --slug karpathy
```

Create a knowledge card from an admitted source:

```bash
expertwiki page create ~/.expertwiki wiki/entities/experts/andrej-karpathy.md \
  --title "Andrej Karpathy" \
  --entity-type expert \
  --source karpathy
```

Validate and query:

```bash
expertwiki lint ~/.expertwiki
expertwiki audit ~/.expertwiki
expertwiki package ~/.expertwiki --dry-run
expertwiki query ~/.expertwiki "agent knowledge bundles"
```

Create a bundle somewhere else by passing an explicit path:

```bash
expertwiki init ./my-expertwiki --title "Internal Engineering Experts"
```

## CLI Reference

```bash
expertwiki init [bundle] --title "<title>"
expertwiki status <bundle> --json
expertwiki ingest <bundle> <local-file> --publisher "<publisher>" --slug <slug>
expertwiki page create <bundle> wiki/<path>/<page>.md --title "<title>" \
  --entity-type <expert|project|viewpoint|topic|comparison|synthesis> \
  --source <source-ref>
expertwiki list <bundle> pages
expertwiki list <bundle> sources
expertwiki show <bundle> wiki/topics/<page>.md
expertwiki query <bundle> "<query>" --json
expertwiki index <bundle>
expertwiki lint <bundle>
expertwiki audit <bundle>
expertwiki package <bundle> --dry-run
```

Exit codes:

- `0`: success
- `1`: validation or preflight failure
- `2`: invalid CLI usage

## Knowledge Card Contract

Generated cards are ordinary Markdown files with YAML frontmatter:

```yaml
type: wiki_page
entity_type: expert
title: Example Expert
status: draft
quality: unreviewed
license: unknown
source_updated_at: unknown
last_reviewed_at: unknown
sources: [/raw/sources/example-source.md]
```

Recommended sections for agent-readable cards:

- `Context`
- `Facts`
- `Human Feedback`
- `Experience Rules`
- `Counterexamples and Risks`
- `Confidence`
- `Sources`

Use `quality` for lifecycle state:

- `unreviewed`
- `reviewed`
- `verified`
- `stale`
- `disputed`
- `rejected`

Use `confidence` in the body for evidentiary strength:

- `single_case`
- `multiple_confirmed`
- `verified`
- `stale`
- `disputed`

## Codex Skill

The repository ships a Codex-compatible skill:

```text
skills/expertwiki/
  SKILL.md
  references/admission-gate.md
```

The packaged skill is:

```text
dist/expertwiki.skill
```

The skill teaches Codex to:

- use `~/.expertwiki` as the default bundle
- inspect source folders one file at a time
- apply the admission gate before ingestion
- reject URLs, directories, AI-only summaries, and unsupported claims
- preserve accepted local files under `raw/sources/`
- create evidence-backed cards under `wiki/`
- query only the synthesized `wiki/` layer

Install the skill into Codex by unpacking `dist/expertwiki.skill` into
`$CODEX_HOME/skills` or by using your Codex skill installer.

## Local Reader API

Run the local HTTP reader against the example bundle:

```bash
PYTHONPATH=src python3 -m expertwiki.server \
  --data-dir bundles/expertwiki-ai-agent-engineering \
  --port 8765
```

Available endpoints:

```text
GET /health
GET /search?q=<query>&limit=10
GET /pages/<id>
GET /pages/<id>.md
GET /graph
GET /llms.txt
```

Example:

```bash
curl "http://127.0.0.1:8765/search?q=agent%20knowledge"
curl "http://127.0.0.1:8765/pages/entities/experts/andrej-karpathy"
curl "http://127.0.0.1:8765/pages/entities/experts/andrej-karpathy.md"
curl "http://127.0.0.1:8765/graph"
curl "http://127.0.0.1:8765/llms.txt"
```

## Example Bundle

The repository includes a seed vertical:

```text
bundles/expertwiki-ai-agent-engineering/
```

It contains raw source records and wiki cards for open-source AI, agent, and
developer-tool knowledge, including:

- an expert page for Andrej Karpathy
- project pages for Model Context Protocol and OpenAI File Search
- a viewpoint page for context as infrastructure
- a topic page for agent knowledge bundles
- a comparison page for knowledge cards and retrieval

Inspect it with:

```bash
PYTHONPATH=src python3 -m expertwiki.cli status bundles/expertwiki-ai-agent-engineering --json
PYTHONPATH=src python3 -m expertwiki.cli list bundles/expertwiki-ai-agent-engineering pages
PYTHONPATH=src python3 -m expertwiki.cli query bundles/expertwiki-ai-agent-engineering "MCP"
```

## Repository Layout

```text
AGENTS.md                         Agent instructions for this repository
README.md                         Project overview and usage
pyproject.toml                    Python package metadata and CLI entry point
src/expertwiki/                   CLI, authoring logic, linting, store, API
tests/                            Unit tests
docs/                             Architecture, MVP, CLI, and strategy notes
bundles/                          Example ExpertWiki bundles
skills/expertwiki/                Codex Skill source
dist/expertwiki.skill             Packaged Codex Skill
THIRD_PARTY_NOTICES.md            Third-party notices
```

## Development

Run tests:

```bash
python3 -m pytest
```

Run bundle validation:

```bash
PYTHONPATH=src python3 -m expertwiki.cli lint bundles/expertwiki-ai-agent-engineering
PYTHONPATH=src python3 -m expertwiki.cli audit bundles/expertwiki-ai-agent-engineering --json
PYTHONPATH=src python3 -m expertwiki.cli package bundles/expertwiki-ai-agent-engineering --dry-run
```

Validate the bundled skill:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/expertwiki
```

## Status

ExpertWiki is early local infrastructure. The file contract, CLI, local search,
linting, audit reports, graph export, `llms.txt`, and Codex Skill workflow are
implemented. Hosted retrieval, MCP service deployment, expert claiming,
licensing, usage metering, payout, and enterprise distribution are not yet part
of this repository.

## License

MIT. See [LICENSE](LICENSE).
