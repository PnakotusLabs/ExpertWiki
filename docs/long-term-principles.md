# Long-term Development Principles

## Product Direction

ExpertWiki is an expert encyclopedia and professional knowledge network for AI
agents.

The repository should help users and agents turn raw sources about experts,
projects, viewpoints, research, cases, and professional evidence into durable,
interlinked Markdown pages. The output should remain readable in any Markdown
viewer, reviewable in Git, maintainable by coding agents, and suitable for
future hosted knowledge APIs.

## North Star

Be the trusted knowledge layer that lets AI agents understand who said what,
what evidence supports it, whether it is still valid, and which credentials,
conflicts, and contacts matter.

## Strategic Memory

The first market wedge is global open-source AI, agent, and developer tooling.
This domain has public source material, visible experts, measurable project
adoption, frequent technical debate, and strong demand from agent developers.

ExpertWiki should not compete primarily as another note-taking app, bookmark
manager, or generic RAG chatbot. Its durable value is the expert knowledge
layer: source-preserving pages that encode people, projects, representative
claims, supporting evidence, freshness, credentials, conflicts, and contact
paths in a format agents can use.

The product strategy is:

```text
GitHub, Hacker News, papers, posts, talks, docs, cases, and expert submissions
  -> raw source records
  -> ExpertWiki expert, project, topic, viewpoint, and synthesis pages
  -> agent-readable vertical knowledge database
  -> local query, JSON graph, llms.txt, and stable citations
  -> Context7-like context delivery
  -> expert claims, ExpertContext API, licensing, and payout
```

This distinction matters: capture tools answer "how do I save and retrieve my
material?" Generic RAG answers "what text chunk matches this prompt?"
ExpertWiki answers "which expert or project is credible on this question, what
did they claim, and what evidence should an agent cite?"

## Lineage

ExpertWiki uses the LLM Wiki pattern as a local artifact foundation, not as its
primary category:

https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

The implementation focuses that pattern on professional knowledge:

1. preserving raw sources,
2. writing expert, project, topic, viewpoint, and synthesis pages,
3. linking related people, projects, claims, and evidence,
4. maintaining index and log files,
5. giving agents a small local CLI and API.

## User Promise

For agent developers:

> My agent can use stable, structured, citable expert knowledge instead of
> relying only on web search, stale training data, or unreviewed snippets.

For experts:

> I can claim my expert page, correct my profile, publish deeper knowledge, and
> gain AI citation, industry exposure, and qualified demand.

For companies and sponsors:

> I can reach professional audiences through industry topics, databases,
> knowledge APIs, brand placement, and targeted distribution.

## Core Product Loop

```text
Seed
  -> collect public sources and adoption signals for one vertical

Ingest
  -> preserve raw sources

Write
  -> create expert, project, topic, viewpoint, and synthesis pages

Link
  -> connect experts, projects, claims, evidence, and topics

Validate
  -> lint structure, links, source references, and freshness fields

Use
  -> let agents query, cite, inspect, and consume graph/export views

Distribute
  -> add MCP and versioned Context7-like delivery after the card contract is stable

Claim
  -> let experts improve and extend their pages

Monetize
  -> offer ExpertContext API, licensed vertical databases, and usage-based distribution
```

## Design Principles

### Expert-aware

Pages should preserve who made a claim, what qualifies them, and what conflicts
or affiliations may affect interpretation.

### Source-preserving

Raw source records live under `raw/sources/` and remain available for future
inspection.

### Claim-and-evidence

Professional assertions should be tied to sources, dates, and opposing evidence
when practical.

### Freshness-explicit

Pages should make update dates and source dates visible so agents can avoid
treating stale knowledge as current.

### Link-rich

Pages should reference related experts, projects, topics, comparisons, and
syntheses with Markdown links.

### Local-first

The knowledge bundle should work as a local folder before any remote service
exists.

### Agent-readable

Agents should be able to understand the bundle from `AGENTS.md`, `index.md`,
`log.md`, frontmatter, and predictable CLI output.

### Plain Markdown

The bundle should remain useful in editors, GitHub, and ordinary Markdown tools.

## Current Implementation Priorities

1. Stable bundle layout.
2. Simple CLI commands.
3. Reliable lint checks.
4. Local page search.
5. Page templates for experts, projects, viewpoints, topics, comparisons, and
   syntheses.
6. Agent workflow documentation.
7. Example open-source AI and agent-tooling knowledge bundles.
