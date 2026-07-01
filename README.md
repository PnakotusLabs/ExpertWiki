# ExpertWiki

ExpertWiki is a human-verified OKF knowledge API for agents.

The first MVP targets agent developers who need current, source-audited answers
about AI engineering tools, APIs, and integration patterns. The core artifact is
an Open Knowledge Format bundle: a directory of markdown concept files with YAML
frontmatter. The API is a consumer of that bundle, not the source of truth.

## MVP Shape

- Agent-facing API first, human website later.
- OKF bundle first, database later.
- Claim-level provenance rather than page-level citations.
- Expert review, source audit, editor identity, and cross-checks as first-class
  metadata.
- MCP/API distribution so Codex, Claude Code, Cursor, and custom agents can use
  the same trusted knowledge layer.

## Long-term Direction

ExpertWiki is being developed toward a local-first knowledge exchange
marketplace for agent-maintained LLM Wikis. Users should be able to compile
their own private knowledge locally, publish selected verified bundles to an
organization or public registry, and receive nomination, reputation, or future
rewards when others reuse that knowledge. Open bundles may be installed locally;
paid, private, or enterprise bundles should default to permissioned remote
queries rather than full bundle download.

See [Long-term Development Principles](docs/long-term-principles.md).

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

## Repository Layout

```text
bundles/              OKF knowledge bundles consumed by agents and APIs
docs/                 Product, architecture, and verification policy
src/expertwiki/       Dependency-free API prototype
tests/                Unit tests for loading and search behavior
```

## Status

This is a foundation for validating the product direction against the
Karpathy/OKF vision. It is intentionally small and dependency-free until the
bundle contract, review model, and MCP surface are proven.
