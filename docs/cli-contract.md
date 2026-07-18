# CLI Contract: Local OKF Knowledge Bundles

ExpertWiki CLI commands are designed for human users and coding agents. The CLI
reads and writes local ExpertWiki OKF knowledge bundles. The bundle is the
source of truth; hosted retrieval, MCP, and ExpertContext API services are
future adapters.

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
| `query` | appends `log.md` | Search local expert and project knowledge. |
| `init` | yes | Create a knowledge bundle in a new or empty directory. Defaults to `~/.expertwiki`. |
| `ingest` | yes | Add one local source file under `raw/sources/`; URLs and directories are rejected. |
| `page create` | yes | Create a Markdown knowledge card under `wiki/`. |
| `index` | yes | Rebuild derived `index.md` files. |
| `audit` | yes | Write a local audit report. |
| `package --dry-run` | no | Run preflight checks. |

## Knowledge Card Fields

Pages created by the CLI declare an `entity_type` and quality lifecycle fields
so a downstream agent can distinguish an expert profile from a project or
topic, and can avoid treating unreviewed or stale material as current.

```yaml
type: wiki_page
entity_type: expert
status: draft
quality: unreviewed
license: unknown
source_updated_at: unknown
last_reviewed_at: unknown
```

## Stable JSON Usage

Prefer `--json` when another tool or agent will parse output:

```bash
PYTHONPATH=src python3 -m expertwiki.cli status <wiki> --json
PYTHONPATH=src python3 -m expertwiki.cli lint <wiki> --json
PYTHONPATH=src python3 -m expertwiki.cli list <wiki> pages --json
PYTHONPATH=src python3 -m expertwiki.cli package <wiki> --dry-run --json
```

JSON schemas are early, but every JSON output includes enough fields for an
agent to determine paths, counts, issues, and next actions. The local HTTP
reader exposes `/health`, `/search`, `/pages/{id}`, `/pages/{id}.md`, `/graph`,
and an llms.txt-compatible `/llms.txt` index.
