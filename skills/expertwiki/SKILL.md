---
name: expertwiki
description: Build and query local ExpertWiki knowledge bundles from human-authored files. Use when the user asks to turn notes, reviews, diffs, incident reports, test results, project documentation, or other local material into source-backed expert/project/topic knowledge cards, or asks to search an existing ExpertWiki bundle. Process one file at a time, apply the admission gate, preserve accepted local sources, and never ingest URLs or treat unconfirmed AI output as knowledge.
---

# ExpertWiki

Use the ExpertWiki CLI as a local authoring and query tool. The bundle is the
source of truth. The model may use its own tokens to interpret and write cards,
but the CLI itself does not call a model or fetch remote content.

## CLI Resolution

Prefer the installed command:

```bash
expertwiki status <bundle> --json
```

When working from this repository without an installed command, run:

```bash
PYTHONPATH=src python3 -m expertwiki.cli <command> ...
```

Use only local files with `ingest`. URL sources are intentionally unsupported.
Do not add a URL ingestion workaround or fetch remote content.

## Workflow Decision

### Create or update knowledge

1. Identify the bundle. If the target is already an ExpertWiki bundle, verify
   it with `expertwiki status <bundle> --json`. Otherwise initialize or reuse
   the user's default bundle at `~/.expertwiki`, not a repo-local `./expertwiki`
   tied to the current working directory:

   ```bash
   expertwiki init ~/.expertwiki --title "<title>"
   ```

   If `~/.expertwiki` already exists, run `expertwiki status ~/.expertwiki --json`
   and update it instead of reinitializing it. Never initialize a non-empty
   directory and never overwrite the user's input folder. Bundle output lives
   under `<bundle>/wiki/`; raw accepted sources live under
   `<bundle>/raw/sources/`.

2. Enumerate candidate files and process them one at a time. Do not bulk-ingest
   a directory. Skip binary files, generated build output, caches, and obvious
   duplicates. Preserve the relative input path in the source notes or page
   metadata when it helps provenance.

3. Apply the admission gate in [references/admission-gate.md](references/admission-gate.md)
   before creating a source record or page. A file must contain at least one
   admissible human-confirmed judgment, feedback item, human edit with reason,
   observed result, decision rationale, failure/counterexample, or usable
   context. For mixed files, gate each relevant passage or event separately;
   do not promote the whole file because one paragraph qualifies. If origin is
   unknown or the material is AI-only, reject it and report the path and reason.
   Do not convert rejected material merely because it is long, polished, or
   technically interesting.

4. For an admitted local file, preserve it first:

   ```bash
   expertwiki ingest <bundle> <local-file> --publisher "<publisher>" --slug <slug>
   ```

5. Create or update the smallest useful set of cards. Use the CLI to scaffold a
   card, then write the evidence-backed content into the Markdown file:

   ```bash
   expertwiki page create <bundle> wiki/<type>/<slug>.md \
     --title "<title>" --entity-type <expert|project|viewpoint|topic|comparison|synthesis> \
     --source <source-slug>
   ```

   Do not create a card for every file. Merge closely related evidence only
   when the page can retain clear source links and context.

6. Write each admitted card with these sections, adapting the page type as
   needed:

   - `Context`: project, stack, task, role, constraints, and time/version.
   - `Facts`: what happened and the evidence for it.
   - `Human Feedback`: what a person accepted, rejected, questioned, or changed.
   - `Experience Rules`: what worked or failed and under which conditions.
   - `Counterexamples and Risks`: when not to apply the rule.
   - `Confidence`: `single_case`, `multiple_confirmed`, `verified`, `stale`, or
     `disputed`, with a short justification.
   - `Sources`: links to the preserved raw source records.

   Keep `quality` as the lifecycle state (`unreviewed`, `reviewed`, `verified`,
   `stale`, `disputed`, or `rejected`) and use `confidence` for evidentiary
   strength. Never upgrade quality or confidence without evidence.

7. Rebuild indexes and validate after writes:

   ```bash
   expertwiki index <bundle>
   expertwiki lint <bundle>
   expertwiki audit <bundle>
   expertwiki package <bundle> --dry-run
   ```

   Report admitted files, rejected files with reasons, pages created or
   updated, source links, confidence states, and validation results.

### Query knowledge

1. Confirm the bundle and query only the synthesized `wiki` layer:

   ```bash
   expertwiki query <bundle> "<question or topic>" --json
   ```

2. Inspect relevant pages with `expertwiki show` when the result needs detail.
   Return the answer with page paths, source paths, facts, human feedback,
   confidence, and known risks. Do not silently search `raw/sources` or invent
   a conclusion when no page supports the answer.

3. If no result is found, say that the current ExpertWiki knowledge layer has
   no matching evidence. Do not promote an unreviewed raw source into an answer
   without passing the admission gate and writing a card first.

## Non-Negotiable Boundaries

- Do not fetch, ingest, or resolve URLs through the CLI.
- Do not treat an AI-generated summary as knowledge without identifiable human
  confirmation, a human edit, or an observed result.
- Do not extract context-free prompt tricks, chat filler, emotions, templates,
  duplicate content, automatic logs, unsupported assertions, or success-only
  stories without their basis and outcome.
- Do not claim that a page is verified when it is based on one unconfirmed case.
- Do not delete raw accepted sources when revising a card.
- Do not answer from a card whose evidence is stale or disputed without saying so.
