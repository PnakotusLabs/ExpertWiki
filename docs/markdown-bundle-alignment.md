# Markdown Bundle Alignment

## Baseline

ExpertWiki follows the LLM Wiki idea:

https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

The durable artifact is a local Markdown bundle:

- a directory tree of Markdown files,
- YAML frontmatter on source records and wiki pages,
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

Wiki pages are the primary unit. A page can represent a topic, entity,
comparison, or synthesis.

Recommended page frontmatter:

```yaml
type: wiki_page
title: OAuth
description: Notes about OAuth token handling.
tags: [oauth, auth]
sources:
  - /raw/sources/oauth.md
updated_at: 2026-07-04
```

## Source Contract

Raw source records preserve source metadata and extracted notes.

```yaml
type: raw_source
title: OAuth Notes
resource: /absolute/path/or/url
publisher: Me
retrieved_at: 2026-07-04
```
