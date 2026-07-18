---
type: wiki_page
entity_type: project
title: Model Context Protocol
description: Protocol context for connecting AI systems to external tools and data.
tags: [project, protocol, mcp, agents]
sources: [/raw/sources/anthropic-mcp-2024-11-25.md]
status: published
quality: reviewed
license: unknown
source_updated_at: 2026-07-04
last_reviewed_at: 2026-07-18
updated_at: 2026-07-18
domain: Agent tool and data connectivity
canonical_url: https://www.anthropic.com/news/model-context-protocol
---

# Model Context Protocol

## Summary

The Model Context Protocol is a protocol-level reference for connecting AI
systems to external tools and data sources. In the ExpertWiki architecture, it
is a future delivery surface for knowledge cards rather than the source of
truth.

## Problem Area

Agents need stable, explicit interfaces for discovering and reading external
context. A protocol adapter can expose search, page, source, and graph reads
without moving authoring or review logic out of the bundle.

## Representative Viewpoints

- The cited announcement is the primary source for the protocol context in this
  page.
- ExpertWiki should add an MCP server only after the local card and citation
  contract is stable.

## Release And Maintenance State

- Source status: public announcement captured in this bundle.
- Adapter status: future ExpertWiki integration, not shipped by this repository.

## Risks And Open Questions

- Which tools should be read-only by default?
- How should source dates and quality states appear in MCP results?

## Sources

- [Introducing the Model Context Protocol](../../../raw/sources/anthropic-mcp-2024-11-25.md)
