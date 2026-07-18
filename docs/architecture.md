# Architecture

## Core Pipeline

```text
public sources, expert submissions, project data, and adoption signals
  -> source records
  -> expert, project, topic, viewpoint, comparison, and synthesis pages
  -> markdown links and structured metadata
  -> index.md and log.md
  -> lint, query, audit, package
  -> local CLI, API, JSON graph, and llms.txt
  -> coding/business agents and future hosted knowledge APIs
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
      experts/
      projects/
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
local extracted notes. Sources may include GitHub repositories, issue threads,
release notes, Hacker News threads, papers, talks, posts, documentation, case
studies, expert submissions, or company pages.

Required fields:

- `type: raw_source`
- `title`
- `resource`
- `publisher`
- `retrieved_at`

## Wiki Page

A wiki page is the primary knowledge unit. Pages should be readable Markdown,
but their frontmatter and sections should be predictable enough for agents to
parse.

Required fields:

- `type: wiki_page`
- `title`

Recommended fields:

- `description`
- `tags`
- `sources`
- `updated_at`
- `freshness`
- `entity_type`
- `status`
- `quality`
- `license`
- `source_updated_at`
- `last_reviewed_at`

Recommended sections:

- `Context`
- `Facts`
- `Human Feedback`
- `Experience Rules`
- `Counterexamples and Risks`
- `Confidence`
- `Sources`

## Expert Page

Expert pages are entity pages for people who supply or influence professional
knowledge.

Recommended fields:

- `type: wiki_page`
- `entity_type: expert`
- `title`
- `domain`
- `credentials`
- `affiliations`
- `conflicts`
- `contact`
- `claim_status`
- `sources`
- `updated_at`

Recommended sections:

- `Summary`
- `Domains`
- `Representative Viewpoints`
- `Evidence Sources`
- `Credentials`
- `Affiliations and Conflicts`
- `Contact and Follow Paths`
- `Freshness`
- `Related Pages`

## Project Page

Project pages are entity pages for open-source projects, developer tools,
standards, products, or protocols.

Recommended fields:

- `type: wiki_page`
- `entity_type: project`
- `title`
- `repository`
- `maintainers`
- `domain`
- `adoption_signals`
- `license`
- `sources`
- `updated_at`

Recommended sections:

- `Summary`
- `Problem Area`
- `Maintainers and Experts`
- `Adoption Signals`
- `Release and Maintenance State`
- `Representative Viewpoints`
- `Risks and Open Questions`
- `Sources`

## Viewpoint Page

Viewpoint pages capture a professional claim or position that agents may need to
cite.

Recommended fields:

- `type: wiki_page`
- `entity_type: viewpoint`
- `title`
- `claim`
- `speaker`
- `domain`
- `sources`
- `updated_at`
- `freshness`

Recommended sections:

- `Claim`
- `Supporting Evidence`
- `Opposing Evidence`
- `Applicability`
- `Freshness`
- `Related Experts and Projects`
- `Sources`

## Local API

### `GET /health`

Returns service status and loaded counts.

### `GET /search?q=<query>&limit=10`

Returns matching wiki pages and source metadata.

### `GET /pages/<id>`

Returns one wiki page with frontmatter, body, and source records.

### `GET /pages/<id>.md`

Returns the original Markdown knowledge card. `/llms.txt` links to this clean
Markdown representation for agent-readable detail; the JSON endpoint remains
available for structured consumers.

### `GET /graph`

Returns page and source nodes with citation edges for graph-aware agents.

### `GET /llms.txt`

Returns a Markdown-formatted, llms.txt-compatible inventory with an H1 title,
blockquote summary, H2 resource sections, and links to the Markdown knowledge
cards. This is a local export today, not a hosted discovery standard.

Future API surfaces should prioritize agent needs:

- Search by expert, project, topic, domain, claim, or source.
- Return citations and source dates with every relevant answer.
- Preserve credentials, conflicts, freshness, and claim status where available.
- Make contact and follow paths available when a page is public and approved for
  distribution.
- Add an MCP server for safe tool-based access.
- Serve versioned vertical context packages through a Context7-like hosted
  service.
- Keep ExpertContext API concerns such as licensing, metering, payout, and
  enterprise permissions outside this local CLI.

## Design Rules

- Preserve raw sources.
- Keep synthesized knowledge in expert, project, topic, viewpoint, comparison,
  and synthesis pages.
- Link related pages with normal Markdown links.
- Keep indexes readable for humans and agents.
- Use lint and audit to maintain structure, source references, freshness, and
  claim traceability as the wiki grows.
