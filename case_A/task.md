# 案例 A：复现 VeriHarness 前的配置核查（必做，有/无 Skill 公平对照）

## 场景与用户
参赛者本人（"Agent 长程执行降幻觉"方向的研究工程师，课题卡见 `materials/topic_card.md`）要把 VeriHarness 作为对比基线：先复现它的选择（select）结果，再与自己的方法比较。过去两次复现都是跑完才发现漏了设置（判官模型版本、基准子集），各返工约一周。本次要在动手前，用一个下午把"论文给了什么、没给什么、哪里矛盾、先补什么"查清楚。

## 输入
- `materials/A/veriharness_2610.00972v1.pdf`（arXiv 2610.00972v1，28 页，CC BY 4.0）及同名 `.txt`（PyMuPDF 1.26.5 逐页导出，页码与 PDF 一致）
- `materials/topic_card.md`（读者条件）
- 提示词：`cases/A/prompt.txt`（with/without 逐字相同）

## 运行条件（两组一致）
Claude Code 2.1.309，claude-opus-5-5，effort high，单次预算上限 5 美元，工具 Bash/Read/Write/Edit/Glob/Grep/Skill，全新配置目录与工作目录，无联网工具；提示要求只依据论文本身。唯一差别：with 组工作目录下有 `.claude/skills/repro-config-auditor/`。

## 期望产出
`output/report.md`：复现就绪度结论、配置清单（值+页码或"未报告"）、阻断清单与补救途径、冲突与易错点、最小复现方案。

## 评判
见 `cases/A/acceptance.md`（运行前冻结）。每对 with/without 由新会话盲评（X/Y 随机，种子记录），另用脚本统计"原文中找不到的设置值/数字"。
