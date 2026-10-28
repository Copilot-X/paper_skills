# 《VeriHarness: Scaling Agentic Verification for Long-Horizon Tasks》复现配置核查：先复现 select 主表，再与我的长程降幻觉方法对比

> 材料：`veriharness_2610.00972v1.pdf`，28 页（正文 p.1-12 / 参考文献 p.12-17 / 附录 A–K p.18-28），提取状态 ok，无截断告警；
> 核查表 81 行覆盖 26/26 项：已报告 61 / 部分 10 / 未报告（原文缺失）9 / 前后不一致 1 / 不适用 0 / 不在材料中 0；门禁检查 problems = 0。

## 0. 结论先行

- **复现就绪度**：补齐 high 缺口后可复现。high 缺口共 12 行，其中必须靠仓库或作者才能补的是提示词与技能正文、验证阶段解码参数、agent 步数与超时、基线实现这 4 类（5 行）；其余 7 行可以用已发布 rollout 池与"以池为准"的口径规避或降级。
- **阻断复现的前 3 项**：
  1. 提示词与技能正文在材料中缺失：原文称技能库与工具"在附录 H 全文给出"，但附录 H（p.23-25）只有组件表、使用率图和 18 个技能的名称与脚本名 [P3, p.5]；三段提示（resolver / challenger / adjudication）与技能文本全文在材料中没有 [P3b]。
  2. 解码与运行上限在材料中缺失：除 thinking level = high 外，temperature、top-p、max tokens、上下文窗口、agent 最大步数/超时都没有 [M2, p.20][M2c][M3]。
  3. benchmark 内容不随发布提供：作者只发布 rollout 池（轨迹+交付文件+grader 分数），任务、输入工作区、rubric、参考答案都需回到原基准自取，而这些基准是否可公开下载、是否需要申请，论文没有交代 [D4, p.22][D4b]。
- **第一步做什么**：先不花 API 钱。下载已发布的 rollout 池，用它复算 Table 2 里"不依赖模型"的两行——single rollout（Flash 47.2 / Opus 49.6）与 selection oracle（Flash 62.7 / Opus 63.1）[T1i, p.8][T1j, p.8][T1g, p.8][T1h, p.8]。这两行对上了，才说明池、任务 id 映射和评分口径都能对齐；对不上，后面花的钱全是噪音。

## 1. 要复现的目标

主结果是 Table 2 的 select 行（p.8）：VeriHarness(select) 五基准均值 51.6（Gemini 3.5 Flash）与 53.7（Claude Opus 4.8），相对 single rollout 分别 +4.4 与 +4.1 [T1, p.8][T1b, p.8][T1e, p.8][T1f, p.8]。分基准看：Flash 为 APEX 53.3±1.2、WSB 62.0±0.9、WorkBuddy 77.8±1.4、SB-2 31.5±2.4、JobBench 33.5±1.8；Opus 为 41.2±0.7、65.0±0.5、83.0±0.4、33.4±1.2、46.1±0.8。带 revision 的完整版是另一套数（Flash 53.4 / Opus 56.1），**不要和 select 行混用** [T1c, p.8][T1d, p.8]。

复现判据的分母也在表里：selection oracle（在该池内取 grader 最高的一条）为 Flash 62.7 / Opus 63.1 [T1g, p.8][T1h, p.8]。只盯 51.6 这个绝对值意义不大，因为它随任务难度浮动；更有意义的是"相对池均值的增益"和"占 oracle 上限的比例"。

关键消融（Table 4，p.23，注意它是 **revision 模式**下的分数）告诉我们哪个设置最不能错：Opus 去掉 challenger（只留 resolver）为 54.3，去掉 resolver（只留 challenger）为 52.6，完整 56.1 [T2b, p.23]；也就是说 resolver 承载的增益更大，两个上下文合并成单上下文损失 0.8（Opus 55.3）[T2c, p.23]；去掉技能库降到 53.8（Opus）/ 51.3（Flash）[T2, p.23]。按池熵分组看，增益几乎全部来自分歧池：154 个 consensus 池只高 0.6 分，262 个 disputed 池高 6.1 分 [T2d, p.10]。**这意味着子集若偏向"大家答案一致"的任务，复现会看不到增益**，选子集时必须先算池熵分布。

## 2. 配置总表（26 项，81 行）

| ID | 项目 | 状态 | 论文给出的值 | 出处 | 复现还缺什么 | 影响 |
|---|---|---|---|---|---|---|
| M1 | 被测/主模型 | 部分 | Gemini 3.5 Flash；Claude Opus 4.8（同一模型既当 generator 又当 verifier） | [M1, p.7] | 未给两家的 API 版本号/快照日期与调用时间窗；只有市场版本名，模型迭代后无法重取同一权重 | high |
| M2 | 解码参数 | 已报告 | 生成与验证统一 thinking level = high | [M2, p.20] | — | high |
| M2b | 解码参数 | 已报告 | temperature zero（仅用于 claim 统计那张图，不是验证阶段） | [M2b, p.19] | — | low |
| M2c | 解码参数 | 未报告（原文缺失） | — | [M2c]，已查页见 audit.jsonl | 验证各阶段（resolver / challenger / adjudication）的 temperature、top-p、采样条数都没给；thinking level 之外无任何解码参数 | high |
| M3 | 长度与步数上限 | 未报告（原文缺失） | — | [M3]，已查页见 audit.jsonl | max output tokens、上下文窗口、agent 最大步数/轮数、单任务超时与重试策略全都没有给出（原文缺失） | high |
| M3b | 长度与步数上限 | 部分 | 自演化候选库中的技能脚本有 ten-minute 执行上限 | [M3b, p.26] | 该上限只约束技能脚本，不是验证 agent 的每任务超时或最大工具调用数 | low |
| M4 | 辅助模型 | 已报告 | APEX-Agents 与 JobBench 的 rubric 逐项由 Gemini 3 Flash 判分 | [M4, p.21] | — | high |
| M4b | 辅助模型 | 已报告 | Workspace-Bench Lite：benchmark 自带 agent-as-a-judge，Claude Code + Claude Opus 4.8 | [M4b, p.21] | — | high |
| M4c | 辅助模型 | 已报告 | WorkBuddy Bench：composite verifier，code 域用测试与规则，office 域用规则 + Gemini 3.5 Flash 判官 | [M4c, p.21] | — | medium |
| M4d | 辅助模型 | 已报告 | SpreadsheetBench 2：重算交付工作簿并逐格比对，无 LLM 判官 | [M4d, p.21] | — | medium |
| D1 | 基准/数据集 | 已报告 | APEX-Agents v1.0，480 任务；artifact 为 memo/model/answer；expert rubric 评分 | [D1, p.7] | — | high |
| D1b | 基准/数据集 | 已报告 | Workspace-Bench Lite：100 任务 Lite 子集 | [D1b, p.20] | — | high |
| D1c | 基准/数据集 | 已报告 | WorkBuddy Bench：code 80、office 50、web 70（不含 security 域） | [D1c, p.20] | — | medium |
| D1d | 基准/数据集 | 已报告 | SpreadsheetBench 2：321 任务，recompute + compare 评分 | [D1d, p.7] | — | high |
| D1e | 基准/数据集 | 已报告 | JobBench，65 任务、覆盖 35 个白领职业；rubric judge 评分 | [D1e, p.7] | — | high |
| D2 | 实际子集 | 已报告 | 每任务每模型 N = 10 条 rollout，五种方法共用同一冻结池 | [D2, p.7] | — | high |
| D2b | 实际子集 | 已报告 | 自演化实验：dev/held-out 约 75% / 25%（正文另述约 three:one） | [D2b, p.26] | — | medium |
| D2c | 实际子集 | 前后不一致 | APEX-Agents 任务数 480（正文主表）vs 434（附录 A 的 claim 分析） | [D2c, p.7]；另见 p.19 | 两处任务数不一致；正文 p.10 又给出 154 个 consensus pool 与 262 个 disputed pool（合计 416）。到底用 480/434/416 中的哪个子集做 APEX 主结果，原文未说明（原文缺失） | high |
| D2d | 实际子集 | 已报告 | claim 级统计：917 个 consensus claim 与 775 个 disputed claim | [D2d, p.19] | — | medium |
| D2e | 实际子集 | 未报告（原文缺失） | — | [D2e]，已查页见 audit.jsonl | 自演化划分所用的固定 seed 数值未给；哪 480/434/416 个 APEX 任务进入 pool 的入选规则也未给 | medium |
| D3 | 过滤与排除 | 已报告 | 不跑 WorkBuddy 的 security 域（任务会触发 API 安全告警） | [D3, p.20] | — | medium |
| D3b | 过滤与排除 | 已报告 | 自演化实验：APEX 排除 file-deliverable 任务；SB-2 只取 template 与 financial-model 任务 | [D3b, p.26] | — | medium |
| D3c | 过滤与排除 | 未报告（原文缺失） | — | [D3c]，已查页见 audit.jsonl | 失败 rollout 与不可解任务如何计入未写：是否重跑、全部失败的池如何进入均值、是否有去重（原文缺失） | medium |
| D4 | 数据可得性 | 已报告 | rollout 池公开；但 benchmark 内容（任务、输入 workspace、rubric、参考答案）不随发布提供 | [D4, p.22] | — | high |
| D4b | 数据可得性 | 部分 | 输入需从各 benchmark 原始出处获取（每条 rollout 带官方 task id） | [D4b, p.22] | 五个 benchmark 各自的获取方式、许可与是否 gated 未在原文说明；APEX-Agents 等能否公开下载需自行确认 | high |
| P1 | 方法流程 | 已报告 | 流程：暴露 workspace → 并发开两个互不可见的上下文（resolver / challenger）→ 各写证据记录 → 新上下文 adjudication → delivery | [P1, p.20] | — | high |
| P1b | 方法流程 | 已报告 | adjudication 在独立上下文读两份证据记录，不继承调查者的对话历史 | [P1b, p.6] | — | high |
| P1c | 方法流程 | 已报告 | training-free、plug-and-play，不训练也不改权重 | [P1c, p.3] | — | high |
| P1d | 方法流程 | 已报告 | select-only 评估下返回被裁决的 base，原样不改 | [P1d, p.6] | — | high |
| P2 | 方法超参 | 部分 | 停止准则为定性判断：证据定案即关闭 claim，判断再查也不会改变结论时停止 | [P2, p.5] | 没有最大检查次数、置信阈值或步数预算，停止点完全由模型判断，复现时不同实现的最长/最短搜索会差很远 | high |
| P2b | 方法超参 | 已报告 | 自演化每轮生成 K=3 个候选库、后期 K=5；脚本 ten-minute 上限 | [P2b, p.26] | — | low |
| P2c | 方法超参 | 已报告 | 自演化轮数：C 十轮、D 八轮，轮数在看 held-out 轨迹前固定 | [P2c, p.26] | — | low |
| P3 | 提示词 | 部分 | 原文声称技能库与工具在附录 H 全文给出 | [P3, p.5] | 附录 H（p.23-25）实际只有 Table 5 的组件表、Figure 7 的使用率、Table 6 的 18 个技能名称与脚本名，没有提示词、技能正文或系统消息；与 p.5 的声称不符 | high |
| P3b | 提示词 | 未报告（原文缺失） | — | [P3b]，已查页见 audit.jsonl | 系统提示、任务提示、resolver/challenger/adjudication 三段提示全文、18 个技能文本正文与脚本内容，材料中都没有 | high |
| P4 | 运行环境与工具 | 已报告 | runtime 为开源 pi coding agent（MIT）的薄层；Claude 经本地 LiteLLM 代理 | [P4, p.21] | — | high |
| P4b | 运行环境与工具 | 已报告 | 验证器只有读取、检索、shell 三类工具 | [P4b, p.21] | — | high |
| P4c | 运行环境与工具 | 已报告 | 沙箱：rollout、任务输入与环境只读挂载，无网络；仅输出目录可写 | [P4c, p.21] | — | high |
| P4d | 运行环境与工具 | 部分 | 生成侧 scaffold：APEX-Agents runner + 工具服务；JobBench 用 opencode；SB-2 用自带 agent；WorkBuddy 与 WSB 用 Claude Code | [P4d, p.20] | 四个 scaffold 的版本/commit 与各自系统提示未给；rollout 生成端的细节只能靠已发布池绕过 | high |
| P4e | 运行环境与工具 | 部分 | pi coding agent（MIT） | [P4e, p.21] | pi 的版本号或 commit 未给；agent loop 与工具调用的具体实现随版本变化 | medium |
| P5 | 基线配置 | 部分 | LLM-as-a-Verifier 基线：按标准拆分任务、逐标准两两比较排序 | [P5, p.21] | 各基线的提示词、调用次数与实现代码均未给，只能按被引论文自行重写；majority voting 与 tournament 的具体判定规则也未给 | high |
| P5b | 基线配置 | 已报告 | LLM-as-a-Verifier 每次比较 four evaluations | [P5b, p.27] | — | medium |
| P6 | 对照公平性 | 已报告 | 所有方法用同一冻结池，验证前冻结 | [P6, p.21] | — | high |
| P6b | 对照公平性 | 已报告 | 同 N = 10 池、同模型；single rollout 取池均值 | [P6b, p.21] | — | high |
| P6c | 对照公平性 | 部分 | 对照按生成成本对齐（同样 ten rollouts） | [P6c, p.12] | 验证侧算力未对齐：p.27 显示各法每任务验证成本相差约一个量级，故“同预算”只对候选池成立，不对验证调用量成立 | medium |
| E1 | 指标与计分 | 已报告 | 各基准原生尺度：APEX 任务成功率；JobBench 与 WSB 的 rubric 均分；WorkBuddy 三域 task-weighted 均值；SB-2 headline accuracy | [E1, p.21] | — | high |
| E1b | 指标与计分 | 已报告 | single rollout = 池均值；oracle 为固定池期望，无需重采样 | [E1b, p.21] | — | high |
| E1c | 指标与计分 | 已报告 | 主表比较的是“选择已有 rollout”，不含重写 | [E1c, p.21] | — | high |
| E2 | 评分者与可靠性 | 已报告 | 用各 benchmark 自带 grader 评分，verifier 全程不可见 | [E2, p.21] | — | high |
| E2b | 评分者与可靠性 | 部分 | 判官模型与基线在同一轮打分，用同轮差值控制 drift | [E2b, p.21] | 判官可靠性与同源性未评估：WSB 用 Opus 4.8 判 Opus 4.8 的输出，人评一致率、kappa、标注样本量都没给 | high |
| E2c | 评分者与可靠性 | 已报告 | 报告归档基线分 + 同轮差值 | [E2c, p.21] | — | medium |
| E3 | 重复与方差 | 已报告 | three-seed 均值，附跨 seed 标准差（主表 ± 值） | [E3, p.8] | — | high |
| E3b | 重复与方差 | 未报告（原文缺失） | — | [E3b]，已查页见 audit.jsonl | 三个 seed 的具体数值、每个 seed 的 verifier 采样种子、任务级方差与置信区间都未给；single rollout 行没有 ± | medium |
| E4 | 显著性检验 | 未报告（原文缺失） | — | [E4]，已查页见 audit.jsonl | 全文没有显著性检验（无 t-test、bootstrap、permutation、McNemar），只有“gains more than the cross-seed spread”这类定性说法 | medium |
| R1 | 算力 | 未报告（原文缺失） | — | [R1]，已查页见 audit.jsonl | 没有 GPU/CPU 规格、节点数，也没有“仅调用 API”的显式声明；无法据此估算复现算力 | medium |
| R2 | 成本与耗时 | 已报告 | Gemini 3.5 Flash：selection 每任务 $1.44（为 LLM-as-a-Verifier 的十分之一） | [R2, p.27] | — | high |
| R2b | 成本与耗时 | 已报告 | Claude Opus 4.8：selection 每任务 $3.92 | [R2b, p.27] | — | high |
| R2c | 成本与耗时 | 已报告 | revision 成本约为 selection 的 three 倍 | [R2c, p.27] | — | high |
| R2d | 成本与耗时 | 已报告 | 86–91% 输入 token 走 cache | [R2d, p.27] | — | high |
| R2e | 成本与耗时 | 已报告 | 整池约 26,000 条 rollout，生成成本超过 $100,000 | [R2e, p.1] | — | high |
| R3 | 软件与时间 | 已报告 | CLI 版本：Gemini CLI 0.46.0、Claude Code 2.1.246、Codex 0.149.1 | [R3, p.21] | — | medium |
| R3b | 软件与时间 | 未报告（原文缺失） | — | [R3b]，已查页见 audit.jsonl | API 调用日期区间与模型快照、Python/依赖库版本（pi、LiteLLM、判官侧依赖）都未给；闭源模型会随时间漂移 | high |
| A1 | 代码 | 已报告 | https://github.com/google-research/veriharness（许可证未在原文说明） | [A1, p.22] | 仓库许可证、可运行范围（是否含提示词与技能）需要打开仓库确认 | high |
| A2 | 数据/轨迹/输出 | 已报告 | HuggingFace 数据集 caiqizh/veriharness：每条 rollout 含 trajectory、交付文件与 grader 分数 | [A2, p.22] | — | high |
| T1 | 主结果 | 已报告 | Flash select：Avg 51.6；APEX 53.3±1.2；WSB 62.0±0.9；WorkBuddy 77.8±1.4；Spreadsheet 31.5±2.4；JobBench 33.5±1.8 | [T1, p.8] | — | high |
| T1b | 主结果 | 已报告 | Opus select：Avg 53.7；APEX 41.2±0.7；WSB 65.0±0.5；WorkBuddy 83.0±0.4；Spreadsheet 33.4±1.2；JobBench 46.1±0.8 | [T1b, p.8] | — | high |
| T1g | 主结果 | 已报告 | Flash 的 selection oracle：Avg 62.7；APEX 67.3；WSB 70.3；WorkBuddy 87.7；Spreadsheet 37.4；JobBench 51.0 | [T1g, p.8] | — | high |
| T1h | 主结果 | 已报告 | Opus 的 selection oracle：Avg 63.1；APEX 53.8；WSB 72.4；WorkBuddy 89.4；Spreadsheet 39.6；JobBench 60.4 | [T1h, p.8] | — | high |
| T1i | 主结果 | 已报告 | Flash 的 single rollout（池均值）：Avg 47.2；APEX 48.1；WSB 56.5；WorkBuddy 73.2；Spreadsheet 27.3；JobBench 30.9 | [T1i, p.8] | — | high |
| T1j | 主结果 | 已报告 | Opus 的 single rollout（池均值）：Avg 49.6；APEX 35.8；WSB 60.5；WorkBuddy 79.0；Spreadsheet 30.1；JobBench 42.8 | [T1j, p.8] | — | high |
| T1c | 主结果 | 已报告 | Flash + revision：Avg 53.4；APEX 54.8±1.0；WSB 65.4±1.0；WorkBuddy 78.2±0.2；Spreadsheet 32.2±0.6；JobBench 36.2±1.1 | [T1c, p.8] | — | high |
| T1d | 主结果 | 已报告 | Opus + revision：Avg 56.1；APEX 47.5±0.2；WSB 67.3±0.2；WorkBuddy 83.7±0.7；Spreadsheet 34.3±0.2；JobBench 47.6±0.5 | [T1d, p.8] | — | high |
| T1e | 主结果 | 已报告 | Flash + revision 相对单次 rollout 的增益：Avg +6.2、APEX +6.7、WSB +8.9、WorkBuddy +5.0、Spreadsheet +4.9、JobBench +5.3 | [T1e, p.8] | — | high |
| T1f | 主结果 | 已报告 | Opus + revision 相对单次 rollout 的增益：Avg +6.4、APEX +11.7、WSB +6.8、WorkBuddy +4.7、Spreadsheet +4.2、JobBench +4.8 | [T1f, p.8] | — | high |
| T2 | 消融与敏感性 | 已报告 | 去掉技能库（Flash）：Avg 51.3、APEX 50.9、WSB 63.5、WorkBuddy 77.1、Spreadsheet 30.6、JobBench 34.4 | [T2, p.23] | — | high |
| T2b | 消融与敏感性 | 已报告 | 只用 resolver（Opus）：Avg 54.3、APEX 44.6、WSB 65.5、WorkBuddy 82.3、Spreadsheet 32.9、JobBench 46.3 | [T2b, p.23] | — | high |
| T2c | 消融与敏感性 | 已报告 | 单上下文合并两路（Opus）：Avg 55.3、APEX 46.1、WSB 66.5、WorkBuddy 83.3、Spreadsheet 33.5、JobBench 47.0 | [T2c, p.23] | — | high |
| T2d | 消融与敏感性 | 已报告 | 按池熵分组（Opus / APEX）：154 个 consensus 池只高 0.6；262 个 disputed 池高 6.1 | [T2d, p.10] | — | high |
| X1 | 局限与偏差 | 已报告 | 结果依赖十条 rollout 的池；池子贵 | [X1, p.12] | — | high |
| X1b | 局限与偏差 | 已报告 | consensus 盲点：约 70% 的漏错是查了正确的中途结果，错误在更后一步 | [X1b, p.10] | — | high |
| X1c | 局限与偏差 | 已报告 | 换到 Claude Code 时 Opus 在 JobBench 与 SB-2 掉回单次 rollout 水平 | [X1c, p.7] | — | high |
| X1d | 局限与偏差 | 已报告 | 自演化增益不超出已评测的任务分布；无 grader 反馈时能否改进未知 | [X1d, p.27] | — | medium |

## 3. 复现阻断清单（impact=high 且非"已报告"，共 12 行；P3 与 P3b 同源，合并为一行）

| 优先级 | ID | 缺什么 | 去哪补（查找建议） | 补不到时的替代取值（推断） |
|---|---|---|---|---|
| 1 | P3 / P3b | 三段提示全文、18 个技能文本与脚本 | GitHub `google-research/veriharness`（p.22 给出地址）的 skills/ 与 prompts；作者邮箱见 p.1 | 推断：按 §3.2-3.4 与附录 C 的文字自行重写等价提示（角色分工、证据记录字段、交付规则）；同时做"空技能库"变体，用 Table 4 的 without-skills 差值（−2.1/−2.3 分）界定自有实现的复现上限 |
| 2 | M2c | 验证各阶段的 temperature / top-p / 采样条数 | 仓库中模型调用配置；或问作者 | 推断：沿用厂商默认（前沿 API 通常 temperature=1.0、不设 top-p），并把它列为敏感性维度 |
| 3 | M3 | max tokens、上下文窗口、最大步数、单任务超时 | 仓库 runtime 配置；pi coding agent 上游默认值 | 推断：先跑 5 个任务看工具调用次数的 95 分位，再取 2 倍作上限（如 40 步 / 30 分钟），并在报告中声明 |
| 4 | P2 | 搜索停止准则只有定性描述，无阈值/最大检查数 | §3.2（p.5）与附录 C（p.20）；仓库求解循环 | 推断：固定"每 claim 最多 3 次 check、单任务总 check ≤ 40"，把停止预算作为消融维度 |
| 5 | D4b | 五个 benchmark 的获取方式与许可 | 各基准原始论文：APEX-Agents arXiv 2601.14242、WSB 2605.03596、WorkBuddy 2607.20911、SB-2 2606.29955、JobBench 2605.26329（均见本文参考文献） | 推断：优先用 SB-2（重算逐格比对、无 LLM 判官）与 WSB Lite（100 任务）起步，APEX 视授权情况后置 |
| 6 | D2c | APEX 任务数 480 / 434 / 416 三个数不一致 | 附录 D（p.20-21）与发布池的任务清单 | 推断：以发布池中实际存在的 task id 为准（480 是名义任务数），并在报告中写明所用子集 |
| 7 | P4d | 四个生成侧 scaffold 的版本与系统提示 | 各基准 runner 仓库；发布池已含轨迹可绕过生成 | 推断：直接用发布池，完全跳过 scaffold 复现（这也是省钱的关键） |
| 8 | P5 | 各基线（majority voting、best-of-N、tournament、LLM-as-a-Verifier）的提示与实现 | LLM-as-a-Verifier arXiv 2607.05391；仓库 baselines/ | 推断：先只复现最强的两条（LLM-as-a-Verifier 与 agentic verifier），其余按被引论文重写并标注"自行实现" |
| 9 | E2b | 判官同源（WSB 用 Opus 判 Opus）与判官可靠性 | WSB 的 agent-as-a-judge 论文 | 推断：select 只返回池内已有 rollout，直接读归档 grader 分数，规避重判（见 §6） |
| 10 | M1 | 两家模型的 API 快照/版本号 | 仓库 README 的模型串；作者 | 推断：以论文 v1 日期 2026-10-02 为时间锚，记录自己实际调用的模型串与日期 |
| 11 | R3b | API 调用时间窗、依赖库版本 | 仓库 lockfile 与 commit 日期 | 推断：自建环境用当前最新稳定版并全部锁版本，报告里写清"非原版环境" |

这 11 行的性质不同：第 1–4 行（提示词与技能、解码、步数、停止准则）缺任意一项，写出来的东西就不再是 VeriHarness，只能叫"同构重实现"，分数差多少无法归因；第 5–6 行（benchmark 授权、任务数口径）决定你能不能用自己的数据，属于"能不能开工"；其余几行只影响与论文数值的可比性，不影响方向判断。

## 4. 冲突与易错点

1. **APEX-Agents 的任务数三处不一致**：Table 1 写 480 [D2c, p.7]，附录 A 的 claim 分析写 434 个任务、1,692 条 claim [D2c, p.19]，正文 §6 又按 154 个 consensus 池 + 262 个 disputed 池（合计 416）统计 [D2c, p.10]。复现时必须先确定自己用哪个子集，否则分母不同、分数不可比。
2. **"全文给出"与实际内容不符**：p.5 称技能库"listed in full with the tools in Appendix H" [P3, p.5]，但附录 H（p.23-25）只有 Table 5 组件表、Figure 7 使用率和 Table 6 的技能名与脚本名，提示词与技能正文在材料中没有 [P3, p.23]。这是最容易被忽略的坑：照论文写不出 VeriHarness。
3. **两套增益容易张冠李戴**：正文与摘要说 +6.2（Flash）/ +6.4（Opus），这是**五基准平均、带 revision**；Figure 1 图注说 +6.7（APEX）与 +8.9（WSB），是**单基准、带 revision** [T1e, p.8]。而 select 的增益是 +4.4 / +4.1 [T1, p.8]。三个数各有口径。
4. **select 与 revision 是两套表行**：select 51.6 / 53.7，revision 53.4 / 56.1；Table 4 的消融全部在 revision 模式下 [T2, p.23]，不能拿去和 Table 2 的 select 数直接比。
5. **single rollout 没有 ±**：其余行都有跨 seed 标准差，只有 single rollout 与 oracle 没有，因为它们是固定池上的期望、不需重采样 [E1b, p.21]。别把它当成方差缺失。
6. **单位陷阱**："262 个 disputed pool" 与 "775 个 disputed claim" 不是矛盾，一个是池数一个是 claim 数 [T2d, p.10][D2d, p.19]。
7. **术语漂移**：p.7 说"three independent verifier runs"，表注说"three-seed mean"，指的是同一件事（三次验证器运行）[E3, p.8]。
8. **WorkBuddy 的 200 是三个域之和**：code 80 + office 50 + web 70，security 域明确不跑 [D1c, p.20][D3, p.20]。

## 5. 对照我的条件

| 我的条件 | 论文设置 | 出处 | 差异对复现的影响 |
|---|---|---|---|
| 只能调闭源前沿 API | 生成与验证都用 Gemini 3.5 Flash / Claude Opus 4.8，同模型设定 | [M1, p.7] | 方向一致。但论文没有快照日期，我只能锁"当下可调的最新串"；版本漂移会同时改变池质量与验证质量，绝对值必然偏离 |
| 不能训练、不能改权重 | 明确 training-free、plug-and-play，技能库以文本形式积累 | [P1c, p.3] | 完全兼容，不需要 8×H200 |
| 8×H200 可用 | 论文只涉及 API 调用，成本按 token 与 list price 计，硬件规格原文缺失 | [R2, p.27][R1] | 该机器对复现本论文无用；可留给我自己的方法或开源模型对照，但会引入"不同基座"的混淆 |
| 单次预算约 200 美元 | select 每任务 $1.44（Flash）/ $3.92（Opus）；revision 约为其 3 倍 | [R2, p.27][R2b, p.27][R2c, p.27] | 按每任务均价算，200 美元约够 Flash 130 个任务-次、或 Opus 50 个；带 revision 分别降到 45 与 17 个左右。必须选小样本 + 单基准 |
| 一周工时 | 论文未给人工工作量；rollout 池已发布 | [A2, p.22] | 省掉最贵的池生成（原池成本 > $100,000）[R2e, p.1]，一周可做到"池对齐 + 单基准 select" |
| 开工前不能联系作者 | 提示词与技能只在仓库里 | [P3, p.5][A1, p.22] | 先按仓库走；仓库若不含提示词，就走 §3 第 1 项的替代方案，并把结论限定为"自有提示下的重实现" |

## 6. 最小复现方案

**阶段 0：不花 API 钱，先对齐池（半天）**
用发布池复算两行：single rollout（Flash 47.2 / Opus 49.6）与 selection oracle（Flash 62.7 / Opus 63.1）[T1i, p.8][T1j, p.8][T1g, p.8][T1h, p.8]；两行都是固定池上的期望，无需重采样 [E1b, p.21]。判据：与论文差 < 0.5 分即通过；差得多说明任务 id 映射或均值口径（任务加权 vs 简单平均）理解错了，先修这个再往下走。

**阶段 1：单基准 select 复现（3–4 天，约 $115–150）**
- 为什么先选 APEX-Agents（推断）：它的 oracle 上限离池均值最远之一（Flash 19.2 分、Opus 18.0 分）[T1g, p.8][T1h, p.8]，select 增益在 Opus 上最大（+5.4）、在 Flash 上与 WSB 基本持平（+5.2 对 +5.5）[T1, p.8][T1b, p.8]，信噪比最好；且用归档分数的做法绕开了它依赖 Gemini 3 Flash 判官的弱点 [M4, p.21]。SB-2 虽然判分完全可复算，但池均值离上限只有 10.1 分 [T1g, p.8]，小样本更难分辨。
- 子集：APEX-Agents 抽 80 个任务（全 10 条 rollout，N 不能改小，改小池就不同了 [D2, p.7]），只做 select 不做 revision。
- 对照：single rollout（= 池均值）、selection oracle、以及一个弱基线（best-of-N 单次判定），用来确认"不是随便选都涨"。
- 关键技巧（推断）：select 只把池内一条 rollout 原样返回 [P1d, p.6]，而发布池里每条 rollout 都带 grader 分数 [A2, p.22]，所以**选中哪条就能直接查到它的分数，不需要再付判官钱**，也绕开了判官漂移 [E2b, p.21]。这条同时解决了 §3 第 9 项和预算问题。
- 成功阈值（推断）：先看增益而不是绝对值。论文 APEX 上 select 比池均值高 +5.2（Flash，其分数 ±1.2）/ +5.4（Opus，±0.7）[T1, p.8]。80 个任务的二项标准误约 √(0.53×0.47/80)≈5.6 分，单看绝对值无法分辨 ±5 分；因此改用**配对差**（同一任务上"harness 选中条 vs 池均值"的差）并做 bootstrap 95% 区间，判据设为"配对差区间下界 > 0 且点估计落在 +2 至 +8 分"。若把池熵分布也对齐（consensus 池约占三分之一强 [T2d, p.10]），点估计还应与本地的池熵分层结果一致。
- 预算：80 任务 × $1.44 ≈ $115；留 $35 给调试与重跑。

**阶段 2：与我的方法对比（2–3 天）**
同一冻结池、同一 N=10、同一 grader 口径；两条方法各跑一遍 select，报"增益"与"占 oracle 上限比例"两个指标。论文的 oracle 回收率（推断，由 Table 2 的 oracle 行与 single rollout 行相减得到 [T1g, p.8][T1h, p.8]）：Flash 为 APEX 27%、WSB 40%、WorkBuddy 32%、SB-2 42%、JobBench 13%；Opus 为 30%、38%、38%、35%、19%。这个归一化指标比裸分更能跨基准比较，也更适合小样本。

**不建议现在做的**：revision 分支（成本 3 倍且必须重新判分，200 美元不够）、自演化分支（10 轮 × K 个候选库，成本远超预算 [P2b, p.26][P2c, p.26]）、CLI 部署分支（依赖宿主 agent，Opus 上 JobBench/SB-2 会掉回单次水平 [X1c, p.7]）。

## 7. 事实 / 推断 / 未报告

- **原文事实**：五基准、两模型、每任务 N=10 的冻结池，同一模型既生成又验证；select 主结果 51.6 / 53.7，revision 53.4 / 56.1 [T1, p.8]；graders 为 Gemini 3 Flash（APEX、JobBench）、Opus 4.8 的 agent-as-a-judge（WSB）、composite verifier（WorkBuddy）、重算比对（SB-2）[M4, p.21]；select 每任务 $1.44 / $3.92，86–91% 输入 token 走缓存 [R2, p.27][R2d, p.27]；rollout 池与代码公开，benchmark 内容不随发布 [D4, p.22]。
- **推断**：select 可用归档 grader 分数免判官复现（依据 p.6 的"原样返回"与 p.22 的"每条 rollout 带分数"）；oracle 回收率由 Table 2 相减得出；80 任务下的标准误与配对判据为本文假设，论文未报告（原文缺失）方差口径之外的检验 [E4]。
- **未报告（原文缺失，已查 p.1-12、p.18-28 全部候选页）**：验证阶段解码参数 [M2c]、步数与超时 [M3]、提示词与技能正文 [P3b]、各基线实现 [P5]、任务数口径冲突的裁决 [D2c]、API 快照与调用时间窗 [M1][R3b]、显著性检验 [E4]、按 benchmark 分列的成本 [R2]。这些只能靠仓库、被引论文或作者补齐，材料本身给不出。

## 8. 自查

- 门禁：`check_audit.py --report` 退出码 0，problems = 0；26 项全部覆盖，81 行，最后一次检查带 `--report`。
- 附录每一页（p.18-28）都读过，Table 1–7、Figure 1–8、算法框都已进入核查表；`check_report.json` 的 `material_missing_objects` 只有一项 `Algorithm 1`，属于标题排版无空格（p.20 提取为"Algorithm 1VeriHarness"）造成的误报，伪代码块本身在材料中，故 P1 保持"已报告"。
- 多值项已拆行：模型/判官（M1、M4a-d）、基准（D1a-e）、目标（T1a-j：select / revision / gain / oracle / single rollout 各一行）、流程（P1a-d）、消融（T2a-d）、成本（R2a-e）。
- 每个 `not_reported` 都有 `searched` 与 `next_step`；12 个 high 缺口全部进入 §3 阻断清单。
- 材料完整（28 页，含参考文献与附录 A–K），因此 §3 用"原文缺失"表述的是论文本身没写，不是文件被截断。
- 提取路径：沙箱内无 PyMuPDF，`extract_text.py` 走 pypdf 回退（`extract_report.json` 的 engine 为 pypdf，status ok，28 页均有文字层，无截断告警）。
- 未完成：未打开任何代码仓库或外部资料（本轮按要求只依据论文本身）；成本按任务平均口径给出，论文未按 benchmark 分列，实际 APEX 类长任务的每任务成本可能高于 $1.44。
