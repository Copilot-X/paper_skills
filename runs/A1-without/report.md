# VeriHarness（arXiv 2610.00972v1）复现配置梳理报告

> 依据：只用 `materials/A/veriharness_2610.00972v1.pdf`（以及同名 .txt）。没有联网，没有看代码仓库。
> 引用格式：**[p.页码 §节/表/图；txt L行号]**。页码是 PDF 页码，行号对应 .txt 文件，方便回原文核对。
> 复现目标：**VeriHarness (select)** 的选择结果（Table 2）。之后在你的系统上和你的方法比较。

---

## 0. 一页结论（先读这里）

1. **select 的分数很可能不用重新跑判官。** 论文公开了 rollout 池，每条 rollout 都附带 benchmark 判官给的分数 [p.22 App.E；txt L1432–1438]。select 只是从池里挑一条原样返回 [p.6 §3.4；txt L407–408]。所以它的分数原则上就是"被选中那条 rollout 的存档分"。论文**没有明说** select 行就是这么算的（见 G1），但这是最可能的做法。如果成立，判官版本、判官漂移这些坑在 select 复现里就绕开了。你之前那次"判官版本不同"的返工，这次在 select 阶段不会重演。到了比较你自己的方法时（新产物要重新判分），这些坑会回来。
2. **最该先查的三个缺口：**
   - (a) 你拿到的任务集是否与 Table 1 一致。APEX 在文中出现 480 / 434 / 416 三个任务数；rollout 总数 "约 26,000" 与 Table 1 算出的 23,320 对不上。这正是你上次"用了子集"那类坑。
   - (b) 18 个技能的全文、resolver/challenger/adjudicator 的 prompt 都**不在论文里**。论文说技能"listed in full"，实际只给了一张摘要表。这些只能去代码仓库补。
   - (c) 判官模型版本前后不一致：APEX 和 JobBench 写的是 "Gemini 3 Flash"，其他地方都是 "Gemini 3.5 Flash"。
3. **最小复现建议：** Gemini 3.5 Flash，APEX-Agents（备选 Workspace-Bench Lite），只做 VeriHarness (select) 加 1 个对照基线，**只在"池内分数有差异"的任务上跑 verifier**。池内分数全相同的任务，选哪条结果都一样，可以直接用存档分填上，对 select 指标是精确等价的。以论文 $1.44/任务的成本估算 [p.27 App.K；txt L1932–1933]，200 美元大约够 130 次任务级运行。

---

## 1. 论文给出了哪些设置（可直接照抄）

### 1.1 总体设定
| 设置 | 论文的取值 | 出处 |
|---|---|---|
| 设定 | 同模型：生成器和验证器用同一个模型；验证器看不到参考答案、rubric 和判官 | [p.2 §1；txt L110–112]；[p.3 §2；txt L194–198] |
| 模型 | Gemini 3.5 Flash、Claude Opus 4.8，thinking level = **high** | [p.7 §4.1；txt L462–463]；[p.20 App.D；txt L1368–1369] |
| 池大小 | 每个任务每个模型 **N = 10** 条 rollout，冻结后所有方法共用 | [p.7 Table 1；txt L430]；[p.21；txt L1377–1378] |
| 运行次数 | 每个方法 **3 次独立的 verifier 运行**（"three seeds"），报告均值和跨 seed 标准差 | [p.7 §4.1；txt L475]；[p.21 Metrics；txt L1421–1422] |
| Single rollout | **池均值**（期望值，不需要重采样） | [p.21；txt L1400–1401, L1422–1423] |
| Selection oracle | 每个任务取判官分最高的那条，作为 select 的上界 | [p.21；txt L1407–1408] |

### 1.2 Benchmark 与任务数（Table 1，[p.7；txt L430–461]，App.D [p.20；txt L1357–1367]）
| Benchmark | 任务数 | 版本或子集 | 指标 [p.21 Metrics；txt L1419–1421] |
|---|---|---|---|
| APEX-Agents | 480 | **v1.0** | task success rate |
| Workspace-Bench Lite | 100 | 用的是 100 任务的 **Lite 子集** | mean rubric score |
| WorkBuddy Bench | 200 | 只用 code/office/web 三个域，任务数为 **80/50/70**；**排除 security 域**（会触发 API 安全拦截） | 三域按任务数加权平均 |
| SpreadsheetBench 2 | 321 | 未说明 | headline accuracy |
| JobBench | 65 | 35 个职业 | mean rubric score |

注意 Table 1 的原话是 "Tasks is the number of tasks **in our pools**"。也就是说，这些数字不一定等于各 benchmark 官方的完整规模（见 §3 G2）。

### 1.3 生成器脚手架（只在你要自己重新生成池时才需要）[p.20–21 App.D；txt L1370–1373]
- APEX-Agents：官方 agent runner 加它的 tool servers
- JobBench：opencode
- SpreadsheetBench 2：官方 agent，带 shell 和表格查看工具
- WorkBuddy、Workspace-Bench Lite：Claude Code
- 两个模型在同一 benchmark 上用同一个脚手架

### 1.4 Verifier 运行时 [p.21 App.D "Harness runtime"；txt L1380–1390]，[p.24 App.H "Tools"；txt L1724–1728]
- 基于开源的 **pi coding agent**（MIT 许可）做了一层薄封装。Claude 通过本地 **LiteLLM proxy** 调用。
- 工具：`read, ls, find, grep, bash, write, edit`。其中 write 和 edit 只能写输出目录。
- 沙箱：rollout、任务输入、环境都以只读方式挂载，**无网络**。
- 表格会额外渲染成 cell-level 文本。
- 协议：resolver 和 challenger **并发运行，各自独立上下文，互相看不到对方记录**。adjudication 开一个**新上下文**，读入两份证据记录加任务和 rollout。delivery 在 adjudication 的上下文里继续。[p.20 Alg.1；txt L1325–1349]
- select 模式：直接返回 adjudication 选出的 base ∈ R，不做修改 [p.6 §3.4；txt L407–408]。
- base 的选择准则：在任务的实质性要求上，"证据支持的缺陷"最少；按缺陷对交付物的重要性加权 [p.6；txt L403–405]。
- CLI 版本（Table 2 的 CLI 行）：Gemini CLI 0.46.0、Claude Code 2.1.246、Codex 0.149.1 [p.21；txt L1388–1390]。

### 1.5 技能库 [p.24–25 App.H, Table 6；txt L1729–1850]
人工编写的 18 个技能，分四类：
- 6 个 evidence：xlsx/pdf/docx/pptx/bundle/patch
- 4 个 resolve：answer/bundle/workbook/patch
- 3 个 falsify：answer/bundle/workbook
- 5 个 repair

Table 6 给了每个技能的用途摘要和脚本名，例如 `xlsx_dump, xlsx_diff, xlsx_gaps, xlsx_forks, xlsx_render, pdf_tables, docx_changes, bundle_inventory, patchlab, pageprobe, xlsx_recalc`。Figure 7 给了各技能在各 benchmark 上的调用比例 [p.24；txt L1720–1723]，可以用来核对你的实现是否在相近位置调用了相近的技能。

### 1.6 判官与计分 [p.21 "Grading protocol"；txt L1391–1399]
| Benchmark | 判官 |
|---|---|
| APEX-Agents、JobBench | 逐条 rubric 用 LLM judge 打分，写的是 **"Gemini 3 Flash"**（见 C1） |
| Workspace-Bench Lite | agent-as-a-judge：Claude Code + **Claude Opus 4.8** |
| WorkBuddy | code 域用测试和规则；office 域用规则加 LLM judge（Gemini 3.5 Flash）；web 域用 benchmark 自己的 judge 管线 |
| SpreadsheetBench 2 | 重新计算工作簿，与参考工作簿逐格比较（确定性） |
| 防判官漂移 | 判官是模型时，base 和交付物在**同一轮**打分。报告值 = **存档的 base 分 + 同一轮内的差值** |

### 1.7 基线定义 [p.21 "Baselines"；txt L1400–1413]，[p.27 App.K；txt L1945]
- Majority voting：选出与其他 rollout 最一致的那条
- Best-of-N judge：一次调用给全部 rollout 打分
- Pairwise tournament：两两比较，胜者晋级
- LLM-as-a-Verifier（Kwok et al., 2026）：把任务拆成准则，逐准则两两比较。**每次比较评 4 次**（这个参数只出现在 App.K）
- Agentic verifier (env. access)：把 BoN judge 做成带工具的 agent，沙箱和工具与 VeriHarness 相同，但只有一条打分指令，没有协议和技能

### 1.8 目标数字：VeriHarness (select)，Table 2 [p.8；txt L559–572, L667–680]
| 模型 | Avg | APEX | WSB | WorkBuddy | SB-2 | JobBench |
|---|---|---|---|---|---|---|
| Flash single | 47.2 | 48.1 | 56.5 | 73.2 | 27.3 | 30.9 |
| **Flash select** | **51.6** | 53.3±1.2 | 62.0±0.9 | 77.8±1.4 | 31.5±2.4 | 33.5±1.8 |
| Flash oracle | 62.7 | 67.3 | 70.3 | 87.7 | 37.4 | 51.0 |
| Opus single | 49.6 | 35.8 | 60.5 | 79.0 | 30.1 | 42.8 |
| **Opus select** | **53.7** | 41.2±0.7 | 65.0±0.5 | 83.0±0.4 | 33.4±1.2 | 46.1±0.8 |
| Opus oracle | 63.1 | 53.8 | 72.4 | 89.4 | 39.6 | 60.4 |

我核对过：Table 2 和 Table 4 所有行的 Avg 都等于五项算术平均（误差 ≤0.05），"gain over single rollout" 各格也全部吻合。表内算术没有问题。

### 1.9 成本（用于定规模）[p.27 App.K；txt L1932–1942]
- select 每个任务的成本：Flash **$1.44**，Opus **$3.92**。前提是 86–91% 的输入 token 命中缓存，并按 cache-read 价计费。
- 如果缓存没命中、按全价计：Flash **$5.40**，Opus **$13.06**。
- 加上 revision 的完整版，成本约为 select 的 3 倍。

---

## 2. 论文没写的设置（缺口清单）

**影响**一栏：**高** = 很可能导致复现不出来；中 = 会带来几个点的偏差；低 = 基本无关紧要。

| # | 缺口 | 影响 | 去哪补 | 补不到时的替代值 |
|---|---|---|---|---|
| G1 | **select 的分数怎么算**：是查被选 rollout 的存档分，还是重新判分？论文只对 single 和 oracle 明说"只依赖池即可复现"[txt L1436–1438]，没提 select | 高（决定要不要跑判官、要花多少钱） | 代码仓库的评测脚本；README | 默认查存档分。select 不产生新产物，"存档 base 分 + 同轮差值"的规则下差值为 0，结果相同 |
| G2 | **任务清单**：Table 1 的任务数是否就是官方完整集？SB-2 的 321、JobBench 的 65、APEX 的 480 有没有经过筛选？ | 高（你上次就栽在子集上） | 公开池（HF 数据集）里的官方 task id 列表 [txt L1435–1436]；各 benchmark 论文和仓库里的官方规模 | 以公开池中出现的 task id 为准，不要用官方全集 |
| G3 | **技能全文**：§3.1 说技能"listed in full with the tools in Appendix H"[txt L344]，但 App.H 只有摘要表，没有技能正文，也没有脚本源码 | 高（Table 4 显示，去掉技能后 Opus 平均从 56.1 掉到 53.8，APEX 从 47.5 掉到 42.0） | 代码仓库 `github.com/google-research/veriharness` [txt L1431] | 按 Table 6 的"What it supplies"一栏自己写，并在报告里明确标注为"重写版" |
| G4 | **resolver / challenger / adjudicator / delivery 的 prompt**，以及 base 选择的输出格式 | 高 | 代码仓库 | 按 §3.2–3.4、Alg.1 和 Eq.(6) 自己写。adjudicator 必须输出 `(base, revision_plan, unresolved)` 三元组 |
| G5 | **预算上限**：最大轮数、token 上限、超时、停止条件。论文只说"the model chooses … when to stop"[txt L336–337]。唯一给出的数值是 self-evolution 里脚本限时 10 分钟 [txt L1878] | 中到高（直接决定成本和效果） | 代码仓库配置文件；pi agent 默认值 | 用 pi agent 的默认值，并记录每个任务实际用的轮数和 token |
| G6 | **select 模式下 base = ∅ 怎么处理**。Eq.(6) 允许 base = ∅ [txt L402–406]，但 select 必须返回 R 里的一条 | 中 | 代码仓库 | 退回到 adjudicator 的次优候选。如果没有次优，就选第一条或随机选，并记录这种情况出现的频率 |
| G7 | **采样参数**：verifier 的 temperature、top-p，以及"seed"的具体含义（Claude 的 API 不支持固定种子）；Claude 的 "thinking level high" 对应什么参数（effort 还是 budget_tokens） | 中 | 代码仓库；LiteLLM 配置 | 用 API 默认 temperature；Claude 开 extended thinking，使用高档 effort 或较大的 budget。"3 seeds" 按 3 次独立重跑处理 |
| G8 | **模型快照版本或日期**：Gemini 3.5 Flash、Claude Opus 4.8 没给 snapshot id | 中（API 侧静默升级会带来漂移） | 代码仓库配置；论文的发布日期（2026-10-01） | 用你调用时的版本，并记下 model id 和日期 |
| G9 | **pi coding agent 的版本**，以及 LiteLLM 版本 | 低到中 | 代码仓库的依赖锁文件 | 用最新版并记录版本号 |
| G10 | **verifier 能看到 rollout 的哪些部分**。§3.1 说 artifact、最终 workspace 和 trace 都以文件形式暴露 [txt L332–333]。但 trace 很长时是否截断、用什么格式，没写 | 中 | 公开池的文件结构；代码仓库 | 全量挂载为文件，让 agent 自己去读 |
| G11 | **基线细节**：MV 用什么做"一致性"度量（每 seed 有标准差，说明是 LLM 判断的）；BoN 一次塞 10 条长 rollout 时怎么截断；tournament 的对阵结构；LLM-as-a-Verifier 除"每次比较评 4 次"外的其他参数 | 中（只影响基线行，不影响 select 本身） | 代码仓库；Kwok et al. 2026（arXiv 2607.05391） | 最小复现只做一个基线（建议 Agentic verifier，见 §5） |
| G12 | **其余 4 个 benchmark 的版本或 commit**（只有 APEX 写了 v1.0） | 中（rubric 修订会让存档分和你重新判的分不一致） | 公开池的元数据；各 benchmark 仓库的 tag | 选和论文发布日期（2026-10）最接近的 release |
| G13 | **APEX "task success rate" 怎么从逐条 rubric 得出**（是全部 rubric 通过才算成功，还是设了阈值？） | 中（只在你重新判分时才相关） | APEX-Agents 论文（Vidgen et al. 2026，arXiv 2601.14242）的官方评测脚本 | 按官方脚本 |
| G14 | **判官的采样参数**（temperature、thinking） | 中（只在重新判分时相关） | 代码仓库；各 benchmark 官方判官配置 | 按 benchmark 官方默认值 |
| G15 | **Figure 5 的池级熵怎么定义**：池的熵是怎样由 claim 熵聚合而来，low/medium/high 的阈值是多少 | 低（分析用，不影响主表） | 代码仓库 | 不复现这一项 |

---

## 3. 前后不一致或可疑之处

| # | 不一致 | 出处 | 对复现的影响和建议 |
|---|---|---|---|
| **C1** | **判官模型版本**：APEX 和 JobBench 的 LLM judge 写作 "**Gemini 3 Flash**"；全文其他地方（包括 WorkBuddy 的 office 判官）都是 "Gemini 3.5 Flash" | [p.21；txt L1392–1393] 对比 [txt L1395] | 可能是笔误，也可能是有意沿用 benchmark 默认判官。**这和你上次踩的坑一模一样。** 只做 select 并用存档分时不受影响；要给你自己的方法重新判分时必须先查清楚（看代码仓库的判官配置，或给作者发邮件）。在查清之前，用池里的存档分做锚点：拿两种判官各给 20 条 rollout 重新打分，哪个和存档分一致就用哪个 |
| **C2** | **APEX 的任务数有三个版本**：Table 1 是 480；App.A 的 claim 分析是 434 个任务；Figure 5 / §6 的 154+139+108+15 = **416** 个池（其中 disputed = 262，内部自洽） | [txt L438]；[txt L1277]；[p.10 Fig.5；txt L845–852, L886–887] | 434 和 416 可能是剔除了某些任务（无可分 rubric、文件型交付物？），但论文没说明剔除规则。复现主表时以 480 为准，并核对公开池里 APEX 的 task id 数量 |
| **C3** | **rollout 总数**：摘要说"approximately 26,000"，按 Table 1 算 (480+100+200+321+65)×10×2 = **23,320**，差了约 2,700 条 | [p.1；txt L22] 对比 [p.7 Table 1] | 公开池里可能包含 Table 1 之外的任务（比如 WorkBuddy 的 security 域，或被剔除的任务）。**下载池之后一定要按 Table 1 的任务清单过滤**，否则就是"用错子集"的反方向 |
| **C4** | **Figure 5 和 Table 2 的增益对不上**：按 Fig.5 的 n 加权，整体 selection gain = (154×0.6+139×4.5+108×7.7+15×9.4)/416 ≈ **4.1**；但 Table 2 中 Opus APEX 的 select − single = 41.2 − 35.8 = **5.4** | [txt L845–866] 对比 [txt L667–675] | 可能是任务集不同（416 vs 480），也可能是计分口径不同（Fig.5 可能用 rubric 分而不是 success rate）。**不要拿 Fig.5 当复现锚点**，以 Table 2 为准 |
| C5 | **"验证器和生成器用同样的工具"** 和实现不符：正文说 "uses the same model and tools as the generator"，但生成器用的是各 benchmark 的脚手架（APEX tool servers、opencode 等），verifier 用的是 pi agent 的 read/ls/find/grep/bash/write/edit | [txt L111, L194, L1308] 对比 [txt L1370–1373, L1383, L1724–1726] | 以 App.D 和 App.H 为准：verifier 用的是通用文件和 shell 工具，**不能调用 APEX 的 tool servers**，环境只以只读文件形式提供 |
| C6 | **"技能 listed in full"** 与实际只给摘要不符 | [txt L344] 对比 [txt L1745–1850] | 见 G3 |
| C7 | **正文的措辞比数据强**："exceeds every baseline in all ten settings"。但 Flash SB-2 上 select 只比最好的基线（Agentic verifier 30.9）高 0.6，而 select 自身的标准差是 2.4；Flash JobBench 只比 MV 高 1.1，标准差 1.8。"gains more than the cross-seed spread" 说的是相对 single rollout 的增益，不是相对基线 | [txt L477–480]；Table 2 | 在 SB-2 / JobBench（Flash）上，**复现出来的排名可能翻转，这属于正常噪声**，不要据此判定复现失败。最小复现别选这两个格子 |
| C8 | "with Flash, both CLIs match our implementation **within two points** on every benchmark"：实际差值在 APEX（Gemini CLI −2.0、Codex −1.8）和 WorkBuddy（Codex −2.0）上正好卡在 2.0 | [txt L487] 对比 Table 2 | 影响不大。说明 CLI 版本的效果和专用 runtime 相当，可以作为备选实现路径（见 §5） |
| C9 | Figure 1 把 LLM-as-a-Verifier 标为 "Prior best"，但 Flash 的 SB-2 上 Agentic verifier 更高（30.9 > 30.2），JobBench 上 MV 更高（32.4 > 31.9） | [p.1 Fig.1；txt L83–86] 对比 Table 2 | 只是图示问题，不影响复现 |

---

## 4. 哪些缺口最可能让你复现不出来（按风险排序）

1. **任务子集或清单不对（G2、C2、C3）**：风险最高，而且查起来最便宜。补法：公开池的 task id，对照 Table 1。验收：池均值和 oracle 要能精确复现 Table 2 的 single 行和 oracle 行（论文明说这两行只依赖池 [txt L1436–1438]）。**这一步对不上就不要往下跑。**
2. **技能和 prompt 缺失（G3、G4）**：这是方法本身的核心。按 Table 4，去掉技能会掉 2–5 个点，正好吃掉 select 相对基线的大部分优势。补法：代码仓库。替代方案：如果仓库不可用，按 Table 6 重写，但要把结果定性为"按论文描述重新实现"，同时降低预期，以"超过 Agentic verifier"为目标，不要求打到 53.3。
3. **select 的计分方式（G1）**：如果你误以为必须重新判分，会多花很多钱，还会引入判官漂移。先在代码仓库里确认。
4. **判官版本（C1）**：select 阶段影响不大；比较你自己的方法时就是高风险。
5. **预算上限和采样参数（G5、G7、G8）**：会让单任务成本和效果都偏离论文。用"每任务成本是否接近 $1.44（Flash）"作为侧面校验：偏离很大，说明你的轮数、缓存或上下文配置和论文不同。
6. **缓存命中率**：成本估算的前提是 86–91% 缓存命中 [txt L1939]。你的 API 调用方式不同的话，实际成本可能接近全价 $5.40/任务，预算会缩水到约 1/4。

**建议后续去查的资料（本报告没有访问这些）：**
- 代码仓库：`https://github.com/google-research/veriharness` [txt L1431]。重点看技能全文、prompt、runtime 配置、判官配置、评测脚本、seed 定义。
- 公开池：`https://huggingface.co/datasets/caiqizh/veriharness` [txt L1430]。重点看 task id 清单、存档分、文件结构。
- 各 benchmark 原论文和仓库：APEX-Agents（arXiv 2601.14242）、Workspace-Bench（2605.03596）、WorkBuddy（2607.20911）、SpreadsheetBench 2（2606.29955）、JobBench（2605.26329）。重点看任务规模、版本 tag、官方判官配置。
- 基线：LLM-as-a-Verifier（Kwok et al., arXiv 2607.05391）；Agentic aggregation（Lee et al. 2026b, COLM）。
- 作者联系方式：cz391@cam.ac.uk 等 [txt L97]。可以准备一份问题清单（C1–C4、G1、G6），但按你的约束，先开工再联系。

---

## 5. 最小复现方案

### 第 0 步：零模型成本的核对（必须做，约半天）
1. 下载公开池，按 Table 1 的任务数过滤，确认 APEX 是 480 条、WSB 是 100 条等，每条 10 个 rollout。顺带弄清 C3 里多出来的约 2,700 条是什么。
2. 用存档分计算 **single（池均值）** 和 **oracle（每任务最大值的均值）**，与 Table 2 对比。比如 Flash APEX 应该是 48.1 / 67.3，Opus APEX 是 35.8 / 53.8。还可以用无放回抽样复现 Figure 6 的 oracle-vs-N 曲线。**误差应该在 ±0.1 以内**。对不上就说明任务清单或计分口径有问题，先停下来查。
3. 统计每个任务池内分数是否全部相同。**全相同的任务，任何选择方法得分都一样**，可以直接把存档分填进去；只有"分数有差异"的任务才需要跑 verifier。对 select 指标，这样做是精确等价的（前提是 G1 成立）。这一步能决定实际要跑多少个任务。

### 第 1 步：选目标数字
- **主选：Gemini 3.5 Flash × APEX-Agents × VeriHarness (select)，目标 53.3 ± 1.2**（single 48.1）。理由有四点：
  - select 增益大（+5.2）
  - 相对最强基线的领先最大（+3.5，对比 LLM-as-a-Verifier 的 49.8），翻转的可能性小
  - Flash 便宜（$1.44/任务）
  - APEX 是 claim 级分析（Fig.2/5、Table 7）所用的 benchmark，和你课题里"编造中间结果、早期错误传播"关系最密切
- **备选：Flash × Workspace-Bench Lite（62.0 ± 0.9，single 56.5）**。全集只有 100 个任务，不需要抽样；指标是连续的 rubric 分，方差比 APEX 的二值 success rate 小。缺点是相对 LLM-as-a-Verifier 只领先 1.6。
- **避开**：Flash 的 SB-2 和 JobBench（见 C7，排名本身在噪声范围内）。Opus 的成本是 Flash 的 2.7 倍，第一轮不要用。

### 第 2 步：规模与预算（以 200 美元为上限）
- **试点**：先跑 10 个"分数有差异"的任务，测出实际的每任务成本和缓存命中率。
  - 成本接近 $1.44：可以跑约 130 次任务级运行，例如差异任务 ≤130 个时跑 1 个 seed，更少的话跑 2–3 个 seed。
  - 成本接近 $5.40：只够约 35 次，那就把 APEX 的差异任务随机抽 30–35 个（按 APEX 的领域 banking/law/consulting 分层）。
- **对照基线（建议只做一个）：Agentic verifier (env. access)**，Flash APEX 上是 49.0 ± 0.8 [Table 2]。它和 VeriHarness 用同一个沙箱和工具，只是换一条打分指令，实现成本最低。它也是最关键的内部对照：如果你的 VeriHarness ≈ Agentic verifier，就说明协议或技能没有起作用（论文的结论是：只有环境访问只能拿到约一半的增益 [txt L482–484]）。
- **备选实现路径**：如果代码仓库暂时跑不起来，可以把协议和技能作为指令放进 Gemini CLI 0.46.0 运行。Flash APEX 上 CLI 版本是 51.3 ± 1.1，与专用 runtime 相差约 2 点 [Table 2；txt L486–491]。但 CLI 的成本约为 3 倍 [txt L1936–1937]。

### 第 3 步：怎样算复现成功
记 *S* = 存档分（全同任务）+ verifier 选中 rollout 的存档分（差异任务），按全部 480 个任务计算。
1. **数值一致**：*S* 落在论文均值 ± 2 倍跨 seed 标准差加抽样误差之内。对 Flash APEX 来说，大约是 **[50.9, 55.7]**。如果只抽样了部分差异任务，用 bootstrap 估计置信区间，要求 53.3 落在你的 95% CI 内。
2. **方向一致**：*S* − single > 0，且 VeriHarness (select) > Agentic verifier，要求在差异任务上做配对比较（同一任务、同一个池）。
3. **过程一致**（辅助判断）：每任务成本和 $1.44 在同一数量级；技能调用分布大致符合 Figure 7，例如 APEX 上 resolve-answer 和 falsify-answer 应该是主要被调用的技能。
4. 第 1 条不满足、但第 2 条满足：说明方法有效、实现有偏差。优先排查 G3/G4（技能和 prompt）和 G5（预算上限）。

### 第 4 步：之后和你的方法比较时需要注意
- 比较必须基于**同一个冻结池**（同样 N=10、同一个生成模型）和**同一个 verifier 模型**（同模型设定，[txt L976–979]）。如果你的方法改的是生成侧（长程执行中的幻觉），它就和 VeriHarness 不在同一个比较框架里：VeriHarness 要求池固定。这时需要另行设计"你的方法生成的池 + 统一的选择器"之类的对比。
- 你的方法如果产生新产物，就必须重新判分。到那时 C1（判官版本）、G13/G14（判分细则）和"存档 base 分 + 同轮差值"的协议 [txt L1397–1399] 都要落实。建议也和 **VeriHarness 完整版（带 revision，Flash APEX 54.8）** 以及 **Agentic verifier + revision（50.5）** 比较，而不只是和 select 比。

---

## 附：关键数字速查（全部可回原文核对）
- 池：N=10 [txt L430]；3 次 verifier 运行 [txt L475]；thinking high [txt L463]
- Flash APEX：single 48.1 / select 53.3±1.2 / Agentic verifier 49.0±0.8 / LLM-as-V 49.8±0.5 / oracle 67.3 / full 54.8±1.0 [p.8 Table 2]
- Flash WSB：single 56.5 / select 62.0±0.9 / LLM-as-V 60.4±0.2 / oracle 70.3 [p.8 Table 2]
- 成本：select 每任务 Flash $1.44、Opus $3.92；全价 $5.40 / $13.06 [txt L1932–1942]
- 判官：APEX、JobBench 写作 "Gemini 3 Flash" [txt L1392–1393]；WSB 是 Claude Code + Opus 4.8 [txt L1393–1394]
- 公开资源：HF `caiqizh/veriharness`、GitHub `google-research/veriharness` [txt L1430–1431]
