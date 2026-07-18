---
type: wiki_page
entity_type: project
title: File Search
description: Retrieval tool context for finding relevant material at agent query time.
tags: [project, retrieval, agents, api]
sources: [/raw/sources/openai-file-search-docs.md]
status: published
quality: reviewed
license: unknown
source_updated_at: 2026-07-04
last_reviewed_at: 2026-07-18
updated_at: 2026-07-18
domain: Agent retrieval infrastructure
canonical_url: https://developers.openai.com/api/docs/guides/tools-file-search
---

# File Search

## Summary

File Search is a retrieval reference for finding relevant material at query
time. It is adjacent to ExpertWiki: retrieval can locate evidence, while
ExpertWiki preserves expert identity, viewpoint, quality, freshness, and
citations as durable knowledge cards.

## Representative Viewpoints

- Retrieval and curated knowledge cards are complementary layers.
- An agent should be able to inspect the source record behind a result.

## Risks And Open Questions

- Which retrieved material is strong enough to become a reviewed viewpoint?
- How should a hosted context service expose both retrieval and provenance?

## Sources

- [File Search](../../../raw/sources/openai-file-search-docs.md)
