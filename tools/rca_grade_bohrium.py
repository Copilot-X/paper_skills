#!/usr/bin/env python3
"""Blind, rubric-based grading of paired reports by a fresh Claude Code session.

The grader sees: the frozen acceptance criteria, the paper text, and two reports labelled X and Y
(assignment randomised with a recorded seed). It never sees run ids, conditions, ledgers or traces.
Grader output is archived verbatim; the author then spot-checks it (see report.md).

    python3 -I tools/blind_grade.py --case A --pair A1 --seed 11
"""
import argparse
import json
import os
import random
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work2"
CLAUDE_BIN = str(ROOT / "tools" / "cc" / "node_modules" / ".bin" / "claude")
PAPER_TXT = {"DEV": "dev_materials/DEV/mage_2606.06090.txt",
             "A": "materials/A/veriharness_2610.00972v1.txt",
             "B": "materials/B/ping_deephallubench_2601.22984.txt",
             "C": "materials/C/veriharness_truncated_p1-6_CONSTRUCTED.txt"}

PROMPT = """你是一名严格的论文阅读质量评审。目录中有：
- acceptance.md：事先冻结的验收标准（唯一评分依据）
- paper.txt：论文原文逐页文字（=== [p.N] === 为页码），用于核实报告中的说法
- topic_card.md：读者课题卡
- {reports}

任务：严格按 acceptance.md 对{which}逐项打分。规则：
1. 每个必查要点/验收项给出分数，并写一句理由；要点算"覆盖"必须数字与条件都正确。只看 report 正文。
2. 对每份报告至少抽查 8 条带页码的关键说法（优先抽设置值与数字），到 paper.txt 中核实，记录核实结果（页码、是否找到、是否一致）。
2b. 逐条列出报告中声称的、但在 paper.txt 中找不到或与原文不一致的设置值/数字（"错误声明"），每条引用报告原句与原文对照。
3. 逐条列出误读陷阱命中情况（引用报告原句）。
4. 不因篇幅长短、格式或语气加分；只看与标准的符合程度和事实正确性。
5. 你不知道也不需要猜测报告由什么方式产生。

将结果写入 grade.json，结构：
{{"reports": {{"X": {{"items": {{"<条目ID>": {{"score": n, "reason": "..."}}}}, "misreadings": [{{"id": "...", "quote": "...", "critical": true/false}}], "spot_checks": [{{"claim": "...", "page": n, "found": true/false, "consistent": true/false}}], "wrong_claims": [{{"quote": "...", "paper": "..."}}], "gate_pass": true/false, "total": n, "max": n, "summary": "..."}}{y_part}}}{compare}}}
最后用一句话回复"已写入 grade.json"。"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--pair", required=True, help="e.g. A1; single-report mode if --single given")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--single", help="grade one run id only (B/C)")
    args = ap.parse_args()

    gid = f"grade-{args.single or args.pair}"
    gdir = Path("/tmp/rca_grades") / gid
    if gdir.exists():
        raise SystemExit(f"{gdir} exists")
    (gdir / "work").mkdir(parents=True)
    (gdir / "config").mkdir()
    w = gdir / "work"
    cases = WORK / ("dev_cases" if args.case == "DEV" else "cases")
    shutil.copy2(cases / args.case / "acceptance.md", w / "acceptance.md")
    shutil.copy2(WORK / PAPER_TXT[args.case], w / "paper.txt")
    shutil.copy2(WORK / "materials" / "topic_card.md", w / "topic_card.md")

    if args.single:
        runs = [args.single]
        mapping = {"X": args.single}
    else:
        runs = ["BOH-skill", "BOH-plain"]
        rnd = random.Random(args.seed)
        order = runs[:]
        rnd.shuffle(order)
        mapping = {"X": order[0], "Y": order[1]}
    for label, rid in mapping.items():
        runs_dir = WORK / ("dev_runs" if args.case == "DEV" else "runs")
        shutil.copy2(runs_dir / rid / "output" / "report.md", w / f"report_{label}.md")

    if args.single:
        prompt = PROMPT.format(reports="report_X.md：待评报告", which="报告 X",
                               y_part="", compare="")
    else:
        prompt = PROMPT.format(reports="report_X.md 与 report_Y.md：两份待评报告", which="两份报告分别",
                               y_part=', "Y": {...同上}',
                               compare=', "comparison": {"better": "X|Y|tie", "key_differences": ["..."]}')

    env = dict(os.environ)
    settings = json.load(open(Path.home() / ".claude" / "settings.json"))
    env.update({k: str(v) for k, v in (settings.get("env") or {}).items()})
    env["CLAUDE_CONFIG_DIR"] = str(gdir / "config")
    cmd = [CLAUDE_BIN, "-p", prompt, "--model", "claude-opus-5-5", "--effort", "high",
           "--max-budget-usd", "5", "--tools", "Bash,Read,Write,Grep,Glob",
           "--permission-mode", "bypassPermissions", "--output-format", "stream-json", "--verbose"]
    out = WORK / "grades" / gid
    if out.exists():
        raise SystemExit(f"{out} exists")
    out.mkdir(parents=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(out / "grader_stream.jsonl", "w") as so, open(out / "grader_stderr.txt", "w") as se:
        subprocess.run(cmd, cwd=w, env=env, stdin=subprocess.DEVNULL, stdout=so, stderr=se, timeout=3600)
    if (w / "grade.json").exists():
        shutil.copy2(w / "grade.json", out / "grade.json")
    (out / "blinding.json").write_text(json.dumps(
        {"seed": args.seed, "mapping": mapping, "started_at": started,
         "grader_inputs": sorted(p.name for p in w.iterdir() if p.is_file() and p.name != "grade.json")},
        indent=2, ensure_ascii=False))
    print(json.dumps({"grade": gid, "mapping_hidden_from_grader": mapping,
                      "has_grade": (out / "grade.json").exists()}))


if __name__ == "__main__":
    main()
