# ExpertWiki MVP

## Decision

Build the local authoring substrate for an agent-readable expert encyclopedia
and professional knowledge network.

The first vertical is global open-source AI, agent, and developer tooling.
ExpertWiki should turn source material about experts, projects, opinions,
research, cases, and diffusion signals into structured Markdown knowledge pages
that AI agents can cite and inspect.

## Target Users

- Agent developers who need reliable domain knowledge for AI products.
- AI application teams building agents in law, medicine, finance, open-source
  software, developer tools, and other professional domains.
- Experts who want to claim their pages, add knowledge, and receive AI
  citation, industry exposure, and qualified demand.
- Companies and sponsors that want industry topics, professional databases,
  knowledge APIs, brand visibility, and targeted distribution.

## Product Promise

Agents can answer with structured, citable professional knowledge that makes it
clear who said what, what evidence supports it, whether it is still current,
what credentials and conflicts matter, and where the expert or project can be
followed.

ExpertWiki keeps the raw source trail available so knowledge pages remain
auditable instead of becoming detached summaries.

## MVP Features

1. Initialize a local ExpertWiki knowledge bundle.
2. Ingest local files as raw source records; URL ingestion is unsupported.
3. Create agent-readable expert, project, topic, comparison, and synthesis
   pages under `wiki/`.
4. Track source references, update dates, credentials, conflicts, and contact
   paths on relevant pages.
5. List and show pages, sources, and audits.
6. Rebuild directory indexes.
7. Lint required files, frontmatter, source references, and Markdown links.
8. Write local audit reports.
9. Run package preflight checks.
10. Serve local search, page lookup, JSON graph, and `llms.txt` over HTTP.

## First Vertical

The MVP should focus on open-source AI, agents, and developer tools because the
project can seed this domain from GitHub, Hacker News, open-source project
propagation, and star-growth data.

Initial page types:

- Expert profiles: domain, credentials, representative claims, evidence,
  source dates, conflicts, contact paths, and claim status.
- Project profiles: repository, maintainers, problem area, adoption signals,
  release state, dependencies, and related experts.
- Viewpoint pages: a specific technical or strategic claim, its supporting
  sources, opposing evidence, and freshness.
- Topic pages: durable concepts such as agent memory, MCP, file search,
  evaluation, tool calling, and open-source model operations.

## Launch Sequence

1. Build a vertical expert and project database.
2. Let agent developers call, inspect, and cite it.
3. Use stable citations and traffic to attract expert page claims.
4. Let claimed experts add knowledge and publish deeper content.
5. Monetize professional traffic through industry topics, databases, APIs,
   brand placement, and targeted distribution.

## Success Criteria

- A user can create a vertical expert/project knowledge bundle from source
  material in one local workflow.
- A coding agent can inspect `AGENTS.md`, run CLI commands, and maintain pages.
- Search returns useful expert, project, topic, and viewpoint pages with source
  metadata.
- Agents can distinguish facts, claims, evidence, freshness, credentials, and
  conflicts from the page structure.
- Lint catches broken structure, broken links, and broken source references.
- Future MCP and hosted ExpertContext layers can consume the same card contract
  without moving source-of-truth ownership out of the bundle.
