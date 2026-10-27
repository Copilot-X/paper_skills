# 论文原文片段（核查用）

论文：Zhang et al., *VeriHarness: Scaling Agentic Verification for Long-Horizon Tasks*，arXiv:2610.00972v1（2026-10-01），arXiv 页面标注许可为 CC BY 4.0。

以下片段用 PyMuPDF 1.26.5 从 PDF 逐页提取，页码是 PDF 页码。内容没有改写，保留了提取时产生的换行和连字符。完整 PDF 见 https://arxiv.org/abs/2610.00972v1 。

## p.1 · 摘要（这两个数字是带 revision 的结果）

```text
Across five long-horizon workspace
benchmarks and two frontier models, VeriHarness achieves the highest selection scores among the
evaluated baselines. Evidence-backed revision further improves average performance, bringing gains
over a single rollout to 6.2 points with Gemini 3.5 Flash and 6.4 points with Claude Opus 4.8.
```

## p.7 · §4.1 设置：模型、冻结池、基线、三次验证器运行

```text
Same-model comparison. We use Gemini 3.5 Flash and Claude Opus 4.8 as both generator and
verifier, with thinking level high. For every task and model, all methods receive the same frozen pool
of 𝑁= 10 rollouts and the same model. Outputs are scored by the benchmark graders, which are
never available to the verifier. Appendix D gives the task, runtime, and grading details.
Baselines. We compare VeriHarness with majority voting, best-of-𝑁judging, a pairwise tourna-
ment, and the most recent LLM-as-a-Verifier (Kwok et al., 2026). We also implement an agentic verifier
(env. access) given the same workspace and evidence tools as our verifier but no VeriHarness protocol
or skills. VeriHarness (select) returns the base chosen by adjudication, and VeriHarness also
applies the evidence-backed revision plan. For the latter, we add aggregation of the pool into a new
artifact (Lee et al., 2026b; Wang et al., 2025a), which also produces an artifact absent from the pool.
We also include an agentic verifier + revision baseline: the same model checks the pool against the
workspace, selects a base, and revises it using the same evidence tools. The grader-informed selection
oracle bounds selection from the fixed pool. We report each benchmark’s native score over three
independent verifier runs. Appendix D defines the baselines, metrics, and revision protocol.
```

## p.8 · 表 2 表注（select 与 revision 分开报告）

```text
Table 2 | Main results. Three-seed mean score on each benchmark’s own scale, with the cross-seed
standard deviation in gray; Avg is the unweighted mean over the five benchmarks, and gains are over
the single rollout. Within each model, bold marks the best score in the primary selection comparison
and, separately, among the methods with revision; CLI variants are reported separately, followed by
methods that produce new artifacts. The single rollout is a reference baseline. The selection oracle
takes the highest-scoring rollout per task under the benchmark grader and bounds selection from the
fixed pool; it does not bound revision. SB-2: SpreadsheetBench 2; WSB: Workspace-Bench Lite.
```

## p.8 · 表 2 中 select 相关行（逐行原样提取）

PyMuPDF 把表格拆成一格一行。列的顺序与表头一致：Avg、APEX、WSB、WorkBuddy、SB-2、JobBench。下面是 Flash 和 Opus 的 single rollout 行与 VeriHarness (select) 行，以及紧随其后的 "gain over single rollout" 行。

```text
Gemini 3.5 Flash
Single rollout
47.2
48.1
56.5
73.2
27.3
30.9
...
VeriHarness (select)
51.6
53.3 ±1.2
62.0 ±0.9
77.8 ±1.4
31.5 ±2.4
33.5 ±1.8
gain over single rollout
+4.4
+5.2
+5.5
+4.6
+4.2
...
Claude Opus 4.8
Single rollout
49.6
35.8
60.5
79.0
30.1
42.8
...
VeriHarness (select)
53.7
41.2 ±0.7
65.0 ±0.5
83.0 ±0.4
33.4 ±1.2
46.1 ±0.8
gain over single rollout
+4.1
+5.4
+4.5
+4.0
+3.3
```

读法（作者判断）：Flash 的 select 平均分是 51.6，比单 rollout 的 47.2 高 4.4；Opus 的 select 平均分是 53.7，比单 rollout 的 49.6 高 4.1。摘要里的 6.2 / 6.4 是表中另一组 "With revision" 的结果。

（对照：玻尔 Uni-Parser 把同一张表还原成了 Markdown 表格行，例如 "| VERIHARNESS (select) | 51.6 | \(53.3 \pm 1.2\) | ..."，见 §6。）

## p.19 · 附录 A：temperature zero 只用于离线分析

```text
A. Claim-Level Analysis Protocol
This appendix describes how the claim statistics of Figure 2 are computed. The analysis uses the
ten-rollout pools of Claude Opus 4.8 on APEX-Agents and covers 434 tasks and 1,692 claims. It is an
offline analysis that reads the benchmark’s rubrics, which the verifier never sees.
Claims and values. Each rubric criterion names one quantity or determination that the answer
should state, and we treat each criterion as one claim 𝑝. Claude Opus 4.8 reads the ten answers at
temperature zero and records the value 𝑣𝑖,𝑝that each rollout asserts for the criterion. Numbers count
as the same value when they agree at the criterion’s precision, determinations count as the same value
when they state the same conclusion, and a rollout that does not address the criterion receives the
value absent. The grouped values give 𝜋𝑝and 𝐻(𝜋𝑝) in Eq. (1), which yields 917 consensus claims
and 775 disputed claims.
```

## p.20 · 附录 D：基准子集与生成脚手架

```text
D. Experimental Details
Benchmarks. All five benchmarks require an agent to produce an artifact from a workspace without
exposing the grading rubric or reference answer. APEX-Agents (Vidgen et al., 2026) contains long-
horizon investment-banking, legal, and consulting tasks in file-rich simulated environments. All
our experiments use version 1.0 of the benchmark. Workspace-Bench (Tang et al., 2026) contains
realistic workspaces with large file-dependency graphs; we use its 100-task Lite subset. WorkBuddy
Bench (WorkBuddy Team et al., 2026) contains tasks derived from real commits and business scenarios;
we evaluate its code, office, and web domains, with 80, 50, and 70 tasks, and do not run its security
domain, whose tasks consistently trigger safety alerts from the model APIs. SpreadsheetBench 2 (Zhu
et al., 2026) evaluates financial modeling, template completion, debugging, and visualization in
large workbooks. JobBench (Li et al., 2026b) covers 35 white-collar occupations with heterogeneous
reference files.
Models and rollout pools. We use Gemini 3.5 Flash and Claude Opus 4.8 with the thinking level set
to high. For each benchmark and model, the generator runs in the benchmark’s own agent scaffold
with its standard tools and instructions and produces 𝑁= 10 rollouts per task. The scaffolds are the
APEX-Agents agent runner with its tool servers, opencode for JobBench, the SpreadsheetBench 2
agent with its shell and spreadsheet-viewing tools, and Claude Code for WorkBuddy Bench and
Workspace-Bench Lite. Both models use the same scaffold on each benchmark.
```

## p.21 · 附录 D：运行时与评分协议

```text
Harness runtime. Our runtime is a thin layer over the open-source pi coding agent (MIT license),
which provides the agent loop, tool calling, and session records; Claude is served through a local
LiteLLM proxy. The verifier has file reading, search, and shell tools. Rollouts, task inputs, and the
environment are mounted read-only in a sandbox with no network access; only the output directory
is writable. Spreadsheets are also rendered as cell-level text for comparison, and evidence skills cover
spreadsheets, documents, presentations, PDFs, document bundles, and code patches (Appendix H).
The two investigations run concurrently in separate contexts of the same model, and neither reads
the other’s record. Adjudication opens a fresh context that receives the two evidence records, and
delivery continues in the adjudication context. The CLI rows of Table 2 run the same instruction and
skills inside Gemini CLI 0.46.0, Claude Code 2.1.246, and Codex 0.149.1, using each CLI’s own tools
and sandbox in place of our runtime.
Grading protocol. Each benchmark’s own grader scores the delivered artifacts; the verifier never
accesses that grader. APEX-Agents and JobBench grade each rubric item with an LLM judge, for which
we use Gemini 3 Flash. Workspace-Bench Lite uses its agent-as-a-judge, a Claude Code agent with
Claude Opus 4.8. WorkBuddy Bench uses its composite verifier, which applies tests and rules in the
code domain, rules and an LLM judge (Gemini 3.5 Flash) in the office domain, and the benchmark’s
judge pipeline in the web domain. SpreadsheetBench 2 recalculates the delivered workbook and
compares it cell by cell with the reference workbook. When the grader is a judge model, the base
and delivered rollouts are scored in the same round. We report the archived base score plus their
same-round difference, which controls for judge drift between rounds.
```

## p.21 · 附录 D：指标口径与种子

```text
Metrics. Scores use each benchmark’s native scale: task success rate for APEX-Agents, mean rubric
score for JobBench and Workspace-Bench Lite, the task-weighted mean across WorkBuddy Bench’s
three domains, and headline accuracy for SpreadsheetBench 2. We report the three-seed mean, gain
over the single-rollout score, and cross-seed standard deviation. The single-rollout mean and oracle
are expectations over the fixed pool and require no resampling.
```

## p.22 · 附录 E：公开的 rollout 池

```text
E. Released Rollout Pool
We release the rollout pools used in this paper at https://huggingface.co/datasets/caiqizh/
veriharness and the verification code at https://github.com/google-research/veriharness.
The release covers both models on all five benchmarks with ten rollouts per task. For each rollout, it
contains the trajectory, the delivered files, and the score assigned by the benchmark’s grader. The
release contains no benchmark content: task descriptions, input workspaces, rubrics, and reference
answers are not redistributed, and every rollout carries the official task identifier, so the inputs can
be obtained from the original benchmark. Results that depend only on the pool can therefore be
reproduced without running a model, including the single-rollout and selection-oracle rows of Table 2
and the curves of Figure 6.
```

## p.26 · 附录 I：固定种子未给取值；不确立显著性

```text
The split uses a fixed seed, balances task categories as far as the grouping
permits, and is shared by conditions A–D throughout.
...
The figures report point estimates and do not establish statistical significance.
```

## p.27 · 附录 K：成本口径（部分为估算）

```text
Metering. Costs are computed from the token counts of the runs at list price, with cached input
charged at the cache-read rate. Gains are the five-benchmark means of Table 2. LLM-as-a-Verifier is
run with four evaluations per comparison. Majority voting, best-of-𝑁, and the CLI runs are estimates
from their call counts and context sizes rather than metered runs and are shown with hollow markers
and an asterisk; the aggregation baseline calls its own client and could not be metered.
```
