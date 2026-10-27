# 案例 A 验收标准（运行前冻结）

论文：VeriHarness（arXiv 2610.00972v1）。读者目标：复现选择（select）结果并作为基线。

## 评分规则
- G1–G32 每项 2 分（满分 64）：值或"未报告/不一致"的判断正确，且给出正确页码（±1 页可接受）= 2；提到了但缺关键值、缺页码、或判断含糊 = 1；未提及或错误 = 0。
- "未报告"类条目（标 ★）：报告须明确指出论文没有给出该项，才得 2 分；只说"见代码"而不指出论文未写，得 1 分；给出论文中并不存在的具体值，得 0 分，并计误读。
- 误读陷阱 M1–M6：每命中一处扣 2 分（引用报告原句）。
- 门槛（任一不满足则不合格）：报告给出复现就绪度结论；至少 15 个设置值带页码；没有关键误读（M1/M2/M3）。
- 额外记录（不计分，用于对照）：报告中在原文找不到或与原文不一致的设置值/数字条数；耗时；估算成本。

## 必查要点
| ID | 要点 | 页 |
|---|---|---|
| G1 | 生成器与验证器同一模型：Gemini 3.5 Flash 与 Claude Opus 4.8，thinking level high | 7, 20 |
| G2 | 模型版本/快照日期、API 调用日期区间 ★未报告 | — |
| G3 | 解码参数（temperature/top-p）★未报告；唯一给出的是附录 A 离线分析中 Opus 读答案时 temperature zero（不是主实验） | 19 |
| G4 | 验证器的步数/轮数/token/时间上限 ★未报告（只说验证器自行决定何时停止） | 5 |
| G5 | 五个基准与版本：APEX-Agents v1.0、Workspace-Bench 的 100 题 Lite 子集、WorkBuddy Bench、SpreadsheetBench 2、JobBench | 7, 20 |
| G6 | 任务数：480 / 100 / 200 / 321 / 65（表 1） | 7 |
| G7 | WorkBuddy 只跑 code/office/web（80/50/70），不跑 security 域及原因 | 20 |
| G8 | 每任务每模型 N=10 rollouts，冻结后所有方法共用同一池 | 7, 21 |
| G9 | 生成脚手架：APEX 用官方 runner、JobBench 用 opencode、SB-2 用官方 agent、WorkBuddy 与 WSB 用 Claude Code | 20 |
| G10 | 发布的 rollout 池（HuggingFace caiqizh/veriharness）与代码（github google-research/veriharness）；池不含基准内容，需从原基准获取输入 | 22 |
| G11 | 验证器运行时：基于开源 pi coding agent（MIT）的薄层，Claude 经本地 LiteLLM 代理；只读沙箱、无网络、仅输出目录可写 | 21 |
| G12 | 工具：read/ls/find/grep/bash/write/edit（写入限输出目录）；表格渲染为单元格文本 | 21, 24 |
| G13 | 技能库 18 个（6 evidence / 4 resolve / 3 falsify / 5 repair），附录 H 表 6 列出名称与脚本 | 24, 25 |
| G14 | 协议：resolver 与 challenger 并行、独立上下文、互不可见；新上下文裁决，并在裁决上下文中交付；算法 1 | 6, 20, 21 |
| G15 | 验证器各阶段的提示词全文 ★未在论文中给出（只有协议描述与技能表） | — |
| G16 | 基线定义：多数投票、best-of-N 判官、两两锦标赛、LLM-as-a-Verifier、agentic verifier（同沙箱同工具、单一评分指令、无协议/技能） | 7, 21 |
| G17 | LLM-as-a-Verifier 每次比较 4 次评估 | 27 |
| G18 | 基线的提示词/其余超参（如锦标赛配对方式、best-of-N 判官提示）★未报告 | 21 |
| G19 | 评分：APEX 与 JobBench 用 Gemini 3 Flash 做逐项判官；WSB 用 Claude Opus 4.8 的 Claude Code agent-as-a-judge；WorkBuddy office 用 Gemini 3.5 Flash 判官 | 21 |
| G20 | 判官漂移控制：基础与交付 rollout 同轮评分，报告"存档基础分 + 同轮差值" | 21 |
| G21 | 指标口径：APEX 任务成功率、JobBench/WSB 平均 rubric 分、WorkBuddy 三域按任务加权、SB-2 headline accuracy；Avg 为五基准不加权平均 | 8, 21 |
| G22 | 三个独立验证器运行（three seeds），报告均值与跨种子标准差；单 rollout 与 oracle 为池上期望，无需重采样 | 7, 8, 21 |
| G23 | 种子具体取值 ★未报告；显著性检验 ★未报告（附录 I 明说不确立统计显著性） | 26 |
| G24 | 复现目标（选择）：Flash select Avg 51.6（+4.4），Opus select Avg 53.7（+4.1）；带修订 53.4（+6.2）/ 56.1（+6.4）——须区分 select 与 revision | 8 |
| G25 | 仅凭发布的池即可复现单 rollout 与 selection oracle 行及图 6，无需运行模型 | 22 |
| G26 | 成本：Flash select $1.44/任务、Opus select $3.92/任务；修订约 3 倍；按标价、缓存按 cache-read 计；缓存全价时 $5.40 / $13.06 | 27 |
| G27 | 部分成本为估算非实测：多数投票、best-of-N、CLI 行为估算；聚合基线未计量 | 27 |
| G28 | 生成 rollout 池总成本超过 $100,000、约 26,000 条（复现者应直接用发布的池） | 1 |
| G29 | CLI 版本：Gemini CLI 0.46.0、Claude Code 2.1.246、Codex 0.149.1；Opus 在 JobBench（及 Claude Code 在 SB-2）回落到单 rollout 水平 | 7, 21 |
| G30 | 消融（附录 F 表 4）：resolver only / challenger only / 无技能 / 单上下文，Opus Avg 54.3 / 52.6 / 53.8 / 55.3（均为带修订分数） | 23 |
| G31 | 自进化实验：约 3:1 开发/留出划分、固定种子（取值未报告）、K=3 后 K=5、脚本限时 10 分钟、轮数 C 10 / D 8；APEX 排除文件交付任务、SB-2 只含模板与财务模型任务，所以分数与表 2 不同 | 9, 26 |
| G32 | Figure 1 的数字是 Flash 带修订（非 select），图注中 APEX +6.7、WSB +8.9 | 1 |

## 误读陷阱（每处 −2）
- M1：把带修订的 6.2/6.4 当作选择（select）结果或复现目标。
- M2：编造论文没有给出的 temperature、种子值、步数上限、提示词内容等具体数值。
- M3：把附录 A 离线分析的 temperature zero 说成主实验的解码设置。
- M4：把 Figure 4/附录 I 的留出子集分数与表 2 全量分数混为一谈。
- M5：把 Workspace-Bench Lite 当作完整 Workspace-Bench，或把 WorkBuddy 200 题说成包含 security 域。
- M6：把多数投票/best-of-N/CLI 的估算成本当作实测成本。
