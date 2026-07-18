# AI Agent Engineering Wiki Agent Instructions

This directory is a local ExpertWiki OKF bundle for open-source AI, agent, and
developer-tool experts and projects.

ExpertWiki provides the file contract, CLI operations, validation, and packaging
checks. It does not provide a hosted model or automatic synthesis by itself.
The user runs a local agent such as Codex or Claude Code to synthesize wiki
content from preserved raw sources.

## Product Boundary

- Treat GitHub, Hacker News, papers, talks, project docs, and expert submissions
  as upstream source systems.
- Treat `raw/sources/` as the preserved source record inside this bundle.
- Treat `wiki/` as the synthesized expert and project knowledge layer.
- Do not turn this bundle into a general note-taking inbox or generic directory.
- Do not delete or rewrite raw sources to make synthesis easier.

## Workflow

1. Read index.md and log.md before editing.
2. Preserve source material under raw/sources/.
3. Write synthesized expert, project, topic, viewpoint, comparison, and
   synthesis pages under wiki/.
4. Use Markdown links between related pages.
5. Cite raw sources from each wiki page when source material exists.
6. Run lint after write operations.
7. Run audit before packaging or sharing.

## Recommended Agent Loop

Run these commands from this bundle directory:

```bash
expertwiki status . --json
expertwiki list . sources
expertwiki list . pages
```

When source material exists, inspect the relevant files under `raw/sources/`.
Then create or update a small set of high-value wiki pages. Prefer fewer,
better pages over many shallow pages.

After edits:

```bash
expertwiki index .
expertwiki lint .
expertwiki audit .
expertwiki package . --dry-run
```

If the `expertwiki` command is not installed and you are working from an
ExpertWiki source checkout, use the repository form:

```bash
PYTHONPATH=src python3 -m expertwiki.cli status . --json
```

## Page Type Guide

Use the path to signal the page role:

- `wiki/topics/`: stable concepts, themes, methods, or problem areas.
- `wiki/entities/experts/`: expert profiles, viewpoints, credentials, conflicts,
  and contact paths.
- `wiki/entities/projects/`: projects, products, standards, datasets, and
  protocols.
- `wiki/viewpoints/`: attributable claims and professional positions.
- `wiki/comparisons/`: tradeoffs between two or more options.
- `wiki/synthesis/`: cross-source conclusions, recommendations, and higher-level
  judgments.

Examples:

```text
wiki/topics/agent-knowledge-bundles.md
wiki/entities/experts/andrej-karpathy.md
wiki/entities/projects/model-context-protocol.md
wiki/viewpoints/context-as-infrastructure.md
wiki/comparisons/knowledge-cards-and-retrieval.md
```

## Synthesis Planning

Before writing many pages, form a short page plan:

1. List the raw sources that matter.
2. Identify recurring concepts for `wiki/topics/`.
3. Identify experts for `wiki/entities/experts/` and projects for
   `wiki/entities/projects/`.
4. Identify attributable viewpoints for `wiki/viewpoints/`.
5. Identify decisions or tradeoffs for `wiki/comparisons/`.
6. Identify conclusions that require multiple sources for `wiki/synthesis/`.
7. Create only the pages that are useful now.

The plan can live in the conversation with the user. Only write it into the
bundle if the user asks for a durable planning artifact.

## Writing Rules

- Ground factual claims in listed sources.
- Preserve uncertainty. Put unresolved issues in "Open Questions".
- Do not invent sources, dates, quotations, or project capabilities.
- Do not hide broken functionality with fallback prose.
- Keep pages readable as ordinary Markdown.
- Prefer explicit links to related pages.
- Keep source references in each page's frontmatter and "Sources" section.
- Record meaningful changes in `log.md` through the CLI when possible.

## Page Creation Pattern

Create pages with the CLI so frontmatter and indexes stay consistent:

```bash
expertwiki page create . wiki/topics/example-topic.md \
  --title "Example Topic" \
  --description "Short description." \
  --source example-source
```

Then fill the generated sections from the cited source material.
