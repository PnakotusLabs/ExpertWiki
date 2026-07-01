# Architecture

## Core Pipeline

```text
raw sources
  -> extraction
  -> claim drafting
  -> source audit
  -> expert review
  -> OKF bundle
  -> access policy
  -> local API, remote API, and MCP tools
  -> agent clients
```

## Objects

### OKF Bundle

The source of truth is a directory of markdown concept files with YAML
frontmatter. The API indexes this bundle at startup. There is no legacy JSONL
compatibility path.

Bundles are the author's durable artifact. Marketplace consumers do not
automatically receive the full bundle. Access policy decides whether a consumer
can download the bundle, query it remotely, or only view previews.

Reserved filenames:

- `index.md`: progressive disclosure for a directory.
- `log.md`: chronological change history.

### Source Concept

An immutable reference used to support claims.

Required fields:

- `id`
- `title`
- `url`
- `publisher`
- `published_at`
- `retrieved_at`
- `type`

### Verified Claim Concept

The smallest unit an agent should rely on.

Required fields:

- `id`
- `text`
- `topic`
- `entities`
- `status`
- `confidence`
- `sources`
- `reviewers`
- `last_verified_at`

Allowed statuses:

- `draft`
- `reviewed`
- `verified`
- `disputed`
- `stale`
- `rejected`

### Access Policy

Published knowledge products must declare one access mode:

- `open`: full bundle download is allowed.
- `gated`: previews are public, full access requires permission or purchase.
- `remote_only`: remote query is allowed, full bundle download is denied.
- `enterprise_private`: access stays inside an organization deployment.

Remote-only responses may include answer text, selected cited claims,
confidence, freshness, and limited source metadata. They must not include full
raw archives, full extraction notes, private reviewer rationale, or the complete
claim graph unless the license explicitly allows it.

## API Contract

### `GET /health`

Returns service status and loaded counts.

### `GET /search?q=<query>&status=verified&limit=10`

Returns matching claims and their provenance metadata.

### `GET /claims/<id>`

Returns one claim with sources, review status, and provenance.

For remote-only or enterprise-private bundles, this endpoint must enforce access
policy and may return a redacted claim view.

### Future Remote Marketplace API

```text
GET /marketplace/search?q=<query>
GET /marketplace/bundles/<owner>/<name>
POST /marketplace/bundles/<owner>/<name>/subscribe
POST /marketplace/bundles/<owner>/<name>/query
POST /marketplace/claims/<id>/nominate
```

### Future MCP Tools

```text
expertwiki.search
expertwiki.get_claim
expertwiki.answer_with_citations
expertwiki.report_stale_or_wrong
expertwiki.marketplace_search
expertwiki.remote_query
expertwiki.nominate_claim
```

## Design Rules

- Return claims and citations, not unsupported prose.
- Do not hide uncertainty. Use `disputed`, `stale`, and `confidence`.
- Prefer primary sources over summaries.
- Store enough provenance for agents to cite and for humans to audit.
- Keep the raw source separate from the reviewed claim.
- Treat full bundle download as a license decision, not the default marketplace
  behavior.
- Distinguish `install` for open bundles from `subscribe` and `remote_query` for
  paid, gated, or private bundles.
