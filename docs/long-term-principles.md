# Long-term Development Principles

## Product Direction

ExpertWiki is a local-first authoring system and access-controlled knowledge
exchange marketplace for LLM Wikis.

This open-source repository is the local authoring CLI and local wiki runtime.
It should be safe for users to fork, inspect, modify, and run offline. Users
should be able to use Codex or another agent to turn their own sources and
experience into a private wiki, use it locally, and then explicitly package
selected knowledge products for an organization or public registry.

Open bundles may be downloadable. Paid, private, or enterprise bundles should be
consumed through permissioned remote queries by default. When other users or
agents reuse that knowledge, the contributor can receive nomination, reputation,
credits, or future rewards through a registry layer outside this local authoring
repo.

## North Star

Make useful human knowledge portable for authors, verifiable for reviewers,
controlled for marketplaces, reusable by agents, and rewardable without locking
it into one model vendor, database, protocol, or UI.

For this repository specifically, the north star is narrower:

> Be the transparent, local-first authoring tool that creates, validates,
> queries, audits, and packages ExpertWiki knowledge bundles.

## Lineage

ExpertWiki should combine three layers:

1. Karpathy's LLM Wiki idea as the knowledge model:
   raw sources are preserved, LLMs compile and maintain a wiki, and the wiki
   compounds over time through ingest, query, lint, and update loops.
2. The parts of `nvk/llm-wiki` that match Karpathy's idea as workflow
   inspiration:
   local-first operation, topic isolation, immutable raw sources, compiled
   markdown wiki articles, index/log navigation, lint, librarian, audit, and
   explicit promotion of session knowledge.
3. ExpertWiki's own contribution:
   a verified knowledge exchange layer where local bundles can be reviewed,
   packaged into licensed knowledge products, queried under access control,
   nominated, and rewarded.

This repository implements the local bundle authoring layer. Marketplace,
registry, payment, anti-abuse, and reward systems are separate layers that may
consume packages produced by this repository.

## User Promise

For knowledge contributors:

> I can use my own agent to organize what I know into a private LLM Wiki, keep
> it under my control, and publish only the parts I choose.

For knowledge users:

> My agent can discover reusable knowledge from trusted bundles, cite where it
> came from, and show who reviewed it and when.

For paid knowledge consumers:

> My agent can query licensed knowledge without receiving the full raw bundle
> unless the license explicitly allows download.

For organizations:

> Internal knowledge can move from individual notes into reviewed shared
> bundles, while preserving ownership, provenance, and contribution credit.

## Core Product Loop

```text
Create
  -> local agent compiles a personal or team wiki

Verify
  -> sources, claims, privacy, licensing, and reviewer identity are checked

Package
  -> selected knowledge is prepared as open, gated, remote-only, or enterprise private

Use
  -> other agents install open bundles or query licensed bundles remotely

Nominate
  -> users mark claims, bundles, and contributors as useful

Reward
  -> reputation, credits, organization recognition, or future payouts accrue

Improve
  -> stale, disputed, or wrong knowledge is repaired and republished
```

## Development Principles

### Open-source repo boundary

This repository should contain only functionality that can be fully open,
inspectable, forkable, and runnable by end users. Its job is local authoring,
local validation, local querying, local auditing, packaging, and client-side
registry integration.

This repository should not contain the marketplace backend, paid/private remote
query implementation, reward settlement logic, anti-abuse scoring, private
registry internals, or hidden permission enforcement. Those belong in a registry
or marketplace service outside the local authoring CLI.

### Local-first

The user's local wiki is the primary working environment. No knowledge should be
uploaded automatically. Publishing must be explicit, reviewable, and reversible.

### Author-local, marketplace-controlled

Local-first applies to authors. It does not mean every marketplace consumer gets
a full copy of paid or private knowledge. Open knowledge can be installed as a
complete bundle. Paid, gated, or enterprise knowledge should default to remote
query access, controlled excerpts, and license-bound responses.

The open-source CLI may call remote registry APIs as a client, but it should not
pretend to enforce marketplace protections locally. Local code is visible and
modifiable by users, so paid/private enforcement must live server-side.

### OKF-first

The durable knowledge artifact is an OKF-compatible markdown bundle. Databases,
search indexes, vector stores, APIs, and websites are derived consumers.

### Protocol-neutral

MCP should be a first-class interface, but ExpertWiki must not depend on one
agent protocol. HTTP APIs, CLI commands, Codex/Claude skills, OpenAI tool
schemas, and future protocols should be adapters over the same bundle model.

### Vendor-neutral

Do not tie the knowledge model to one model provider, hosting platform, database,
or editor. Agents should be able to use ExpertWiki through files, CLI, HTTP, or
MCP.

### Human-verifiable

Important knowledge should be represented as source-backed claims with reviewer
metadata, confidence, freshness, and dispute state. Generated prose is useful,
but claims and citations are the unit of trust.

### Access is part of the knowledge product

Every published bundle should declare an access mode:

- `open`: full bundle download is allowed.
- `gated`: metadata and previews are public, full access requires permission.
- `remote_only`: consumers can query the bundle, but cannot download the full
  raw/wiki bundle.
- `enterprise_private`: bundle stays inside an organization-controlled registry
  or private deployment.

Preview access should expose enough metadata to evaluate usefulness without
leaking the full knowledge asset.

### Raw sources are immutable

Imported source material is preserved as evidence. Synthesis, claims, reviews,
and outputs live in separate layers.

### Raw sources are not marketplace payloads by default

Raw sources support verification, but paid consumers should not receive raw
source archives, full extraction notes, full claim graphs, or private review
rationale unless the license explicitly grants that access.

### Explicit promotion

Session notes, user feedback, private chats, and agent discoveries are not
automatically promoted into durable knowledge. They become durable only after an
explicit review and promotion step.

### No hidden fallback

If a bundle, claim, source, review, or index is invalid, fail clearly. Do not
silently fall back to stale formats or unverifiable data.

### No legacy compatibility by default

Old experimental formats should be removed unless there is a strong product
reason to keep them. Early velocity matters less than keeping the knowledge
model clean.

### Marketplace later, contribution accounting early

Do not start with cash rewards. Start with nominations, usage events,
reputation, verified contributor identity, and organization acceptance. Money
can come after abuse, licensing, attribution, and tax risks are understood.

### Usage events must be license-aware

Remote query access gives the marketplace a natural way to record which bundles
and claims helped an answer. Those events can feed nomination and rewards. Full
offline installs are appropriate for open knowledge, but they cannot be the only
usage model for paid knowledge because attribution and resale control become
weak.

## Product Boundaries

ExpertWiki should not become:

- a generic RAG wrapper,
- a hosted-only SaaS knowledge base,
- a single-agent plugin,
- a social posting platform,
- a marketplace backend inside the public authoring repo,
- a client-side DRM system for paid knowledge,
- a web scraper that republishes copyrighted content,
- a database-first schema with markdown export as an afterthought.

ExpertWiki should become:

- a local CLI and agent workflow for compiling personal/team LLM Wikis,
- an OKF-compatible bundle format with verification metadata,
- package and publish-preflight tooling for registry submission,
- a client for installing open bundles and querying licensed remote bundles,
- a protocol layer for agents to query verified knowledge,
- a contribution system for nomination, reputation, and future rewards.

The contribution, nomination, reputation, and reward systems may be supported by
client commands here, but their authoritative state and enforcement belong to a
registry service.

## Suggested Roadmap

### Phase 1: Personal ExpertWiki

- `expertwiki init`
- `expertwiki ingest`
- `expertwiki compile`
- `expertwiki verify`
- `expertwiki list`
- `expertwiki show`
- `expertwiki mark`
- `expertwiki query`
- `expertwiki lint`
- `expertwiki audit`
- OKF bundle output

Phase 1 is complete only when a single user can run the full local knowledge
lifecycle without a hosted service:

1. initialize a wiki,
2. ingest local notes, files, or URL records as sources,
3. generate draft claims from sources,
4. list and inspect pending drafts,
5. verify claims with reviewer identity, review method, confidence, and
   verification date,
6. query verified knowledge,
7. mark claims as stale, disputed, rejected, or draft again,
8. audit the bundle,
9. run privacy, license, access-policy, and source-reference preflight checks,
10. export or package the bundle locally.

### Phase 2: Organization Registry

- registry client commands in this repo
- `expertwiki publish --visibility org`
- `expertwiki publish --dry-run`
- `expertwiki package`
- privacy and license preflight checks
- organization review workflow
- open bundle install
- gated and remote-only subscription
- claim-level nomination
- usage event tracking
- contributor reputation inside the organization

### Phase 3: Public Marketplace

- public bundle registry
- verified contributor profiles
- public nomination and reputation
- dispute and stale-claim workflows
- access modes for open, gated, remote-only, and enterprise private bundles
- credits or revenue-sharing experiments

## Access Model

```text
Author local wiki
  -> full private OKF bundle
  -> source material, compiled claims, reviews, audits

Open marketplace listing
  -> metadata, preview claims, public rating, license, contributor identity
  -> full download allowed only when access.mode = open

Paid or private marketplace listing
  -> metadata, limited previews, proof of review
  -> remote query access after permission or purchase
  -> controlled answer, cited claims, confidence, and limited citation detail
  -> no full raw/wiki bundle download by default
```

Default CLI meanings:

- `expertwiki install <bundle>` downloads an open bundle.
- `expertwiki subscribe <bundle>` grants permission to query a gated or
  remote-only bundle.
- `expertwiki query --remote <bundle> "<question>"` queries licensed knowledge
  without downloading the full bundle.
- `expertwiki publish` must run privacy, license, and access-mode checks before
  upload.

`subscribe`, `query --remote`, `publish`, nomination, and reward-related commands
are clients of a registry service. They must not rely on local-only enforcement
for paid or private knowledge.

## Default Design Decision

When product or engineering choices conflict, prefer the option that keeps
knowledge:

- local-first,
- portable,
- human-verifiable,
- source-backed,
- protocol-neutral,
- easy to audit,
- easy to publish selectively,
- access-controlled when sold or private,
- and easy to reward fairly later.
