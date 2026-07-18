---
type: wiki_page
entity_type: comparison
title: Knowledge Cards And Retrieval
description: Comparison between durable expert knowledge cards and query-time retrieval.
tags: [comparison, knowledge-cards, retrieval, agents]
sources: [/raw/sources/karpathy-llm-wiki-2026-04-04.md, /raw/sources/openai-file-search-docs.md]
status: published
quality: reviewed
license: unknown
source_updated_at: 2026-07-04
last_reviewed_at: 2026-07-18
updated_at: 2026-07-18
---

# Knowledge Cards And Retrieval

## Summary

Retrieval helps an agent find relevant material at query time. Knowledge cards
add a durable layer for expert identity, project context, viewpoints, quality,
freshness, and citation paths.

## Key Points

- Retrieval is strong at locating source material.
- Knowledge cards are strong at preserving reviewed synthesis and relationships.
- A Context7-like service can combine both: retrieve versioned cards and expose
  the evidence behind them.

## Related Pages

- [Agent Knowledge Bundles](../topics/agent-knowledge-bundles.md)
- [Context As Infrastructure](../viewpoints/context-as-infrastructure.md)
- [File Search](../entities/projects/openai-file-search.md)

## Open Questions

- Which retrieval results should become durable cards?
- What citation format is stable across local, MCP, and hosted delivery?

## Sources

- [Karpathy Local Knowledge Wiki Gist](../../raw/sources/karpathy-llm-wiki-2026-04-04.md)
- [File Search](../../raw/sources/openai-file-search-docs.md)
