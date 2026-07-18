# Codex Workflows

These workflows describe how Codex should use the ExpertWiki CLI when helping a
user maintain a local ExpertWiki knowledge bundle.

## Create A Local Expert Knowledge Bundle

User intent:

> Create a local expert knowledge bundle for open-source AI tooling.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli init --title "Open Source AI Experts"
PYTHONPATH=src python3 -m expertwiki.cli status ~/.expertwiki --json
PYTHONPATH=src python3 -m expertwiki.cli lint ~/.expertwiki
```

Expected behavior:

- Confirm the wiki path.
- Report next actions from `status`.

## Add A Local Source

User intent:

> Add this local review note to my open-source AI knowledge bundle.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli ingest ~/.expertwiki ./notes/mcp-review.md --publisher "Internal review" --slug mcp-review
PYTHONPATH=src python3 -m expertwiki.cli lint ~/.expertwiki
```

Expected behavior:

- Preserve the local source under `raw/sources/`.
- Rebuild indexes.
- Do not pass a URL; URL ingestion is unsupported.

## Create A Wiki Page

User intent:

> Create an expert or project page from the source.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli page create ~/.expertwiki wiki/entities/projects/model-context-protocol.md --title "Model Context Protocol" --entity-type project --source model-context-protocol
PYTHONPATH=src python3 -m expertwiki.cli show ~/.expertwiki wiki/entities/experts/example-maintainer.md
PYTHONPATH=src python3 -m expertwiki.cli lint ~/.expertwiki
```

Expected behavior:

- Create a Markdown page under `wiki/`.
- Include a source reference.
- Leave TODO sections for the user or agent to fill with credentials,
  representative viewpoints, evidence, conflicts, freshness, and contact paths
  when the card is an expert profile.

## Query The Wiki

User intent:

> Search the bundle for MCP maintainer notes.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli query ~/.expertwiki "MCP maintainer notes" --json
```

Expected behavior:

- Return matching knowledge pages.
- Include source metadata when available.
