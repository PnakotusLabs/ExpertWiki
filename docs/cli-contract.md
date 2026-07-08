# CLI Contract

ExpertWiki CLI commands are designed for human users and coding agents. The CLI
reads and writes local LLM Wiki bundles.

## Exit Codes

- `0`: success.
- `1`: validation or preflight failed.
- `2`: invalid CLI usage.

## Command Safety Matrix

| Command | Writes files | Default agent use |
|---|---:|---|
| `status` | no | Run first to understand wiki state. |
| `lint` | no | Run after write operations. |
| `list` | no | Find pages, sources, or audits. |
| `show` | no | Inspect one page, source, or audit. |
| `query` | appends `log.md` | Search local wiki pages. |
| `init` | yes | Create a wiki in a new or empty directory. |
| `ingest` | yes | Add source material under `raw/sources/`. |
| `page create` | yes | Create a Markdown page under `wiki/`. |
| `index` | yes | Rebuild derived `index.md` files. |
| `audit` | yes | Write a local audit report. |
| `package --dry-run` | no | Run preflight checks. |

## Stable JSON Usage

Prefer `--json` when another tool or agent will parse output:

```bash
PYTHONPATH=src python3 -m expertwiki.cli status <wiki> --json
PYTHONPATH=src python3 -m expertwiki.cli lint <wiki> --json
PYTHONPATH=src python3 -m expertwiki.cli list <wiki> pages --json
PYTHONPATH=src python3 -m expertwiki.cli package <wiki> --dry-run --json
```

JSON schemas are early, but every JSON output includes enough fields for an
agent to determine paths, counts, issues, and next actions.
