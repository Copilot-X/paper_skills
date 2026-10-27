#!/usr/bin/env python3
"""Extract a paper PDF into page-tagged text and report source-quality signals.

Usage:
    python3 extract_text.py PAPER.pdf --out-dir DIR

Writes:
    DIR/paper.txt          full text, every page prefixed with "=== [p.N] ==="
    DIR/extract_report.json  page count, chars per page, detected sections,
                             truncation / missing-text-layer warnings

Exit codes: 0 ok, 2 unreadable file, 3 readable but degraded (see warnings).
Requires PyMuPDF (pip install pymupdf); falls back to pypdf if PyMuPDF is absent.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Headings are matched on short lines only; optional numbering such as "4.", "4.2.", "A.".
_NUM = r"^\s*(?:[0-9]+(?:\.[0-9]+)*\.?|[A-H]\.)?\s*"
SECTION_PATTERNS = {
    "abstract": _NUM + r"abstract\b",
    "introduction": _NUM + r"introduction\b",
    "experiments": _NUM + r"(experiments?|experimental (setup|results)|evaluation|results)\b",
    "limitations": _NUM + r"limitations?\b",
    "conclusion": _NUM + r"conclusions?\b",
    "references": r"^\s*(references|bibliography)\s*$",
    "appendix": r"^\s*(appendix|appendices|[A-H]\.\s+[A-Z][a-z]+.*)$",
}


def load_pages(pdf_path):
    try:
        import pymupdf  # type: ignore
        doc = pymupdf.open(pdf_path)
        pages = [p.get_text() for p in doc]
        meta = {"engine": "pymupdf", "metadata_title": (doc.metadata or {}).get("title")}
        toc = [{"level": lv, "title": t, "page": pg} for lv, t, pg in doc.get_toc()]
        return pages, meta, toc
    except ImportError:
        pass
    from pypdf import PdfReader  # type: ignore
    reader = PdfReader(pdf_path)
    pages = [(p.extract_text() or "") for p in reader.pages]
    return pages, {"engine": "pypdf", "metadata_title": None}, []


def detect_sections(pages):
    found = {}
    for i, text in enumerate(pages, start=1):
        for line in text.splitlines():
            low = line.strip().lower()
            if not low or len(low) > 60:
                continue
            for name, pat in SECTION_PATTERNS.items():
                if name not in found and re.search(pat, low, re.I):
                    found[name] = i
    return found


def ends_mid_sentence(last_page):
    """True when the final page's last prose line stops without terminal punctuation.

    Trailing page numbers and short figure/table fragments are skipped, so a paper whose
    last page is an appendix figure is not flagged.
    """
    lines = [ln.strip() for ln in last_page.splitlines() if ln.strip()]
    while lines and (re.fullmatch(r"\d{1,3}", lines[-1]) or len(lines[-1]) < 25):
        lines.pop()
    if not lines:
        return False
    return not re.search(r"[.!?:;)\]}\"”]\s*$", lines[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        pages, meta, toc = load_pages(args.pdf)
    except Exception as exc:  # unreadable / not a PDF / encrypted
        report = {"status": "unreadable", "error": f"{type(exc).__name__}: {exc}"}
        (out / "extract_report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        return 2

    chars = [len(p.strip()) for p in pages]
    sections = detect_sections(pages)
    warnings = []
    if not pages:
        warnings.append("PDF has zero pages")
    low_text = [i + 1 for i, c in enumerate(chars) if c < 200]
    if pages and len(low_text) > len(pages) / 2:
        warnings.append(f"most pages have <200 chars of text ({len(low_text)}/{len(pages)}); "
                        "likely scanned/image-only, text layer missing")
    elif low_text:
        warnings.append(f"pages with <200 chars of text: {low_text}")
    for must in ("experiments", "references"):
        if must not in sections:
            warnings.append(f"no '{must}' heading detected; document may be truncated or "
                            "non-standard -- confirm before drawing conclusions about it")
    toc_last = max((t["page"] for t in toc), default=0)
    if toc and toc_last > len(pages):
        warnings.append(f"outline references page {toc_last} but file has {len(pages)} pages; "
                        "file is likely truncated")
    if pages and "references" not in sections and ends_mid_sentence(pages[-1]):
        warnings.append("last page ends mid-sentence and no reference list was found; "
                        "possible truncation")
    pages = [p.replace("\x00", "") for p in pages]

    with open(out / "paper.txt", "w", encoding="utf-8") as fh:
        for i, text in enumerate(pages, start=1):
            fh.write(f"=== [p.{i}] ===\n{text.rstrip()}\n\n")

    report = {
        "status": "degraded" if warnings else "ok",
        "source": str(args.pdf),
        "engine": meta["engine"],
        "metadata_title": meta["metadata_title"],
        "page_count": len(pages),
        "chars_per_page": chars,
        "total_chars": sum(chars),
        "detected_sections_first_page": sections,
        "outline": toc,
        "warnings": warnings,
        "text_file": str(out / "paper.txt"),
    }
    (out / "extract_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    summary = {k: report[k] for k in ("status", "page_count", "total_chars",
                                       "detected_sections_first_page", "warnings", "text_file")}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 3 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
