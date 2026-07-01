# Codex Workflows

These workflows describe how Codex should use the ExpertWiki CLI when helping a
user maintain a local bundle.

## Create A Local Wiki

User intent:

> Create a new local ExpertWiki bundle for my engineering notes.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli init my-wiki --title "Engineering Notes"
PYTHONPATH=src python3 -m expertwiki.cli status my-wiki --json
PYTHONPATH=src python3 -m expertwiki.cli lint my-wiki
```

Expected behavior:

- Do not upload anything.
- Confirm the bundle path.
- Report next actions from `status`.

## Add A Source And Draft A Claim

User intent:

> Add `docs/oauth.md` to my wiki and create draft claims, but do not verify them.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli ingest my-wiki docs/oauth.md --publisher "local notes"
PYTHONPATH=src python3 -m expertwiki.cli compile my-wiki oauth --claim "<one draft claim>"
PYTHONPATH=src python3 -m expertwiki.cli list my-wiki claims --status draft
PYTHONPATH=src python3 -m expertwiki.cli lint my-wiki
```

Expected behavior:

- Create only draft claims.
- Ask the user to review drafts.
- Do not run `verify` without explicit approval.

## Verify A Claim

User intent:

> I reviewed this draft claim and approve it.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli show my-wiki <claim-ref> --kind claims
PYTHONPATH=src python3 -m expertwiki.cli verify my-wiki <claim-ref> --reviewer "<user>" --method source_audit --confidence high
PYTHONPATH=src python3 -m expertwiki.cli query my-wiki "<relevant query>"
```

Expected behavior:

- Record reviewer identity.
- Set `verified_at`.
- Confirm the claim appears in default query results.

## Mark Knowledge As Stale Or Disputed

User intent:

> This claim is out of date.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli mark my-wiki <claim-ref> --status stale --reason "<reason>"
PYTHONPATH=src python3 -m expertwiki.cli audit my-wiki
PYTHONPATH=src python3 -m expertwiki.cli query my-wiki "<query>"
```

Expected behavior:

- Keep the claim in the bundle.
- Remove it from default trusted query results.
- Record the lifecycle reason.

## Package Preflight

User intent:

> Check whether this bundle is ready to share.

Commands:

```bash
PYTHONPATH=src python3 -m expertwiki.cli lint my-wiki
PYTHONPATH=src python3 -m expertwiki.cli audit my-wiki
PYTHONPATH=src python3 -m expertwiki.cli package my-wiki --dry-run --json
```

Expected behavior:

- Do not upload.
- Report blocking issues.
- Remind the user that paid/private enforcement belongs to a registry service,
  not this local CLI.
