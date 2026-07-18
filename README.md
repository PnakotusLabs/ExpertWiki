# ExpertWiki

ExpertWiki is an expert encyclopedia and professional knowledge network for AI
agents.

The first wedge is global open-source AI, agent, and developer tooling. Agent
developers and AI application teams need stable, trusted, structured, and
citable professional knowledge to improve agents in law, medicine, finance,
open-source software, developer tools, and adjacent expert domains.

An ExpertWiki bundle is a source-preserving OKF knowledge package that agents
can read, edit, link, lint, query, audit, and package. Raw sources are preserved
under `raw/`; synthesized expert, project, topic, viewpoint, comparison, and
synthesis cards live under `wiki/`; navigation and change history are
maintained through `index.md`, `log.md`, and Markdown links.

The durable knowledge units are expert, project, topic, viewpoint, comparison,
and synthesis pages. They should help an agent answer:

- Who said what?
- What evidence supports it?
- Is the claim still current?
- What credentials, conflicts, and source dates should be considered?
- How can the expert or project be contacted or followed?

## Project Shape

- Expert and project knowledge pages first.
- Agent-readable Markdown and structured metadata first.
- Raw sources preserved before synthesis.
- Evidence, credentials, conflicts, freshness, and contact paths tracked on
  expert pages.
- Interlinked topic, entity, viewpoint, comparison, and synthesis pages under
  `wiki/`.
- `AGENTS.md`, `index.md`, and `log.md` as the agent operating surface.
- Local CLI and API first; JSON graph and `llms.txt` exports are available
  locally. MCP, hosted Context7-like delivery, and the ExpertContext API are
  future distribution layers.

## Market Entry

ExpertWiki should start by building one vertical expert and knowledge database:
global open-source AI, agents, and developer tools.

This wedge fits the current repository because GitHub, Hacker News,
open-source project propagation, and star-growth data can seed the first expert
profiles, project records, representative viewpoints, and diffusion histories.

The intended launch sequence is:

1. Build a vertical expert and project knowledge database.
2. Let agent developers call and cite the knowledge.
3. Use stable citations and traffic to motivate experts to claim pages.
4. Let experts add knowledge, publish deeper content, and receive AI citation,
   industry exposure, and qualified demand.
5. Sell industry topics, professional databases, knowledge APIs, brand
   placement, and targeted distribution to companies and sponsors.

## Bundle Layout

```text
~/.expertwiki/
  AGENTS.md
  index.md
  log.md

  raw/
    index.md
    sources/
      karpathy.md

  wiki/
    index.md
    topics/
      agent-context.md
    entities/
      experts/       # expert profiles and viewpoints
      projects/      # projects, tools, protocols, and datasets
    viewpoints/
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

Create a wiki in your user-level ExpertWiki directory:

```bash
expertwiki init --title "Open Source AI Experts"
expertwiki ingest ~/.expertwiki ./sources/karpathy.md \
  --publisher "GitHub" --slug karpathy
expertwiki page create ~/.expertwiki wiki/entities/experts/andrej-karpathy.md \
  --title "Andrej Karpathy" --entity-type expert --source karpathy
expertwiki lint ~/.expertwiki
expertwiki query ~/.expertwiki "notes"
```

Pass an explicit directory to create a bundle somewhere else:

```bash
expertwiki init my-wiki --title "Open Source AI Experts"
```

Run from source without installing:

```bash
PYTHONPATH=src python3 -m expertwiki.cli status bundles/expertwiki-ai-agent-engineering --json
```

## Codex Skill

The repository includes a Codex-compatible `expertwiki` skill under
`skills/expertwiki/`. The distributable package is `dist/expertwiki.skill`.
Install that package in Codex separately from the CLI installation. The skill
processes local files one at a time, applies the admission gate, preserves
accepted sources, creates evidence-backed cards, and queries only the `wiki/`
layer. It does not ingest URLs or treat unconfirmed AI output as knowledge.

Run the local reader API and exports:

```bash
PYTHONPATH=src python3 -m expertwiki.server \
  --data-dir bundles/expertwiki-ai-agent-engineering \
  --port 8765
```

Query it:

```bash
curl "http://127.0.0.1:8765/search?q=LLM%20Wiki"
curl "http://127.0.0.1:8765/pages/entities/experts/andrej-karpathy"
curl "http://127.0.0.1:8765/graph"
curl "http://127.0.0.1:8765/llms.txt"
```

## CLI

```bash
expertwiki init [wiki] --title "<title>"
expertwiki ingest <wiki> <local-file> --publisher "<publisher>" --slug <slug>
expertwiki page create <wiki> wiki/<path>/<page>.md --title "<title>" \
  --entity-type <expert|project|viewpoint|topic|comparison|synthesis> --source <source-ref>
expertwiki list <wiki> pages
expertwiki show <wiki> wiki/topics/<page>.md
expertwiki query <wiki> "<query>"
expertwiki lint <wiki>
expertwiki audit <wiki>
expertwiki package <wiki> --dry-run
```

## Repository Layout

```text
bundles/              Example ExpertWiki knowledge bundles
docs/                 Architecture, CLI, and agent workflow notes
src/expertwiki/       Dependency-free local CLI and API
tests/                Unit tests for authoring, linting, and search
```

## Status

This is an early implementation focused on the OKF file contract, CLI
ergonomics, local querying, graph/export surfaces, and agent-maintained expert
knowledge workflows. The current CLI is the authoring substrate for the broader
expert encyclopedia and professional knowledge network; it does not yet
provide remote access control, expert claiming, payout, or a hosted MCP service.
