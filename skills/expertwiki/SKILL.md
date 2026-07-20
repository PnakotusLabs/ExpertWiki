---
name: expertwiki
description: Build and query local ExpertWiki knowledge bundles from human-authored files. Use when the user asks to turn notes, reviews, diffs, incident reports, test results, project documentation, or other local material into a source-backed, interlinked AI second brain, or asks to search an existing ExpertWiki bundle. The invoking host AI performs extraction and synthesis itself through the ExpertWiki job protocol; no separate model API is required.
---

# ExpertWiki

Use ExpertWiki as a deterministic local compiler controlled by the AI currently
running this skill. The CLI owns source preservation, SQLite state, incremental
dependencies, validation, drafts, citations, review, and publishing. You are the
model: read each claimed job's local inputs, produce its strict JSON result, and
submit that result back to the CLI. Do not wait for the CLI to call an LLM and do
not ask the user to run the host-AI job loop for you.

The normal backend is `host`. A configured OpenAI-compatible API is an optional
unattended backend and may be used only when the user explicitly asks for
`--backend api`.

## CLI Resolution

Prefer the installed command:

```bash
expertwiki status <bundle> --json
```

When working from the ExpertWiki repository without an installed command, use:

```bash
PYTHONPATH=src python3 -m expertwiki.cli <command> ...
```

Use only local files. Never fetch, ingest, or resolve a URL through ExpertWiki.

## Create Or Update Knowledge

First identify the bundle. Verify an existing bundle with `status --json`. If no
bundle was requested, use `~/.expertwiki`; initialize it only when it does not
exist and never initialize a non-empty unrelated directory.

Process candidate files one at a time. Apply the admission gate in
[references/admission-gate.md](references/admission-gate.md) before ingestion.
Admit identifiable human judgments, decisions and rationale, feedback, edits
with reasons, observed outcomes, failures, counterexamples, or useful factual
context. Reject AI-only material, unknown-origin assertions, generated output,
caches, duplicates, and unsupported claims. Preserve each admitted file with:

```bash
expertwiki add <bundle> <local-file> --publisher "<publisher>" --slug <slug>
```

`add` preserves the source and queues the first host-AI job. After all admitted
files are added, run the following loop yourself until `job` is `null`:

```bash
expertwiki jobs next <bundle> --json
```

The returned object contains a persistent job ID and a dynamic `payload`. Never
invent a job, edit SQLite directly, or reuse output from another job.

### Analyze Source Job

For `kind: analyze_source`, read `payload.source.path` under the bundle in full.
Use one-based physical line numbers, including frontmatter lines; frontmatter is
metadata and is not evidence. Inspect `payload.existing_concepts` before naming
concepts. Follow `payload.instructions` and return exactly the object described
by `payload.output_schema`:

```json
{
  "summary": "2-3 source-grounded sentences",
  "quality": "high",
  "language": "en",
  "suggested_topics": ["topic"],
  "named_references": ["exact source name"],
  "concepts": [
    {
      "name": "Canonical Concept",
      "aliases": ["surface form present in this source"],
      "summary": "durable concept summary",
      "tags": ["tag"],
      "confidence": 0.8,
      "provenance_state": "extracted",
      "source_ranges": ["12-18"],
      "contradicted_by": []
    }
  ]
}
```

Extract three to eight durable concepts when the source supports them. Reuse a
canonical concept only when the name or alias clearly matches. Every range must
exist in the current source. Do not include Markdown fences or commentary in the
result file.

### Compile Concept Job

For `kind: compile_concept`, read every local file in `payload.sources`, not only
the changed source. This all-contributor aggregation is mandatory for the
concept-to-sources dependency contract. Use `source_ranges` as relevance hints,
inspect surrounding context, read `existing_page.path` when present, honor every
`rejection_feedback` item, and link only canonical titles listed in
`related_pages`.

Return exactly the object described by `payload.output_schema`:

```json
{
  "title": "Canonical Concept",
  "description": "concise source-grounded description",
  "tags": ["tag"],
  "entity_type": "topic",
  "body": "# Canonical Concept\n\n## Context\n\n..."
}
```

The body must begin with an H1 and should use Context, Facts, Human Feedback,
Experience Rules, Counterexamples and Risks, Confidence, Sources, and Related
Pages when supported. Append citations to factual prose in the exact form
`^[raw/sources/file.md:START-END]`. Multiple source references may share one
marker, separated by commas. Do not emit YAML frontmatter; the CLI owns it. Do
not describe evidence as human-confirmed unless a source explicitly says so.

### Submit Or Fail

Write only the JSON object to a temporary result file, then submit it with the
actual host name, such as `codex`, `claude-code`, or `cursor`:

```bash
expertwiki jobs submit <bundle> <job-id> \
  --result <result.json> --generator <host-name> --json
```

The CLI rechecks input hashes, parses the schema, validates source ranges and
citations, updates dependencies, and writes only a review draft. If validation
fails, correct the JSON and submit the same active job again. If the host cannot
complete the job, record the real reason instead of fabricating output:

```bash
expertwiki jobs fail <bundle> <job-id> --error "<reason>"
```

Retry a repaired failure explicitly with `expertwiki jobs retry <bundle>
<job-id>`. Continue `jobs next` after every successful submission. Analysis jobs
are exhausted before compile jobs are created, so newly extracted concepts and
the reverse dependency graph always exist before synthesis.

When the queue is empty, inspect candidates with `expertwiki review <bundle>`.
Show the user the smallest useful review set and explain sources, confidence,
and known risks. Never run `approve` unless the human explicitly confirms that
candidate. Approval is the only operation that promotes a generated draft into
`wiki/`:

```bash
expertwiki approve <bundle> <card>
expertwiki reject <bundle> <card> --feedback "<human feedback>"
```

After approved writes, rebuild and validate:

```bash
expertwiki index <bundle>
expertwiki lint <bundle>
expertwiki audit <bundle>
expertwiki package <bundle> --dry-run
```

Report admitted and rejected inputs, completed and failed jobs, draft or page
paths, source links, confidence states, and validation results.

## Query Knowledge

Query only approved wiki pages:

```bash
expertwiki query <bundle> "<question or topic>" --json
```

Read the relevant returned pages and answer with the capabilities of the host AI
running this skill. Cite page and source paths, distinguish facts from inference,
and state confidence and risks. Do not silently search `raw/sources` to answer a
question. If no approved page supports the answer, say the current wiki layer
has no matching evidence. `expertwiki ask --backend api` is optional and must
not be selected merely because API environment variables happen to exist.

## Non-Negotiable Boundaries

- Preserve accepted source material under `raw/sources/`; never delete it while revising a card.
- Keep generated output in `.expertwiki/drafts/` until explicit human approval.
- Never write generated Markdown directly into `wiki/` to bypass the job and review contracts.
- Never approve, raise quality, or raise confidence without human or observed evidence.
- Never overwrite an imported or manually edited published page unless the user explicitly authorizes it.
- Never answer from stale or disputed evidence without saying so.
