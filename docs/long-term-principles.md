# Long-term Development Principles

## Product Direction

ExpertWiki is a local-first authoring CLI for LLM Wikis.

The repository should help users and agents turn raw sources into durable,
interlinked Markdown pages. The output should remain readable in any Markdown
viewer, reviewable in Git, and maintainable by coding agents.

## North Star

Be the transparent local tool that creates, maintains, validates, searches, and
packages LLM Wiki bundles.

## Strategic Memory

PKM and capture tools are upstream systems. They help users save notes, links,
snippets, highlights, files, and daily thoughts with low friction.

ExpertWiki should not compete primarily as another note-taking or bookmark
manager. Its durable value is the downstream compiler layer: turning raw,
captured material into a trusted, source-preserving, reviewable, interlinked
Markdown wiki.

The product strategy is:

```text
PKM / capture tools
  -> raw sources
  -> ExpertWiki synthesis, links, provenance, lint, and audit
  -> durable wiki bundle
```

This distinction matters: PKM answers "how do I save and retrieve my material?"
ExpertWiki answers "how do these materials become a maintainable knowledge
system?"

## Lineage

ExpertWiki follows the LLM Wiki idea:

https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

The implementation focuses on:

1. preserving raw sources,
2. writing Markdown wiki pages,
3. linking related pages,
4. maintaining index and log files,
5. giving agents a small local CLI.

## User Promise

For knowledge authors:

> I can ask my agent to organize my source material into a local Markdown wiki
> that I control.

For agent users:

> My agent can read the wiki, follow links, inspect sources, and update pages
> across sessions.

For teams:

> Shared knowledge can live in a portable folder that works with Git, local
> editors, and agent tools.

## Core Product Loop

```text
Create
  -> initialize a local wiki

Ingest
  -> preserve raw sources

Write
  -> create wiki pages

Link
  -> connect related pages

Validate
  -> lint structure, links, and source references

Use
  -> query pages locally

Maintain
  -> update pages and log changes
```

## Design Principles

### Page-first

The primary knowledge unit is a Markdown wiki page.

### Source-preserving

Raw source records live under `raw/sources/` and remain available for future
inspection.

### Link-rich

Pages should reference related pages with Markdown links.

### Local-first

The wiki should work as a local folder before any remote service exists.

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
5. Agent workflow documentation.
6. Example LLM Wiki bundles.
