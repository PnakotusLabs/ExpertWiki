# ExpertWiki

ExpertWiki is a human-verified OKF knowledge API for agents.

The first MVP targets agent developers who need current, source-audited answers
about AI engineering tools, APIs, and integration patterns. The core artifact is
an Open Knowledge Format bundle: a directory of markdown concept files with YAML
frontmatter. The API is a consumer of that bundle, not the source of truth.

## MVP Shape

- Authoring CLI first, local API/MCP adapters later.
- OKF bundle first, database later.
- Claim-level provenance rather than page-level citations.
- Expert review, source audit, editor identity, and cross-checks as first-class
  metadata.
- Local bundle tooling so Codex, Claude Code, Cursor, and custom agents can help
  users create, lint, query, audit, and package their own knowledge.
- Registry and marketplace backends stay outside this open-source authoring
  repo; this repo may provide client commands and publish-preflight checks.

## Long-term Direction

ExpertWiki is being developed toward a local-first knowledge exchange
marketplace for agent-maintained LLM Wikis. Users should be able to compile
their own private knowledge locally, publish selected verified bundles to an
organization or public registry, and receive nomination, reputation, or future
rewards when others reuse that knowledge. Open bundles may be installed locally;
paid, private, or enterprise bundles should default to permissioned remote
queries rather than full bundle download.

This open-source repo is the local authoring CLI and local wiki runtime. It
should stay fully inspectable, forkable, and useful offline. Marketplace
backends, paid/private remote query enforcement, reward settlement, and anti-abuse
systems belong in a separate registry service; this repo may provide client
commands and publish-preflight tooling for that service.

See [Long-term Development Principles](docs/long-term-principles.md).

## Codex Usage

This repository is intended to be usable through Codex and other local coding
agents. Agents should read [AGENTS.md](AGENTS.md) first, then use
`expertwiki status <bundle> --json` to understand bundle state before changing
files.

Additional agent-facing references:

- [CLI Contract](docs/cli-contract.md)
- [Codex Workflows](docs/codex-workflows.md)

## Quick Start

This prototype uses only the Python standard library.

```bash
PYTHONPATH=src python3 -m expertwiki.server \
  --data-dir bundles/expertwiki-ai-agent-engineering \
  --port 8765
```

Then query it:

```bash
curl "http://127.0.0.1:8765/search?q=MCP"
curl "http://127.0.0.1:8765/claims/mcp-open-standard"
```

Check an OKF bundle:

```bash
PYTHONPATH=src python3 -m expertwiki.cli lint bundles/expertwiki-ai-agent-engineering
```

Create and manage a local bundle:

```bash
PYTHONPATH=src python3 -m expertwiki.cli init my-wiki --title "My Wiki"
PYTHONPATH=src python3 -m expertwiki.cli status my-wiki --json
PYTHONPATH=src python3 -m expertwiki.cli ingest my-wiki ./notes.md --publisher "Me"
PYTHONPATH=src python3 -m expertwiki.cli compile my-wiki notes --claim "Draft claim to review."
PYTHONPATH=src python3 -m expertwiki.cli list my-wiki claims --status draft
PYTHONPATH=src python3 -m expertwiki.cli show my-wiki notes --kind sources
PYTHONPATH=src python3 -m expertwiki.cli verify my-wiki draft-claim-to-review --reviewer "me"
PYTHONPATH=src python3 -m expertwiki.cli mark my-wiki draft-claim-to-review --status stale --reason "Needs refresh"
PYTHONPATH=src python3 -m expertwiki.cli index my-wiki
PYTHONPATH=src python3 -m expertwiki.cli query my-wiki "What do we know?"
PYTHONPATH=src python3 -m expertwiki.cli audit my-wiki
PYTHONPATH=src python3 -m expertwiki.cli package my-wiki --dry-run
```

## Repository Layout

```text
bundles/              OKF knowledge bundles consumed by agents and APIs
docs/                 Product, architecture, and verification policy
src/expertwiki/       Dependency-free API prototype
tests/                Unit tests for loading and search behavior
THIRD_PARTY_NOTICES.md Third-party license notices for adapted code and ideas
```

## Status

This is a foundation for validating the local authoring direction against the
Karpathy/OKF vision. It is intentionally small and dependency-free until the
bundle contract, review model, authoring CLI, and local adapter surface are
proven.
