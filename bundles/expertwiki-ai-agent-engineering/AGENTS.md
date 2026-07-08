# AI Agent Engineering Wiki Agent Instructions

This directory is a local LLM Wiki. Agents maintain it by preserving raw sources,
writing interlinked Markdown pages, updating indexes, and recording changes in
log.md.

## Workflow

1. Read index.md and log.md before editing.
2. Preserve source material under raw/sources/.
3. Write synthesized pages under wiki/.
4. Use Markdown links between related pages.
5. Cite raw sources from each wiki page when source material exists.
6. Run lint after write operations.
7. Run audit before packaging or sharing.
