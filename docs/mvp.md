# ExpertWiki MVP

## Decision

Build a local-first authoring CLI and local wiki runtime for creating,
validating, querying, auditing, and packaging ExpertWiki OKF bundles.

## Target Users

- Agent framework and tool developers.
- Enterprise teams building internal agents.
- Researchers and analysts evaluating agent capabilities.
- Advanced AI users who want reliable agent-readable sources.

## First Vertical

AI agent engineering knowledge:

- OpenAI, Anthropic, MCP, Vercel, Stripe, Supabase, LangChain, LlamaIndex.
- API behavior, limits, pricing-sensitive facts, SDK gotchas, integration
  patterns, security caveats, and stale documentation conflicts.

## Product Promise

Local users and their agents can create and query ExpertWiki knowledge that is:

- sourced to primary or high-credibility references,
- reviewed by an identifiable human or organization,
- represented as small claims rather than opaque generated prose,
- marked with confidence, freshness, and disputed/stale status,
- available through local CLI first, with local HTTP/MCP adapters later.

Contributors can compile private knowledge locally and publish selected bundles
with explicit access modes. Paid or private knowledge is queried remotely by
default instead of being downloaded wholesale, but that enforcement belongs to a
registry service outside this authoring repo.

## MVP Features

1. Search verified claims by keyword.
2. Fetch a claim with citations and review metadata.
3. Return answer bundles composed from claims, not unsupported generation.
4. Accept feedback that a claim is stale, wrong, or missing nuance.
5. Provide a review workflow outside the runtime API.
6. Store knowledge only as OKF markdown bundles; do not maintain legacy JSONL or
   database compatibility paths before there is a proven need.
7. Define access modes before marketplace publishing: `open`, `gated`,
   `remote_only`, and `enterprise_private`.
8. Reserve `install` for open bundles and use `subscribe` plus remote query for
   paid or private bundles.
9. Provide a deterministic local `expertwiki lint` command for OKF conformance,
   source references, indexes, links, and access policy checks.
10. Keep marketplace backend, paid/private enforcement, reward settlement, and
    anti-abuse outside this repository.
11. Provide local `init`, `index`, `query`, and `package --dry-run` commands
    before adding remote registry client commands.
12. Provide local `ingest`, `compile`, and `audit` commands that preserve raw
    sources, generate draft claims for human review, and write audit reports
    without automated fact invention.
13. Provide `verify`, `list`, `show`, and `mark` commands so a single user can
    inspect drafts, promote reviewed claims, and maintain stale/disputed/rejected
    lifecycle states locally.

## Non-goals

- General encyclopedia coverage.
- Fully automated web crawling.
- Social feed or community voting.
- Enterprise SSO and permission matrix.
- Vector search before keyword search and claim quality are validated.
- Downloading paid or private bundles to consumers by default.
- Marketplace backend or paid/private enforcement inside this open-source repo.
- Cash rewards before nomination, usage accounting, abuse controls, and
  licensing rules are understood.

## Success Criteria

- 50 verified claims in one domain.
- 20 real agent tasks evaluated with and without ExpertWiki.
- Measured improvement in answer correctness, citation quality, and time saved.
- At least 5 stale or disputed cases handled without silent fallback.
- At least one open bundle flow and one remote-only bundle flow are specified
  and tested at the contract level.
- A new user can initialize, lint, query, and package a local bundle without
  needing a hosted service.
