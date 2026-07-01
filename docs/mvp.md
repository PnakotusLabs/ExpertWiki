# ExpertWiki MVP

## Decision

Build a local-first authoring workflow plus an access-controlled verified
knowledge API for agent developers.

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

Agents can ask ExpertWiki for knowledge that is:

- sourced to primary or high-credibility references,
- reviewed by an identifiable human or organization,
- represented as small claims rather than opaque generated prose,
- marked with confidence, freshness, and disputed/stale status,
- available over HTTP and MCP-compatible tool contracts.

Contributors can compile private knowledge locally and publish selected bundles
with explicit access modes. Paid or private knowledge is queried remotely by
default instead of being downloaded wholesale.

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

## Non-goals

- General encyclopedia coverage.
- Fully automated web crawling.
- Social feed or community voting.
- Enterprise SSO and permission matrix.
- Vector search before keyword search and claim quality are validated.
- Downloading paid or private bundles to consumers by default.
- Cash rewards before nomination, usage accounting, abuse controls, and
  licensing rules are understood.

## Success Criteria

- 50 verified claims in one domain.
- 20 real agent tasks evaluated with and without ExpertWiki.
- Measured improvement in answer correctness, citation quality, and time saved.
- At least 5 stale or disputed cases handled without silent fallback.
- At least one open bundle flow and one remote-only bundle flow are specified
  and tested at the contract level.
