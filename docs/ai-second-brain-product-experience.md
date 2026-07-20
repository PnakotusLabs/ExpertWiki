# ExpertWiki AI Second Brain Product Experience

This document defines the beginner-facing product experience for ExpertWiki's AI second brain automation. It is the user-facing counterpart to the engineering replacement plan. The engineering system may use source hashes, SQLite state, concept dependency graphs, draft queues, and incremental compilation, but the product experience should feel like a simple local knowledge assistant: add material, review what AI understood, approve useful knowledge, and ask questions against the approved wiki.

The core product decision is to hide compiler language from normal users. ExpertWiki should not ask beginners to think about `source_concepts`, frozen slugs, compile state, citation spans, or manual edit hashes. Those concepts are necessary for correctness, but they belong in developer docs, debug output, and advanced commands. The everyday experience should say: ExpertWiki reads your files, proposes knowledge cards, waits for your approval, and answers only from the approved wiki.

## Product Promise

ExpertWiki helps a user turn scattered local material into an interlinked, source-backed second brain without losing control. The user keeps the original files. AI proposes structured knowledge cards. Nothing becomes trusted knowledge until the user approves it. Later, when the user asks a question, ExpertWiki answers from the approved wiki rather than improvising from raw files.

The simplest mental model is:

```text
Add material
  -> AI understands it
  -> Review suggested cards
  -> Approve useful cards
  -> Ask the approved wiki
```

This should be the model used in README examples, onboarding copy, CLI help text, and future UI screens. The deeper compiler model still exists, but it should be described as "how ExpertWiki keeps the wiki accurate and up to date" rather than as the main product surface.

## Target Users

The first user is a non-expert CLI user who has useful files but does not know how to design a wiki. They may have meeting notes, research notes, project docs, GitHub findings, reviews, or saved articles. They want the system to do the organizing work, but they still want to confirm what becomes part of their trusted knowledge base.

The second user is an agent developer or power user who cares about provenance, repeatability, and local-first control. They are willing to inspect drafts, run validation, and publish bundles to other tools. They need the advanced commands, but they should still benefit from the same simple default flow.

The third user is a future hosted or SaaS user. For them, the same product model should become a visual workflow: upload or connect sources, review generated cards, approve, publish, and ask. The CLI should therefore avoid terms that cannot translate into a simple UI later.

## Beginner Vocabulary

ExpertWiki should use product words in the beginner path. A raw source should be called "material" or "source material." A generated draft should be called a "suggested card." A published wiki page should be called an "approved card." A compile run should be called "organizing" or "updating the wiki." A source hash mismatch should be called "changed material." A stale page should be called "needs refresh." A rejected draft should be called "sent back with feedback."

The advanced vocabulary can still exist behind `--verbose`, `doctor`, debug logs, and developer docs. The product should never make beginners feel that they are maintaining a build system. They are curating a trusted second brain.

## Primary CLI Experience

The beginner path should have four primary commands:

```bash
expertwiki add <file-or-folder>
expertwiki review
expertwiki approve <card>
expertwiki ask "What should I know about this?"
```

`expertwiki add` should preserve the file, read it, and prepare suggested cards. If the user adds a folder, ExpertWiki should summarize what it found before doing expensive work: how many readable files, how many skipped files, and whether it needs confirmation. For a single file, it can proceed directly. The output should say what happened in human language: "Saved 1 source. Found 4 possible cards. Wrote 3 suggestions for review."

`expertwiki review` should show pending suggested cards, grouped by topic. A beginner should see titles, short descriptions, source count, confidence, and the action needed. The command should not show database IDs by default. A good review list feels like an inbox: clear enough to decide what to open, not a dump of internal state.

`expertwiki approve <card>` should publish one suggested card into the wiki. The output should say where it was saved and what it links to. It should also make the next action obvious: approve another card, ask a question, or run validation. Approval is the trust moment, so the wording should reinforce that the card is now part of the approved wiki.

`expertwiki ask` should answer from approved cards only. If no approved card supports the question, it should say that clearly and suggest adding or approving material. It should not quietly read raw sources and invent an answer, because that breaks the user's trust model.

## Advanced CLI Experience

The engineering commands should remain available, but they should be positioned as advanced controls:

```bash
expertwiki analyze
expertwiki compile
expertwiki review reject <card> --feedback "..."
expertwiki doctor
expertwiki lint
expertwiki audit
expertwiki publish
```

`analyze` and `compile` are useful terms for developers, but they should not be required in the beginner tutorial. The beginner command `add` can internally run analysis and draft generation. Power users can split the steps when they want more control over cost, model choice, or batch size.

`doctor` should become the friendly health command for state problems. It can report changed material, stale cards, broken links, rejected suggestions, and pending approvals. `lint` can remain the stricter structural validator. The product distinction is that `doctor` helps users understand what to do next, while `lint` verifies the bundle contract.

## First-Run Experience

The first run should start from a single helpful command:

```bash
expertwiki start
```

If no bundle exists, `start` creates one in the default location, asks for a title only when needed, and prints the next useful command. If a bundle already exists, `start` should show its health: approved cards, pending suggestions, source materials, host-AI jobs, and whether any source material changed since the last update.

The first-run path should not expose model-provider configuration. When invoked as a skill, the current host AI processes ExpertWiki's persistent jobs with its existing capabilities. OpenAI-compatible provider settings belong only to an advanced, explicitly selected unattended API backend.

## Add Material Flow

When the user runs `expertwiki add notes.md`, ExpertWiki should preserve the original source before doing anything else. The status output should make that visible because source preservation is a core trust feature. The next line should say that AI is looking for reusable knowledge, not merely summarizing the file.

A good output shape is:

```text
Saved source: raw/sources/notes.md
Reading for reusable knowledge...
Found 5 candidate ideas.
Created 3 suggested cards:
  1. Agent Memory
  2. Tool Calling Failure Modes
  3. Context Window Budgeting
Review them with: expertwiki review
```

If the file is not useful, the product should say why without sounding like a crash: "Saved the source, but did not create suggestions because the file appears to contain only generated boilerplate." In strict mode, it may reject the source before preservation if that is required by the admission gate. The key is that the user understands the decision.

## Review Flow

Review is the most important screen in the product. It is where AI output becomes trusted knowledge or gets rejected. The review experience should show the card title, why it was suggested, which sources support it, and what changed if it updates an existing card. The user should not have to inspect raw Markdown just to make a basic decision.

The default `expertwiki review` output should be compact:

```text
3 suggested cards need review

[1] Agent Memory
    New topic card, supported by 2 sources, medium confidence
    Sources: karpathy-llm-wiki.md, mcp-notes.md

[2] Model Context Protocol
    Updates existing project card, supported by 1 changed source
    Sources: anthropic-mcp.md

[3] Context as Infrastructure
    New synthesis card, supported by 3 sources, high confidence
    Sources: karpathy-llm-wiki.md, openai-file-search-docs.md, anthropic-mcp.md
```

Opening a card should show a readable preview with source references. The user should be able to approve, reject, or edit. Rejection should ask for feedback because that feedback becomes useful on the next generation. A simple rejection flow is better than forcing the user to fix the AI's draft manually.

## Approval Flow

Approval should feel like publishing into the trusted wiki. The command should move the card from suggestions into `wiki/`, rebuild indexes, update the log, and make it available to `ask`. The user-facing copy should say "approved" rather than "compiled" or "flushed state."

A good approval response is:

```text
Approved: Agent Memory
Saved to: wiki/topics/agent-memory.md
Linked to: Tool Calling, Context Window Budgeting
The card is now available to: expertwiki ask
```

Bulk approval should exist, but it should be explicit. Beginners should not accidentally approve every suggestion. A safe command is `expertwiki approve --all-reviewed`, where "reviewed" means the user has opened or marked each draft. `expertwiki approve --all` should either be advanced-only or require confirmation.

## Ask Flow

The question experience should reinforce that ExpertWiki answers from approved knowledge. The response should include the answer, the cards used, and a short confidence or coverage note. It should avoid raw source citations unless the user asks for evidence detail, but it should always make the supporting cards visible.

A good answer shape is:

```text
Answer
Agent memory works best when reusable knowledge is promoted into stable cards
instead of kept as temporary chat context...

Used cards
- Agent Memory
- Context as Infrastructure
- Model Context Protocol

Coverage
Good coverage from 3 approved cards. No contradictory approved card found.
```

If the wiki cannot answer, the product should be honest:

```text
I do not have an approved card that answers this yet.

Next useful actions:
1. Add source material about this topic.
2. Review pending suggestions.
3. Search raw sources manually if you are still collecting evidence.
```

## Update Flow

When source material changes, ExpertWiki should describe it as a refresh need. The user should not see "hash mismatch" unless verbose mode is enabled. A friendly update summary is:

```text
2 sources changed since the last update.
4 approved cards may need refresh.
Run: expertwiki update
```

`expertwiki update` should analyze changed material, create update suggestions, and leave existing approved cards untouched until approval. If a user manually edited an approved card, the product should say: "This card was edited by you, so ExpertWiki will not overwrite it automatically." That protects local ownership while keeping the explanation simple.

## Error and Empty States

Empty states should teach the next action. A new bundle with no sources should say: "Add your first source material with `expertwiki add <file>`." A bundle with sources but no suggestions should say whether AI is not configured, the sources were not admissible, or analysis failed. A bundle with suggestions but no approved cards should say: "Review and approve at least one card before asking questions."

Errors should separate user-fixable problems from system problems. Missing file, unsupported format, stale host-AI job, invalid result schema, and invalid token should have direct next steps. Internal state problems should point to `expertwiki doctor`. A missing model provider is relevant only after the user explicitly selects `--backend api`. The product should not hide broken functionality with reassuring prose; it should make the problem understandable and recoverable.

## Future Visual UI

The same experience should translate into a future desktop or SaaS UI with five primary areas: Sources, Suggestions, Approved Wiki, Ask, and Health. Sources shows preserved material. Suggestions is the review inbox. Approved Wiki is the user's trusted second brain. Ask is the grounded question surface. Health explains stale cards, changed material, broken links, and publish readiness.

The UI should not expose compiler internals by default. It can show advanced diagnostics behind a "Details" or "Developer" panel. The main screen should answer three questions quickly: what did I add, what does AI suggest, and what is already trusted?

## Product Metrics

The product should measure progress through trust and usefulness, not raw generation volume. Useful metrics include sources added, suggestions created, suggestions approved, suggestions rejected with feedback, approved cards used in answers, unanswered questions, stale cards refreshed, and broken links resolved.

The most important activation moment is the first approved card that successfully answers a later question. The second important moment is the first update where changed source material produces a clear card refresh suggestion without overwriting the user's existing wiki.

## Experience Principles

ExpertWiki should feel conservative by default. It should preserve raw material, suggest knowledge, wait for approval, and answer from trusted pages. It should not behave like a generic chat app that confidently synthesizes from anything it can see.

ExpertWiki should make AI work visible but not overwhelming. Users should know that AI found candidate ideas and wrote suggested cards, but they should not need to understand the dependency graph behind that work.

ExpertWiki should reward review. The product should make approval fast, rejection useful, and source inspection available. Human confirmation is not friction to eliminate; it is the trust boundary that makes the second brain reliable.

ExpertWiki should scale down before it scales up. The first experience must work for one file and three suggested cards. The same model can later handle folders, projects, public libraries, and SaaS publishing, but the beginner path should stay small and legible.

## Recommended Product Surface

The recommended beginner-facing command set is:

```text
expertwiki start      Set up or summarize the current wiki
expertwiki add        Add material and let AI suggest cards
expertwiki review     Review suggested cards
expertwiki approve    Approve suggestions into the wiki
expertwiki reject     Reject suggestions with feedback
expertwiki ask        Ask the approved wiki
expertwiki update     Refresh suggestions after material changes
expertwiki doctor     Explain what needs attention
```

The recommended advanced command set is:

```text
expertwiki ingest     Preserve sources without AI automation
expertwiki analyze    Extract concepts from preserved sources
expertwiki compile    Generate draft cards from concepts
expertwiki lint       Validate bundle structure
expertwiki audit      Write a local audit report
expertwiki package    Run package preflight checks
expertwiki publish    Publish approved public pages
```

This split lets ExpertWiki keep the rigorous compiler underneath while presenting a simple second brain product above it. Beginners get a trusted workflow they can understand. Power users still get precise controls. Developers still get a clean implementation model.
