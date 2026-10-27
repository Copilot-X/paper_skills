#!/usr/bin/env python3
"""List, for every checklist item, the pages of paper.txt that mention it.

Usage:
    python3 scan_config.py --paper paper.txt --out candidates.json

The search terms are deliberately broad: the goal is that no page mentioning an item is
missed, so the reader must open each candidate page before writing "not_reported".
For every item the output gives the candidate pages (body pages and appendix pages are
listed separately, references pages are skipped) and up to 3 short snippets per page.
"""
import argparse
import json
import re
import sys

PAGE_MARK = re.compile(r"^=== \[p\.(\d+)\] ===$", re.M)

TERMS = {
    "M1": [r"\bgpt-?\d", r"\bclaude\b", r"\bgemini\b", r"\bllama", r"\bqwen", r"\bdeepseek",
           r"\bmistral", r"\bo[134](-mini)?\b", r"\bbackbone\b", r"\bbase model\b", r"\bsnapshot\b"],
    "M2": [r"temperature", r"top[- ]?p\b", r"top[- ]?k\b", r"\bsampl", r"\bgreedy\b", r"\bdecoding\b",
           r"reasoning effort", r"\bthinking\b"],
    "M3": [r"max(imum)?[ _-]?(new[ _-])?tokens?", r"context (length|window)", r"max(imum)? (number of )?(steps|turns|iterations|rounds)",
           r"step (limit|budget)", r"\btimeout\b", r"token (limit|budget)"],
    "M4": [r"\bjudge\b", r"\bverifier\b", r"\bembedding", r"\bretriever\b", r"\breranker\b", r"\bcritic\b",
           r"\bevaluator\b", r"\breward model\b"],
    "D1": [r"\bbenchmark", r"\bdataset", r"\bsplit\b", r"\bversion\b"],
    "D2": [r"\bsubset\b", r"\bsampled?\b", r"\btest set\b", r"\bdev(elopment)? set\b", r"\bvalidation\b",
           r"\b\d+ (tasks|questions|problems|instances|examples|samples|queries|episodes)\b", r"\bseed"],
    "D3": [r"\bfilter", r"\bexclud", r"\bremov", r"\bdiscard", r"\bdeduplicat", r"\bdrop(ped)?\b", r"\bunsolvable\b"],
    "D4": [r"\bpublicly available\b", r"\blicen[cs]e", r"\bproprietary\b", r"\bprivate\b", r"\bhuggingface\b",
           r"\bdownload", r"\breleased?\b"],
    "P1": [r"\balgorithm\b", r"\bpipeline\b", r"\bframework\b", r"\bprocedure\b", r"\bstage\b", r"\bstep \d"],
    "P2": [r"\bhyper-?parameters?\b", r"\bthreshold\b", r"\b[nkKN]\s*=\s*\d", r"\bnumber of (candidates|samples|rollouts|iterations)",
           r"\bwe set\b", r"\bset to\b", r"\bdefault\b"],
    "P3": [r"\bprompts?\b", r"\binstruction", r"\bsystem message\b", r"\btemplate\b", r"\bfew-shot\b", r"\bin-context\b"],
    "P4": [r"\bharness\b", r"\bscaffold", r"\btools?\b", r"\bsandbox", r"\bdocker\b", r"\benvironment\b", r"\bapi\b",
           r"\bbrowser\b", r"\bsearch engine\b", r"\bframework\b"],
    "P5": [r"\bbaselines?\b", r"\bcompared? (with|to|against)\b", r"\bwe compare\b", r"\bprior (work|methods)\b"],
    "P6": [r"\bsame (pool|budget|model|input|candidates|setting)", r"\bfair", r"\bshared\b", r"\bcontrolled\b",
           r"\bmatched\b", r"\bequal (budget|compute)"],
    "E1": [r"\bmetrics?\b", r"\baccuracy\b", r"\bpass@\d", r"\bsuccess rate\b", r"\bscore\b", r"\bF1\b", r"\bpass rate\b",
           r"\baverage[ds]?\b", r"\brubric"],
    "E2": [r"\bannotat", r"\bhuman (eval|judg|rater)", r"\bagreement\b", r"\bkappa\b", r"\bLLM[- ]as[- ]a[- ]judge\b",
           r"\bjudge\b", r"\bgrader\b", r"\binter-?rater\b"],
    "E3": [r"\bruns?\b", r"\bseeds?\b", r"\bstandard deviation\b", r"\bstd\b", r"±", r"\bvariance\b",
           r"\bconfidence interval", r"\brepeat", r"\btrials?\b", r"\berror bars?\b"],
    "E4": [r"\bsignifican", r"\bp\s*[<=>]\s*0?\.\d", r"\bp-value", r"\bt-test\b", r"\bbootstrap", r"\bwilcoxon\b",
           r"\bmcnemar\b", r"\bpermutation test\b"],
    "R1": [r"\bGPUs?\b", r"\bA100\b", r"\bH100\b", r"\bH200\b", r"\bTPU", r"\bCPU", r"\bcompute\b", r"\bnodes?\b"],
    "R2": [r"\bcost", r"\$\s?\d", r"\bUSD\b", r"\btokens?\b", r"\blatency\b", r"\bwall[- ]clock\b", r"\bhours?\b",
           r"\bminutes\b", r"\bbudget\b", r"\bexpens"],
    "R3": [r"\bversion\b", r"\bpython\b", r"\bpytorch\b", r"\btransformers\b", r"\bvllm\b",
           r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
           r"\b20[12]\d-\d\d", r"\baccessed\b"],
    "A1": [r"\bcode\b", r"\bgithub\b", r"\brepository\b", r"\bopen[- ]source", r"https?://"],
    "A2": [r"\btrajector", r"\blogs?\b", r"\bwill be released\b", r"\brelease\b", r"\bavailable at\b", r"https?://"],
    "T1": [r"\btable \d", r"\bmain results?\b", r"\boutperform", r"\bimprov", r"\bstate[- ]of[- ]the[- ]art\b"],
    "T2": [r"\bablat", r"\bsensitiv", r"\bwithout\b", r"\bw/o\b", r"\bvary(ing)?\b", r"\beffect of\b"],
    "X1": [r"\blimitation", r"\bfailure", r"\bfail(s|ed)?\b", r"\bbias", r"\bcaveat", r"\bthreat", r"\bdoes not\b",
           r"\bfuture work\b"],
}


def split_pages(raw):
    marks = list(PAGE_MARK.finditer(raw))
    if not marks:
        return [(1, raw)]
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(raw)
        out.append((int(m.group(1)), raw[m.end():end]))
    return out


def page_kind(text, state):
    """Return 'body', 'references' or 'appendix'; state carries what was seen before."""
    lines = [l.strip().lower() for l in text.splitlines() if l.strip()]
    if any(re.fullmatch(r"(appendix|appendices|supplementary materials?)( [a-z])?", l) for l in lines):
        state["appendix"] = True
    if state["appendix"]:
        return "appendix"
    if any(re.fullmatch(r"(references|bibliography)", l) for l in lines):
        state["refs"] = True
        return "references"
    if state["refs"]:
        # reference pages are dense with years; the first page after them that is not is appendix
        years = len(re.findall(r"\b(?:19|20)\d\d\b", text))
        if years >= 10:
            return "references"
        state["appendix"] = True
        return "appendix"
    return "body"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    pages = split_pages(open(args.paper, encoding="utf-8").read())

    state = {"refs": False, "appendix": False}
    kinds = {no: page_kind(txt, state) for no, txt in pages}
    result = {"page_kinds": kinds, "items": {}}
    for item, pats in TERMS.items():
        rx = re.compile("|".join(pats), re.I)
        hits = {}
        for no, txt in pages:
            if kinds[no] == "references":
                continue
            flat = re.sub(r"\s+", " ", txt)
            snippets = []
            for m in rx.finditer(flat):
                s = flat[max(0, m.start() - 60): m.end() + 60].strip()
                if not snippets or s[:40] != snippets[-1][:40]:
                    snippets.append(s)
            if snippets:
                hits[no] = {"count": len(snippets), "snippets": snippets[:3]}
        ranked = sorted(hits, key=lambda n: -hits[n]["count"])
        result["items"][item] = {
            "body_pages": sorted(n for n in hits if kinds[n] == "body"),
            "appendix_pages": sorted(n for n in hits if kinds[n] == "appendix"),
            "top_pages": ranked[:6],
            "hits": hits,
        }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False)
    n_app = sum(1 for k in kinds.values() if k == "appendix")
    n_ref = sum(1 for k in kinds.values() if k == "references")
    print(json.dumps({"pages": len(pages), "appendix_pages": n_app, "reference_pages": n_ref}))
    for item, r in result["items"].items():
        print(f"{item}: top {r['top_pages']}  appendix {r['appendix_pages']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
