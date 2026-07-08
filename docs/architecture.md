# Architecture

## Core Pipeline

```text
raw sources
  -> source records
  -> wiki pages
  -> markdown links
  -> index.md and log.md
  -> lint, query, audit, package
  -> local CLI and local API
  -> agent clients
```

## Bundle

The source of truth is a local directory of Markdown files.

```text
bundle/
  AGENTS.md
  index.md
  log.md
  raw/
    sources/
  wiki/
    topics/
    entities/
    comparisons/
    synthesis/
  audits/
```

Reserved files:

- `AGENTS.md`: operating instructions for agents.
- `index.md`: directory navigation.
- `log.md`: chronological change history.

## Raw Source

A raw source record preserves where source material came from and can include
local extracted notes.

Required fields:

- `type: raw_source`
- `title`
- `resource`
- `publisher`
- `retrieved_at`

## Wiki Page

A wiki page is the primary knowledge unit.

Required fields:

- `type: wiki_page`
- `title`

Recommended fields:

- `description`
- `tags`
- `sources`
- `updated_at`

Recommended sections:

- `Summary`
- `Key Points`
- `Related Pages`
- `Open Questions`
- `Sources`

## Local API

### `GET /health`

Returns service status and loaded counts.

### `GET /search?q=<query>&limit=10`

Returns matching wiki pages and source metadata.

### `GET /pages/<id>`

Returns one wiki page with frontmatter, body, and source records.

## Design Rules

- Preserve raw sources.
- Keep synthesized knowledge in wiki pages.
- Link related pages with normal Markdown links.
- Keep indexes readable for humans and agents.
- Use lint and audit to maintain structure as the wiki grows.
