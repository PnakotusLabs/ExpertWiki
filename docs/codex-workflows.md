# Codex Workflows

These workflows describe how Codex should use the ExpertWiki CLI when helping a
user maintain a local LLM Wiki.

## Create A Local Wiki

User intent:

> Create a local wiki for my engineering notes.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli init my-wiki --title "Engineering Notes"
PYTHONPATH=src python3 -m expertwiki.cli status my-wiki --json
PYTHONPATH=src python3 -m expertwiki.cli lint my-wiki
```

Expected behavior:

- Confirm the wiki path.
- Report next actions from `status`.

## Add A Source

User intent:

> Add `docs/oauth.md` to my wiki.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli ingest my-wiki docs/oauth.md --publisher "local notes" --slug oauth
PYTHONPATH=src python3 -m expertwiki.cli lint my-wiki
```

Expected behavior:

- Preserve the source under `raw/sources/`.
- Rebuild indexes.

## Create A Wiki Page

User intent:

> Create a topic page about OAuth from the source.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli page create my-wiki wiki/topics/oauth.md --title "OAuth" --source oauth
PYTHONPATH=src python3 -m expertwiki.cli show my-wiki wiki/topics/oauth.md
PYTHONPATH=src python3 -m expertwiki.cli lint my-wiki
```

Expected behavior:

- Create a Markdown page under `wiki/`.
- Include a source reference.
- Leave TODO sections for the user or agent to fill.

## Query The Wiki

User intent:

> Search the wiki for OAuth notes.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli query my-wiki "OAuth notes" --json
```

Expected behavior:

- Return matching wiki pages.
- Include source metadata when available.
