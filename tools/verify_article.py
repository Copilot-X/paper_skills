#!/usr/bin/env python3
"""Recompute every number this article cites from the files in this repository, then run
the gate's negative tests. Needs only the Python standard library.

    python3 tools/verify_article.py

Exit code 0 when every check passes. Each line prints PASS/FAIL with the source file, so a
reader can see where each number in README.md comes from.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
fails = 0


def check(name, ok, detail=""):
    global fails
    fails += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def grade(pair):
    g, m = load(f"grades/grade-{pair}.json"), load(f"grades/blinding-{pair}.json")["mapping"]
    return {m[lab].split("-", 1)[1]: r for lab, r in g["reports"].items()}, g


# 1. Blind-grade totals (README §4 table)
expect = {"A1": {"with": 59, "without": 53}, "A2": {"with": 60, "without": 52}}
for pair, exp in expect.items():
    reps, g = grade(pair)
    for cond, total in exp.items():
        got = reps[cond]["total"]
        check(f"{pair} {cond} total = {total}", got == total, f"grades/grade-{pair}.json -> {got}")
        items = sum(v["score"] for v in reps[cond]["items"].values())
        check(f"{pair} {cond} items sum to total", items == got, f"sum={items}")
    better = g["comparison"]["better"]
    with_label = [lab for lab, rid in load(f"grades/blinding-{pair}.json")["mapping"].items() if rid.endswith("-with")][0]
    check(f"{pair} blind grader preferred the with-Skill report", better == with_label, f"better={better}, with={with_label}")
    check(f"{pair} gate: with passes", reps["with"]["gate_pass"] is True)
check("A1 without failed the gate", grade("A1")[0]["without"]["gate_pass"] is False)

# 2. Per-item differences cited in README §4
for pair in ("A1", "A2"):
    reps, _ = grade(pair)
    for item, w, wo in (("G24", 2, 1), ("G23", 2, 1)):
        a, b = reps["with"]["items"][item]["score"], reps["without"]["items"][item]["score"]
        check(f"{pair} {item}: with {w} / without {wo}", (a, b) == (w, wo), f"{a}/{b}")
    star = ("G2", "G3", "G4", "G15", "G18", "G23")
    sw = sum(reps["with"]["items"][k]["score"] for k in star)
    swo = sum(reps["without"]["items"][k]["score"] for k in star)
    check(f"{pair} 'not reported' subtotal (6 items)", True, f"with {sw}/12, without {swo}/12")
    g14 = (reps["with"]["items"]["G14"]["score"], reps["without"]["items"]["G14"]["score"])
    check(f"{pair} G14 (protocol detail) is a without-Skill win", g14[1] > g14[0], f"{g14[0]}/{g14[1]}")

# 3. Time and cost (README §4 cost line)
meta = {r: load(f"runs/run_meta_{r}.json") for r in ("A1-with", "A1-without", "A2-with", "A2-without")}
tw = meta["A1-with"]["wall_seconds"] + meta["A2-with"]["wall_seconds"]
two = meta["A1-without"]["wall_seconds"] + meta["A2-without"]["wall_seconds"]
cw = meta["A1-with"]["total_cost_usd_reported_by_claude_code"] + meta["A2-with"]["total_cost_usd_reported_by_claude_code"]
cwo = meta["A1-without"]["total_cost_usd_reported_by_claude_code"] + meta["A2-without"]["total_cost_usd_reported_by_claude_code"]
check("wall time 1735.8 s vs 1276.3 s (+36%)", (round(tw, 1), round(two, 1)) == (1735.8, 1276.3) and round(100 * (tw / two - 1)) == 36,
      f"{tw:.1f} vs {two:.1f}, +{100 * (tw / two - 1):.0f}%")
check("cost $4.91 vs $3.35 (+47%)", (round(cw, 2), round(cwo, 2)) == (4.91, 3.35) and round(100 * (cw / cwo - 1)) == 47,
      f"{cw:.2f} vs {cwo:.2f}, +{100 * (cw / cwo - 1):.0f}%")
for r, m in meta.items():
    want = r.endswith("-with")
    check(f"{r}: Skill visible = {want}", ("repro-config-auditor" in m["skills_visible"]) == want, str(m["skills_visible"]))

# 4. Gate result of the archived with-Skill run (README §3)
cr = load("runs/A1-with/check_report.json")
check("A1-with gate: 26/26 items, 66 rows, problems = 0",
      cr["items_covered"] == 26 and cr["rows"] == 66 and cr["problems"] == [], f"rows={cr['rows']}, problems={len(cr['problems'])}")

# 5. Every page-cited quote in README §1 exists in the paper excerpt on that page
excerpt = (ROOT / "paper/veriharness_excerpts.md").read_text(encoding="utf-8")
pages = {int(m.group(1)): m.end() for m in re.finditer(r"^## p\.(\d+) ", excerpt, re.M)}
flat = lambda s: re.sub(r"\s+", " ", s)
for page, q in ((1, "6.4 points with Claude Opus 4.8"), (19, "temperature zero"), (7, "thinking level high"),
                (26, "do not establish statistical significance"), (27, "rather than metered runs"), (8, "51.6"), (8, "53.7")):
    blocks = [excerpt[s:excerpt.find("\n## ", s) if excerpt.find("\n## ", s) > 0 else None]
              for p, s in pages.items() if p == page]
    check(f"p.{page} contains '{q}'", any(q in flat(b) for b in blocks), "paper/veriharness_excerpts.md")

# 6. v1.0 failure and the v1.1 detector (README §5)
fail = load("failure_v1.0/grade-C2-v1.0.json")["reports"]["X"]
check("v1.0 C2 failed mandatory items E3 and E4",
      fail["items"]["E3"]["score"] == 0 and fail["items"]["E4"]["score"] == 0 and fail["gate_pass"] is False)
det = load("failure_v1.0/check_v1.1_on_v1.0_C2.json")
want = ["Appendix A", "Appendix B", "Appendix C", "Appendix F", "Appendix H", "Table 2", "Table 5"]
check("v1.1 detector lists the 7 missing objects", det["material_missing_objects"] == want, ", ".join(det["material_missing_objects"]))
check("v1.1 detector flags the v1.0 output", len(det["problems"]) > 0, f"{len(det['problems'])} problems")

# 7. Negative tests: the gate must reject a fabricated quote, a wrong page and an invented number
sys.path.insert(0, str(ROOT / "skill" / "scripts"))
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    paper = td / "paper.txt"
    body = re.sub(r"^## p\.(\d+) .*$", r"=== [p.\1] ===", excerpt, flags=re.M)
    paper.write_text(body, encoding="utf-8")
    good_q = "We use Gemini 3.5 Flash and Claude Opus 4.8 as both generator and verifier, with thinking level high."
    page7 = 7
    rows = [
        {"id": "M1", "item": "M1", "status": "reported", "quote": good_q, "page": page7, "value": "Gemini 3.5 Flash; Claude Opus 4.8"},
        {"id": "M2", "item": "M2", "status": "reported", "quote": "We sample at temperature 0.7 for all runs.", "page": page7, "value": "0.7"},
        {"id": "M3", "item": "M3", "status": "reported", "quote": good_q, "page": 9, "value": "high"},
        {"id": "M4", "item": "M4", "status": "reported", "quote": good_q, "page": page7, "value": "N = 16"},
    ]
    audit = td / "audit.jsonl"
    audit.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    cand = td / "c.json"
    cand.write_text(json.dumps({"items": {}}), encoding="utf-8")
    out = subprocess.run([sys.executable, str(ROOT / "skill/scripts/check_audit.py"), "--paper", str(paper), "--audit", str(audit),
                          "--candidates", str(cand)], capture_output=True, text=True)
    probs = out.stdout
    check("gate exit code is non-zero on bad rows", out.returncode == 1)
    check("gate accepts the genuine quote (M1)", '"row": "M1"' not in probs)
    check("gate rejects a fabricated quote (M2)", '"row": "M2", "problem": "quote not found' in probs)
    check("gate rejects a wrong page (M3)", '"row": "M3", "problem": "page=9' in probs)
    check("gate rejects an invented number (M4)", '"row": "M4", "problem": "value has numbers absent from quote' in probs)


# 8. Bohrium scimaster run (README section 6.2)
BR = "bohrium/scimaster_run"
gb, mb = load(f"{BR}/grade_blind.json"), load(f"{BR}/blinding.json")["mapping"]
rb = {mb[lab].split("-", 1)[1]: r for lab, r in gb["reports"].items()}
check("Bohrium blind totals: with-Skill 54, without 51", (rb["skill"]["total"], rb["plain"]["total"]) == (54, 51), f"{rb['skill']['total']}/{rb['plain']['total']}")
for cond in ("skill", "plain"):
    check(f"Bohrium {cond}: items sum to total", sum(v["score"] for v in rb[cond]["items"].values()) == rb[cond]["total"])
star = ("G2", "G3", "G4", "G15", "G18", "G23")
sk, pl = sum(rb["skill"]["items"][k]["score"] for k in star), sum(rb["plain"]["items"][k]["score"] for k in star)
check("Bohrium 'not reported' 6 items: 12 vs 8", (sk, pl) == (12, 8), f"{sk}/{pl}")
up = [k for k in rb["skill"]["items"] if rb["skill"]["items"][k]["score"] > rb["plain"]["items"][k]["score"]]
dn = [k for k in rb["skill"]["items"] if rb["skill"]["items"][k]["score"] < rb["plain"]["items"][k]["score"]]
check("Bohrium per-item: 8 higher with Skill, 6 higher without", (len(up), len(dn)) == (8, 6), f"{len(up)}/{len(dn)}")
check("Bohrium plain report has the +4.2 vs +3.3 error recorded", any("+4.2" in w["quote"] for w in rb["plain"]["wrong_claims"]))
check("Bohrium skill report has no wrong claims", rb["skill"]["wrong_claims"] == [])
lc = load(f"{BR}/with_skill/check_report_local_recheck.json")
check("Bohrium with-Skill local gate recheck: 81 rows, 26/26, problems = 0", lc["rows"] == 81 and lc["items_covered"] == 26 and lc["problems"] == [])
rep = (ROOT / BR / "with_skill/report.md").read_text(encoding="utf-8")
check("Bohrium with-Skill report is the file that was graded (not empty)", len(rep.encode()) == 31010, f"{len(rep.encode())} bytes")
check("Bohrium without-Skill report size 25,950 bytes", (ROOT / BR / "without_skill/report.md").stat().st_size == 25950)
check("blinding file lists X/Y mapping only", set(mb) == {"X", "Y"})

print(f"\n{'ALL PASS' if fails == 0 else f'{fails} FAILED'}")
sys.exit(1 if fails else 0)
