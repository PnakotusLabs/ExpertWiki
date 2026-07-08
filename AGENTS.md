# ExpertWiki Agent Instructions

ExpertWiki is a local-first authoring CLI for LLM Wikis. Treat this repository
as user-owned local tooling.

## Core Rules

1. Preserve raw source material under `raw/sources/`.
2. Write synthesized knowledge as Markdown pages under `wiki/`.
3. Use Markdown links between related pages.
4. Keep `index.md` files current.
5. Record meaningful changes in `log.md`.
6. Run `lint` after write operations.
7. Run `audit` before packaging or sharing a bundle.
8. Keep project files in English.

## Preferred Agent Workflow

Before changing a wiki:

```bash
PYTHONPATH=src python3 -m expertwiki.cli status <wiki> --json
```

Create a local wiki:

```bash
PYTHONPATH=src python3 -m expertwiki.cli init <wiki> --title "<title>"
```

Add source material:

```bash
PYTHONPATH=src python3 -m expertwiki.cli ingest <wiki> <file-or-url> --publisher "<publisher>" --slug <slug>
```

Create a wiki page:

```bash
PYTHONPATH=src python3 -m expertwiki.cli page create <wiki> wiki/topics/<page>.md --title "<title>" --source <source-ref>
```

Inspect wiki content:

```bash
PYTHONPATH=src python3 -m expertwiki.cli list <wiki> pages
PYTHONPATH=src python3 -m expertwiki.cli show <wiki> wiki/topics/<page>.md
PYTHONPATH=src python3 -m expertwiki.cli query <wiki> "<query>"
```

Validate:

```bash
PYTHONPATH=src python3 -m expertwiki.cli lint <wiki>
PYTHONPATH=src python3 -m expertwiki.cli audit <wiki>
PYTHONPATH=src python3 -m expertwiki.cli package <wiki> --dry-run
```

## Failure Handling

If a command fails:

1. Run `status --json` and `lint --json` when the wiki exists.
2. Explain the failing command and the exact validation issue.
3. Prefer fixing wiki structure with local authoring commands.
