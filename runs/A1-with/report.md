# 《VeriHarness: Scaling Agentic Verification for Long-Horizon Tasks》复现配置核查：复现 VeriHarness (select) 的选择结果，作为课题基线

> 材料：materials/A/veriharness_2610.00972v1.pdf（arXiv 2610.00972v1），28 页（正文 p.1–12，参考文献 p.12–17，附录 p.18–28），提取状态 ok，无截断；正文提到的表、图、附录都在文件中（`material_missing_objects` 为空）。
> 核查表 `output/audit.jsonl` 共 66 行，覆盖 26/26 项。按行计：reported 36 / partial 22 / not_reported 2 / conflicting 6 / not_applicable 0 / not_in_material 0。门禁检查 `check_report.json`：problems = 0（最后一次运行带 `--report`）。
> 依据：只用论文本身，没有联网。代码仓库和被引文献只作为"查找建议"列出，内容未经确认。下文 `[ID, p.N]` 指核查表行号和原文页码，回 PDF 的对应页即可核对。

## 0. 结论先行

- **复现就绪度：补齐 4 项后可以复现。** 复现 select 有一个很大的便利：作者公开了全部 rollout 池，每个 rollout 都附有基准判官的存档分数 [A2, p.22]。select 模式下返回的是池中原样未改的 rollout [P1b, p.6]，所以**不必重新生成 rollout，也不必运行判官**（推断：依据 [E2, p.21] 的计分方式"存档 base 分 + 同轮差值"，select 时差值为 0）。真正复现不出来的风险，集中在验证器本身"怎么写"。
- **最可能导致复现失败的 3 项：**
  1. **验证器提示词和 18 个技能的正文都没有给。** 正文说附录 H "listed in full"，但附录 Table 6 只有技能名、一句话用途和脚本名 [P3, p.23][P3b, p.5；p.25]。消融显示去掉技能库后 Opus 平均分从 56.1 降到 53.8 [T2, p.23]；同样有环境访问但没有协议和技能的 agentic verifier，只拿到约一半增益 [T2c, p.7]。
  2. **验证器的轮数、token 和超时上限都没有给。** 论文只说"何时停止由模型决定"（未报告：已查全文 p.1–28 [M3]）。解码参数也只给了 thinking level high，没有 temperature 和 max tokens [M2, p.20]。
  3. **模型快照和运行时版本没有给。** 论文只写了 Gemini 3.5 Flash / Claude Opus 4.8 [M1, p.7]，pi coding agent、LiteLLM 和沙箱镜像都没有版本 [P4, p.21]。作者也承认宿主运行时会影响协议的执行效果 [X1b, p.23]。
- **第一步：** 先去查公开代码仓库 github.com/google-research/veriharness [A1, p.22]，看里面有没有技能正文、各上下文的指令、max-turn 配置和模型 ID。同时下载 rollout 池，零成本核对 Table 2 的 single rollout 行和 oracle 行（论文明确说这两行仅凭池就能复现 [A2, p.22]），并清点 APEX 的任务数，处理 §4 里的冲突。

## 1. 要复现的目标

- **select 主结果（Table 2，三种子均值 ± 跨种子标准差，N=10 池）：**
  - Gemini 3.5 Flash：Avg 51.6；APEX 53.3±1.2、WSB 62.0±0.9、WorkBuddy 77.8±1.4、SB-2 31.5±2.4、JobBench 33.5±1.8；相对 single rollout 的增益为 +4.4 / +5.2 / +5.5 / +4.6 / +4.2 / +2.6 [T1, p.8]。
  - Claude Opus 4.8：Avg 53.7；APEX 41.2±0.7、WSB 65.0±0.5、WorkBuddy 83.0±0.4、SB-2 33.4±1.2、JobBench 46.1±0.8 [T1b, p.8]。
  - 参照行：Flash single rollout 47.2（WSB 56.5）[T1c, p.8]；Flash 最强的选择基线是 LLM-as-a-Verifier 49.5（WSB 60.4）和 agentic verifier 49.4（WSB 60.1）[T1d, p.8]；oracle 上界 Flash 62.7、Opus 63.1 [T1i, p.8][T1j, p.8]。
- **样本量：** APEX 480、WSB 100、WorkBuddy 200（code 80 / office 50 / web 70）、SB-2 321、JobBench 65 题，每题每模型 10 个 rollout [D2a, p.7][D2e, p.7][D2b, p.20]。
- **消融告诉我们什么最不能错：** Table 4 的所有消融都在含 revision 的设置下做，**没有 select-only 消融** [T2, p.23]。其中去掉技能库对 APEX 的伤害最大（Flash 54.8→50.9）[T2b, p.23]。在 select 层面，可参照的是 agentic verifier：它有同样的环境访问，但只拿到约一半增益 [T2c, p.7]。结论是：**协议和技能的文本是最不能错的配置**。复现结果如果落在 agentic verifier 的水平附近（Flash WSB 约 60.1），基本说明协议或技能没有还原到位。

## 2. 配置总表（26 项，66 行；多值项已拆行）

| ID | 项目 | 状态 | 论文给出的值 | 出处 | 复现还缺什么 | 影响 |
|---|---|---|---|---|---|---|
| M1 | 被测/主模型 | 部分 | 生成器与验证器同为 Gemini Flash（版本号见引文），或同为 Claude Opus（见引文）；两模型各自做同模型设置（主实验） | p.7 | 只有模型名，未给 API 快照/模型版本字符串、调用日期区间；闭源模型会随时间漂移 | 高 |
| M1b | 被测/主模型 | 已报告 | 自进化实验只用 Claude Opus（见引文），同时担任验证器和技能库提议者 | p.26 | — | 低 |
| M2 | 解码参数 | 部分 | 生成与验证均为 thinking level = high | p.20 | 未给 temperature、top-p、每次调用的 max output tokens；'thinking level high' 对 Claude 如何映射（effort 或 thinking budget token 数）未说明；三次验证器运行的随机性来源未说明 | 高 |
| M2b | 解码参数 | 已报告 | 仅用于离线 claim 分析：Claude Opus 以 temperature zero 抽取每个 rollout 的取值 | p.19 | — | 低 |
| M3 | 长度与步数上限 | 未报告 | — | 已查 1-28（全文逐页，含附录 p.16-28） | 验证器（resolver/challenger/adjudicator 各上下文）的最大轮数、最大 token、上下文长度、单任务超时均未给；论文只说由模型自行决定何时停止 | 高 |
| M3b | 长度与步数上限 | 已报告 | 自进化中候选技能附带的脚本运行时限为十分钟（ten-minute limit） | p.26 | — | 低 |
| M4 | 辅助模型（判官） | 部分 | APEX-Agents 与 JobBench 的逐条 rubric LLM 判官：Gemini 3 Flash | p.21 | 无模型快照/版本；注意是 'Gemini 3 Flash' 而非生成器的 'Gemini 3.5 Flash'，原文未解释是否笔误；判官提示词是否沿用基准官方版本未说明 | 中 |
| M4b | 辅助模型（判官） | 部分 | Workspace-Bench Lite：agent-as-a-judge，即运行 Claude Opus 4.8 的 Claude Code 代理 | p.21 | 判官所用 Claude Code 版本、判官提示词未给；判官与 Opus 生成器同源（自偏好风险） | 中 |
| M4c | 辅助模型（判官） | 部分 | WorkBuddy Bench：code 域用测试与规则；office 域用规则 + LLM 判官 Gemini 3.5 Flash；web 域用基准自带判官流水线 | p.21 | web 域判官模型未写；office 判官与 Flash 生成器同源 | 中 |
| D1 | 基准/数据集 | 已报告 | APEX-Agents 1.0 版本 | p.20 | — | 中 |
| D1b | 基准/数据集 | 部分 | 其余四个基准：Workspace-Bench Lite、WorkBuddy Bench、SpreadsheetBench 2、JobBench | p.7 | 除 APEX 外均未写版本号/commit/下载日期（Workspace-Bench 参考文献标题为 1.0，但正文未写版本） | 中 |
| D2 | 实际使用的子集 | 已报告 | 每题每模型 N=10 个 rollout；各基准任务数见 D2a、D2e（基准表） | p.7 | — | 高 |
| D2a | 实际使用的子集 | 已报告 | 基准表任务数：APEX 480、Workspace-Bench Lite 100、WorkBuddy 200、SpreadsheetBench 321 | p.7 | — | 高 |
| D2e | 实际使用的子集 | 已报告 | 基准表任务数（续）：SpreadsheetBench 321、JobBench 65 | p.7 | — | 高 |
| D2b | 实际使用的子集 | 已报告 | WorkBuddy 只跑 code/office/web 三域，分别 80、50、70 题 | p.20 | — | 中 |
| D2c | 实际使用的子集 | 冲突 | APEX-Agents 任务数不一致：基准表写 480，附录 A 的 claim 分析覆盖 434 题 | p.7；p.19 | Table 1 写 480 题；附录 A 的 claim 分析覆盖 434 题；Section 6 / Figure 5 按熵分组为 154 + 262 = 416 个池。未说明 46 或 64 题被去掉的原因，以及 Table 2 的 APEX 分数是否在全部 480 题上计算 | 高 |
| D2d | 实际使用的子集 | 部分 | 自进化：约 75% 开发 / 25% 留出，按工作区/模板分组切分，固定种子 | p.26 | 种子值、两个子集的确切任务数与任务 ID 未给 | 低 |
| D3 | 过滤与排除 | 已报告 | 排除 WorkBuddy 安全域（会持续触发模型 API 安全告警） | p.20 | — | 中 |
| D3b | 过滤与排除 | 部分 | 自进化：APEX 排除需提交文件的任务；SB-2 只含模板与财务模型任务 | p.26 | 主实验中失败/超时/无产物的 rollout 如何计分、API 报错任务如何处理未说明；p.9 的 'eligible tasks' 未定义 | 中 |
| D4 | 数据可得性 | 已报告 | rollout 池公开于 HuggingFace caiqizh/veriharness；不含基准内容（任务描述、输入工作区、rubric、参考答案），需凭官方任务 ID 从原基准获取 | p.22 | — | 高 |
| P1 | 方法流程 | 已报告 | 算法框（Algorithm）：两个互不可见、并发运行的上下文（disagreement resolver、consensus challenger）各写证据记录，再由新上下文裁决（adjudication）输出 base、revision_plan、unresolved | p.20 | — | 高 |
| P1b | 方法流程 | 已报告 | select 模式：直接返回裁决选出的 base（∈R），不做修改 | p.6 | — | 高 |
| P1c | 方法流程 | 部分 | 裁决选 base 的规则：证据支持缺陷最少、按对交付物的重要性加权 | p.6 | 该规则如何写成提示词、select 模式下 base=∅ 时如何处理（选择评测要求 base∈R）未说明 | 高 |
| P2 | 方法超参 | 已报告 | 候选池大小 N = 10（所有方法共享同一冻结池） | p.7 | — | 高 |
| P2b | 方法超参 | 部分 | 自进化：每轮 K 个候选库，先 K=3 后 K=5；C 跑十轮、D 跑八轮（p.26） | p.26 | 何时从 K=3 切到 K=5 未说明 | 低 |
| P3 | 提示词 | 部分 | 协议与技能以文本指令形式交给模型；论文未给任何验证器提示词全文 | p.23 | resolver / challenger / adjudicator / delivery 的系统提示与任务提示均未给出；18 个技能只有 Table 6 的一行摘要，没有技能正文和脚本 | 高 |
| P3b | 提示词 | 冲突 | 正文称技能库在附录 H 完整列出 | p.5；p.25 | 正文说附录 H 'listed in full'，但附录 H 的 Table 6 只给技能名、适用交付物、一句话用途和脚本名，没有技能正文，不能照着重写 | 高 |
| P4 | 运行环境与工具 | 部分 | 验证器运行时：基于开源 pi coding agent（MIT）的薄封装；Claude 经本地 LiteLLM 代理调用；只读挂载 rollout/输入/环境，无网络沙箱，仅输出目录可写；工具 read/ls/find/grep/bash/write/edit（p.24） | p.21 | pi coding agent 与 LiteLLM 版本、沙箱实现（容器镜像、预装库如 LibreOffice/Python 包）未给；电子表格'渲染为单元格级文本'的工具未给 | 高 |
| P4b | 运行环境与工具 | 部分 | 生成 rollout 的脚手架：APEX 用官方 agent runner + tool servers；JobBench 用 opencode；SB-2 用官方 agent；WorkBuddy 与 WSB 用 Claude Code | p.20 | 各脚手架版本未给 | 低 |
| P4c | 运行环境与工具 | 已报告 | CLI 变体版本：Gemini CLI 0.46.0、Claude Code 2.1.246、Codex 0.149.1 | p.21 | — | 中 |
| P5 | 基线配置 | 已报告 | Single rollout = 池均值；Selection oracle = 每题取判官分最高的 rollout | p.21 | — | 中 |
| P5b | 基线配置 | 部分 | 多数投票：选与其他 rollout 最一致者；Best-of-N：一次调用对所有 rollout 按任务描述打分；两两锦标赛：两两比较、胜者晋级 | p.21 | 多数投票的一致性度量；Best-of-N 的评分刻度、平局处理、提示词；锦标赛的对阵结构、顺序、是否交换位置去偏置均未给 | 中 |
| P5c | 基线配置 | 部分 | LLM-as-a-Verifier：把任务分解为评价标准，逐标准两两比较排序；每次比较评估四次 | p.27 | 标准数量、比较的配对方式、聚合方式未给 | 中 |
| P5d | 基线配置 | 部分 | Agentic verifier (env. access)：在同一沙箱、同样工具下把 best-of-N 判官作为工具代理运行，只有单条打分指令，没有协议与技能 | p.21 | 打分指令文本未给 | 中 |
| P6 | 对照公平性 | 已报告 | 所有方法共享同一 rollout 池与同一模型；验证器看不到判官、参考答案与 rubric | p.3 | — | 中 |
| E1 | 指标与计分 | 部分 | APEX：任务成功率；JobBench、WSB：平均 rubric 分；WorkBuddy：三域按任务加权平均；SB-2：headline accuracy | p.21 | APEX '任务成功'的判定（是否须全部 rubric 项通过）、SB-2 headline accuracy 的定义均依赖原基准，原文未展开 | 高 |
| E1b | 指标与计分 | 已报告 | Avg 为五个基准的不加权平均；增益相对 single rollout | p.8 | — | 中 |
| E2 | 评分者与可靠性 | 部分 | 判官重评协议：判官为模型时，base 与交付 rollout 同轮评分，报告'存档 base 分 + 同轮差值'以抵消判官漂移 | p.21 | 判官与人工的一致率、判官重复评分方差未报告；WSB（Opus 判官）与 WorkBuddy office（Flash 判官）存在判官与生成器同源 | 中 |
| E3 | 重复与方差 | 部分 | 三次独立验证器运行（three-seed），报告均值与跨种子标准差；single rollout 与 oracle 是池上的期望，不需重采样 | p.21 | 种子值、'种子'控制的是什么（API 采样不可设种子时随机性从哪来）未说明；只报 3 次运行的标准差，样本很小 | 中 |
| E4 | 显著性检验 | 未报告 | — | 已查 7, 8, 10, 21, 22, 23, 26, 27（含 scan 候选页 26）及全文 | Table 2 / Table 4 未做显著性检验，只有跨种子标准差；p.7 的 'gains more than the cross-seed spread' 不是统计检验 | 低 |
| E4b | 显著性检验 | 已报告 | 自进化结果只报点估计，作者明确声明不构成统计显著性 | p.26 | — | 低 |
| R1 | 算力 | 部分 | 模型均通过 API 调用（Claude 经本地 LiteLLM 代理） | p.21 | 沙箱/评测机器的 CPU/GPU、并发数未给 | 低 |
| R2 | 成本与耗时 | 已报告 | select 每题验证成本：Flash $1.44，Opus $3.92（缓存读取按缓存价计）；revision 约为 select 的三倍（p.27） | p.27 | — | 高 |
| R2b | 成本与耗时 | 已报告 | 86–91% 输入 token 命中缓存；若缓存按全价计，select 成本 Flash 5.40 美元、Opus 13.06 美元每题 | p.27 | — | 高 |
| R2c | 成本与耗时 | 部分 | 完整 rollout 池生成成本超过 100,000 美元 | p.1 | 单任务耗时（wall-clock）未报告；只说验证会增加延迟（p.12） | 中 |
| R3 | 软件与时间 | 部分 | 仅 CLI 版本给出（Gemini CLI 0.46.0、Claude Code 2.1.246、Codex 0.149.1） | p.21 | API 调用日期区间、pi coding agent 与 LiteLLM 版本、Python/表格处理库版本未给；论文日期为 2026-10-02（p.1） | 中 |
| A1 | 代码 | 已报告 | 验证代码：github.com/google-research/veriharness | p.22 | — | 高 |
| A2 | 数据/轨迹 | 已报告 | rollout 池：huggingface.co/datasets/caiqizh/veriharness，两模型×五基准×每题十个 rollout，含轨迹、交付文件和基准判官分 | p.22 | — | 高 |
| A2b | 数据/轨迹 | 冲突 | 摘要称发布约 26,000 个 rollout | p.1；p.7 | 按 Table 1 计算：(480+100+200+321+65)=1166 题 × 10 × 2 模型 = 23,320，比'约 26,000'少约 2,700；可能含未进入主表的 rollout，原文未说明 | 中 |
| T1 | 主结果 | 已报告 | Flash，VeriHarness (select)：Avg 51.6；APEX 53.3±1.2，WSB 62.0±0.9，WorkBuddy 77.8±1.4，SB2 31.5±2.4，JobBench 33.5±1.8；相对 single rollout 增益 +4.4 / +5.2 / +5.5 / +4.6 / +4.2 / +2.6 | p.8 | — | 高 |
| T1b | 主结果 | 已报告 | Opus，VeriHarness (select)：Avg 53.7；APEX 41.2±0.7，WSB 65.0±0.5，WorkBuddy 83.0±0.4，SB2 33.4±1.2，JobBench 46.1±0.8；增益 +4.1 / +5.4 / +4.5 / +4.0 / +3.3 / +3.3 | p.8 | — | 高 |
| T1c | 主结果 | 已报告 | Flash 参照行：single rollout Avg 47.2（APEX 48.1 / WSB 56.5 / WorkBuddy 73.2 / SB2 27.3 / JobBench 30.9） | p.8 | — | 高 |
| T1d | 主结果 | 已报告 | Flash 最强选择基线：LLM-as-a-Verifier Avg 49.5（APEX 49.8 / WSB 60.4 / WorkBuddy 75.3 / SB2 30.2 / JobBench 31.9）；Agentic verifier (env. access) Avg 49.4（APEX 49.0 / WSB 60.1） | p.8 | — | 中 |
| T1e | 主结果 | 已报告 | Opus 参照行：single rollout Avg 49.6（APEX 35.8 / WSB 60.5 / WorkBuddy 79.0 / SB2 30.1 / JobBench 42.8） | p.8 | — | 中 |
| T1i | 主结果 | 已报告 | Selection oracle（选择上界）：Flash Avg 62.7（APEX 67.3 / WSB 70.3 / WorkBuddy 87.7 / JobBench 51.0） | p.8 | — | 中 |
| T1j | 主结果 | 已报告 | Selection oracle：Opus Avg 63.1（APEX 53.8 / WSB 72.4 / WorkBuddy 89.4 / JobBench 60.4） | p.8 | — | 中 |
| T1f | 主结果 | 冲突 | Opus 完整 VeriHarness（含 revision）Avg 56.1，增益行写 +6.4（摘要同为 6.4） | p.8；p.8 | 56.1 − 49.6 = 6.5，与表中 +6.4 差 0.1；按五个分项增益平均 (11.7+6.8+4.7+4.2+4.8)/5 = 6.44，属舍入口径差异 | 低 |
| T1g | 主结果 | 冲突 | APEX、Opus：154 个共识池 select 高出池均值 0.6；262 个分歧池高出 6.1 | p.10；p.8 | 按 416 个池加权：(154×0.6 + 262×6.1)/416 ≈ 4.1，而 Table 2 的 APEX(Opus) select 增益是 +5.4；两者分母不同（416 对 480），也未说明 Figure 5 用的是哪一个种子或三种子均值 | 中 |
| T1h | 主结果 | 冲突 | 正文称 Flash 下两个 CLI 在每个基准上与专用实现相差两分以内 | p.7；p.8 | Flash JobBench：Codex 35.6 对专用实现 select 33.5，相差 2.1，略超'两分以内'；APEX 的 Gemini CLI 51.3 对 53.3 恰为 2.0 | 低 |
| T2 | 消融 | 已报告 | 消融（含 revision）Opus：single 49.6；Resolver only 54.3；Challenger only 52.6；without skills 53.8 | p.23 | — | 中 |
| T2b | 消融 | 已报告 | 消融（含 revision）Flash：Resolver only 51.5；Challenger only 50.0；without skills 51.3（APEX 50.9）；single context 52.6 | p.23 | — | 中 |
| T2c | 消融 | 已报告 | select 层面最接近的'消融'：同样环境访问、无协议无技能的 agentic verifier 只拿到约一半增益（数值见 T1d 与 T1） | p.7 | — | 高 |
| X1 | 局限与偏差 | 已报告 | 作者声明的局限：依赖每题十个 rollout 的池；不给单个 rollout 打分；仅同模型设置；延迟较高 | p.12 | — | 中 |
| X1b | 局限与偏差 | 已报告 | 宿主运行时影响协议执行：Opus 下 CLI 部署在 JobBench 与 SB-2 上明显变弱 | p.23 | — | 高 |
| X1c | 局限与偏差 | 已报告 | 共识错误残留：被 challenger 维持的全体一致错误中 70% 是检查了正确的中间量、错误在下游 | p.27 | — | 低 |
| T1k | 主结果 | 已报告 | 首页图（Figure One）的增益是含 revision 的完整 VeriHarness（APEX +6.7、WSB +8.9），不是 select；摘要中的平均增益同样是 revision 口径 | p.1 | — | 高 |

## 3. 复现阻断清单（impact=high 且状态不是 reported）

| 优先级 | ID | 缺什么 | 去哪补（查找建议） | 补不到时的替代取值 |
|---|---|---|---|---|
| 1 | P3 / P3b / P1c | resolver、challenger、adjudicator 的指令全文；18 个技能的正文和脚本；裁决选 base 的提示词 [P3, p.23][P3b, p.5；p.25][P1c, p.6] | 代码仓库的技能目录和指令文件 [A1, p.22] | 推断：按 §3.1–3.4、Algorithm 1 [P1, p.20] 和 Table 6 的一句话描述自己写，并原样保存为实验产物。这样算"论文方法的再实现"，不算严格复现，报告里要说明 |
| 2 | M3 | 每个上下文的最大轮数、max tokens、超时（未报告：已查 p.1–28） | 代码仓库中 pi agent 的配置 | 推断：按成本设上限，每题验证花费不超过论文均值的 3 倍（Flash 约 $4.3，依据 [R2, p.27] 的 $1.44），并记录触顶比例；触顶比例高时说明上限过紧 |
| 3 | M2 | temperature、top-p、max output tokens；Claude 的 "thinking level high" 怎样映射 [M2, p.20] | 代码仓库 / LiteLLM 配置 | 推断：temperature 等用 API 默认值，只把 thinking 设为 high 档。论文对每个种子的随机性来源没有说明，默认采样是最自然的读法 |
| 4 | M1 | 模型快照 ID 和调用日期 [M1, p.7]；R3 也缺日期 [R3, p.21] | 发布池轨迹元数据；代码仓库 | 推断：用当前能拿到的 Gemini 3.5 Flash 正式版，记录模型 ID 和调用日期，同时承认存在漂移风险 |
| 5 | P4 | pi coding agent / LiteLLM 版本；沙箱镜像；"电子表格渲染成单元格文本"的工具 [P4, p.21] | 代码仓库 Dockerfile；pi coding agent 仓库 | 推断：退而使用论文的 CLI 变体（Gemini CLI 0.46.0）[P4c, p.21]。Flash 下 CLI 与专用实现大体在 2 分以内 [T1h, p.7]，但 Opus 下差距更大 [X1b, p.23] |
| 6 | D2c | APEX 任务数：Table 1 写 480，附录 A 写 434，Figure 5 合计 416；Table 2 用哪个分母不明 [D2c, p.7；p.19] | 清点发布池；代码仓库分析脚本 | 推断：先避开 APEX，用 WSB 做最小复现 |
| 7 | E1 | APEX "任务成功"的判定和 SB-2 "headline accuracy" 的定义，论文都交给原基准 [E1, p.21] | APEX-Agents（arXiv 2601.14242）、SpreadsheetBench 2（arXiv 2606.29955）原论文 | 只做 select 时直接用池里的存档分，不需要自己实现指标 |

（R2、A1、A2、D4、T1 虽然 impact 是 high，但状态为 reported，不在本表中。A1 只确认了链接，仓库内容未经核实。）

## 4. 冲突与易错点

1. **首页图和摘要里的数字不是 select 的数字。** 6.2 / 6.4 和 Figure 1 中的 +6.7、+8.9 都是含 revision 的完整版 [T1k, p.1]。select 的平均增益是 +4.4（Flash）和 +4.1（Opus）[T1, p.8][T1b, p.8]。选复现目标时，必须取 Table 2 中 "VeriHarness (select)" 那一行。
2. **APEX 任务数前后不一致。** 有 480 [D2a, p.7]、434 [D2c, p.19]，以及 154+262=416 [T1g, p.10] 三个数。按 416 个池加权，Figure 5 的 select 增益约为 4.1。Table 2 中 APEX（Opus）的 select 增益则是 +5.4 [T1b, p.8]（推断：两者的任务集合或口径不同，论文没有解释）。
3. **"Listed in full" 和实际内容不符。** 正文说附录 H 完整列出了技能 [P3b, p.5]，附录 Table 6 实际只有摘要 [P3b, p.25]。
4. **判官模型名容易看混。** APEX 和 JobBench 的判官是 "Gemini 3 Flash"，WorkBuddy office 的判官是 "Gemini 3.5 Flash" [M4, p.21][M4c, p.21]，论文没有解释是不是笔误。另外，WSB 的判官是 Claude Opus 4.8，和 Opus 生成器同源 [M4b, p.21]。
5. **rollout 数量对不上。** 摘要写"约 26,000 个 rollout"[A2b, p.1]。按 Table 1 计算是 1166 题 × 10 × 2 = 23,320 [A2b, p.7]（推断：池中可能含有没进入主表的 rollout）。
6. **舍入口径。** Opus 完整版的平均分差是 56.1−49.6=6.5，表中写的是 +6.4 [T1f, p.8]，属于"平均分之差"和"逐基准增益取平均"两种口径的差别。
7. **"两分以内"的说法有一处略超。** Flash JobBench 上，Codex 为 35.6，专用实现的 select 为 33.5，相差 2.1 [T1h, p.7；p.8]。
8. **不能张冠李戴的设置。** temperature 0 只用于附录 A 的离线 claim 抽取，不是验证器的设置 [M2b, p.19]；十分钟脚本时限、K=3/5、75/25 切分都只属于自进化实验 [M3b, p.26][P2b, p.26][D2d, p.26]。

## 5. 对照我的条件

| 我的条件 | 论文设置 | 出处 | 差异对复现的影响 |
|---|---|---|---|
| 可以调用闭源 API（Claude / Gemini / GPT） | 生成器和验证器都是 Gemini 3.5 Flash 或 Claude Opus 4.8，thinking high | [M1, p.7][M2, p.20] | 模型可得，但快照未知；用当前版本可能产生漂移，要记录模型 ID 和日期 |
| 8×H200 可以跑开源模型 | 论文没有用开源模型 | [M1, p.7] | 复现基线用不上。拿开源模型当验证器属于新设置，不能和 Table 2 直接比 |
| 每次复现约 $200 API | select 每题 $1.44（Flash）/ $3.92（Opus），缓存命中 86–91%；缓存按全价算则为 $5.40 / $13.06 | [R2, p.27][R2b, p.27] | Flash 在 WSB 上跑 100 题约 $144（推断：假设 WSB 的单题成本接近五基准均值；论文没有分基准的成本）。缓存不能命中时是 $540，超出预算。Opus 全量和三种子都超预算 |
| 开工前不能联系作者 | 提示词、技能、上限、快照都要靠代码仓库补 | [A1, p.22] | 仓库缺什么，就只能按 §3 的替代值做"再实现"，报告里要写明 |
| 可以查公开代码仓库 | 代码和 rollout 池已公开 | [A1, p.22][A2, p.22] | 第一步就查；rollout 池让 select 复现不需要重新生成，也不需要判官 |
| 课题要和自己的方法比较 | 所有方法共享同一冻结的 10-rollout 池和同一模型 | [P6, p.3][P2, p.7] | 你的方法也应该在同一个发布池上做选择，才能和 Table 2 对齐。如果你的方法会改写产物，就要自己运行各基准的判官 [M4, p.21][M4b, p.21]，并沿用论文的"同轮评分"口径 [E2, p.21] |

## 6. 最小复现方案

- **第 0 步（零 API 成本，约半天）：** 下载 rollout 池 [A2, p.22]，按任务 ID 计算 Flash 和 Opus 在各基准的池均值和 oracle，与 Table 2 的 single rollout 行、oracle 行对比 [T1c, p.8][T1i, p.8]（这两行论文明确说仅凭池可复现）。偏差超过 0.1 时，先查自己的任务集合。同时清点 APEX 的任务数，处理 [D2c]；清点 rollout 总数，处理 [A2b]。
- **第 1 步（选基准和模型）：** 选 **Gemini 3.5 Flash × Workspace-Bench Lite（100 题）**。理由：select 增益 +5.5，跨种子标准差 0.9，在五个基准中信号和噪声的比值较好 [T1, p.8]；题数少；不涉及 APEX 的分母冲突。select 不需要运行 WSB 的 agent 判官，直接取存档分。JobBench 题更少（65 题），但增益只有 +2.6、标准差 1.8 [T1, p.8]，难以和噪声区分，不推荐。
- **第 2 步（先跑 20 题试点，约 $30，推断）：** 实测每题成本、缓存命中率、轮数触顶比例。命中率远低于 86% 时 [R2b, p.27]，全量就会超出预算，需要先修好提示缓存再继续。
- **第 3 步（全量单种子）：** 100 题跑 1 个种子（约 $144，推断）。如果有余量，在同一批题上跑同环境、只给单条打分指令的 agentic verifier 作为对照 [P5d, p.21]。不过它的成本论文没有给，预算可能不够，可以放到第二周。
- **成功阈值（假设）：** 论文只报告了 3 个种子的标准差（WSB 为 0.9）[T1, p.8]。我把 **WSB select 得分落在 62.0 ± 1.8（论文均值 ± 2 倍跨种子标准差），即相对池均值 56.5 至少 +3.7**，作为"复现成功"的标准。这个阈值是假设：3 个种子估计的标准差很不稳定，而且单种子本身也有方差。如果得分 ≤ 60.4（LLM-as-a-Verifier / agentic verifier 的水平 [T1d, p.8]），判为"协议或技能没有还原"，优先回查 P3。另外建议用逐题配对 bootstrap，比较 select 和池均值的差，因为论文本身没有做显著性检验 [E4, p.26]。
- **扩展：** 预算允许时，再补 2 个种子，或扩展到 SB-2（官方计分是重算后逐单元格比对，确定性最强，见 p.21 Grading protocol 段），注意 SB-2 的标准差有 2.4 [T1, p.8]。

## 7. 事实 / 推断 / 未报告

- **原文事实：** N=10 冻结池，所有方法共享 [P2, p.7]；thinking high [M2, p.20]；三种子均值 ± 标准差 [E3, p.21]；select 原样返回 base [P1b, p.6]；运行时是 pi coding agent 加只读、无网络的沙箱 [P4, p.21]；代码和池都已公开 [A1, p.22][A2, p.22]；select 每题 $1.44 / $3.92 [R2, p.27]。
- **推断：** select 复现不需要判官，得分等于存档分（依据 [E2, p.21][P1b, p.6]）；WSB 单种子约 $144（依据 [R2, p.27]，假设各基准的单题成本相近）；Figure 5 与 Table 2 中 APEX 的任务集合不同（依据 [T1g, p.10][D2c, p.19]）；成功阈值 ±2σ 是假设。
- **未报告（已查全文 p.1–28，包括附录 p.18–28 全部页）：** 验证器的轮数、token、超时上限 [M3]；显著性检验 [E4]；temperature、top-p [M2]；模型快照和 API 调用日期 [M1][R3]；验证器提示词和技能正文 [P3]；种子值 [E3]；单题耗时 [R2c]。查找建议：先查代码仓库；查不到再在允许联系作者后发邮件（cz391@cam.ac.uk，见 p.1）。

## 8. 自查

- [x] `check_report.json` 中 problems 为空，26/26 项覆盖，最后一次检查带了 `--report`。
- [x] 附录 p.18–28 逐页读过：附录 A 的 temperature 0、附录 D 的脚手架/判官/指标/基线、附录 E 的发布链接、附录 F 的消融表、附录 H 的工具和 18 个技能、附录 I 的自进化超参、附录 K 的成本，都已进入核查表。
- [x] 多值项已拆行（M1/M2/M3/M4、D1/D2/D3、P1/P2/P3/P4/P5、R2、T1、T2、X1）。没有只写主实验，自进化的设置单列并标为低影响。
- [x] 两个 not_reported 都写了 searched 和 next_step；所有 high 缺口都进入了 §3 阻断清单。
- [x] 报告里的数字都来自核查表行，或者是由表中数字算出的推断（如 23,320、416、≈4.1、$144），推断处都已标注。
- 本次未完成：没有联网核实代码仓库和 rollout 池的实际内容；Figure 4 / 6 / 7 / 8 中只出现在图里的数值没有逐点读取。
