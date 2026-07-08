# Competitive Landscape: LLM Wiki Builders and Private Knowledge Capture Tools

Research date: 2026-07-09

This document consolidates the research from the current discussion about LLM wiki builders, Obsidian-oriented wiki tools, repository-to-wiki systems, and quick private knowledge capture tools. GitHub repository metadata was checked through the GitHub API on 2026-07-09 unless otherwise noted. Stars and last-push dates are volatile.

## Executive Summary

ExpertWiki sits between two active categories:

1. LLM wiki builders that turn source material into structured, interlinked Markdown or wiki pages.
2. Private capture tools that help users quickly save notes, links, snippets, highlights, and files, but usually do not synthesize them into a curated wiki.

The closest direct competitor is [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki), a fast-growing desktop LLM Wiki application with about 14k stars as of 2026-07-09. Other direct competitors cluster around Obsidian and Karpathy's LLM Wiki pattern, including [kytmanov/obsidian-llm-wiki-local](https://github.com/kytmanov/obsidian-llm-wiki-local), [Ar9av/obsidian-wiki](https://github.com/Ar9av/obsidian-wiki), [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki), and [green-dalii/obsidian-llm-wiki](https://github.com/green-dalii/obsidian-llm-wiki).

The largest adjacent demand signal comes from repository-to-wiki systems such as [AsyncFuncAI/deepwiki-open](https://github.com/AsyncFuncAI/deepwiki-open), which had about 17.2k stars, and from private capture tools such as [usememos/memos](https://github.com/usememos/memos), [Joplin](https://github.com/laurent22/joplin), [SiYuan](https://github.com/siyuan-note/siyuan), [Logseq](https://github.com/logseq/logseq), [Karakeep](https://github.com/karakeep-app/karakeep), and [Linkwarden](https://github.com/linkwarden/linkwarden).

The strategic implication is clear: ExpertWiki should not position itself as another generic note app or RAG chat system. Its strongest position is as a local-first, source-preserving, auditable wiki compiler that ingests raw material from capture tools and produces a structured, reviewable, portable wiki bundle.

## Decision Context

The decision being evaluated:

Should ExpertWiki compete mainly as a standalone LLM Wiki product, as an Obsidian/local Markdown companion, or as a downstream compiler for many capture sources?

Alternatives:

1. Standalone LLM Wiki application.
2. Obsidian-first plugin or workflow.
3. Local-first command-line and agent workflow for compiling captured material into audited wiki bundles.
4. Repository-to-wiki system focused on codebases.
5. Capture-first note or bookmark application.

Recommended strategic direction:

ExpertWiki should prioritize option 3 while staying compatible with options 2 and 4. It should integrate with capture tools rather than replace them.

## Research Scope

Included:

- Projects that compile local files, Markdown, notes, documents, repositories, or Obsidian vaults into wiki-like pages.
- Obsidian and Markdown tools that organize notes into linked knowledge structures.
- Self-hosted or local-first capture tools for notes, links, snippets, web pages, and private knowledge fragments.
- Repository-to-wiki tools where the output is structured documentation or an AI-readable wiki.

Excluded from primary analysis:

- Pure vector-search or RAG chat tools that do not create durable wiki pages.
- Generic CMS projects that are not focused on personal/local knowledge capture.
- Search engines or infrastructure projects that do not capture user knowledge directly.

## Taxonomy

### Category A: Direct LLM Wiki Builders

These projects are closest to ExpertWiki because they explicitly transform source material into a persistent wiki or structured Markdown knowledge base.

| Project | Stars | Created | Last Push | License | Fit | Source |
|---|---:|---:|---:|---|---|---|
| [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki) | 14,007 | 2026-04-08 | 2026-07-08 | NOASSERTION | Direct competitor | GitHub API, README |
| [Ar9av/obsidian-wiki](https://github.com/Ar9av/obsidian-wiki) | 2,743 | 2026-04-06 | 2026-07-07 | MIT | Direct Obsidian/agent competitor | GitHub API |
| [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki) | 1,303 | 2026-04-04 | 2026-07-08 | Apache-2.0 | Direct LLM Wiki competitor | GitHub API |
| [kytmanov/obsidian-llm-wiki-local](https://github.com/kytmanov/obsidian-llm-wiki-local) | 767 | 2026-04-07 | 2026-05-26 | MIT | Direct local Obsidian competitor | GitHub API |
| [ussumant/llm-wiki-compiler](https://github.com/ussumant/llm-wiki-compiler) | 295 | 2026-04-04 | 2026-05-05 | MIT | Direct compiler-style competitor | GitHub API |
| [green-dalii/obsidian-llm-wiki](https://github.com/green-dalii/obsidian-llm-wiki) | 254 | 2026-04-26 | 2026-07-06 | Apache-2.0 | Direct Obsidian plugin competitor | GitHub API |
| [domleca/llm-wiki](https://github.com/domleca/llm-wiki) | 169 | 2026-04-08 | 2026-06-15 | MIT | Direct Obsidian plugin competitor | GitHub API |
| [cclank/lanshu-wiki-skill](https://github.com/cclank/lanshu-wiki-skill) | 14 | 2026-05-24 | 2026-05-24 | MIT | Adjacent Claude Code skill | GitHub API |
| [mohammadmaso/echowiki](https://github.com/mohammadmaso/echowiki) | 2 | 2026-07-05 | 2026-07-05 | MIT | Early-stage direct competitor | GitHub API |

Observations:

- This category formed quickly around April 2026, shortly after Karpathy's LLM Wiki pattern circulated.
- Most projects are young, but the growth of `nashsu/llm_wiki` shows strong demand.
- Obsidian compatibility is a common route because it already supplies Markdown, local files, links, and graph UX.
- Several projects use language such as "raw" to "wiki", "concept pages", "entity pages", "auto-links", and "persistent wiki", which overlaps heavily with ExpertWiki's intended domain.

### Category B: Repository-to-Wiki and Codebase Documentation

These tools focus on code repositories rather than personal documents, but they prove demand for automatic wiki generation.

| Project | Stars | Created | Last Push | License | Fit | Source |
|---|---:|---:|---:|---|---|---|
| [AsyncFuncAI/deepwiki-open](https://github.com/AsyncFuncAI/deepwiki-open) | 17,216 | 2025-04-30 | 2026-06-03 | MIT | Strong adjacent competitor | GitHub API |
| [AIDotNet/OpenDeepWiki](https://github.com/AIDotNet/OpenDeepWiki) | 3,403 | 2025-04-27 | 2026-07-07 | MIT | Strong adjacent competitor | GitHub API |
| [sopaco/deepwiki-rs](https://github.com/sopaco/deepwiki-rs) | 1,347 | 2025-09-05 | 2026-05-16 | MIT | Adjacent repo documentation tool | GitHub API |
| [daeisbae/open-repo-wiki](https://github.com/daeisbae/open-repo-wiki) | 308 | 2024-12-14 | 2026-04-06 | Apache-2.0 | Adjacent repo wiki generator | GitHub API |
| [davialabs/davia](https://github.com/davialabs/davia) | 1,648 | 2025-11-05 | 2026-01-19 | MIT | Adjacent agent-editable docs | GitHub API |

Observations:

- The largest repository-to-wiki project in this scan, `deepwiki-open`, had more stars than every direct LLM Wiki project except the broader capture/workspace tools.
- Codebase documentation is a related but distinct use case. It values architecture diagrams, code references, and API maps more than provenance-preserving source synthesis.
- ExpertWiki can borrow patterns from this category, especially repo ingestion, structured output, diagrams, and MCP interfaces, without making codebases the core wedge.

### Category C: Obsidian, Markdown Import, and Note Quality Tools

These projects do not always generate wiki pages from arbitrary raw sources, but they sit near the workflow.

| Project | Stars | Created | Last Push | License | Fit | Source |
|---|---:|---:|---:|---|---|---|
| [obsidianmd/obsidian-importer](https://github.com/obsidianmd/obsidian-importer) | 1,524 | 2023-07-11 | 2026-05-29 | MIT | Upstream importer | GitHub API |
| [QuentinWach/obsidian.ai](https://github.com/QuentinWach/obsidian.ai) | 18 | 2024-04-17 | 2024-08-28 | NOASSERTION | Adjacent AI note organizer | GitHub API |

Observations:

- Importers matter because users often arrive with Apple Notes, Evernote, Notion, OneNote, Google Keep, or other existing systems.
- ExpertWiki should treat importers as a way to populate `raw/sources/`, not as a complete solution.

### Category D: Quick Private Capture and Self-Hosted Notes

These projects are not LLM Wiki competitors in a strict sense. They solve the upstream capture problem: get knowledge fragments into a private system quickly.

| Project | Stars | Created | Last Push | License | Fit | Source |
|---|---:|---:|---:|---|---|---|
| [usememos/memos](https://github.com/usememos/memos) | 61,417 | 2021-12-08 | 2026-07-08 | MIT | Top capture-layer reference | GitHub API, README |
| [laurent22/joplin](https://github.com/laurent22/joplin) | 55,481 | 2017-01-16 | 2026-07-07 | NOASSERTION | Mature note and web clipper source | GitHub API, README |
| [siyuan-note/siyuan](https://github.com/siyuan-note/siyuan) | 44,991 | 2020-08-30 | 2026-07-08 | AGPL-3.0 | Strong local-first PKM | GitHub API |
| [logseq/logseq](https://github.com/logseq/logseq) | 43,758 | 2020-05-23 | 2026-07-08 | AGPL-3.0 | Strong local-first outline PKM | GitHub API |
| [karakeep-app/karakeep](https://github.com/karakeep-app/karakeep) | 27,198 | 2024-02-06 | 2026-07-06 | AGPL-3.0 | Bookmark, note, image, AI tagging source | GitHub API, README |
| [linkwarden/linkwarden](https://github.com/linkwarden/linkwarden) | 18,857 | 2022-04-09 | 2026-07-07 | AGPL-3.0 | Bookmark, archive, highlight source | GitHub API, README |
| [foambubble/foam](https://github.com/foambubble/foam) | 17,276 | 2020-06-19 | 2026-06-23 | NOASSERTION | VS Code + Markdown PKM | GitHub API |
| [wallabag/wallabag](https://github.com/wallabag/wallabag) | 12,815 | 2013-04-03 | 2026-07-06 | MIT | Read-it-later and article capture | GitHub API |
| [anyproto/anytype-ts](https://github.com/anyproto/anytype-ts) | 8,372 | 2023-05-22 | 2026-07-07 | NOASSERTION | Local-first object workspace | GitHub API |
| [massCodeIO/massCode](https://github.com/massCodeIO/massCode) | 6,889 | 2022-03-29 | 2026-07-06 | AGPL-3.0 | Developer snippets and notes | GitHub API |
| [standardnotes/app](https://github.com/standardnotes/app) | 6,541 | 2016-12-05 | 2026-07-07 | AGPL-3.0 | Encrypted private notes | GitHub API |
| [silverbulletmd/silverbullet](https://github.com/silverbulletmd/silverbullet) | 5,614 | 2022-02-16 | 2026-07-01 | MIT | Markdown personal productivity platform | GitHub API |
| [shaarli/Shaarli](https://github.com/shaarli/Shaarli) | 3,881 | 2014-07-26 | 2026-06-27 | NOASSERTION | Lightweight self-hosted bookmarking | GitHub API |
| [Dullage/flatnotes](https://github.com/dullage/flatnotes) | 3,146 | 2021-08-03 | 2026-02-17 | MIT | Flat-folder Markdown note source | GitHub API |
| [dnote/dnote](https://github.com/dnote/dnote) | 3,044 | 2017-03-30 | 2026-03-26 | Apache-2.0 | CLI notebook for developers | GitHub API |
| [TriliumNext/Notes](https://github.com/TriliumNext/Notes) | 2,927 | 2024-02-14 | 2025-06-24 | AGPL-3.0 | Personal wiki/notes, but archived | GitHub API |
| [zk-org/zk](https://github.com/zk-org/zk) | 2,709 | 2020-12-23 | 2026-07-08 | GPL-3.0 | Plain-text note-taking assistant | GitHub API |
| [turtl/server](https://github.com/turtl/server) | 633 | 2017-09-19 | 2024-03-25 | AGPL-3.0 | Private notes, lower current relevance | GitHub API |

Observations:

- Memos is the clearest quick-capture reference. Its README emphasizes instant capture, Markdown portability, self-hosting, low deployment friction, and REST/gRPC APIs.
- Joplin, Logseq, SiYuan, Foam, SilverBullet, flatnotes, Dnote, and zk are useful because they either store or export Markdown-like material.
- Karakeep and Linkwarden are especially important for web research workflows because they capture URLs, pages, PDFs, screenshots, highlights, annotations, and AI-generated tags or summaries.
- Capture tools are usually strong at ingestion UX and weak at curated synthesis, provenance audit, and bundle packaging.

## Competitive Positioning

### Direct Competition

Direct competitors answer the same core job:

"Turn my raw knowledge material into a structured, linked wiki."

Projects in this group:

- [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki)
- [kytmanov/obsidian-llm-wiki-local](https://github.com/kytmanov/obsidian-llm-wiki-local)
- [Ar9av/obsidian-wiki](https://github.com/Ar9av/obsidian-wiki)
- [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki)
- [green-dalii/obsidian-llm-wiki](https://github.com/green-dalii/obsidian-llm-wiki)
- [domleca/llm-wiki](https://github.com/domleca/llm-wiki)
- [ussumant/llm-wiki-compiler](https://github.com/ussumant/llm-wiki-compiler)
- [mohammadmaso/echowiki](https://github.com/mohammadmaso/echowiki)

ExpertWiki must assume this category will become crowded. The Karpathy LLM Wiki pattern is easy to explain, easy to demo, and easy for developers to imitate.

### Adjacent Competition

Adjacent competitors answer nearby jobs:

- "Explain this repository as a wiki."
- "Make my knowledge base searchable."
- "Organize my notes."
- "Preserve my links and web pages."
- "Help me capture thoughts quickly."

These tools can become competitors if they add durable wiki synthesis, but today they are also plausible ingestion partners.

### Upstream Data Sources

The strongest upstream sources for ExpertWiki are:

1. Memos for quick Markdown memo capture.
2. Karakeep for bookmarks, notes, images, PDFs, AI tags, and summaries.
3. Linkwarden for archived pages, highlights, annotations, PDFs, and screenshots.
4. Joplin for mature notes and web clipping.
5. Logseq, Foam, SilverBullet, flatnotes, Dnote, and zk for local Markdown or plain-text note graphs.

## Feature Pattern Analysis

### What Direct LLM Wiki Projects Emphasize

- Persistent wiki output instead of ephemeral chat.
- Concept, entity, and source pages.
- Auto-linking across generated pages.
- Obsidian compatibility or Markdown compatibility.
- Local or private processing, often through Ollama or user-provided model credentials.
- Conversational query layered on top of the generated wiki.
- Incremental maintenance of the wiki as new sources arrive.

### What Capture Tools Emphasize

- Low-friction capture: timeline, share sheet, browser extension, web clipper, command line, or mobile app.
- Private ownership: self-hosted, local-first, offline-first, encrypted, or no telemetry.
- Portability: Markdown, export, API, flat files, SQLite, or open formats.
- Retrieval: full-text search, tags, collections, graph, backlinks, or filters.
- Preservation: archived HTML, PDFs, screenshots, attachments, notes, highlights, and metadata.

### What Most Projects Do Not Fully Solve

- Source-preserving compilation with explicit provenance.
- Human review loops for generated pages.
- Linting and auditing of the wiki as an artifact.
- Packaging or sharing a complete bundle with sources, generated pages, logs, and audit outputs.
- Clear separation between immutable raw sources and synthesized knowledge.
- Repeatable command-line workflows for agents.

This gap is the best strategic opening for ExpertWiki.

## Recommended ExpertWiki Positioning

Recommended positioning statement:

ExpertWiki is a local-first, source-preserving LLM wiki compiler for serious knowledge work. It ingests raw material from files, notes, bookmarks, and repositories, then produces an auditable Markdown wiki bundle with links, indexes, logs, and provenance.

Avoid positioning ExpertWiki as:

- A generic note-taking app.
- A generic self-hosted bookmark manager.
- A generic RAG chat system.
- A pure Obsidian plugin.
- A pure codebase documentation generator.

## Strategic Options

### Option 1: Standalone LLM Wiki App

Supporting evidence:

- [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki) shows strong demand for a direct "documents to wiki" product.
- Users can understand a desktop or web app faster than a CLI.

Opposing evidence:

- UI-heavy competition will be hard to match quickly.
- Desktop apps must solve onboarding, file watching, graph UX, review UX, and model configuration.

Key uncertainty:

- Whether ExpertWiki's target users value reproducible local authoring more than a graphical product.

Confidence:

- Medium.

### Option 2: Obsidian-First Workflow

Supporting evidence:

- Many direct competitors are Obsidian-oriented.
- Obsidian provides Markdown, backlinks, graph visualization, and an existing PKM audience.

Opposing evidence:

- Obsidian plugin competition can become crowded quickly.
- Tying the core product to Obsidian may weaken the broader "local wiki bundle" model.

Key uncertainty:

- Whether ExpertWiki users already use Obsidian as their primary reading and editing surface.

Confidence:

- Medium-high as an integration path, not as the whole strategy.

### Option 3: Downstream Compiler for Capture Tools

Supporting evidence:

- Memos, Joplin, Logseq, SiYuan, Karakeep, Linkwarden, and similar tools already solve capture.
- Their weak point is synthesis, audit, packaging, and durable wiki construction.
- ExpertWiki already has natural concepts for raw sources, generated wiki pages, logs, lint, audit, and package.

Opposing evidence:

- Integrations multiply maintenance work.
- Users may expect one-click importers for every source.

Key uncertainty:

- Which capture sources have the highest overlap with ExpertWiki's intended users.

Confidence:

- High.

### Option 4: Codebase-to-Wiki

Supporting evidence:

- `deepwiki-open` shows strong developer demand.
- Code repositories are local directories with structured references, which fit ExpertWiki's CLI orientation.

Opposing evidence:

- Repository documentation is already a competitive category.
- Codebase docs require code-aware parsing, call graphs, dependency analysis, and language-specific UX.

Key uncertainty:

- Whether codebase wiki generation should be a core use case or a later vertical.

Confidence:

- Medium.

## Recommended Product Moves

### 1. Build Capture-Source Ingestion Connectors

Suggested priority:

1. Markdown folder ingestion for flatnotes, Logseq, Foam, SilverBullet, zk, and generic directories.
2. Memos ingestion through API or export.
3. Joplin Markdown or JEX export ingestion.
4. Linkwarden ingestion for URLs, archived pages, annotations, screenshots, and PDFs.
5. Karakeep ingestion for bookmarks, notes, images, PDFs, AI tags, and summaries.

Reasoning:

Markdown folder ingestion is the lowest-risk foundation. Memos, Joplin, Linkwarden, and Karakeep then cover the most important non-folder capture flows.

### 2. Make Provenance a First-Class Feature

Every generated page should preserve:

- Source references.
- Ingest timestamp.
- Source path or URL.
- Publisher or origin system.
- Generation command.
- Model and prompt metadata where practical.
- Change log entry.
- Review status.

This is the cleanest way to separate ExpertWiki from note apps and lightweight LLM Wiki demos.

### 3. Add a Review Loop

The product should support a workflow like:

1. Ingest sources into `raw/sources/`.
2. Generate proposed wiki changes.
3. Show changed pages and source references.
4. Approve, edit, or reject changes.
5. Record meaningful changes in `log.md`.
6. Run lint and audit.

This review loop is more valuable than another chat interface because it turns LLM output into maintainable knowledge.

### 4. Keep Output Tool-Agnostic

ExpertWiki should generate plain Markdown with normal links and indexes. Obsidian, VS Code, GitHub, static site generators, and local preview tools can all become frontends.

### 5. Treat Chat as Secondary

Chat is useful, but it should query and explain the durable wiki, not replace the wiki. The durable artifact is the differentiator.

## Evidence Table

| Claim | Evidence | Source Date | Confidence |
|---|---|---:|---|
| LLM Wiki is an active direct category | Multiple new projects appeared in April 2026 around Karpathy's LLM Wiki pattern. | GitHub created dates, 2026-04 | High |
| `nashsu/llm_wiki` is the strongest direct competitor found | It had 14,007 stars and active pushes as of 2026-07-09. | GitHub API, 2026-07-09 | High |
| Obsidian is the dominant UI/workflow reference for direct LLM Wiki projects | Several direct competitors explicitly target Obsidian or Obsidian vaults. | GitHub API and README descriptions, 2026-07-09 | High |
| Repository-to-wiki is a large adjacent market | `AsyncFuncAI/deepwiki-open` had 17,216 stars. | GitHub API, 2026-07-09 | High |
| Quick capture tools are more mature than LLM Wiki builders | Memos, Joplin, Logseq, SiYuan, Karakeep, and Linkwarden have much older created dates and larger communities. | GitHub API, 2026-07-09 | High |
| Capture tools are likely upstream sources, not direct substitutes | Their core jobs are capture, clipping, bookmarking, notes, snippets, or PKM, not auditable wiki compilation. | README descriptions and project positioning | Medium-high |
| ExpertWiki can differentiate through auditability | Few reviewed projects emphasize raw-source preservation, lint, audit, packaging, and review as the main product surface. | Comparative review, 2026-07-09 | Medium-high |

## Risk and Unknowns

1. Crowding risk: LLM Wiki projects are easy to create and will continue appearing.
2. UI expectation risk: users may compare ExpertWiki to polished desktop or Obsidian plugin experiences.
3. Integration scope risk: supporting every capture tool can dilute focus.
4. Trust risk: LLM-generated wiki pages need source traceability and review, or users will distrust the output.
5. Format risk: some capture tools store data in proprietary databases, custom JSON, or app-specific formats.
6. License risk: several adjacent tools use AGPL-3.0; integrations should avoid copying code or creating unintended licensing constraints.
7. Activity risk: some projects, such as TriliumNext/Notes, are archived or less active, lowering priority.

## Red-Team Critique

The strongest critique is that ExpertWiki may be squeezed from both sides:

- Capture tools can add AI summaries and wiki pages.
- LLM Wiki tools can add importers, audit views, and Obsidian export.

If that happens, a small CLI wiki compiler may look too narrow.

Counterargument:

The narrowness can be a strength if ExpertWiki owns the artifact quality layer. Capture apps optimize speed. LLM Wiki demos optimize wow-factor generation. ExpertWiki can optimize durable knowledge engineering: raw preservation, explicit provenance, reviewable diffs, lint, audit, and package.

The strategic test is whether ExpertWiki can make users trust and reuse generated pages over time. If it cannot, it becomes another summarizer.

## Recommended Next Steps

### Product Research

1. Run the same source set through `nashsu/llm_wiki`, `kytmanov/obsidian-llm-wiki-local`, and `Ar9av/obsidian-wiki`.
2. Compare output on page structure, link quality, source traceability, editability, and regeneration behavior.
3. Test Memos, Karakeep, Linkwarden, and Joplin as upstream capture sources.
4. Identify the highest-value import format for each capture source.

### ExpertWiki Roadmap Candidates

1. Generic Markdown folder ingestion.
2. Memos API/export ingestion.
3. Linkwarden/Karakeep web capture ingestion.
4. Joplin export ingestion.
5. Review queue for generated page changes.
6. Provenance frontmatter and source-reference validation.
7. Bundle package preview with raw sources, wiki pages, log, lint result, and audit result.

### Metrics to Track

1. Ingest friction: minutes from source to raw material.
2. Page quality: percentage of generated pages requiring major edits.
3. Link quality: useful internal links per page.
4. Provenance coverage: percentage of factual claims with source refs.
5. Regeneration stability: how often pages churn without meaningful source changes.
6. Audit pass rate.
7. Export usefulness: whether generated Markdown works in Obsidian, GitHub, and a static preview.

## Source List

Primary GitHub repository sources:

- [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki)
- [kytmanov/obsidian-llm-wiki-local](https://github.com/kytmanov/obsidian-llm-wiki-local)
- [ussumant/llm-wiki-compiler](https://github.com/ussumant/llm-wiki-compiler)
- [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki)
- [green-dalii/obsidian-llm-wiki](https://github.com/green-dalii/obsidian-llm-wiki)
- [mohammadmaso/echowiki](https://github.com/mohammadmaso/echowiki)
- [domleca/llm-wiki](https://github.com/domleca/llm-wiki)
- [Ar9av/obsidian-wiki](https://github.com/Ar9av/obsidian-wiki)
- [AIDotNet/OpenDeepWiki](https://github.com/AIDotNet/OpenDeepWiki)
- [AsyncFuncAI/deepwiki-open](https://github.com/AsyncFuncAI/deepwiki-open)
- [sopaco/deepwiki-rs](https://github.com/sopaco/deepwiki-rs)
- [daeisbae/open-repo-wiki](https://github.com/daeisbae/open-repo-wiki)
- [QuentinWach/obsidian.ai](https://github.com/QuentinWach/obsidian.ai)
- [obsidianmd/obsidian-importer](https://github.com/obsidianmd/obsidian-importer)
- [davialabs/davia](https://github.com/davialabs/davia)
- [cclank/lanshu-wiki-skill](https://github.com/cclank/lanshu-wiki-skill)
- [usememos/memos](https://github.com/usememos/memos)
- [karakeep-app/karakeep](https://github.com/karakeep-app/karakeep)
- [linkwarden/linkwarden](https://github.com/linkwarden/linkwarden)
- [Dullage/flatnotes](https://github.com/dullage/flatnotes)
- [silverbulletmd/silverbullet](https://github.com/silverbulletmd/silverbullet)
- [logseq/logseq](https://github.com/logseq/logseq)
- [siyuan-note/siyuan](https://github.com/siyuan-note/siyuan)
- [TriliumNext/Notes](https://github.com/TriliumNext/Notes)
- [laurent22/joplin](https://github.com/laurent22/joplin)
- [dnote/dnote](https://github.com/dnote/dnote)
- [zk-org/zk](https://github.com/zk-org/zk)
- [foambubble/foam](https://github.com/foambubble/foam)
- [standardnotes/app](https://github.com/standardnotes/app)
- [anyproto/anytype-ts](https://github.com/anyproto/anytype-ts)
- [AppFlowy-IO/AppFlowy](https://github.com/AppFlowy-IO/AppFlowy)
- [massCodeIO/massCode](https://github.com/massCodeIO/massCode)
- [shaarli/Shaarli](https://github.com/shaarli/Shaarli)
- [wallabag/wallabag](https://github.com/wallabag/wallabag)
- [turtl/server](https://github.com/turtl/server)

Conceptual source:

- [Karpathy LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
