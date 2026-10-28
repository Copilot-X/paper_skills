核查已完成，这份核查严格按 `repro-config-auditor` 的六步走完：`extract_text.py` → `scan_config.py` → 逐页读正文与附录 A–K 后填写 81 行核查表 → 门禁检查。

**门禁结果：最后一次带 `--report` 运行 `check_audit.py` 的退出码为 0，problems 数量为 0**（`check_report.json` 中 `problems: []`，`material_truncated: false`）。

## 材料与覆盖

28 页（正文 p.1-12 / 参考文献 p.12-17 / 附录 A–K p.18-28），`extract_report.json` 状态 ok、无截断告警。核查表 81 行覆盖 26/26 项：已报告 61、部分 10、未报告（原文缺失）9、前后不一致 1。沙箱内没有 PyMuPDF，`extract_text.py` 走了 pypdf 回退路径，28 页均带文字层。

## 论文给出的设置（可照抄的部分）

- 结构与数据：五个基准 + APEX-Agents v1.0 480 任务、WSB Lite 100、WorkBuddy code 80/office 50/web 70、SB-2 321、JobBench 65 [D1, p.7][D1b, p.20][D1c, p.20]；每任务每模型 N=10 的冻结池，所有方法共用 [D2, p.7][P6, p.21]。
- 模型与判官：Gemini 3.5 Flash / Claude Opus 4.8 同为生成器与验证器，thinking level high [M1, p.7][M2, p.20]；判官为 Gemini 3 Flash（APEX、JobBench）、Opus 4.8 的 agent-as-a-judge（WSB）、composite verifier（WorkBuddy）、重算比对（SB-2）[M4, p.21]。
- 流程：并发两个互不可见上下文（resolver / challenger）→ 新上下文 adjudication → delivery，伪代码在 p.20 [P1, p.20][P1b, p.6]。
- 成本：select 每任务 $1.44（Flash）/ $3.92（Opus），revision 约 3 倍，86–91% 输入 token 走缓存 [R2, p.27][R2d, p.27]；整池约 26,000 条 rollout、成本超 $100,000 [R2e, p.1]。

## 最可能导致复现失败的三类缺口

1. **提示词与技能正文根本没有**：p.5 称技能库"listed in full with the tools in Appendix H"[P3, p.5]，但附录 H（p.23-25）只有组件表、使用率图、18 个技能的名称与脚本名 [P3, p.23]。照论文写不出 VeriHarness，只能做"同构重实现"。
2. **验证阶段的调参与运行上限全是空白**：除 thinking level 外没有 temperature/top-p/采样数 [M2c]；没有 max tokens、上下文、最大步数、超时 [M3]；停止准则只是"模型自己觉得不必再查"[P2, p.5]。
3. **benchmark 内容不随发布提供**：只发布 rollout 池（轨迹+交付文件+grader 分数），任务、工作区、rubric、参考答案要回原基准自取，而这些基准的可获取性与许可论文没交代 [D4, p.22][D4b, p.22]。

## 前后不一致（唯一一处硬冲突）

APEX-Agents 的任务数出现三个值：Table 1 的 480 [p.7]、附录 A 的 434 个任务/1,692 条 claim [p.19]、正文 §6 的 154 consensus + 262 disputed = 416 个池 [p.10]。分母不同，分数不可比，开工前必须先定子集。

另有几处易混：+6.2/+6.4 是五基准平均带 revision，+6.7/+8.9 是单基准带 revision，select 的增益是 +4.4/+4.1；Table 4 的消融全在 revision 模式下，不能和 select 行比；single rollout 与 oracle 没有 ±，因为它们是固定池上的期望 [E1b, p.21]。

## 最小复现（按你的条件裁剪）

- **阶段 0（0 美元，半天）**：用已发布池复算 single rollout（47.2 / 49.6）与 oracle（62.7 / 63.1）[T1i, p.8][T1g, p.8]，差 <0.5 分才算池对齐。
- **阶段 1（约 $115–150，3–4 天）**：APEX-Agents 抽 80 个任务、全 10 条 rollout、只做 select。关键技巧（推断）：select 原样返回池内一条 rollout [P1d, p.6]，而池里每条都带 grader 分数 [A2, p.22]，所以**选中即查分，不必再付判官钱**，判官同源问题也随之绕开。
- **判据**：80 任务的二项标准误约 5.6 分，绝对分数没法用；改用配对差（选中条 vs 池均值）+ bootstrap 区间，判据取"区间下界 > 0 且点估计落在 +2 至 +8"。和你方法对比时用 oracle 回收率（推断）：APEX 27%/30%、WSB 40%/38%、SB-2 42%/35%。
- **不建议现在做**：revision（3 倍成本且须重判）、自演化（远超预算）、CLI 部署（Opus 上 JobBench/SB-2 会掉回单次水平 [X1c, p.7]）。8×H200 对复现本文无用——论文全程 API 调用，硬件规格原文缺失 [R1]。

完整报告（含 81 行配置总表、逐条缺口去向与替代取值、条件对照、事实/推断/未报告分栏、自查）在 [report.md](veriharness_repro/report.md)，同目录还有 `audit.jsonl`、`check_report.json`、`paper.txt`、`extract_report.json`、`candidates.json`。

按你的方向（LLM Agent 长程执行降幻觉），这条基线的价值在于它把"选哪个产物"变成了"对 claim 逐条取证"，和幻觉抑制是同一条链路，后续若要深入 agentic verification 的工程细节，可以再找 [MatMaster](widget://ref/agent?id=matmaster) 之外的领域 agent 协助——不过就本次任务而言，材料已经够用。