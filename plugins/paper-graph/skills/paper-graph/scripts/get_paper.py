#!/usr/bin/env python3
"""Acquire a paper: metadata + full text + figure URLs.

Handles an arXiv id / URL (fetches the arXiv API for metadata, the PDF for
full text, and the arXiv HTML version for figure image URLs) or a local PDF
(metadata unknown, text only). Deterministic outputs so the rest of the
pipeline — and re-runs — see the same inputs.

Usage:
    python3 get_paper.py 2606.00307 --out ./work
    python3 get_paper.py https://arxiv.org/abs/2606.00307
    python3 get_paper.py ./some.pdf --out ./work

Writes into <out> (default: current directory):
    paper.json    metadata + figure list (for block authoring)
    paper.txt     full text, layout preserved (pdftotext -layout)

Then read paper.txt for distillation and use paper.json's figure URLs
directly as `{"type": "image", "url": ...}` blocks.
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

UA = {"User-Agent": "paper-graph-skill/1.1 (+https://arxiv.org)"}
ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")


def fetch(url: str, timeout: float = 30) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse_arxiv_ref(s: str) -> tuple[str, str] | None:
    """'2606.00307' / 'https://arxiv.org/abs/2606.00307v3' → ('2606.00307', 'v3'|'')"""
    m = ARXIV_ID_RE.search(s)
    if not m:
        return None
    return m.group(1), m.group(2) or ""


def arxiv_metadata(arxiv_id: str) -> dict:
    """Metadata via the arXiv API (Atom XML — stable, no HTML scraping)."""
    url = f"http://export.arxiv.org/api/query?id_list={urllib.parse.quote(arxiv_id)}"
    root = ET.fromstring(fetch(url))
    entry = root.find("a:entry", ATOM)
    if entry is None:
        return {}
    txt = lambda p: (entry.findtext(p, default="", namespaces=ATOM) or "").strip()
    return {
        "title": " ".join(txt("a:title").split()),
        "authors": [" ".join(a.findtext("a:name", default="", namespaces=ATOM).split())
                    for a in entry.findall("a:author", ATOM)],
        "abstract": " ".join(txt("a:summary").split()),
        "published": txt("a:published"),
        "updated": txt("a:updated"),
        "primary_category": (entry.find("arxiv:primary_category", ATOM).get("term")
                             if entry.find("arxiv:primary_category", ATOM) is not None else ""),
        "comment": txt("arxiv:comment"),
        "journal_ref": txt("arxiv:journal_ref"),
        "doi": txt("arxiv:doi"),
        "abs_url": f"https://arxiv.org/abs/{arxiv_id}",
    }


def arxiv_figures(arxiv_id: str, version: str = "") -> tuple[str, list[dict]]:
    """Figure URLs from the arXiv HTML rendering. Returns (html_base, figures)."""
    for suffix in ([version] if version else []) + ["", "v3", "v2", "v1"]:
        for host in ("https://arxiv.org/html/", "https://ar5iv.labs.arxiv.org/html/"):
            url = f"{host}{arxiv_id}{suffix}"
            try:
                html = fetch(url).decode("utf-8", "replace")
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
                continue
            if "<img" not in html:
                continue
            # img srcs are relative to the site's /html/ root (they carry the
            # "<id><version>/" prefix), NOT to the page directory
            root = url[: url.index("/html/") + len("/html/")]
            base = url.rstrip("/") + "/"
            figs, seen = [], set()
            # each <figure> block: img src + optional <figcaption> text
            for block in re.findall(r"<figure\b.*?</figure>", html, re.S | re.I):
                srcs = re.findall(r'<img[^>]*\ssrc="([^"]+)"', block, re.I)
                cap = re.findall(r"<figcaption\b[^>]*>(.*?)</figcaption>", block, re.S | re.I)
                caption = re.sub(r"<[^>]+>", " ", cap[0]) if cap else ""
                caption = " ".join(caption.split())[:400]
                for s in srcs:
                    if s.startswith(("http://", "https://")) or s.startswith("/"):
                        continue          # skip funder icons / absolute assets
                    if s in seen:
                        continue
                    seen.add(s)
                    figs.append({"src": s, "url": urllib.parse.urljoin(root, s),
                                 "caption": caption})
            if figs:
                return base, figs
            # no <figure> blocks: fall back to every relative img
    return "", []


def pdf_to_text(pdf: Path, out: Path) -> bool:
    try:
        r = subprocess.run(["pdftotext", "-layout", str(pdf), str(out)],
                           capture_output=True, text=True, timeout=180)
    except FileNotFoundError:
        print("error: pdftotext not found (install poppler-utils); "
              "fall back to reading the PDF with the Read tool in pages", file=sys.stderr)
        return False
    if r.returncode != 0:
        print(f"error: pdftotext failed: {r.stderr.strip()}", file=sys.stderr)
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="arXiv id / URL, or path to a local PDF")
    ap.add_argument("--out", default=".", help="output directory (default: .)")
    args = ap.parse_args()

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    info: dict = {"source": args.source}

    ref = parse_arxiv_ref(args.source)
    src_path = Path(args.source)

    if ref and not src_path.exists():
        arxiv_id, version = ref
        info["arxiv_id"] = arxiv_id
        print(f"arXiv {arxiv_id}{version or ' (latest)'}")
        try:
            info.update(arxiv_metadata(arxiv_id))
            print(f"  title: {info.get('title', '?')[:80]}")
        except Exception as e:                     # metadata is nice-to-have
            print(f"  warning: metadata fetch failed ({e})", file=sys.stderr)

        pdf = out / "paper.pdf"
        try:
            pdf.write_bytes(fetch(f"https://arxiv.org/pdf/{arxiv_id}{version}", timeout=120))
            print(f"  pdf: {pdf} ({pdf.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"  error: PDF download failed ({e})", file=sys.stderr)
            return 1

        base, figs = arxiv_figures(arxiv_id, version)
        if figs:
            info["html_base"] = base
            info["figures"] = figs
            print(f"  figures: {len(figs)} from {base}")
        else:
            print("  figures: none found (no HTML rendering) — images unavailable, "
                  "keep nodes prose+formula+table only", file=sys.stderr)

        if not pdf_to_text(pdf, out / "paper.txt"):
            return 1
    elif src_path.exists():
        info["pdf_path"] = str(src_path.resolve())
        print(f"local PDF: {src_path}")
        if not pdf_to_text(src_path, out / "paper.txt"):
            return 1
        print("  figures: none (local PDF has no hosted rendering) — skip image blocks")
    else:
        print(f"error: '{args.source}' is neither an arXiv reference nor an existing file",
              file=sys.stderr)
        return 2

    txt = out / "paper.txt"
    info["text_path"] = str(txt)
    info["text_lines"] = len(txt.read_text(encoding="utf-8", errors="replace").splitlines())
    (out / "paper.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ntext: {txt} ({info['text_lines']} lines)\nmeta: {out / 'paper.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
