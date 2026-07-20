# ExpertWiki AI Second Brain 自动化替换设计与开发计划

本文档定义 ExpertWiki 下一阶段的替换方向：把当前的本地 Markdown authoring substrate 升级为自动化 LLM Wiki compiler。设计必须重点参考并尽量移植两个上游项目的思路、状态机和产物契约：`obsidian-llm-wiki-local` 与 `llm-wiki-compiler`。前者提供最适合 ExpertWiki 的本地 CLI 工作流，核心是 fast model 抽取概念、SQLite 状态库、heavy model 编译概念页、草稿审核后发布；后者提供更强的工程化编译器模型，核心是 source change detection、concept-to-sources 反向依赖、review queue、line-range citation、journal、lock 与增量重编译。

这次改造不应该从零设计一个新的 second brain 系统，也不应该把 ExpertWiki 继续停留在“让外部 agent 手写 wiki page”的阶段。ExpertWiki 现有的价值是目录契约、raw source 保存、frontmatter、lint、audit、local API 与 llms.txt；这些应该保留为外壳。需要替换的是中间层：从 `raw/sources/` 到 `wiki/` 的过程必须变成一个可重复、可审计、可增量运行的编译流水线，而不是人工或 agent 临场写作。

两个参考项目均为 MIT License。若后续直接复制或改写其代码，应在 `THIRD_PARTY_NOTICES.md` 中保留 `kytmanov` 与 `atomicmemory` 的版权声明，并在被移植模块的文件头或模块文档里标注来源。由于 `llm-wiki-compiler` 是 TypeScript，而 ExpertWiki 是 Python，实际实现更适合按状态机、数据结构、产物契约和测试语义移植；`obsidian-llm-wiki-local` 同样是 Python，可以在结构化模型、SQLite 状态库、compile/review/query 流程上进行更直接的代码级参考。

## 当前 ExpertWiki 的替换边界

当前 ExpertWiki 的 `ingest` 只把本地文件包成 `type: raw_source` Markdown，并写入 `raw/sources/`。它没有概念抽取，没有 content hash 驱动的去重和增量判断，也没有把一个 raw source 拆成多个知识单元。这个部分应该保留“先保存原始来源”的行为，但要把 `ingest_source` 拆成两个阶段：第一阶段继续保存 raw source，第二阶段进入自动分析流水线，对 source body 进行 line numbering、hashing、chunking 和 structured extraction。

当前 ExpertWiki 的 `page create` 只生成一个带 TODO 的 wiki page 模板。这个命令可以继续作为人工作者的低层工具，但不再是主路径。主路径应该变成 `compile`：系统根据状态库中的 concept、alias、source references 和 source spans 自动生成或更新 wiki page 草稿。也就是说，`page create` 是手工 scaffold，`compile` 才是 AI second brain 的核心写作入口。

当前 `KnowledgeStore.search` 是简单 token overlap，`graph` 只有 page 到 source 的 citation edge。这个部分需要替换为两层查询。第一层是 index-based routing，照搬 `obsidian-llm-wiki-local` 的思路，由 fast model 先从 `wiki/index.md` 或扩展后的 page manifest 里选择少量候选页；第二层由 heavy model 读取候选页后生成 grounded answer。非 LLM 环境下可以保留 token search 作为 fallback，但不能把 fallback 包装成主要智能查询能力。

当前 `lint` 只检查 frontmatter、source references、index 和 Markdown links。改造后 lint 必须扩展为 compiler health checker，检查 draft 是否悬挂、source hash 是否 stale、concept-to-sources 是否丢失、wikilink 是否可解析、引用的 source line range 是否存在、published page 是否被人工改动但未重新入库、deleted source 是否导致 frozen concept，以及 rejected draft 是否被错误覆盖。

## 目标流水线

新的 ExpertWiki 主流水线应该是：本地文件先进入 `raw/sources/`，系统计算 source hash 并写入状态库；fast model 对 source body 做结构化抽取，产出 concepts、aliases、summary、suggested topics、named references、confidence、provenance state、contradictions 和 source spans；状态库把 source 与 concepts 连接起来，并维护 alias 到 canonical concept 的解析；compile 阶段从 concept 出发，收集所有贡献该 concept 的 source material，用 heavy model 生成单个 wiki article draft；review 阶段由用户 approve 或 reject；approve 后 draft 才移动到 `wiki/` 并更新 article content hash；query 阶段只读已发布的 wiki pages，而不是每次回到 raw sources 做临时 RAG。

这个目标流水线本质上把 ExpertWiki 从“Markdown 文件管理器”升级为“LLM Wiki 编译器”。raw source 是输入文件，state.sqlite 是编译状态，concept extraction 是 AST，wiki page draft 是 build artifact，review 是 release gate，published wiki 是稳定产物，index/graph/llms.txt 是面向 agent 的读取接口。这个模型应直接继承 `llm-wiki-compiler` 的增量编译思想：如果 source 没有变化，就不重复消耗模型；如果 source A 和 source B 共同贡献 concept X，那么 source A 改动时，concept X 必须用 A 与 B 的内容一起重编译，否则会丢失 B 的贡献。

## 数据模型契约

ExpertWiki 需要新增一个本地 SQLite 状态库，建议路径为 `<bundle>/.expertwiki/state.sqlite`。这个数据库不取代 Markdown 文件作为用户可读的 source of truth，而是作为 compiler state。它应该移植 `obsidian-llm-wiki-local` 的 StateDB 思路，并吸收 `llm-wiki-compiler` 的 source-state 与 dependency index。最小状态表应包括 sources、concepts、source_concepts、concept_aliases、articles、drafts、rejections、compile_runs 和 citation_spans。

`sources` 表记录 raw source 的相对路径、resource、publisher、content hash、body hash、line count、language、quality、status、ingested_at、analyzed_at 和 last_error。这里的 status 至少需要区分 preserved、analyzed、changed、deleted、failed 和 pending_review。现有 raw source Markdown frontmatter 也应该增加 `content_hash`、`body_hash`、`line_count`、`analyzed_at` 与 `analysis_status`，这样即使状态库损坏，Markdown 仍然保留基本可恢复信息。

`concepts` 表记录 canonical concept name、slug、summary、tags、confidence、provenance_state、status、article_path、draft_path、created_at 和 updated_at。concept 的 schema 应该以 `obsidian-llm-wiki-local` 的 `Concept` 和 `AnalysisResult` 为基础，同时吸收 `llm-wiki-compiler` 的 `confidence`、`provenance_state` 和 `contradicted_by` 字段。为了保证小模型稳定输出，LLM-facing schema 必须保持扁平，避免深层嵌套对象。复杂关系可以在 Python 侧由程序派生和合并。

`source_concepts` 表是关键依赖表，记录 source 与 concept 的多对多关系，并保存 source spans、extract summary、confidence 和 extraction hash。这个表就是 ExpertWiki 的 concept-to-sources 反向索引。任何 compile 操作都不能只从“最近变化的 source”生成页面，而必须通过这个表找到该 concept 的全部 contributor sources。这个行为应直接照搬 `llm-wiki-compiler` 的 shared-concept dependency 语义。

`concept_aliases` 表记录 alias、canonical concept、source path 和 observed_at。alias 解析应先查精确 alias，再查 canonical name，再查 slug。它服务三件事：ingest 阶段避免重复概念，compile 阶段向模型提供现有 page title 和 alias map，query 阶段允许用户用别名找到正确页面。

`articles` 表记录 published wiki page 的 canonical concept、relative path、content hash、source hashes、quality、status、compiled_at、approved_at 和 manual_edit_state。compile 前必须读取 on-disk Markdown body 并与数据库 content hash 比较；如果用户改过 published page，而本次没有 `--force`，系统必须像 `obsidian-llm-wiki-local` 一样跳过并标记 deferred_manual_edit，而不是覆盖用户内容。

`drafts` 与 `rejections` 表共同构成 review gate。每个 concept compile 结果先写入 `.expertwiki/drafts/<slug>.md`，并在 drafts 表记录 source set、prompt hash、model、created_at 和 status。用户 approve 后，draft 移动到正式 `wiki/` 路径并更新 articles；用户 reject 后，draft 删除或保留为 rejected artifact，同时 rejection feedback 写入 rejections 表。下一次 compile 同一 concept 时，prompt 必须注入最近几条 rejection feedback，避免模型重复生成用户已经否定的内容。

`citation_spans` 表记录 page paragraph 或 claim 到 source line range 的连接。这里应照搬 `llm-wiki-compiler` 的 line-range citation 契约，即 wiki 正文段落末尾使用 `^[filename.md:START-END]` 或多来源形式。ExpertWiki 的 raw source 在进入分析前应生成稳定行号视图，compile prompt 中给模型提供 numbered source material。lint 后续必须验证这些 line ranges 是否存在，并统计 uncited inferred paragraphs。

## Markdown 产物契约

ExpertWiki 现有 `raw/sources/*.md` 保留，但 frontmatter 要升级。每个 raw source 必须包含 `type: raw_source`、`title`、`resource`、`publisher`、`retrieved_at`、`source_kind`、`content_hash`、`body_hash`、`line_count`、`analysis_status`、`analyzed_at` 和 `language`。正文仍保留原始内容，不应被模型改写。若后续支持 PDF、HTML、transcript 等格式，也应先转为可审计 Markdown source record，而不是直接生成 wiki page。

ExpertWiki 的 published wiki page 仍使用 `type: wiki_page`，但 frontmatter 要变成 compiler-aware。每个页面至少应包含 `entity_type`、`title`、`aliases`、`description`、`tags`、`sources`、`source_hashes`、`status`、`quality`、`confidence`、`provenance_state`、`compiled_at`、`approved_at`、`content_hash`、`generator` 和 `last_reviewed_at`。`sources` 继续使用当前的 raw source path list，`source_hashes` 用于判断该页面是否由过期 source 编译而来。

正文结构不应该完全交给模型自由发挥。为了延续 ExpertWiki 的定位，默认页面仍应有 `Context`、`Facts`、`Human Feedback`、`Experience Rules`、`Counterexamples and Risks`、`Confidence` 和 `Sources`。不过 compile prompt 需要允许不同 `entity_type` 有不同 section profile，例如 expert page、project page、topic page、comparison page 和 synthesis page。section profile 可以来自 `llm-wiki-compiler` 的 schema/profile 思路，但首版只需要内置几种 ExpertWiki 页面类型，不需要做完整用户可配置 schema。

Draft 产物必须放在 `.expertwiki/drafts/`，并保持与正式 wiki page 相同的 frontmatter 加一个 `draft_status: pending_review`。review candidate 不应该污染正式 `wiki/index.md`；`expertwiki review` 直接从 SQLite 与该目录读取候选。approve 前，query 默认不读取 draft。

Query synthesis 可以写入 `wiki/synthesis/` 或新增 `wiki/queries/`。这里应参考 `obsidian-llm-wiki-local` 的 query pipeline：fast model 选页，heavy model 回答，用户可选择保存为 synthesis。保存 synthesis 时必须有 duplicate strategy 和 manual edit conflict detection，避免同一问题被反复写成多个浅页面。

## Ingest 设计

新的 `ingest` 不应该立即生成 wiki pages。它应该先保存 raw source，然后执行 analysis。analysis 使用 fast model 和扁平 schema。对短文档，直接把 body 放入 prompt；对长文档，按 fast context 的安全比例切 chunk，不需要 overlap，分别抽取后合并。合并逻辑应照搬 `obsidian-llm-wiki-local`：concept 按 canonical name case-insensitive 去重，aliases 合并，suggested topics 去重，named references 去重，summary 使用第一块或最高质量块，quality 取保守最低值，language 取第一个可信值。

analysis prompt 必须明确要求 3 到 8 个值得建页的 standalone concepts，禁止 trivial details，要求 alias 是作者真实使用过的 surface forms，要求 named references 是从原文复制的专名，不能翻译、不能推断。这个 prompt 应把现有 wiki index 或 concept alias list 作为去重上下文，直接继承 `llm-wiki-compiler` 避免重复 concepts 的策略。

analysis 输出入库后，系统应更新 source status 为 analyzed，并把每个 concept 关联到该 source。对于已有 alias 或 canonical concept，系统应合并到既有 concept；对于新 concept，生成 slug 但不立即发布页面。若 LLM 输出不合法，状态库记录 failed 和 error，raw source 仍保留。失败不应破坏已有 wiki。

## Compile 设计

新的 `compile` 应以 concept 为单位，而不是以 source 为单位。它首先从状态库找出 needing compile 的 concepts。一个 concept 需要 compile 的条件包括：有新 analyzed source，source hash 改变，published article 的 source_hashes 过期，draft 被 reject 后需要重试，或者该 concept 是由 broken wikilink 生成的 stub。这个判定应直接参考 `obsidian-llm-wiki-local` 的 `concepts_needing_compile` 和 `compile_concepts`。

对每个 concept，compile 必须通过 `source_concepts` 找到全部 contributor sources，并在 context budget 内装配 source material。装配时应提供 numbered source lines、source title、source path、source quality、existing page excerpt、known wiki titles、aliases、vault schema 和 rejection history。heavy model 只负责为一个 concept 生成一个 `SingleArticle` 风格的结果：title、markdown content、tags。confidence、wikilinks 清洗、frontmatter、content hash、source_hashes 和 citation validation 由程序生成，不能完全信任模型。

compile 输出必须先写 draft，不直接覆盖 published wiki。若 `.expertwiki/drafts/<slug>.md` 已存在且没有 `--force`，系统应跳过并标记 deferred_draft。若正式 page 存在且 on-disk content hash 与 articles 表不一致，系统应跳过并标记 deferred_manual_edit。这个手动编辑保护是必须照搬的行为，因为 ExpertWiki 的核心价值之一是用户拥有本地 Markdown。

compile 对 context overflow 的处理应照搬 `obsidian-llm-wiki-local` 的降级思想：先缩小 source budget，再缩小 existing content 和 related page budget，最后仍失败就记录 failed，不写半成品。不能在模型失败时写一个看似成功的空泛页面。ExpertWiki 的失败策略应该是 fail visible，而不是 fallback prose。

## 增量编译与删除语义

ExpertWiki 需要引入 `detect_changes`。每次 compile 前，系统扫描 `raw/sources/`，对比状态库里的 content hash，把 source 标记为 new、changed、unchanged 或 deleted。new 和 changed source 进入 extraction；unchanged source 默认跳过。这个规则来自 `llm-wiki-compiler` 的 compile pipeline。

仅检测直接 changed source 还不够。必须维护 concept-to-sources 反向依赖。如果 changed source A 与 unchanged source B 都贡献了 concept X，那么 B 也要作为 affected source 加入本次 compile 的 context。否则 concept X 会被重新写成只包含 A 的版本，丢失 B 的知识。这个 shared-concept dependency 是整个自动化 second brain 的关键正确性约束。

deleted source 的语义更谨慎。如果某个 concept 只由 deleted source 拥有，可以把对应 page 标记为 orphaned 或 stale；如果 deleted source 与其他 source 共同贡献该 concept，则该 concept slug 应 frozen，不能立刻用剩余 source 重写页面。这个规则也来自 `llm-wiki-compiler`，目的是防止删除一个 source 后静默丢失历史综合内容。

状态写入应采用 lock 和 journal。compile 开始时获取 bundle lock，所有中间状态写入 draft state，只有 link resolution、page write、index rebuild 全部成功后才 flush durable state。首版可以用简单 `.expertwiki/compile.lock` 加 SQLite transaction；后续再引入更完整 journal。原则是不能出现 page 已写入但 state 没更新，或 state 标记已编译但 page 写失败的半提交状态。

## Review 设计

ExpertWiki 需要新增 review 命令组：`expertwiki review list`、`expertwiki review show <draft>`、`expertwiki review approve <draft>` 和 `expertwiki review reject <draft> --feedback "<text>"`。approve 把 draft 移动到正式 wiki path，更新 articles、source compile state、content_hash、approved_at 和 log。reject 删除或归档 draft，写入 rejections，并把 concept 标记为 pending_retry 或 rejected。

review 不只是人工确认页面质量，也是模型反馈闭环。下一次 compile 同一 concept 时，prompt 必须包含最近几条 rejection feedback。这个设计直接参考 `obsidian-llm-wiki-local`。如果某个 concept 连续被 reject 达到阈值，系统应停止自动重试，要求用户手动处理或 `--force`。

review mode 还应该支持 `compile --review`，即只写 candidates，不改变 published wiki 和 source compiled marker。这个行为对应 `llm-wiki-compiler` 的 review queue 设计，可以让用户安全试跑大批量来源，确认候选页后再 approve。

## Link、Index 与 Graph 设计

ExpertWiki 的 link resolution 应从 Markdown 正文中解析 `[[wikilinks]]` 和普通 Markdown links，并用 title、slug、alias map 解析目标。模型可以建议 wikilinks，但程序必须清洗未知链接，避免生成不存在页面的幻觉链接。若 unknown wikilink 有价值，可以生成 stub concept，而不是直接保留坏链接。

`index.md` 不应该只是目录表。compile 后应生成 page manifest，包含 title、aliases、description、tags、entity_type、quality、confidence、sources 和 updated_at。query router 会优先读这个 index。这个思路来自 `obsidian-llm-wiki-local` 的 index routing，也符合 ExpertWiki 面向 agent 的读取方式。

`graph` 需要从现在的 citation graph 扩展成 knowledge graph。节点包括 sources、concepts、wiki pages、aliases 和 optionally named references。边包括 cites、mentions、wikilinks_to、alias_of、contradicts、derived_from、supersedes 和 orphaned_from。首版最重要的是 page-to-page wikilinks 与 page-to-source citations；后续再加入 contradiction 和 named reference graph。

## Query 设计

新的 query pipeline 应照搬 `obsidian-llm-wiki-local` 的“index-based routing -> grounded answer”。第一步读取 wiki index 或 manifest；第二步 fast model 选择 1 到 5 个页面；第三步加载这些页面正文；第四步 heavy model 使用页面内容回答，并且只能使用已存在页面的 wikilinks；第五步可选保存为 synthesis 或 query note。

query 默认只能读 published wiki，不读 raw sources。这个边界保留 ExpertWiki 现有产品承诺：raw source 是证据库，wiki 是综合知识层。如果 query 找不到支持页面，系统应该说 wiki layer 没有证据，而不是临时挖 raw source 生成答案。只有当用户显式要求 `ingest/compile` 时，raw source 才进入知识层。

保存 synthesis 时，需要 duplicate detection 和 manual edit protection。可以用 question hash、selected pages、answer content hash 建立 synthesis record。如果同一问题已存在 synthesis，默认返回 existing；若用户指定 update，则读取现有内容、检查 manual edit hash，再生成更新 draft。

## CLI 替换计划

ExpertWiki 的 CLI 应保留现有命令，但主路径要扩展。`expertwiki ingest` 默认仍保存 raw source，但新增 `--analyze` 或配置默认开启 analysis。`expertwiki analyze` 可以单独重跑 source extraction。`expertwiki compile` 负责 concept-driven draft generation。`expertwiki review` 负责 approve/reject。`expertwiki query` 默认继续返回检索结果；新增 `expertwiki ask` 或 `expertwiki query --answer` 运行 LLM grounded answer。`expertwiki index`、`lint`、`audit` 和 `package --dry-run` 都要理解新状态库和 drafts。

为了避免一次性破坏现有用户，旧 `page create` 和旧 token search 保持可用，并标记为 manual authoring path。默认自动化不再由 CLI 隐式选择 provider，而是由调用 ExpertWiki Skill 的宿主 AI 通过 SQLite job protocol 执行：CLI 产生带输入哈希和产物 schema 的任务，宿主 AI 读取本地文件并提交 JSON，CLI 校验后写草稿。可配置 LLM provider 只保留为用户显式选择的 `--backend api` 无人值守路径。

## 模块替换计划

新增 `src/expertwiki/state.py`，直接承担 SQLite schema、migration、source hash、concept alias、article hash、draft/rejection 记录。这个模块应参考 `obsidian-llm-wiki-local` 的 StateDB，避免把状态散落在 Markdown frontmatter 中。

`src/expertwiki/agent_jobs.py` 定义宿主 AI 的 structured job request/response、领取、提交、失败、重试和 stale-input 校验；`src/expertwiki/llm.py` 保留 LLMClientProtocol 与 OpenAI-compatible adapter，作为显式 API backend。两者都不能污染 authoring/store/lint 的纯文件逻辑。

新增 `src/expertwiki/pipeline/ingest.py`，承接 raw source analysis、chunking、structured extraction、merge chunk results 和 state update。现有 `authoring.ingest_source` 只保留 source preservation，然后调用 pipeline 或返回可分析状态。

新增 `src/expertwiki/pipeline/compile.py`，承接 concept-driven compile、context assembly、manual edit protection、draft write、compile state update 和 failure categorization。这个模块是 `obsidian-llm-wiki-local` compile_concepts 的 ExpertWiki 版本。

新增 `src/expertwiki/pipeline/deps.py`，承接 `llm-wiki-compiler` 的 dependency tracking：build concept-to-sources map、find affected sources、find frozen slugs、orphan deleted-source pages。这个模块可以从 TypeScript 逻辑逐段移植为 Python。

新增 `src/expertwiki/pipeline/review.py`，承接 draft list/show/approve/reject。approve 要同时写 Markdown、state、index 和 log；reject 要保留 feedback 给下一次 prompt。

新增 `src/expertwiki/pipeline/query.py`，替代当前只有 token overlap 的 query 主路径。当前 `KnowledgeStore.search` 可保留为 fallback 和 API search，LLM answer 放到新的 query pipeline。

扩展 `src/expertwiki/linting.py`，加入 state-aware lint。扩展 `src/expertwiki/store.py`，让 graph 包含 wikilinks、concepts、aliases 和 source spans。扩展 `src/expertwiki/server.py`，增加 `/ask`、`/drafts`、`/concepts` 或只先暴露 `/graph` 的增强结果。

## 开发顺序

第一步应先做状态库和迁移，不接 LLM。实现 `state.py`、SQLite schema、migration、source hash、load existing bundle into state，并给现有样例 bundle 写测试。完成后，当前 3 个 raw source 和 6 个 wiki page 应能被导入 state，lint 仍为零问题。

第二步做 structured extraction 的数据模型和 mock LLM 测试。先把 `Concept`、`AnalysisResult`、`ExtractedConcept`、`SingleArticle` 等模型落到 Python，测试 chunk merge、alias merge、quality conservative merge、invalid JSON retry 和 failed state。此阶段可以用 fake client，不依赖真实模型。

第三步做 `analyze`。默认路径把 raw source 路径、哈希、行数、已有 concepts 和严格输出 schema 写成宿主 AI 任务；宿主 AI 返回的 JSON 经校验后写入 sources、concepts、source_concepts、aliases。API backend 仍可调用 fast model。验收标准是一篇 raw source 可以产生多个 concepts，同名 concept 可以合并 aliases，重复运行不会重复入库，source hash 不变时不会重跑。

第四步做 `compile` 到 draft。它按 concept 聚合所有 contributor sources，构造 heavy prompt，写 `.expertwiki/drafts/<slug>.md`，并记录 draft state。验收标准是不会覆盖 published page，不会覆盖 existing draft，manual edit hash 冲突会 deferred，context overflow 会 failed visible。

第五步做 review approve/reject。approve 后正式 wiki page 出现，index 重建，articles 表更新，query/search 可见。reject 后 draft 不发布，feedback 入库，下一次 compile prompt 能看到 feedback。

第六步做 `detect_changes` 与 dependency compile。实现 source hash 扫描、new/changed/deleted buckets、affected sources、frozen slugs 和 orphan marking。验收标准是两个 source 共享同一 concept 时，任一 source 改动都会让该 concept 用两个 source 一起重编译；删除共享 source 不会静默覆盖综合页。

第七步做 query pipeline。先实现 index routing 和 page loading，再接 heavy answer，再做 optional synthesis save。验收标准是 query 不读 raw source，只读 selected wiki pages；回答中的 wikilinks 只能指向已存在页面；保存 synthesis 有 duplicate protection。

第八步扩展 lint/audit/API。lint 必须识别 stale page、broken citation line range、unknown wikilink、dangling draft、source-state mismatch 和 orphan/frozen 状态。audit 应输出 compiler health summary。API 的 graph 应暴露新边类型。

## 测试策略

测试应先围绕状态机，而不是模型质量。宿主路径直接提交固定 structured objects，API 路径通过 fake client 返回相同对象。需要覆盖任务领取/提交/失败/重试、stale input rejection、raw source 首次 ingest、重复 ingest、source changed、source deleted、shared concept affected compile、manual edit protection、draft approve、draft reject with feedback、line citation lint、query page selection 和 synthesis duplicate detection。

端到端测试应使用一个小 bundle：两个 raw sources 共同提到同一 concept，另一个 source 提到独立 concept。测试先 analyze 三个 source，再 compile 生成两个 draft，approve 一个，reject 一个，然后修改其中一个共享 source，确认 affected source 被带入重编译 context。这个测试直接证明 ExpertWiki 已经具备 second brain compiler 的核心正确性。

真实模型测试不应进入默认 CI。宿主 AI 的真实能力由 Skill 端到端人工 smoke test 覆盖；API backend 可以用 `EXPERTWIKI_LLM_TEST=1` 连接本地 Ollama 或 OpenAI-compatible endpoint。CI 默认只验证任务和产物契约，保持快速和稳定。

## 迁移策略

现有 bundle 不应该被破坏。首次运行新版本时，系统扫描 `raw/sources/` 和 `wiki/`，计算 hash，导入 state。已有 wiki pages 标记为 imported_published，content_hash 来自当前正文，source_hashes 尽可能从 frontmatter sources 反查。因为旧页面没有 extraction state，首轮 compile 不应自动覆盖它们；只有用户显式运行 `analyze --all` 和 `compile --force`，才允许把旧页面纳入新 compiler 管理。

样例 bundle `bundles/expertwiki-ai-agent-engineering` 可作为迁移验收对象。迁移完成后，它应继续保持 status ok 和 lint zero，同时 state 中能看到 3 个 raw sources、6 个 imported pages 和 0 个 pending drafts。之后再用 analyze/compile 生成新 draft，不直接覆盖已有手写页面。

## 不做的事情

首版不做 hosted SaaS，不做云端同步，不做专家认领，不做复杂权限，不做多用户协作，也不做全格式 ingestion。PDF、HTML、YouTube、image/audio/video 都可以后置。现在最重要的是复制两个参考项目已经验证过的 compiler loop：structured extraction、stateful dependency tracking、concept-driven draft generation、review gate、incremental rebuild 和 grounded query。

也不应该把 embedding 作为核心依赖。`llm-wiki-compiler` 把 semantic retrieval 作为 fallback enhancement，而不是 compile 正确性的根基。ExpertWiki 首版应先依赖 index routing、alias map、wikilink graph 和 source-state；embedding 可以后续作为 search enhancement，失败时只给 warning，不影响 compile。

## 最终判断

ExpertWiki 当前的优势是文件契约清楚、source preservation 正确、local-first 边界明确。它缺的不是更多页面模板，而是自动化 compiler。下一阶段应明确抛弃“主要靠外部 agent 临时写卡片”的路线，把 `obsidian-llm-wiki-local` 的本地 CLI 状态机和 `llm-wiki-compiler` 的增量编译工程化完整移植进来。完成这个替换后，ExpertWiki 才会从 source-backed Markdown bundle 变成真正的 interlinked AI second brain。
