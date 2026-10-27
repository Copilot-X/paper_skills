#!/usr/bin/env python3
"""Gate check for audit.jsonl: completeness, required fields, verbatim quotes, numbers.

Usage:
    python3 check_audit.py --paper paper.txt --audit audit.jsonl --candidates candidates.json \
        [--out check_report.json]

Checks (each failure is listed as a PROBLEM line):
  * every checklist ID (references/checklist.md) has at least one row; no unknown IDs;
  * status is one of the allowed values and the fields it requires are present;
  * every quote / quote2 is found in paper.txt (same matcher as verify_quotes.py) and its page is right;
  * every number written in `value` occurs in the row's quote(s), so values cannot be invented;
  * a not_reported / not_in_material row lists in `searched` every page that scan_config.py ranked
    as a top candidate for that item, so "not reported" is only claimed after looking there;
  * material completeness: tables, figures and appendices that the text refers to but that never
    appear as a caption/heading are listed as missing. If any are missing (or extract_report.json
    says the file is truncated), then
      - a `reported` row whose value/quote/note cites a missing object fails (the cited source is
        not in the file, so the value is only a claim, use `partial` and say "not verifiable");
      - with --report, every sentence of report.md that says "未报告/not reported" must also say the
        material is incomplete (未见/缺失/不在材料/截断/not in material...), otherwise it is flagged,
        because absence from an incomplete file is not absence from the paper.
Exit code 0 when there are no problems, 1 otherwise. Also prints status counts per item group.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_quotes import PAGE_MARK, SOFT, find, normalise, split_pages  # noqa: E402

ITEMS = ["M1", "M2", "M3", "M4", "D1", "D2", "D3", "D4", "P1", "P2", "P3", "P4", "P5", "P6",
         "E1", "E2", "E3", "E4", "R1", "R2", "R3", "A1", "A2", "T1", "T2", "X1"]
REQUIRED = {
    "reported": ["quote", "page", "value"],
    "partial": ["quote", "page", "missing"],
    "not_reported": ["searched", "missing", "next_step"],
    "conflicting": ["quote", "page", "quote2", "page2", "missing"],
    "not_applicable": ["missing"],
    "not_in_material": ["searched", "next_step"],
}
NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*")


def locate(quote, pages, full):
    q = normalise(quote).replace(SOFT, "")
    hit = [no for no, txt in pages if find(q, txt) >= 0]
    if hit:
        return hit
    if find(q, full) >= 0:
        return ["cross-page"]
    q_ns = re.sub(r"\s", "", q)
    return [no for no, txt in pages if find(q_ns, re.sub(r"\s", "", txt)) >= 0]


def numbers(s):
    return {n.replace(",", "") for n in NUM.findall(normalise(s or ""))}


REF = re.compile(r"\b(Table|Figure|Fig\.|Appendix|Algorithm)\s+([A-Z]?\d+|[A-K])\b")
NOT_REPORTED = re.compile(r"(论文|原文|作者)?(未报告|没有报告|未给出|没有给出|未说明|没写|未写)|not reported", re.I)
INCOMPLETE = re.compile(r"未见|缺失|缺页|不在(本)?(文件|材料)|材料(中|里)?(没有|不全|不完整|缺)|截断|not_in_material|"
                        r"not in (the )?material|truncat|missing from the file|需完整版|完整版", re.I)


def material_gaps(raw, args):
    """Objects referenced in the text but never defined in it, and the extractor's truncation flag."""
    text = re.sub(r"\s+", " ", raw)
    refs = {f"{k.replace('Fig.', 'Figure')} {n}" for k, n in REF.findall(text)}
    defined = set()
    # captions ("Table 2 | ...", "Figure 3: ...") and algorithm boxes ("Algorithm 1 VeriHarness")
    for k, n in re.findall(r"(?:^|\n)\s*(Table|Figure|Algorithm)\s+([A-Z]?\d+)\s*(?:[|:.]|\s+[A-Z])", raw):
        defined.add(f"{k} {n}")
    # appendix headings: "A. Claim-Level ...", "B Evaluation Framework", or a lone "A" line followed by a title
    for n in re.findall(r"(?:^|\n)\s*([A-K])(?:\.\s*|\s+|\s*\n\s*)[A-Z][a-z]+(?:[- ][A-Za-z]+)*\s*(?:\n|$)", raw):
        defined.add(f"Appendix {n}")
    missing = sorted(refs - defined)
    ext = args.extract_report or str(Path(args.paper).with_name("extract_report.json"))
    truncated = False
    if Path(ext).exists():
        warn = " ".join(json.load(open(ext, encoding="utf-8")).get("warnings", []))
        truncated = bool(re.search(r"truncat", warn, re.I))
    return missing, truncated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", required=True)
    ap.add_argument("--audit", required=True)
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--report", help="report.md; checked for 'not reported' wording when material is incomplete")
    ap.add_argument("--extract-report", help="extract_report.json (default: next to paper.txt)")
    ap.add_argument("--out")
    args = ap.parse_args()

    raw = open(args.paper, encoding="utf-8").read()
    pages = [(no, normalise(t)) for no, t in split_pages(raw)]
    full = normalise(PAGE_MARK.sub(" ", raw))
    cand = json.load(open(args.candidates, encoding="utf-8"))["items"]

    problems, rows = [], []
    for n, line in enumerate(open(args.audit, encoding="utf-8"), start=1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                problems.append({"row": f"line{n}", "problem": f"bad JSON: {exc}"})

    seen = Counter(r.get("item") for r in rows)
    for item in ITEMS:
        if not seen[item]:
            problems.append({"row": item, "problem": "checklist item has no row"})
    for item in seen:
        if item not in ITEMS:
            problems.append({"row": str(item), "problem": "unknown item ID"})

    status_count = Counter()
    for r in rows:
        rid = r.get("id") or r.get("item")
        st = r.get("status")
        status_count[st] += 1
        if st not in REQUIRED:
            problems.append({"row": rid, "problem": f"invalid status {st!r}"})
            continue
        for f in REQUIRED[st]:
            if r.get(f) in (None, "", []):
                problems.append({"row": rid, "problem": f"status {st} requires field '{f}'"})
        for qf, pf in (("quote", "page"), ("quote2", "page2")):
            if not r.get(qf):
                continue
            hit = locate(r[qf], pages, full)
            if not hit:
                problems.append({"row": rid, "problem": f"{qf} not found verbatim in paper.txt"})
            elif "cross-page" not in hit and r.get(pf) not in hit:
                problems.append({"row": rid, "problem": f"{pf}={r.get(pf)} but {qf} is on page(s) {hit}"})
        if st in ("reported", "partial", "conflicting") and r.get("value"):
            missing = numbers(r["value"]) - numbers(r.get("quote", "") + " " + r.get("quote2", ""))
            if missing:
                problems.append({"row": rid, "problem": f"value has numbers absent from quote: {sorted(missing)}"})
        if st in ("not_reported", "not_in_material"):
            listed = {int(x) for x in re.findall(r"\d+", str(r.get("searched", "")))}
            top = set(cand.get(r.get("item"), {}).get("top_pages", []))
            top = {int(p) for p in top}
            if not top <= listed:
                problems.append({"row": rid, "problem": "searched omits scan_config top candidate pages "
                                 f"{sorted(top - listed)}; open them before claiming absence"})

    missing_objs, truncated = material_gaps(raw, args)
    if missing_objs or truncated:
        for r in rows:
            if r.get("status") != "reported":
                continue
            blob = " ".join(str(r.get(f, "")) for f in ("value", "quote", "quote2", "note"))
            cited = sorted(o for o in missing_objs if re.search(r"\b" + re.escape(o) + r"\b", blob, re.I))
            if cited:
                problems.append({"row": r.get("id"), "problem": f"reported value relies on {cited}, which "
                                 "is not in the material; mark it partial and say it cannot be verified"})
        if args.report and Path(args.report).exists():
            for sent in re.split(r"(?<=[。；;！？!?\n])", Path(args.report).read_text(encoding="utf-8")):
                if sent.lstrip().startswith("#"):
                    continue  # section headings name the category, they are not claims
                if NOT_REPORTED.search(sent) and not INCOMPLETE.search(sent):
                    problems.append({"row": "report.md", "problem": "says 'not reported' although the "
                                     "material is incomplete; say whether it is missing from the file: "
                                     + sent.strip()[:160]})

    groups = {}
    for item in ITEMS:
        sts = [r.get("status") for r in rows if r.get("item") == item]
        groups[item] = sts[0] if sts else None
    summary = {"material_missing_objects": missing_objs, "material_truncated": truncated,
               "rows": len(rows), "items_covered": sum(1 for i in ITEMS if seen[i]),
               "items_total": len(ITEMS), "status_counts": dict(status_count),
               "item_status": groups, "problems": problems}
    text = json.dumps(summary, indent=1, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("rows", "items_covered", "items_total", "status_counts")},
                     ensure_ascii=False))
    for p in problems:
        print("PROBLEM", json.dumps(p, ensure_ascii=False))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
