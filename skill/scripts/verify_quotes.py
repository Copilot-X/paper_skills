#!/usr/bin/env python3
"""Check that every quote in a claim ledger appears verbatim in the extracted paper text.

Usage:
    python3 verify_quotes.py --paper paper.txt --ledger ledger.jsonl [--out verify_report.json]

ledger.jsonl: one JSON object per line with at least
    {"id": "C1", "quote": "<verbatim text copied from paper.txt>", "page": 7, ...}
Lines whose "label" is "unknown" may omit the quote.

Matching is exact after a light normalisation that only undoes PDF-extraction noise:
Unicode NFKC, ligatures, curly quotes/dashes, de-hyphenated line breaks and collapsed
whitespace; as a last resort a whitespace-insensitive match is accepted and flagged.
Paraphrases do NOT pass. For each quote the report gives the matched page and
the character offsets in the normalised text, or the closest page when the quote fails.

Exit code: 0 when all quotes match, 1 when any quote fails (fix or downgrade those rows).
"""
import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher

PAGE_MARK = re.compile(r"^=== \[p\.(\d+)\] ===$", re.M)
TRANS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                       "–": "-", "—": "-", "−": "-", " ": " "})


SOFT = "\u00ad"  # marks a line-break hyphen whose presence in the original word is unknown


def normalise(text):
    text = unicodedata.normalize("NFKC", text).translate(TRANS)
    # A hyphen at a line break is either a split word ("opti-\nmizer") or a real compound
    # ("content-\nrelevant"); keep it as a soft marker and let the matcher accept both.
    text = re.sub(r"(\w)-[ \t]*\n\s*(\w)", r"\1" + SOFT + r"\2", text)
    # Some PDFs leave "ad- ditionally" / "trajec- tories" (hyphen + space inside one line).
    # Treat it as a soft hyphen only when the next letter is lower-case, so real dashes
    # in "state- of-the-art"-style text are still tried both ways.
    text = re.sub(r"(\w)- (?=[a-z])", r"\1" + SOFT, text)
    return re.sub(r"\s+", " ", text).strip()


def find(q, text):
    """Index of quote q in normalised text, treating each soft marker as '-' or ''."""
    if SOFT not in text:
        return text.find(q)
    parts = [re.escape(c) for c in q]
    pattern = (SOFT + "?").join(parts)
    pattern = pattern.replace(re.escape("-"), "[-" + SOFT + "]")
    m = re.search(pattern, text)
    return m.start() if m else -1


def split_pages(raw):
    marks = list(PAGE_MARK.finditer(raw))
    if not marks:
        return [(None, raw)]
    pages = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(raw)
        pages.append((int(m.group(1)), raw[m.end():end]))
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    raw = open(args.paper, encoding="utf-8").read()
    pages = [(no, normalise(txt)) for no, txt in split_pages(raw)]
    full = normalise(PAGE_MARK.sub(" ", raw))

    rows, results = [], []
    with open(args.ledger, encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                results.append({"id": f"line{n}", "status": "bad_json", "error": str(exc)})

    for row in rows:
        rid = row.get("id", "?")
        quote = row.get("quote") or ""
        if not quote.strip():
            status = "no_quote_ok" if row.get("label") == "unknown" else "missing_quote"
            results.append({"id": rid, "status": status})
            continue
        q = normalise(quote).replace(SOFT, "")
        hit_pages = [no for no, txt in pages if find(q, txt) >= 0]
        if hit_pages:
            start = find(q, full)
            claimed = row.get("page")
            res = {"id": rid, "status": "match", "pages": hit_pages,
                   "norm_start": start, "norm_end": start + len(q)}
            if claimed is not None and claimed not in hit_pages:
                res["status"] = "match_wrong_page"
                res["claimed_page"] = claimed
            results.append(res)
            continue
        start = find(q, full)
        if start >= 0:  # spans a page break
            results.append({"id": rid, "status": "match", "pages": ["cross-page"],
                            "norm_start": start, "norm_end": start + len(q)})
            continue
        # PDF text layers drop or insert spaces around symbols ("N= 10" vs "N = 10");
        # accept a quote that matches once all whitespace is removed, but flag it.
        q_ns = re.sub(r"\s", "", q)
        ws_pages = [no for no, txt in pages if find(q_ns, re.sub(r"\s", "", txt)) >= 0]
        if ws_pages:
            results.append({"id": rid, "status": "match", "pages": ws_pages,
                            "note": "matched ignoring whitespace"})
            continue
        best = max(((SequenceMatcher(None, q, txt.replace(SOFT, "")).find_longest_match(
                        0, len(q), 0, len(txt.replace(SOFT, ""))).size, no)
                    for no, txt in pages), default=(0, None))
        results.append({"id": rid, "status": "not_found", "closest_page": best[1],
                        "longest_common_chars": best[0], "quote_chars": len(q)})

    bad = [r for r in results if r["status"] not in ("match", "no_quote_ok")]
    summary = {"total": len(results), "matched": sum(r["status"] == "match" for r in results),
               "unknown_without_quote": sum(r["status"] == "no_quote_ok" for r in results),
               "problems": len(bad), "results": results}
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(json.dumps({k: summary[k] for k in ("total", "matched", "unknown_without_quote", "problems")}))
    for r in bad:
        print("PROBLEM", json.dumps(r, ensure_ascii=False))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
