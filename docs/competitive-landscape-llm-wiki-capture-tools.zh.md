# 竞品格局：LLM Wiki 构建器与私有知识捕捉工具

调研日期：2026-07-09

本文整理当前对话中关于 LLM Wiki 构建器、Obsidian 取向 wiki 工具、代码仓库到 wiki 系统，以及快速私有知识捕捉工具的调研结果。除特别说明外，GitHub 仓库元数据均在 2026-07-09 通过 GitHub API 查询。Stars 和最近 push 时间会持续变化。

## 执行摘要

ExpertWiki 位于两个活跃品类之间：

1. LLM wiki 构建器：把源材料转换成结构化、互相链接的 Markdown 或 wiki 页面。
2. 私有捕捉工具：帮助用户快速保存笔记、链接、代码片段、高亮和文件，但通常不会把它们综合成经过整理的 wiki。

最接近的直接竞品是 [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki)。这是一个增长很快的桌面 LLM Wiki 应用，截至 2026-07-09 约 14k stars。其他直接竞品集中在 Obsidian 和 Karpathy 的 LLM Wiki pattern 周围，包括 [kytmanov/obsidian-llm-wiki-local](https://github.com/kytmanov/obsidian-llm-wiki-local)、[Ar9av/obsidian-wiki](https://github.com/Ar9av/obsidian-wiki)、[lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki) 和 [green-dalii/obsidian-llm-wiki](https://github.com/green-dalii/obsidian-llm-wiki)。

最大的相邻需求信号来自代码仓库到 wiki 系统，例如 [AsyncFuncAI/deepwiki-open](https://github.com/AsyncFuncAI/deepwiki-open)，截至 2026-07-09 约 17.2k stars；以及私有捕捉工具，例如 [usememos/memos](https://github.com/usememos/memos)、[Joplin](https://github.com/laurent22/joplin)、[SiYuan](https://github.com/siyuan-note/siyuan)、[Logseq](https://github.com/logseq/logseq)、[Karakeep](https://github.com/karakeep-app/karakeep) 和 [Linkwarden](https://github.com/linkwarden/linkwarden)。

核心战略含义很清楚：ExpertWiki 不应该把自己定位成又一个通用笔记应用或 RAG 聊天系统。它最强的位置是一个本地优先、保留源材料、可审计的 wiki 编译器：从各种 capture 工具中摄取原始材料，然后产出结构化、可 review、可携带的 wiki bundle。

## 决策背景

正在评估的决策：

ExpertWiki 应该主要竞争为独立 LLM Wiki 产品、Obsidian/本地 Markdown 伴侣，还是多个 capture 来源的下游编译器？

可选方向：

1. 独立 LLM Wiki 应用。
2. Obsidian-first 插件或工作流。
3. 本地优先的命令行与 agent 工作流，用于把捕捉到的材料编译成可审计 wiki bundle。
4. 面向代码库的 repository-to-wiki 系统。
5. capture-first 笔记或书签应用。

建议的战略方向：

ExpertWiki 应优先选择方向 3，同时兼容方向 2 和方向 4。它应该集成 capture 工具，而不是替代它们。

## 调研范围

纳入范围：

- 能把本地文件、Markdown、笔记、文档、代码仓库或 Obsidian vault 编译成 wiki-like 页面的项目。
- 用于把笔记组织成链接知识结构的 Obsidian 与 Markdown 工具。
- 自托管或本地优先的笔记、链接、代码片段、网页和私有知识碎片捕捉工具。
- 输出为结构化文档或 AI-readable wiki 的 repository-to-wiki 工具。

未作为核心分析对象：

- 只做向量检索或 RAG chat、但不生成持久 wiki 页面的工具。
- 不聚焦个人/本地知识捕捉的通用 CMS。
- 不直接捕捉用户知识的搜索引擎或基础设施项目。

## 分类

### A 类：直接 LLM Wiki 构建器

这些项目最接近 ExpertWiki，因为它们明确把源材料转换成持久 wiki 或结构化 Markdown 知识库。

| 项目 | Stars | 创建时间 | 最近 push | License | 相关性 | 来源 |
|---|---:|---:|---:|---|---|---|
| [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki) | 14,007 | 2026-04-08 | 2026-07-08 | NOASSERTION | 直接竞品 | GitHub API, README |
| [Ar9av/obsidian-wiki](https://github.com/Ar9av/obsidian-wiki) | 2,743 | 2026-04-06 | 2026-07-07 | MIT | 直接 Obsidian/agent 竞品 | GitHub API |
| [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki) | 1,303 | 2026-04-04 | 2026-07-08 | Apache-2.0 | 直接 LLM Wiki 竞品 | GitHub API |
| [kytmanov/obsidian-llm-wiki-local](https://github.com/kytmanov/obsidian-llm-wiki-local) | 767 | 2026-04-07 | 2026-05-26 | MIT | 直接本地 Obsidian 竞品 | GitHub API |
| [ussumant/llm-wiki-compiler](https://github.com/ussumant/llm-wiki-compiler) | 295 | 2026-04-04 | 2026-05-05 | MIT | 直接 compiler-style 竞品 | GitHub API |
| [green-dalii/obsidian-llm-wiki](https://github.com/green-dalii/obsidian-llm-wiki) | 254 | 2026-04-26 | 2026-07-06 | Apache-2.0 | 直接 Obsidian 插件竞品 | GitHub API |
| [domleca/llm-wiki](https://github.com/domleca/llm-wiki) | 169 | 2026-04-08 | 2026-06-15 | MIT | 直接 Obsidian 插件竞品 | GitHub API |
| [cclank/lanshu-wiki-skill](https://github.com/cclank/lanshu-wiki-skill) | 14 | 2026-05-24 | 2026-05-24 | MIT | 相邻 Claude Code skill | GitHub API |
| [mohammadmaso/echowiki](https://github.com/mohammadmaso/echowiki) | 2 | 2026-07-05 | 2026-07-05 | MIT | 早期直接竞品 | GitHub API |

观察：

- 这个品类在 2026 年 4 月左右快速形成，与 Karpathy 的 LLM Wiki pattern 传播时间接近。
- 大多数项目都很年轻，但 `nashsu/llm_wiki` 的增长说明需求明确。
- Obsidian 兼容是常见路线，因为 Obsidian 已经提供 Markdown、本地文件、链接和图谱 UX。
- 多个项目使用了 `raw` 到 `wiki`、concept pages、entity pages、auto-links、persistent wiki 等语言，与 ExpertWiki 的目标领域高度重叠。

### B 类：Repository-to-Wiki 与代码库文档化

这些工具主要关注代码仓库，而不是个人文档，但它们证明了自动 wiki 生成有需求。

| 项目 | Stars | 创建时间 | 最近 push | License | 相关性 | 来源 |
|---|---:|---:|---:|---|---|---|
| [AsyncFuncAI/deepwiki-open](https://github.com/AsyncFuncAI/deepwiki-open) | 17,216 | 2025-04-30 | 2026-06-03 | MIT | 强相邻竞品 | GitHub API |
| [AIDotNet/OpenDeepWiki](https://github.com/AIDotNet/OpenDeepWiki) | 3,403 | 2025-04-27 | 2026-07-07 | MIT | 强相邻竞品 | GitHub API |
| [sopaco/deepwiki-rs](https://github.com/sopaco/deepwiki-rs) | 1,347 | 2025-09-05 | 2026-05-16 | MIT | 相邻 repo 文档工具 | GitHub API |
| [daeisbae/open-repo-wiki](https://github.com/daeisbae/open-repo-wiki) | 308 | 2024-12-14 | 2026-04-06 | Apache-2.0 | 相邻 repo wiki generator | GitHub API |
| [davialabs/davia](https://github.com/davialabs/davia) | 1,648 | 2025-11-05 | 2026-01-19 | MIT | 相邻 agent-editable docs | GitHub API |

观察：

- 在本次扫描中，最大的 repository-to-wiki 项目 `deepwiki-open` 的 stars 超过所有直接 LLM Wiki 项目，除非把更广义的 capture/workspace 工具也算进去。
- 代码库文档化是相关但不同的用例。它更重视架构图、代码引用、API map，而不是对源材料进行 provenance-preserving 的综合。
- ExpertWiki 可以借鉴这个类别的 repo ingest、结构化输出、图表和 MCP 接口，但不必把代码库作为核心切入点。

### C 类：Obsidian、Markdown 导入与笔记质量工具

这些项目不一定从任意 raw source 生成 wiki 页面，但它们处在相邻工作流里。

| 项目 | Stars | 创建时间 | 最近 push | License | 相关性 | 来源 |
|---|---:|---:|---:|---|---|---|
| [obsidianmd/obsidian-importer](https://github.com/obsidianmd/obsidian-importer) | 1,524 | 2023-07-11 | 2026-05-29 | MIT | 上游导入器 | GitHub API |
| [QuentinWach/obsidian.ai](https://github.com/QuentinWach/obsidian.ai) | 18 | 2024-04-17 | 2024-08-28 | NOASSERTION | 相邻 AI 笔记整理工具 | GitHub API |

观察：

- 导入器很重要，因为用户经常从 Apple Notes、Evernote、Notion、OneNote、Google Keep 或其他已有系统迁移过来。
- ExpertWiki 应该把导入器视为填充 `raw/sources/` 的方式，而不是完整解决方案。

### D 类：快速私有捕捉与自托管笔记

这些项目严格来说不是 LLM Wiki 竞品。它们解决的是上游 capture 问题：如何快速把知识碎片放进一个私有系统。

| 项目 | Stars | 创建时间 | 最近 push | License | 相关性 | 来源 |
|---|---:|---:|---:|---|---|---|
| [usememos/memos](https://github.com/usememos/memos) | 61,417 | 2021-12-08 | 2026-07-08 | MIT | 最重要 capture-layer 参考 | GitHub API, README |
| [laurent22/joplin](https://github.com/laurent22/joplin) | 55,481 | 2017-01-16 | 2026-07-07 | NOASSERTION | 成熟笔记与 web clipper 来源 | GitHub API, README |
| [siyuan-note/siyuan](https://github.com/siyuan-note/siyuan) | 44,991 | 2020-08-30 | 2026-07-08 | AGPL-3.0 | 强本地优先 PKM | GitHub API |
| [logseq/logseq](https://github.com/logseq/logseq) | 43,758 | 2020-05-23 | 2026-07-08 | AGPL-3.0 | 强本地优先 outline PKM | GitHub API |
| [karakeep-app/karakeep](https://github.com/karakeep-app/karakeep) | 27,198 | 2024-02-06 | 2026-07-06 | AGPL-3.0 | 书签、笔记、图片、AI tagging 来源 | GitHub API, README |
| [linkwarden/linkwarden](https://github.com/linkwarden/linkwarden) | 18,857 | 2022-04-09 | 2026-07-07 | AGPL-3.0 | 书签、归档、高亮来源 | GitHub API, README |
| [foambubble/foam](https://github.com/foambubble/foam) | 17,276 | 2020-06-19 | 2026-06-23 | NOASSERTION | VS Code + Markdown PKM | GitHub API |
| [wallabag/wallabag](https://github.com/wallabag/wallabag) | 12,815 | 2013-04-03 | 2026-07-06 | MIT | read-it-later 与文章 capture | GitHub API |
| [anyproto/anytype-ts](https://github.com/anyproto/anytype-ts) | 8,372 | 2023-05-22 | 2026-07-07 | NOASSERTION | 本地优先 object workspace | GitHub API |
| [massCodeIO/massCode](https://github.com/massCodeIO/massCode) | 6,889 | 2022-03-29 | 2026-07-06 | AGPL-3.0 | 开发者 snippets 与 notes | GitHub API |
| [standardnotes/app](https://github.com/standardnotes/app) | 6,541 | 2016-12-05 | 2026-07-07 | AGPL-3.0 | 加密私有笔记 | GitHub API |
| [silverbulletmd/silverbullet](https://github.com/silverbulletmd/silverbullet) | 5,614 | 2022-02-16 | 2026-07-01 | MIT | Markdown 个人生产力平台 | GitHub API |
| [shaarli/Shaarli](https://github.com/shaarli/Shaarli) | 3,881 | 2014-07-26 | 2026-06-27 | NOASSERTION | 轻量自托管书签 | GitHub API |
| [Dullage/flatnotes](https://github.com/dullage/flatnotes) | 3,146 | 2021-08-03 | 2026-02-17 | MIT | 平铺 Markdown 文件夹笔记来源 | GitHub API |
| [dnote/dnote](https://github.com/dnote/dnote) | 3,044 | 2017-03-30 | 2026-03-26 | Apache-2.0 | 开发者 CLI notebook | GitHub API |
| [TriliumNext/Notes](https://github.com/TriliumNext/Notes) | 2,927 | 2024-02-14 | 2025-06-24 | AGPL-3.0 | 个人 wiki/notes，但已 archived | GitHub API |
| [zk-org/zk](https://github.com/zk-org/zk) | 2,709 | 2020-12-23 | 2026-07-08 | GPL-3.0 | 纯文本 note-taking assistant | GitHub API |
| [turtl/server](https://github.com/turtl/server) | 633 | 2017-09-19 | 2024-03-25 | AGPL-3.0 | 私有笔记，当前相关性较低 | GitHub API |

观察：

- Memos 是最清晰的 quick-capture 参考。它的 README 强调即时捕捉、Markdown 可携带、自托管、低部署摩擦，以及 REST/gRPC API。
- Joplin、Logseq、SiYuan、Foam、SilverBullet、flatnotes、Dnote 和 zk 有价值，因为它们要么直接存储 Markdown-like 材料，要么可以导出类似材料。
- Karakeep 和 Linkwarden 对网页研究工作流尤其重要，因为它们捕捉 URL、网页、PDF、截图、高亮、标注，以及 AI 生成标签或摘要。
- Capture 工具通常擅长 ingestion UX，但在 curated synthesis、provenance audit 和 bundle packaging 上较弱。

## 竞争定位

### 直接竞争

直接竞品回答的是同一个核心任务：

“把我的原始知识材料变成结构化、互相链接的 wiki。”

这一组包括：

- [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki)
- [kytmanov/obsidian-llm-wiki-local](https://github.com/kytmanov/obsidian-llm-wiki-local)
- [Ar9av/obsidian-wiki](https://github.com/Ar9av/obsidian-wiki)
- [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki)
- [green-dalii/obsidian-llm-wiki](https://github.com/green-dalii/obsidian-llm-wiki)
- [domleca/llm-wiki](https://github.com/domleca/llm-wiki)
- [ussumant/llm-wiki-compiler](https://github.com/ussumant/llm-wiki-compiler)
- [mohammadmaso/echowiki](https://github.com/mohammadmaso/echowiki)

ExpertWiki 必须假设这个类别会变得拥挤。Karpathy LLM Wiki pattern 很容易解释、容易 demo，也容易被开发者仿制。

### 相邻竞争

相邻竞品回答的是附近的问题：

- “把这个代码仓库解释成一个 wiki。”
- “让我的知识库可搜索。”
- “整理我的笔记。”
- “保存我的链接和网页。”
- “帮我快速捕捉想法。”

如果这些工具加入持久 wiki synthesis，它们可能变成竞品；但今天它们也可以成为合理的 ingestion partner。

### 上游数据源

ExpertWiki 最强的上游来源是：

1. Memos：快速 Markdown memo capture。
2. Karakeep：书签、笔记、图片、PDF、AI tags 与 summaries。
3. Linkwarden：归档网页、高亮、标注、PDF 和截图。
4. Joplin：成熟笔记和 web clipping。
5. Logseq、Foam、SilverBullet、flatnotes、Dnote 和 zk：本地 Markdown 或纯文本笔记图谱。

## 功能模式分析

### 直接 LLM Wiki 项目强调什么

- 持久 wiki 输出，而不是一次性聊天。
- Concept、entity 和 source pages。
- 生成页面之间的自动链接。
- Obsidian 兼容或 Markdown 兼容。
- 本地或私有处理，通常通过 Ollama 或用户自带模型凭证。
- 在生成 wiki 之上叠加 conversational query。
- 随着新 source 到来，增量维护 wiki。

### Capture 工具强调什么

- 低摩擦 capture：timeline、share sheet、browser extension、web clipper、command line 或 mobile app。
- 私有所有权：自托管、本地优先、离线优先、加密或无 telemetry。
- 可携带性：Markdown、export、API、flat files、SQLite 或开放格式。
- 检索：全文搜索、tags、collections、graph、backlinks 或 filters。
- 保存：归档 HTML、PDF、截图、附件、笔记、高亮和 metadata。

### 大多数项目没有完整解决什么

- 带显式 provenance 的 source-preserving compilation。
- 面向生成页面的人类 review loop。
- 把 wiki 作为 artifact 来 lint 和 audit。
- 打包或分享包含 sources、generated pages、logs 和 audit outputs 的完整 bundle。
- 明确区分不可变 raw sources 与 synthesized knowledge。
- 面向 agents 的可重复命令行工作流。

这个缺口是 ExpertWiki 最好的战略切入口。

## 推荐的 ExpertWiki 定位

推荐定位语：

ExpertWiki 是一个面向严肃知识工作的本地优先、保留源材料的 LLM wiki 编译器。它从文件、笔记、书签和代码仓库中摄取原始材料，然后生成带链接、索引、日志和 provenance 的可审计 Markdown wiki bundle。

避免把 ExpertWiki 定位成：

- 通用笔记应用。
- 通用自托管书签管理器。
- 通用 RAG 聊天系统。
- 纯 Obsidian 插件。
- 纯代码库文档生成器。

## 战略选项

### 选项 1：独立 LLM Wiki 应用

支持证据：

- [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki) 显示了 “documents to wiki” 产品的强需求。
- 用户更容易理解桌面或网页应用，而不是 CLI。

反向证据：

- UI-heavy 竞争很难快速追上。
- 桌面应用需要解决 onboarding、file watching、graph UX、review UX 和模型配置。

关键不确定性：

- ExpertWiki 的目标用户是否更看重可复现本地 authoring，而不是图形界面。

置信度：

- 中。

### 选项 2：Obsidian-first 工作流

支持证据：

- 很多直接竞品都面向 Obsidian。
- Obsidian 提供 Markdown、backlinks、graph visualization 和既有 PKM 用户群。

反向证据：

- Obsidian 插件竞争可能很快拥挤。
- 如果把核心产品绑定到 Obsidian，可能削弱更广义的 “local wiki bundle” 模型。

关键不确定性：

- ExpertWiki 用户是否已经把 Obsidian 当作主要阅读和编辑界面。

置信度：

- 作为集成路径为中高；作为全部战略则不足。

### 选项 3：Capture 工具的下游编译器

支持证据：

- Memos、Joplin、Logseq、SiYuan、Karakeep、Linkwarden 等工具已经解决 capture。
- 它们的弱点在 synthesis、audit、packaging 和持久 wiki 构建。
- ExpertWiki 已经有 raw sources、generated wiki pages、logs、lint、audit 和 package 等天然概念。

反向证据：

- 集成越多，维护成本越高。
- 用户可能期待每个来源都有一键导入。

关键不确定性：

- 哪些 capture sources 与 ExpertWiki 的目标用户重合度最高。

置信度：

- 高。

### 选项 4：Codebase-to-Wiki

支持证据：

- `deepwiki-open` 显示出强开发者需求。
- 代码仓库本质上是本地目录，并且有结构化引用，适合 ExpertWiki 的 CLI 取向。

反向证据：

- 代码库文档化已经是竞争品类。
- 代码库 docs 需要 code-aware parsing、call graphs、dependency analysis 和语言特定 UX。

关键不确定性：

- 代码库 wiki 生成应该是核心用例，还是后续 vertical。

置信度：

- 中。

## 推荐产品动作

### 1. 构建 capture-source ingestion connectors

建议优先级：

1. Markdown folder ingestion，覆盖 flatnotes、Logseq、Foam、SilverBullet、zk 和通用目录。
2. 通过 API 或 export 做 Memos ingestion。
3. Joplin Markdown 或 JEX export ingestion。
4. Linkwarden ingestion，覆盖 URLs、archived pages、annotations、screenshots 和 PDFs。
5. Karakeep ingestion，覆盖 bookmarks、notes、images、PDFs、AI tags 和 summaries。

理由：

Markdown folder ingestion 是最低风险的基础。之后 Memos、Joplin、Linkwarden 和 Karakeep 覆盖最重要的非文件夹 capture 流程。

### 2. 把 provenance 做成一等功能

每个生成页面都应该保留：

- Source references。
- Ingest timestamp。
- Source path 或 URL。
- Publisher 或 origin system。
- Generation command。
- 可行时记录 model 和 prompt metadata。
- Change log entry。
- Review status。

这是把 ExpertWiki 与笔记应用和轻量 LLM Wiki demo 区分开的最清晰方式。

### 3. 加入 review loop

产品应该支持这样的工作流：

1. 把 sources ingest 到 `raw/sources/`。
2. 生成 proposed wiki changes。
3. 展示 changed pages 和 source references。
4. Approve、edit 或 reject changes。
5. 在 `log.md` 中记录 meaningful changes。
6. 运行 lint 和 audit。

这个 review loop 比另一个聊天界面更有价值，因为它把 LLM 输出转化为可维护知识。

### 4. 保持输出 tool-agnostic

ExpertWiki 应生成普通 Markdown、普通链接和 indexes。Obsidian、VS Code、GitHub、静态站点生成器和本地预览工具都可以成为前端。

### 5. 把 chat 放在次要位置

Chat 有用，但它应该查询和解释持久 wiki，而不是替代 wiki。持久 artifact 才是差异点。

## 证据表

| 判断 | 证据 | 来源日期 | 置信度 |
|---|---|---:|---|
| LLM Wiki 是活跃直接品类 | 多个新项目在 2026 年 4 月围绕 Karpathy 的 LLM Wiki pattern 出现。 | GitHub created dates, 2026-04 | 高 |
| `nashsu/llm_wiki` 是目前发现的最强直接竞品 | 截至 2026-07-09 有 14,007 stars，且仍有活跃 push。 | GitHub API, 2026-07-09 | 高 |
| Obsidian 是直接 LLM Wiki 项目的主要 UI/工作流参考 | 多个直接竞品明确面向 Obsidian 或 Obsidian vault。 | GitHub API 与 README descriptions, 2026-07-09 | 高 |
| Repository-to-wiki 是大型相邻市场 | `AsyncFuncAI/deepwiki-open` 有 17,216 stars。 | GitHub API, 2026-07-09 | 高 |
| Quick capture 工具比 LLM Wiki 构建器更成熟 | Memos、Joplin、Logseq、SiYuan、Karakeep 和 Linkwarden 创建时间更早、社区更大。 | GitHub API, 2026-07-09 | 高 |
| Capture 工具更可能是上游来源，而不是直接替代品 | 它们的核心任务是 capture、clipping、bookmarking、notes、snippets 或 PKM，而不是可审计 wiki compilation。 | README descriptions 与项目定位 | 中高 |
| ExpertWiki 可以通过 auditability 做差异化 | 被审查项目中，很少把 raw-source preservation、lint、audit、packaging 和 review 作为主产品界面。 | Comparative review, 2026-07-09 | 中高 |

## 风险与未知

1. 拥挤风险：LLM Wiki 项目容易创建，后续会继续出现。
2. UI 预期风险：用户可能会把 ExpertWiki 与更成熟的桌面应用或 Obsidian 插件体验比较。
3. 集成范围风险：支持每一个 capture 工具会稀释重点。
4. 信任风险：LLM 生成的 wiki 页面如果缺少 source traceability 和 review，用户会不信任输出。
5. 格式风险：一些 capture 工具使用私有数据库、自定义 JSON 或应用特定格式。
6. License 风险：多个相邻工具使用 AGPL-3.0；集成时应避免复制代码或引入意外许可证约束。
7. 活跃度风险：部分项目如 TriliumNext/Notes 已 archived 或活跃度较低，优先级应降低。

## Red-Team 批判

最强的反方观点是：ExpertWiki 可能会被两侧挤压。

- Capture 工具可以增加 AI summaries 和 wiki pages。
- LLM Wiki 工具可以增加 importers、audit views 和 Obsidian export。

如果这些都发生，一个小型 CLI wiki compiler 可能显得过窄。

反驳：

这种“窄”也可能是优势，前提是 ExpertWiki 拥有 artifact quality layer。Capture apps 优化速度。LLM Wiki demos 优化生成的惊艳感。ExpertWiki 可以优化持久知识工程：raw preservation、explicit provenance、reviewable diffs、lint、audit 和 package。

真正的战略测试是：ExpertWiki 能不能让用户长期信任和复用生成页面。如果不能，它就会变成又一个 summarizer。

## 推荐下一步

### 产品研究

1. 用同一批 source set 跑 `nashsu/llm_wiki`、`kytmanov/obsidian-llm-wiki-local` 和 `Ar9av/obsidian-wiki`。
2. 对比输出的页面结构、链接质量、source traceability、可编辑性和 regeneration behavior。
3. 测试 Memos、Karakeep、Linkwarden 和 Joplin 作为上游 capture sources。
4. 为每个 capture source 找出最高价值的导入格式。

### ExpertWiki Roadmap 候选项

1. Generic Markdown folder ingestion。
2. Memos API/export ingestion。
3. Linkwarden/Karakeep web capture ingestion。
4. Joplin export ingestion。
5. 生成页面变更的 review queue。
6. Provenance frontmatter 与 source-reference validation。
7. Bundle package preview，包含 raw sources、wiki pages、log、lint result 和 audit result。

### 需要跟踪的指标

1. Ingest friction：从 source 到 raw material 需要几分钟。
2. Page quality：需要大改的生成页面比例。
3. Link quality：每页有用 internal links 数量。
4. Provenance coverage：有 source refs 的 factual claims 比例。
5. Regeneration stability：没有 meaningful source changes 时页面 churn 的频率。
6. Audit pass rate。
7. Export usefulness：生成 Markdown 能否在 Obsidian、GitHub 和静态预览中有效使用。

## 来源列表

主要 GitHub 仓库来源：

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
- [Dullage/flatnotes](https://github.com/Dullage/flatnotes)
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

概念来源：

- [Karpathy LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
