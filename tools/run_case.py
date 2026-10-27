#!/usr/bin/env python3
"""Run one case condition in a fresh, isolated Claude Code session and archive everything.

    python3 -I tools/run_case.py --run-id A1-with --case A --condition with_skill
    python3 -I tools/run_case.py --run-id A1-without --case A --condition without_skill

Isolation / fairness:
  * fresh CLAUDE_CONFIG_DIR per run (no user plugins, memory, CLAUDE.md, MCP or history);
  * fresh working directory per run containing only materials/ (+ .claude/skills/ for with_skill);
  * identical model, effort, budget, tool allow-list, permission mode and prompt for both conditions.
Credentials are read from ~/.claude/settings.json "env" at run time and passed only through the
process environment; they are never written to the run directory or the archive.
"""
import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Path-adapted for the submission/ layout (skill/, materials/, cases/, runs/). Run logic (model, effort,
# budget, tools, permissions, isolation) is identical to the script that produced the archived runs.
WORK = ROOT
SKILL_SRC = ROOT / "skill"
RUNS_DIR = ROOT / "runs"
SANDBOX = Path("/tmp/rca_runs")
# Claude Code 2.1.309 is required (older global builds are rejected for claude-opus-5-5).
# Install it locally:  npm install --prefix tools/cc @anthropic-ai/claude-code@2.1.309
CLAUDE_BIN = str(ROOT / "tools" / "cc" / "node_modules" / ".bin" / "claude")

MODEL = "claude-opus-5-5"
EFFORT = "high"
BUDGET_USD = "5"
TOOLS = "Bash,Read,Write,Edit,Glob,Grep,Skill"
CASE_MATERIALS = {"A": ["A"], "B": ["B"], "C": ["C"], "DEV": ["DEV"]}


LOCK_FILE = WORK / "cases" / "skill_v1.1_lock.sha256"


def assert_skill_locked():
    import hashlib
    for line in LOCK_FILE.read_text().splitlines():
        digest, rel = line.split(None, 1)
        actual = hashlib.sha256((SKILL_SRC / rel).read_bytes()).hexdigest()
        if actual != digest:
            raise SystemExit(f"skill file {rel} changed since version lock; refusing to run")
    listed = {l.split(None, 1)[1][2:] for l in LOCK_FILE.read_text().splitlines()}
    present = {str(p.relative_to(SKILL_SRC)) for p in SKILL_SRC.rglob("*") if p.is_file()}
    if listed != present:
        raise SystemExit(f"skill file set differs from lock: {sorted(listed ^ present)}")


def main():
    assert_skill_locked()
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--case", required=True, choices=["A", "B", "C", "DEV"])
    ap.add_argument("--condition", required=True, choices=["with_skill", "without_skill"])
    ap.add_argument("--timeout", type=int, default=3600)
    args = ap.parse_args()

    run_root = SANDBOX / args.run_id
    if run_root.exists():
        raise SystemExit(f"{run_root} exists; refusing to reuse a run directory")
    workdir, cfgdir = run_root / "work", run_root / "config"
    (workdir / "materials").mkdir(parents=True)
    (workdir / "output").mkdir()
    cfgdir.mkdir()
    if (WORK / "materials" / "topic_card.md").exists():
        shutil.copy2(WORK / "materials" / "topic_card.md", workdir / "materials" / "topic_card.md")
    dev = args.case == "DEV"  # development-only paper, never part of the submission
    for sub in CASE_MATERIALS[args.case]:
        src = WORK / ("dev_materials" if dev else "materials") / sub
        shutil.copytree(src, workdir / "materials" / sub)
    if args.condition == "with_skill":
        shutil.copytree(SKILL_SRC, workdir / ".claude" / "skills" / "repro-config-auditor")
    prompt = (WORK / ("dev_cases" if dev else "cases") / args.case / "prompt.txt").read_text(encoding="utf-8")

    env = dict(os.environ)
    settings = json.load(open(Path.home() / ".claude" / "settings.json"))
    env.update({k: str(v) for k, v in (settings.get("env") or {}).items()})
    env["CLAUDE_CONFIG_DIR"] = str(cfgdir)
    # python3 with PyMuPDF must be on PATH for both conditions (e.g. activate a venv first)
    cmd = [CLAUDE_BIN, "-p", prompt, "--model", MODEL, "--effort", EFFORT,
           "--max-budget-usd", BUDGET_USD, "--tools", TOOLS,
           "--permission-mode", "bypassPermissions",
           "--output-format", "stream-json", "--verbose"]

    out_dir = RUNS_DIR / args.run_id
    if out_dir.exists():
        raise SystemExit(f"{out_dir} exists; refusing to overwrite archived run")
    out_dir.mkdir(parents=True)
    started = datetime.now(timezone.utc)
    t0 = time.time()
    with open(out_dir / "stream.jsonl", "w", encoding="utf-8") as so, \
         open(out_dir / "stderr.txt", "w", encoding="utf-8") as se:
        try:
            proc = subprocess.run(cmd, cwd=workdir, env=env, stdin=subprocess.DEVNULL,
                                  stdout=so, stderr=se, timeout=args.timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            rc = "timeout"
    elapsed = round(time.time() - t0, 1)

    # archive outputs and native session transcript
    shutil.copytree(workdir / "output", out_dir / "output")
    sessions = list((cfgdir / "projects").rglob("*.jsonl")) if (cfgdir / "projects").exists() else []
    for i, s in enumerate(sorted(sessions)):
        shutil.copy2(s, out_dir / ("native_session.jsonl" if i == 0 else f"native_session_{i}.jsonl"))

    result = {}
    init = {}
    for line in open(out_dir / "stream.jsonl", encoding="utf-8"):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            init = d
        if d.get("type") == "result":
            result = d
    meta = {
        "run_id": args.run_id, "case_id": args.case, "condition": args.condition,
        "started_at": started.isoformat(timespec="seconds"),
        "wall_seconds": elapsed, "exit_code": rc,
        "command": ["claude", "-p", "<cases/%s/prompt.txt>" % args.case] + cmd[3:],
        "claude_code_version": subprocess.run([CLAUDE_BIN, "--version"], capture_output=True,
                                              text=True, env=env).stdout.strip(),
        "model_requested": MODEL, "model_reported": init.get("model"),
        "effort": EFFORT, "budget_usd": float(BUDGET_USD), "tools": TOOLS.split(","),
        "skills_visible": init.get("skills"), "plugins": init.get("plugins"),
        "mcp_servers": init.get("mcp_servers"),
        "result_subtype": result.get("subtype"), "is_error": result.get("is_error"),
        "num_turns": result.get("num_turns"), "duration_ms": result.get("duration_ms"),
        "total_cost_usd_reported_by_claude_code": result.get("total_cost_usd"),
        "usage": result.get("usage"), "model_usage": result.get("modelUsage"),
        "output_files": sorted(str(p.relative_to(out_dir)) for p in (out_dir / "output").rglob("*") if p.is_file()),
        "native_session_files": sorted(p.name for p in out_dir.glob("native_session*.jsonl")),
        "cost_note": "total_cost_usd is Claude Code's client-side estimate at list price; the API is "
                     "reached through a third-party proxy whose actual billing is not available to us.",
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("run_id", "exit_code", "wall_seconds", "result_subtype",
                                           "num_turns", "total_cost_usd_reported_by_claude_code",
                                           "output_files", "skills_visible")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
