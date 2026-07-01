# ExpertWiki Agent Instructions

ExpertWiki is a local-first authoring CLI and local wiki runtime for OKF-style
LLM Wiki bundles. Treat this repository as user-owned local tooling, not as a
marketplace backend.

## Core Rules

1. Never upload, publish, or share user knowledge automatically.
2. Never mark a claim as `verified` unless the user explicitly approves the
   verification or gives clear reviewer identity and review intent.
3. Use `compile` only to create draft claims. Draft claims are not trusted
   knowledge.
4. Query results should rely on `status=verified` claims by default.
5. Use `mark` to move claims to `stale`, `disputed`, or `rejected` when the user
   reports problems.
6. Run `lint` after write operations.
7. Run `audit` before packaging or sharing a bundle.
8. Run `package --dry-run` before any future publish or registry operation.
9. Do not add marketplace backend, paid/private enforcement, reward settlement,
   or anti-abuse logic to this repository.
10. Keep project files in English.

## Preferred Agent Workflow

Before changing a bundle:

```bash
PYTHONPATH=src python3 -m expertwiki.cli status <bundle> --json
```

Create a local bundle:

```bash
PYTHONPATH=src python3 -m expertwiki.cli init <bundle> --title "<title>"
```

Add source material:

```bash
PYTHONPATH=src python3 -m expertwiki.cli ingest <bundle> <file-or-url> --publisher "<publisher>"
```

Create a draft claim:

```bash
PYTHONPATH=src python3 -m expertwiki.cli compile <bundle> <source-ref> --claim "<one source-backed claim>"
```

Review drafts:

```bash
PYTHONPATH=src python3 -m expertwiki.cli list <bundle> claims --status draft
PYTHONPATH=src python3 -m expertwiki.cli show <bundle> <claim-ref> --kind claims
```

Verify only after explicit human approval:

```bash
PYTHONPATH=src python3 -m expertwiki.cli verify <bundle> <claim-ref> --reviewer "<reviewer>" --method source_audit --confidence high
```

Validate:

```bash
PYTHONPATH=src python3 -m expertwiki.cli lint <bundle>
PYTHONPATH=src python3 -m expertwiki.cli audit <bundle>
PYTHONPATH=src python3 -m expertwiki.cli package <bundle> --dry-run
```

## Command Safety

- Safe read-only commands: `status`, `list`, `show`, `query`, `lint`,
  `package --dry-run`.
- Safe local write commands when requested: `init`, `ingest`, `compile`,
  `index`, `audit`.
- Human approval required: `verify`, `mark --status rejected`,
  `mark --status disputed`, `mark --status stale` when the user did not already
  report the lifecycle change.

## Failure Handling

If a command fails:

1. Do not guess silently.
2. Run `status --json` and `lint --json` when the bundle exists.
3. Explain the failing command and the exact validation issue.
4. Prefer fixing bundle structure with local authoring commands instead of
   manual file edits.
