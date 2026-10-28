# VeriHarness（arXiv 2610.00972v1）复现配置报告

**用途**：把这篇论文当作你课题的对比基线，先复现它的 select（选择）结果，再在你的系统上与你的方法比较。
**依据范围**：仅这篇 PDF（28 页，解析无乱码）。所有页码均为 PDF 页码，与页脚打印页码一致，便于回原文核对。
**未做**：未联网、未打开代码仓库、未读被引文献；第 8 节列出的入口只是"后续去哪查"的建议。

---

## 0. 一句话结论

论文把**方法**（协议、技能、成本、评测口径）说得足够细，但把**可执行内容**（提示词正文、18 个技能文本与脚本、停止条件、采样参数、claim 对齐规则）几乎全部留在代码里，同时明确声明发布的数据集**不含基准内容**（p.22），所以：**你能免费复现的是池级两行（single rollout、selection oracle），不能只靠论文复现 4.4 / 4.1 的 select 增益**；按全量 1,166 个任务算，仅 select 一步在 Flash 上就要 $1,679、Opus 上 $4,571，你的 $200 预算只够做 1 个基准、1 个模型、1 个种子的子集复现。

---

## 1. 复现目标行：先确认你要复现的是哪一行

Table 2（p.8）里名字相近的行有三类，口径完全不同，混淆会直接导致"复现不出来"：

| 行 | 含义 | 成本口径 | 关键页 |
|---|---|---|---|
| `Single rollout` | **不是一条 rollout**，而是 10 条 rollout 得分的池均值（Appendix D 明确写 "The single rollout score is the pool mean"） | 0（只读池） | p.21、p.8 |
| `VeriHarness (select)` | adjudication 从池中选出的 base **原样返回**，不做修改 | 每任务计费 | p.5、p.7、p.21 |
| `VeriHarness`（无 select 后缀） | 在 select 的 base 上再应用 revision plan | ≈3× select | p.6、p.27 |

因此 Table 2 的 "+4.4 / +4.1"是**相对 10 条均值**的增益，不是相对某一条 rollout。你的对比表如果写成"vs single rollout = 一条 rollout"，数字会天然差一截。

---

## 2. 论文已明确给出的设置

以下是我能找到的、可直接照抄的配置项。除"备注"列外，均出自原文明示。

| 类别 | 取值 | 页 |
|---|---|---|
| 基准与规模 | APEX-Agents v1.0 480 / Workspace-Bench **Lite** 100 / WorkBuddy Bench 200（code 80 + office 50 + web 70，**不跑 security 域**）/ SpreadsheetBench 2 321 / JobBench 65；合计 1,166 任务 | p.7 Table 1；p.20 Appendix D |
| 池规模 | 每任务 **N = 10**，验证前**冻结**，所有方法用同一池 | p.7、p.20 |
| 模型 | 生成器 = 验证器 = 同一模型：Gemini 3.5 Flash、Claude Opus 4.8，`thinking level = high` | p.7、p.20 |
| 生成 scaffold | 各基准自带：APEX agent runner + 其 tool servers；JobBench 用 **opencode**；SB-2 用基准自带 agent（shell + spreadsheet-viewing）；WorkBuddy 与 WSB-Lite 用 **Claude Code**。两模型在同一基准上共用同一 scaffold | p.20 |
| rollout 内容 | artifact `d_i` + final workspace state `w_i` + action trace `τ_i` | p.3、p.20 |
| 验证 runtime | 开源 **pi** coding agent（MIT）的薄层；Claude 经本地 **LiteLLM** 代理 | p.20 |
| verifier 工具 | `read / ls / find / grep / bash`（含技能自带脚本）、`write / edit` 仅限输出目录 | p.24 |
| 沙箱 | rollout、任务输入、环境**只读挂载、无网络**，仅输出目录可写；xlsx 另渲染为 cell-level 文本 | p.20 |
| 协议 | 两个**并行且互不可见**的上下文（disagreement resolver / consensus challenger）→ fresh 上下文 adjudication → delivery 在同一 adjudication 上下文完成 | p.5–6、p.19–20 Algorithm 1 |
| 技能库 | **18 个**技能，4 类：6 个 evidence、4 个 resolver、3 个 challenger、5 个 revision；随附 `xlsx_dump/xlsx_diff/xlsx_gaps/xlsx_forks/xlsx_render`、`pdf_render/pdf_tables/pdf_words`、`docx_changes/docx_text`、`pptx_render/pptx_text`、`bundle_inventory`、`patchlab/pageprobe`、`xlsx_recalc` | p.24–25 Table 6 |
| 基线 | majority voting、best-of-N（单次调用判全部）、pairwise tournament、LLM-as-a-Verifier（**每次比较 4 次评估**）、agentic verifier (env. access)（同工具、单条打分指令、无协议无技能）、aggregation over the pool、agentic verifier + revision | p.7、p.21、p.27 |
| 指标 | APEX = task success rate；JobBench / WSB-Lite = 平均 rubric 分；WorkBuddy = 三域**按任务数加权**的平均；SB-2 = headline accuracy | p.21 |
| 统计 | 三次独立 verifier run 的均值 + cross-seed 标准差；池级两行确定性、无 ± | p.7、p.8、p.21 |
| 评分器 | APEX、JobBench：LLM judge = **Gemini 3 Flash**；WSB-Lite：agent-as-a-judge = **Claude Code + Opus 4.8**；WorkBuddy：composite（code 用测试+规则、office 用规则+Gemini 3.5 Flash judge、web 用其 judge pipeline）；SB-2：**重算 + 逐单元格比对** | p.21 |
| judge 漂移控制 | 报告"归档 base 分 + 同轮差值" | p.21 |
| 成本 | Flash select **$1.44/任务**、Opus **$3.92/任务**；revision ≈3× select；输入 token 的 **86–91% 命中缓存**；若缓存按全价计则 $5.40 / $13.06 | p.27–28 |
| 池制作成本 | 约 26,000 条 rollout，**>$100,000** | p.1 |
| 发布物 | 代码 `github.com/google-research/veriharness`、池 `huggingface.co/datasets/caiqizh/veriharness`、主页 `veriharness.com` | p.22、p.1 |
| CLI 部署 | Gemini CLI **0.46.0**、Claude Code **2.1.246**、Codex **0.149.1**；协议与技能以文本注入，用宿主自己的工具与沙箱 | p.20 |
| 自进化（可选） | Opus 4.8 同时做 verifier 与 proposer；约 75/25 划分（按源工作区/模板分组后再切）；K=3 后 K=5；C 跑 10 轮、D 跑 8 轮；候选脚本限 10 分钟；自动过滤任务 ID / 基准名 / 开发集文件名 / 参考答案值 | p.9、p.26 |

---

## 3. 论文没写、或写不清的设置

按"缺了会不会直接做不出来"排序。这是本报告的核心部分。

| # | 缺失项 | 论文里的状态 | 后果 | 去哪补 |
|---|---|---|---|---|
| G1 | **提示词正文**：resolver / challenger / adjudication / delivery 的指令文本 | 只给算法框（Algorithm 1）与散文描述，"the model chooses ... and when to stop" | 协议的行为边界全在提示词里；自己重写 = 复现另一个系统 | 代码仓库（p.22） |
| G2 | **18 个技能的文本与脚本** | p.5 称"listed in full with the tools in Appendix H"，但 Appendix H 只给了名字、作用、脚本名（Table 6），**没有正文** | 见下节量化：这一项占平均增益 2.1（Flash）/ 2.3（Opus）点，APEX 上高达 3.9 / 5.5 点 | 代码仓库（p.22） |
| G3 | **停止条件**：最大轮数、工具调用上限、每任务 token/时间预算 | 未给任何数值 | 成本可在数量级上漂移，分数也随之漂移；$200 预算无法预估 | 仓库默认值 + 你自定上限并写进报告 |
| G4 | **采样参数**：verifier 与 generator 的温度 / top-p / max_tokens | 全文只有一处温度：claim 抽取"at temperature zero"（p.19） | "three independent verifier runs"无法定义，± 无法复现 | 仓库配置；否则自定并明示 |
| G5 | **"seed"的定义** | 只说"三次独立 verifier run"、"cross-seed standard deviation"，未说三次之间差什么 | 你无法判断 ±1.2 是采样噪声还是别的 | 仓库；否则自建三次不同随机种子的 run |
| G6 | **跨 rollout 的 claim 对齐规则** | Section 2 只说"let p identify a common question"，没说怎么从 10 个 artifact 里对齐出同一 `p`，也没说"equivalent expressions"的判定细则 | `H(π_p)`、consensus/disputed 划分全靠这一步；错了整个方法的前提就变了 | 仓库 + p.19 Appendix A 的口径（数值按该 criterion 精度一致、判定按同一结论、缺失记为 absent） |
| G7 | **`base = ∅` 时 select 行怎么计分** | 3.4 允许 `base = ∅`（p.6），4.1 说 select 返回"the base chosen by adjudication"（p.7） | 选空时该任务算 0？还是回退到某条？直接影响 APEX/JobBench 绝对分 | 仓库；否则自定并在报告中声明 |
| G8 | **select 交付的是 `d_i` 还是 `(d_i, w_i)`** | 目标定义交付 rollout（p.3），但 select 是"returned unchanged"（p.6）；SB-2 类基准要看 workbook 重算 | xlsx / patch 类任务可能差出可观分数 | 仓库 |
| G9 | **价格表与缓存计价** | 只说"at list price"、"cache-read rate"，未列单价 | $1.44 / $3.92 无法核算，也无法判断你的账单是否异常 | 你的 API 价目表 + 自己的 token 记账 |
| G10 | **模型快照** | 只给产品名（Gemini 3.5 Flash / Opus 4.8 / Gemini 3 Flash），无版本字符串或日期 | 快照漂移会污染绝对分；judge 漂移控制依赖归档 base 分 | 你的 API 版本号，写进报告 |
| G11 | **基准输入与许可** | p.22 明示发布物**不含**任务描述、输入工作区、rubric、参考答案 | 环境证据 `E(χ)` 是方法的一半；没有基准内容，VeriHarness 退化成"只读候选池"的判官 | 五个基准各自的获取渠道（见第 8 节） |
| G12 | **最终 workspace state `w_i` 是否在发布池里** | 3.1 要求把 `d_i, w_i, τ_i` 作为文件暴露给 verifier（p.5），但 p.22 只承诺"trajectory, delivered files, and score" | 若 `w_i` 缺失，从发布池复现出的 verifier 看到的比论文少 | 拿到数据后先核对目录结构 |
| G13 | **生成 rollout 时的采样设置与 API 成本** | 未单列；>$100,000 是总量 | 你要重造池时无法估预算 | 自测 2–3 个任务外推 |
| G14 | **APEX "eligible" 任务规则** | 480（p.7）→ 434（p.19）→ 416（p.10）三种数，未解释筛选 | 你不知道 434/416 是怎么来的，也就无法对齐 Figure 5 的分组 | 仓库中的分析脚本；否则放弃 Figure 5 复现 |
| G15 | **技能脚本的运行环境**（Python 版本、依赖、LibreOffice/headless browser 等） | 只给脚本名（p.25） | `xlsx_render`、`pdf_render`、`pageprobe` 跑不起来会静默降级为纯文本读取 | 仓库依赖文件 |

---

## 4. 前后不一致清单

以下是我在原文内部能对上的矛盾或口径漂移。前三条会实打实影响你的复现数字。

| # | 现象 | 证据页 | 说明与风险 |
|---|---|---|---|
| C1 | 池总规模两种说法：摘要"approximately 26,000 rollouts" vs Table 1 推算 **23,320**（1,166 × 10 × 2） | p.1 vs p.7 | 差约 11%。可能含自进化实验或额外 run，但原文未说。影响：你从发布池统计数量时对不上，别误判下载不全 |
| C2 | APEX 任务数三个口径：480 / 434 / 416（154 consensus + 262 disputed） | p.7 / p.19 / p.10 | 434 是 claim 分析覆盖数，416 是 Figure 5 分组数，均未说明筛选规则 |
| C3 | Figure 5 加权限算出的平均增益 ≈ **4.06** 点（(154×0.6 + 139×4.5 + 108×7.7 + 15×9.4)/416），而 Table 2 的 APEX/Opus select 增益是 **+5.4** | p.10 vs p.8 | 差 1.3 点。子集口径（416 vs 480）应付不了全部差额，原文未解释。影响：如果你用 Figure 5 的机制解释来预测自己系统上的增益，会系统性低估 headroom |
| C4 | "single rollout" 命名与实际定义（10 条池均值）不符 | 命名见 p.8 caption、p.9–10 各处；定义见 p.21 | 极易被误读成"一条 rollout"，导致与你的 baseline 不可比 |
| C5 | 3.1 声称技能"listed in full ... in Appendix H"，但 Appendix H 只有名字/作用/脚本名 | p.5 vs p.24–25 | 表述与内容不符；这是你最大的复现障碍（G2） |
| C6 | Section 6 用 resolver-only 54.3 对比 49.6，而 Table 4 的 resolver-only 是**含 revision** 的口径，select-only 是 53.7 | p.10 vs p.8、p.23 | 两处口径不同，交叉引用会算错"resolver 贡献多少" |
| C7 | 4.2 称"exceeds every baseline in all ten model–benchmark settings"，但 CLI 行里 Opus/JobBench 42.4 低于 majority voting 43.3 | p.7 vs p.8 | caption 已声明 CLI 行单列，但正文措辞容易被二次引用误读 |
| C8 | Appendix D 定义 LLM-as-a-Verifier 为"per-criterion pairwise comparisons"，Appendix K 追加"four evaluations per comparison" | p.21 vs p.27 | 基线超参在两处不一致；你自己实现基线时选哪个都会有人质疑 |
| C9 | LLM-as-a-Verifier 的隐含单价：Flash ≈ $14.4/任务（$1.44 的十倍），Opus ≈ $7.8/任务（$3.92 的两倍） | p.27 | 同一方法在更便宜模型上反贵近 2 倍，与常规价目方向相反；说明 $/任务 是跨基准平均且受 token 结构影响，**不能当单价用**，也提示口径需要核对 |
| C10 | 自进化轮次：正文只说"each round"，附录给 C=10 轮 / D=8 轮；Figure 4b 横轴 0–10 | p.9 vs p.26 vs p.9 | 不矛盾，但正文读不出轮数是预设的；附录还说"round counts alone do not establish a compute advantage" |
| C11 | 部分单元格 ±0.0（如 Opus/SB-2 best-of-N 30.5 ±0.0） | p.8 | 三次 run 完全同分，与"independent runs"表述张力较大（也可能确实稳定），核对时留意 |

> 提取伪影说明：Table 2 中每行"gain over single rollout"末位被我的 PDF 解析器替换为占位符（原文该处为数字）。该值可由同表分数相减恢复，例如 Flash/JobBench select 增益 = 33.5 − 30.9 = **+2.6**，且与印刷的均值 +4.4 自洽。这不是论文缺陷。

---

## 5. 哪些缺口最可能让你"复现不出来"

按"阻断程度 × 你能否用钱绕过"排序。

**第一档：不解决就一定复现不出 4.4 / 4.1（且无法用算力或预算绕过）**

1. **G1 + G2（提示词与 18 个技能文本）**。量化依据在 Table 4（p.23）：Flash 从"无技能"51.3 → 全量 53.4（+2.1），Opus 53.8 → 56.1（+2.3）；APEX 上分别是 50.9 → 54.8（+3.9）、42.0 → 47.5（+5.5）。也就是说技能库单独承担平均增益的 2 点以上，APEX 上超过一半。你若自己重写技能，等于把基线换成了"同类方法的一个弱版本"，对比结论会被审稿人质疑。
   → 补法：先拿 `github.com/google-research/veriharness`（p.22）里的提示词与技能文件，**不要**先动手重写。

2. **G11（基准输入与 rubric）**。方法的一半是"对着环境取证"，而发布物明确不含任务描述、输入工作区、rubric、参考答案（p.22）。没有环境，你只能做"池内判官"，而论文已证明这类方法（best-of-N、LLM-as-a-Verifier）平均只涨 0.1–2.3 点（p.8）。
   → 补法：五个基准分别申请/下载（第 8 节）。这是你一周工期内**最可能卡住**的一步，建议第一天就并行启动。

3. **G3 + G4 + G5（停止条件、采样、seed 定义）**。这三项共同决定你的成本与 ±。缺它们，你既无法预估 $200 够不够，也无法判断"我的复现差 1.5 点"是 bug 还是噪声。
   → 补法：用仓库默认值，然后**冻结**自己的配置（轮数上限、温度、3 个显式种子）并写进报告；不要在不同阶段偷偷改。

**第二档：会让数字偏但不能解释全部偏差**

4. **G7 / G8（`base=∅` 与交付范围）**：只在少数任务上触发，但一旦触发就是 0 分 vs 满分的差别，在 65–100 任务的小子集上足以翻转结论。
5. **G10 / G13（模型快照、生成成本）**：快照变了，绝对分整体平移；这也是为什么"复现要报告**同轮差值**，不要只报绝对分"（p.21 的 judge 漂移控制逻辑）。
6. **G9（价格与缓存）**：直接决定 $200 能跑多少任务。论文的核心成本结论建立在 86–91% 缓存命中上（p.27）；若你的 API 通道没有 prompt caching，同等工作量成本约 ×3.75（$1.44 → $5.40，p.27）。**先在你的通道上实测一次缓存是否生效**，再定子集大小。

**第三档：只影响你能否复现"分析章节"，不影响主表**

7. **G14（APEX eligible 规则）**：Figure 5 的分组复现不了，但 Table 2 不受影响。
8. **G6（claim 对齐细则）**：影响你自己系统的 headroom 预测（见 6.5），不影响论文数字复现。

**一个反直觉但重要的判断**：这篇论文的增益是**条件性**的——它几乎全部来自"池内存在分歧"的任务（Figure 5，p.10：consensus 池 +0.6 点，disputed 池 +6.1 点，高熵池 +9.4 点）。所以真正决定你"复现不出来"的，可能不是上述任何一个设置，而是**你重造的 rollout 池是否同样分歧**。同一模型 + 同一 scaffold + 高温采样通常高度相关；如果你的池偏 consensus，你复现出的增益会自然掉到 1 点以内，而这并不是实现错误。

---

## 6. 最小复现方案（一周 / $200）

### 6.1 先算清预算：全量复现不可行

| 项目 | 计算 | 金额 |
|---|---|---|
| 全量 select，Flash，1 seed | 1,166 × $1.44 | **$1,679** |
| 全量 select，Opus，1 seed | 1,166 × $3.92 | **$4,571** |
| 全量 select，Flash，3 seed（论文口径） | $1,679 × 3 | **$5,037** |
| 全量 with revision，Flash，1 seed | ≈3× select | **≈$5,037** |
| 重造 rollout 池 | 1,166 × 10 × 2 = 23,320 条；按论文"约 26,000 条 / >$100,000"外推 ≈ $4.0/条 | **≈$93,000** |

结论：$200 只够**单基准 + 单模型 + 单/双种子 + select**，且不含评分器开销。**必须用发布池替代自造池**——那部分本来就免费（p.22：池级结果"can therefore be reproduced without running a model"）。

### 6.2 五个阶段与判定门槛

| 阶段 | 内容 | 花费 | 通过门槛（不过就停下查 bug，不要加预算） |
|---|---|---|---|
| **P0**（0.5 天） | 下载发布池；复现 `single rollout` 与 `selection oracle` 两行 | $0 | 与 Table 2（p.8）逐格对上（允许 ±0.1 的四舍五入）。对不上通常是**指标映射**错：WorkBuddy 要三域按任务数（80/50/70）加权，SB-2 是 headline accuracy，APEX 是 success rate（p.21） |
| **P1**（0.5 天） | 用 Appendix A 的协议（p.19）在 1 个基准上算你关心的池的 `H(π_p)` 分布 | $5–15 | 得到 consensus/disputed 任务数；与 Figure 5 的 154/139/108/15（p.10）对比，判断你的 headroom |
| **P2**（1 天） | 取 20–30 个任务，跑 VeriHarness (select)，与同任务池均值配对比较 | $30–40 | 检查三类静默失败：①技能脚本是否真的执行（xlsx/pdf 渲染降级）；②只读挂载 + 无网络是否生效；③`base=∅` 出现频率。方向为负或为 0 时，先查技能加载，再谈结论 |
| **P3**（2–3 天） | 扩到你预注册的 n，单基准、单模型、select-only | ≤$140 | 报告均值差 + 配对 95% CI；**不要**宣称显著性，除非 n 达到 6.3 的门槛 |
| **P4**（1 天） | 你的方法在**同一池、同一 n** 上跑，做三方对比（池均值 / VeriHarness select / 你的方法） | 你方法自身的成本 | 见第 7 节条款 |

预算分配建议：P1+P2 用 $40，P3 用 $140，留 $20 做重跑与失败任务补跑。**不要**在这一周里碰 revision（≈3×）和 self-evolution（要开发集评分器反馈，且属于另一条贡献线，p.9、p.26）。

### 6.3 子集怎么选、要多大

论文的增益幅度（平均 +4.4/+4.1）与跨 seed 标准差（0.2–2.4）决定了小样本几乎必然"复现不出来"。按配对设计、双侧 α=0.05、80% 功效的经验公式 $n \approx (2.8\sigma/\delta)^2$（σ 为逐任务配对差的标准差，需你自测）：

| 逐任务配对 σ | δ=4.4 所需 n | δ=5.5 所需 n |
|---|---|---|
| 10 | 41 | 26 |
| 15 | 91 | 58 |
| 20 | 162 | 104 |
| 30 | 365 | 233 |

对照可用任务数（APEX 480 / WSB-Lite 100 / WorkBuddy 200 / SB-2 321 / JobBench 65），以及每任务 $1.44：

- **推荐主选：Workspace-Bench Lite，Flash，全部 100 任务，1 seed** → $144；若 σ≈20，对 δ=5.5 的功效约 78%，是全库里最贴近预算的组合。
- **若预算更紧**：SB-2（321 任务里抽 60），Flash 1 seed ≈ $86。优点是评分器**重算 + 逐格比对**（p.21），确定性、无 judge 费用；缺点是增益最小且方差最大（Flash +4.2 ±2.4，Opus +4.2 ±1.2，p.8）。
- **不建议**：WSB-Lite 的评分器是 Claude Code + Opus 4.8 的 agent-as-a-judge（p.21），judge 本身的开销可能超过验证开销——如果你要自己重打分，先算这一笔；APEX 的 expert rubric 需要 LLM judge（Gemini 3 Flash），同理。
- **务必**：在 P0 阶段就用发布池里的逐条 grader 分算出真实 σ，再决定 n。这一步免费，却能省掉最大的一笔浪费。

### 6.4 必须记录的内容（否则一周后无法解释结果）

固定并写进报告：模型快照字符串、`thinking level`、温度/top-p、最大轮数与工具调用上限、每任务 token 与美元、技能库版本（commit）、是否命中缓存、`base=∅` 计数、每任务三态（池均值 / select 选中哪条 / 是否被 revision 改动）、逐任务差分与配对 CI。

### 6.5 一周能交付什么、不能交付什么

- **能**：P0 的池级两行**精确**复现（这是论文明确承诺"无需跑模型即可复现"的部分，p.22）；单基准上 select 增益的**方向性**估计与 CI；一份把 15 项配置缺口逐条标注"取自论文/取自仓库/我方自定"的复现卡片。
- **不能**：Table 2 的十格全量复现；revision 行；self-evolution（Section 5）；Figure 5 的分组（G14）；任何"我们的复现与原文一致到 ±0.5"的声明——原文自己给的跨 seed 波动就有 0.2–2.4。

---

## 7. 与你的方法对比时的公平性条款

1. **同池、同 N、同模型、同 scaffold，验证前冻结**（p.7、p.20）。你的方法如果自带更多 rollout，就不是等生成成本比较。
2. **参照系写"10 条池均值"**，不要写"single rollout"（C4）。
3. **select 与 revision 分开报**（p.8）。否则你和"带 revision 的 VeriHarness（+6.4）"比较会自己吃亏。
4. **报告自己池的分歧结构**（consensus / disputed / 高熵占比）。这是唯一能解释"为什么我在自己系统上只复现出 1 点"的量（p.10）。缺这一项，负结果无法归因。
5. **评分器必须同源**。论文的评分器是五套不同实现（p.21）。你若换成自己的 judge，绝对分不可跨研究比较，只能比同轮差值——这正是论文对 judge 漂移的处理方式（"archived base score plus their same-round difference"）。
6. **子集要按任务类别抽，不能按"harness 赢没赢"抽**。论文自己的告诫：开发集与评测集重合会导致过拟合（p.11 引 Wang et al., 2026 的结论；p.26 的分组切分规则）。
7. **不要换验证器模型**。你的 8×H200 在这条基线里**没有位置**：前提是"验证器 = 生成器同一模型"（p.3、p.5），局限性一节也明确把"更强验证器"排除在外（p.12）。若你用本地开源模型当验证器，你测的是另一个设定，需要单独标注，不能与 4.4/4.1 并列。
   - 8×H200 的合理用途：①做"同模型对"的开源复现（生成器与验证器同为同一开源模型），作为**泛化性**的第二个点；②离线复算技能脚本、批量重算 xlsx、复现 claim 抽取（这些不需要前沿 API）。这两项都不进入与论文数字的直接对比。
8. **预算匹配的对照**。若要主张"我的方法更好"，至少加一条与"等预算的纯测试时扩展（更多 rollout / 更强 judge）"的比较，否则无法排除"只是多花了钱"（p.11 引用 Wang et al., 2026 的批评正是这一点）。

---

## 8. 后续去哪查（本次未联网、未打开，仅按论文给出的入口整理）

| 目的 | 入口 | 出处页 |
|---|---|---|
| 提示词、协议实现、18 个技能与脚本、分析脚本（解 G1、G2、G3、G6、G7、G8、G14、G15） | `github.com/google-research/veriharness` | p.22 |
| 26,000 条 rollout 池、逐条 grader 分（解 P0，且用于估 σ） | `huggingface.co/datasets/caiqizh/veriharness` | p.22 |
| 项目主页 | `veriharness.com` | p.1 |
| 验证 runtime 底座（MIT，需按名字自行检索；论文未给 URL/版本） | "pi coding agent" | p.20 |
| 五个基准的输入、rubric、获取方式（解 G11） | APEX-Agents（Vidgen et al., 2026, arXiv 2601.14242）；Workspace-Bench 1.0（Tang et al., 2026, arXiv 2605.03596）；WorkBuddy Bench（2026, arXiv 2607.20911）；SpreadsheetBench 2（Zhu et al., 2026, arXiv 2606.29955）；JobBench（Li et al., 2026b, arXiv 2605.26329） | p.14–16 参考文献 |
| 主基线 LLM-as-a-Verifier 的原始定义（解 C8 的超参歧义） | Kwok et al., 2026, arXiv 2607.05391 | p.14 |
| 缓存与计价假设的对照 | 你自己的 API 价目表与 token 记账 | p.27 |
| 论文对"harness 演化 vs 等预算测试时扩展"的批评 | Wang et al., 2026, arXiv 2607.12227 | p.11 |

以上 arXiv 号与链接均照抄论文参考文献，**我未核验其可访问性与内容**。

---

## 附录：口径备忘（贴在实验记录首页）

- `single rollout` = 10 条 rollout 的**均值**；`selection oracle` = 每任务取 grader 最高的那条，只界定 select 的上界，不界定 revision（p.21）。
- N = 10 固定；`H(π_p) = 0` 为 consensus claim，`H > 0` 为 disputed claim（p.4 Eq. 1）。
- consensus 值有 **34%** 被判错；disputed claim 中 **74%** 存在正确候选，而众数值只有 **47%** 正确（p.2 Figure 2、p.19 Appendix A；样本 = APEX 434 任务 / 1,692 claims / Opus 4.8）。
- 增益分布：consensus 池 +0.6、disputed 池 +6.1、低/中/高熵 +4.5 / +7.7 / +9.4（p.10）。
- 组件贡献（Opus，含 revision 口径，p.23）：池均值 49.6 → 仅协议无技能 53.8 → 全量 56.1；resolver-only 54.3、challenger-only 52.6、合并单上下文 55.3。
- 成本（p.27）：Flash $1.44/任务、Opus $3.92/任务（select）；revision ≈3×；无缓存时 $5.40 / $13.06。
