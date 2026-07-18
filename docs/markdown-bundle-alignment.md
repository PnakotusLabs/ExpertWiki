# Markdown Bundle Alignment

## Baseline

ExpertWiki uses the Karpathy LLM Wiki gist as lineage for the local artifact
pattern, but its product category is expert and project knowledge
infrastructure, not a generic LLM Wiki builder:

https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

The durable artifact is a local Markdown bundle:

- a directory tree of Markdown files,
- YAML frontmatter on source records and knowledge pages,
- `type` fields for producer-defined page kinds,
- normal Markdown links for relationships,
- `index.md` for navigation,
- `log.md` for update history,
- source citations inside pages.

## Concept Types

ExpertWiki currently uses:

- `raw_source`
- `wiki_page`
- `audit_report`

## Page Contract

Wiki pages are the primary unit. A page can represent an expert, project,
viewpoint, topic, comparison, or synthesis.

Recommended page frontmatter:

```yaml
type: wiki_page
entity_type: expert
title: Example Maintainer
description: Expert profile for open-source AI tooling.
tags: [open-source-ai, developer-tools]
sources:
  - /raw/sources/example-maintainer.md
updated_at: 2026-07-04
    status: published
    quality: reviewed
    license: unknown
    source_updated_at: 2026-07-04
    last_reviewed_at: 2026-07-18
    freshness: current_as_of_source_dates
```

## Source Contract

Raw source records preserve source metadata and extracted notes.

```yaml
type: raw_source
title: OAuth Notes
resource: /absolute/path/to/local/file
publisher: Me
retrieved_at: 2026-07-04
```
