---
type: wiki_page
title: LLM Wiki
description: The local wiki pattern for agent-maintained knowledge.
tags: [llm-wiki, local-first, markdown]
sources: [/raw/sources/karpathy-llm-wiki-2026-04-04.md]
updated_at: 2026-07-04
---

# LLM Wiki

## Summary

An LLM Wiki is a local, compounding Markdown knowledge base maintained by an
agent. Raw sources are preserved, synthesized pages are written under the wiki,
and navigation is maintained through links, indexes, and a change log.

## Key Points

- The primary knowledge unit is a Markdown page.
- Pages link to related pages so the wiki becomes navigable as it grows.
- Raw sources remain available under [Raw Sources](../../raw/sources/).
- The update log records how the wiki changes over time.

## Related Pages

- [Model Context Protocol](model-context-protocol.md)
- [LLM Wiki And Retrieval](../comparisons/llm-wiki-and-retrieval.md)

## Open Questions

- Which page templates should agents use for topics, entities, comparisons, and synthesis pages?
- Which lint checks best preserve link quality as the wiki grows?

## Sources

- [LLM Wiki](../../raw/sources/karpathy-llm-wiki-2026-04-04.md)
