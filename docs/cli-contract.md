# CLI Contract

ExpertWiki CLI commands are designed for human users and coding agents such as
Codex. The CLI is local-first: it reads and writes local OKF bundles and does
not implement marketplace backend enforcement.

## Exit Codes

- `0`: success.
- `1`: validation or preflight failed.
- `2`: invalid CLI usage.
- `3`: reserved for unsafe operations blocked by policy.

## Command Safety Matrix

| Command | Writes files | Human approval required | Codex default behavior |
|---|---:|---:|---|
| `status` | no | no | Run first to understand bundle state. |
| `lint` | no | no | Run after write operations. |
| `list` | no | no | Use to find claims, sources, reviews, or audits. |
| `show` | no | no | Use before editing or verifying a concept. |
| `query` | appends `log.md` | no | Use for local verified-claim lookup. |
| `init` | yes | no | Safe when the target directory is new or empty. |
| `ingest` | yes | usually no | Safe when the user asks to add source material. |
| `compile` | yes | no | Creates draft claims only; never treats them as verified. |
| `index` | yes | no | Rebuilds derived `index.md` files. |
| `audit` | yes | no | Writes a local audit report. |
| `verify` | yes | yes | Use only after explicit human approval. |
| `mark` | yes | usually yes | Use after user reports stale, disputed, or rejected knowledge. |
| `package --dry-run` | no | no | Run before any publish or registry operation. |

## Stable JSON Usage

Prefer `--json` when another tool or agent will parse output:

```bash
PYTHONPATH=src python3 -m expertwiki.cli status <bundle> --json
PYTHONPATH=src python3 -m expertwiki.cli lint <bundle> --json
PYTHONPATH=src python3 -m expertwiki.cli list <bundle> claims --status draft --json
PYTHONPATH=src python3 -m expertwiki.cli package <bundle> --dry-run --json
```

JSON schemas are not frozen yet, but every JSON output should include enough
fields for an agent to determine success, paths, issues, and next actions.

## Lifecycle Rules

Claims should move through this lifecycle:

```text
draft -> reviewed -> verified
draft -> rejected
verified -> stale
verified -> disputed
stale/disputed -> verified after review
```

Rules:

- `compile` creates `draft` claims only.
- `verify` may set `reviewed` or `verified`.
- `verified` claims require reviewer metadata, confidence, and `verified_at`.
- `query` returns verified claims by default.
- `stale`, `disputed`, and `rejected` claims stay in the bundle but should not
  be treated as default trusted answers.

## Repository Boundary

This repository may include registry clients and publish-preflight tooling in
the future. It must not include:

- marketplace backend services,
- paid/private remote query enforcement,
- reward settlement,
- anti-abuse scoring,
- client-side DRM for paid knowledge.
