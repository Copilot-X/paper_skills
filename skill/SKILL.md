---
name: repro-config-auditor
description: Reproduction-readiness audit of ONE research paper. Use when the user wants to reproduce a paper, re-implement it as a baseline, or compare their numbers against it, and asks what exact settings the paper reports and what is missing -- e.g. "我要复现这篇论文，帮我把实验配置理清楚", "这篇论文作为基线，哪些设置没写", "check whether this paper gives enough detail to reproduce Table 2". Produces a 26-item configuration audit (models, decoding, data subset, prompts, baselines, metrics, judges, variance, cost, code) where every reported value is tied to a machine-verified verbatim quote with page, every gap is marked not_reported only after the candidate pages were checked, plus a gap list with who/where to ask and a minimal reproduction plan. Not for deciding whether a method is a good idea, literature surveys, or running the paper's code.
---

# Repro Config Auditor（复现配置核查）

复现或拿论文当基线前，先把"论文到底给了哪些设置、哪些没给"逐项查清。每个设置要么有原文逐字引文和页码，要么明确写"原文未报告，已查过第几页"。要等到复现出来的数字对不上，才发现漏了温度、子集、判官模型或提示词，那时才查就晚了。

## 输入
- 必需：论文文件（PDF，或逐页 `.txt`）。
- 可选：用户的复现目标与约束（要复现哪个结果、可用模型/算力/预算、课题卡）。没有时按"复现主表核心结果"处理。
- 可选：输出目录（默认 `output/`）、语言（默认跟随用户）。

## 输出（写入输出目录）
1. `report.md`：给用户的复现就绪报告（模板见 `references/report_template.md`）。
2. `audit.jsonl`：26 项配置核查表，每项一行或多行（清单与状态定义见 `references/checklist.md`）。
3. `check_report.json`：`check_audit.py` 的门禁结果（脚本生成，不可手写）。
4. `paper.txt`、`extract_report.json`、`candidates.json`：提取与检索的中间结果。

## 执行步骤（按顺序，不跳步）
`$SKILL` 指本 SKILL.md 所在目录。

### 第 1 步 提取原文并诊断
```
python3 $SKILL/scripts/extract_text.py <paper.pdf> --out-dir <output>/
```
读取 `extract_report.json`。若 `status` 为 `degraded`/`unreadable`，先看"异常处理"。之后所有引文都从 `<output>/paper.txt` 复制。

### 第 2 步 按清单逐页检索候选位置
```
python3 $SKILL/scripts/scan_config.py --paper <output>/paper.txt --out <output>/candidates.json
```
脚本对 26 项各列出提到它的页（正文/附录分开，跳过参考文献页）。**检索结果只是线索**：每项至少打开 `top_pages` 里的页逐段读；附录（实现细节、提示词、超参表）是这类信息最集中的地方，必须读完。

### 第 3 步 读全文，逐项填 `audit.jsonl`
先通读正文与全部附录，再按 `references/checklist.md` 的 26 项逐项填写。字段：
- `id`（如 `M1`、`M1b`）、`item`（清单 ID）、`status`（`reported`/`partial`/`not_reported`/`conflicting`/`not_applicable`/`not_in_material`）
- `value`：原文给出的设置值（`reported`/`partial` 时写；其中的每个数字都必须出现在 `quote` 里）
- `quote` + `page`：从 `paper.txt` **逐字复制**的单段连续原文（≤300 字符，不拼接、不翻译）；`conflicting` 另加 `quote2` + `page2`
- `missing`：复现还缺什么，写具体（"未给 temperature"而不是"细节不足"）
- `searched`：`not_reported`/`not_in_material` 时必填，列出实际查过的页码（须包含 `candidates.json` 中该项的全部 `top_pages`）
- `next_step`：缺口去哪补（附录节号、代码仓库、作者邮件、被引的原始基准论文），未亲自确认的材料写成"查找建议"
- `impact`：`high`/`medium`/`low`，即这项错了会不会让 T1 主结果复现不出来（判官、子集、模型版本、候选数通常是 high）
- `note`：可选；由原文推出的内容以"推断："开头，并写出依据

规则：
- 同一项有多个值（多个基准、多个模型、不同实验用不同设置）时，**拆成多行**（`M1`、`M1b`…），并在 `value` 写清各自对应的实验。不要只挑主实验。
- 只有原文正面写出的值才能标 `reported`。"following prior work"、"see code"、"standard settings"一律标 `partial`，在 `missing` 写缺什么。
- `not_reported` 只有在打开过候选页以后才能写。写了不等于真没有：在 `next_step` 里给出最可能的出处。
- 摘要/引言中的数字要和正文表格核对，不一致就标 `conflicting`。
- 数字所依据的表/图/附录如果**不在材料里**（文件被截断或只有节选），即使原文写了"(Table 2)"，这个值也只是声称，标 `partial`，在 `missing` 中写"所引 Table 2 不在材料中，未能核实"，不能标 `reported`。

### 第 4 步 门禁检查（必须通过）
```
python3 $SKILL/scripts/check_audit.py --paper <output>/paper.txt --audit <output>/audit.jsonl --candidates <output>/candidates.json --out <output>/check_report.json
```
写完 `report.md` 后，加上 `--report <output>/report.md` 再运行一次（见第 6 步）。脚本会列出正文提到、但文件里没有的表/图/附录（`material_missing_objects`）。
退出码非 0 时按每条 `PROBLEM` 修正后重跑，直到退出码为 0：
- 引文找不到：回 `paper.txt` 重新复制原文；确实没有原文支撑的，改为 `partial`/`not_reported`；
- 页码不对：改正页码；
- `value` 中的数字在引文里找不到：换一句包含该数字的原文，或删掉这个数字；
- `searched` 缺候选页：去读那几页，读完再决定状态。
- `relies on [...] which is not in the material`：这个值所引的表/图/附录不在文件里，改为 `partial`，并写明"未能核实"；
- `says 'not reported' although the material is incomplete`：材料不完整时，报告里不能说"论文/原文未报告"。改写为"材料中未见（文件缺 §x/附录 y），需完整版确认"；只有确认属于论文本身的空白（例如完整的附录里确实没有）时，才在同一句里说明依据。

**不得为了通过检查而删除行或把有原文的项改成 `not_applicable`。**

### 第 5 步 复现风险与最小方案
在 `audit.jsonl` 的基础上：
1. 列出 `impact=high` 且状态不是 `reported` 的项，这就是复现阻断清单。按影响排序，每条写清缺什么、去哪补；补不到时给出可接受的替代取值和理由，替代取值以"推断："开头。
2. 用户有约束时（模型、预算、不能训练等），逐条对照论文设置写成"条件对照"：用户条件、论文设置、出处、差异对复现结果的影响。
3. 最小复现方案：先复现哪个数字、用多大的子集、什么对照、算作"复现成功"的阈值（相对论文报告值的容差，并说明依据，例如论文报告的标准差，或"未报告方差，阈值为假设"）。

### 第 6 步 写 `report.md`
按 `references/report_template.md` 写。报告中出现的每个设置值都要标 `[M1, p.N]`，即核查表 ID 和页码。推断以"推断："开头，原文未给出的以"未报告："开头。材料不完整时，用"材料中未见："代替"未报告："。
写完后带 `--report <output>/report.md` 重跑第 4 步的门禁命令，直到退出码为 0。

## 质量检查（交付前逐项自查，写进报告末尾"自查"）
- [ ] `check_report.json` 中 `problems` 为空，26 项全部覆盖；最后一次检查带了 `--report`。
- [ ] 附录每一页都读过；附录中的超参表、提示词、实现细节已进入核查表。
- [ ] 多值项已拆行，没有只写主实验。
- [ ] 每个 `not_reported` 都有 `searched` 和 `next_step`；每个 high 缺口都出现在阻断清单里。
- [ ] 报告中没有核查表之外的设置值或数字。

## 异常处理
| 情况 | 识别信号 | 处理 |
|---|---|---|
| 材料不完整（截断、缺附录、只有节选） | `extract_report.json` 的 warnings 提示截断或缺参考文献；`check_report.json` 的 `material_missing_objects` 非空 | 报告开头写明缺了什么、依据是什么；所引表格缺失的数字（包括摘要里的结果数字）一律写"仅摘要/正文声称，所引表格不在材料中，未能核实"，不能作为复现目标的已知值；正文提到但文件里没有的部分，相关项标 `not_in_material`（不是 `not_reported`），`searched` 写已查页；就绪度结论写"材料不完整，无法判定"，分成"可判定项/需完整版"两栏；建议获取完整版的途径。不得用记忆补全。 |
| 无文字层（扫描版） | 多数页 < 200 字符 | 停止核查，说明需要 OCR 或文字版 |
| 无法打开 | `status: unreadable` | 停止，报告错误信息，请用户重新提供文件 |
| 缺依赖 | ImportError | 尝试 `pip install pymupdf`；仍失败则使用用户提供的 `.txt`，并在报告中声明 |
| 用户只要部分项 | 例如"只看评测设置" | 仍填 26 项（其余项可简写），报告只展开用户关心的部分 |

## 适用边界
- 适用：有实验的单篇实证/方法/基准论文（ML/AI 优先，其他有实验设置的领域亦可），文字层可提取。
- 不适用：判断方法好不好、跨多篇综述、纯理论证明、读图中数值（图里的数字标"需人工读图"）、运行论文代码。
- 不联网；代码仓库、被引文献只列为"查找建议"，不描述其未经确认的内容。
