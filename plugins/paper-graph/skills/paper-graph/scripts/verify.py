#!/usr/bin/env python3
"""Verify a rendered paper-graph HTML in a real browser engine.

Catches the failures that a screenshot alone would not reveal: NaN/duplicate
node positions (the layout-collapse class of bug), overlapping label pills,
and JS errors during boot. Non-zero exit means the page is structurally bad.

Usage:
    python3 verify.py paper-graph.html

Exits:
    0  verified, or skipped because no headless browser was found
    1  verification failed (details printed)
    2  bad invocation / unreadable file
Set PAPER_GRAPH_CHROME=/path/to/chrome to force a browser binary.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VERIFY_JS = r"""
window.addEventListener("load", () => setTimeout(() => {
  const out = { errs: window.__errs || [] };
  try {
    const nodes = [...document.querySelectorAll("#svg g.node")];
    out.nodeCount = nodes.length;
    const ts = nodes.map(g => g.getAttribute("transform")).filter(Boolean);
    const pos = ts.map(t => {
      const m = t.match(/translate\(([-\d.eE+]+),([-\d.eE+]+)\)/);
      return m ? [parseFloat(m[1]), parseFloat(m[2])] : null;
    }).filter(Boolean);
    out.missingTransform = out.nodeCount - ts.length;
    out.nonFinite = pos.filter(p => !isFinite(p[0]) || !isFinite(p[1])).length;
    out.distinctPositions = new Set(pos.map(p => p.map(v => Math.round(v)).join(","))).size;
    out.branchPills = document.querySelectorAll(".pill-b").length;
    out.branchPillLabels = [...document.querySelectorAll(".pill-text-b")].map(t => t.textContent);
    out.invisiblePills = [...document.querySelectorAll(".pill-b")].filter(p => {
      const cs = getComputedStyle(p);
      return cs.fillOpacity === "0" || cs.fill === "none";
    }).length;

    /* pill overlap: bounding boxes of permanent labels, in page coords */
    const pills = [...document.querySelectorAll(".pill")].filter(p => !p.closest(".hover-pill"));
    const boxes = [];
    for (const p of pills) {
      const b = p.getBBox(), m = p.closest("g.node").getCTM();
      if (m) boxes.push({ x: m.e + b.x * m.a, y: m.f + b.y * m.d, w: b.width * m.a, h: b.height * m.d });
    }
    let overlaps = 0;
    for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      const ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
      const oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
      if (ox > 4 && oy > 4) overlaps++;
    }
    out.pillOverlaps = overlaps;
  } catch (e) { out.probeError = String(e); }
  document.title = "PGVERIFY" + JSON.stringify(out);
}, 500));
"""


def find_browser() -> str | None:
    env = os.environ.get("PAPER_GRAPH_CHROME")
    if env and Path(env).exists():
        return env
    for pat in ("~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome",
                "~/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
                "~/.cache/ms-playwright/chromium_headless_shell-*/chrome-linux/headless_shell"):
        hits = sorted(glob.glob(os.path.expanduser(pat)))
        if hits:
            return hits[-1]          # highest version
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        p = shutil.which(name)
        if p:
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html_file")
    ap.add_argument("--browser", help="browser binary (default: auto-detect)")
    ap.add_argument("--expect-nodes", type=int, help="fail unless exactly N graph nodes")
    args = ap.parse_args()

    src = Path(args.html_file)
    if not src.is_file():
        print(f"error: no such file: {src}", file=sys.stderr)
        return 2
    html = src.read_text(encoding="utf-8", errors="replace")

    browser = args.browser or find_browser()
    if not browser:
        print("skip: no headless browser found (set PAPER_GRAPH_CHROME to a chrome/"
              "chromium binary). Structural verification not performed.")
        return 0

    # inject error capture before the page script, probe after it
    html = html.replace("</title>",
        '</title>\n<script>window.__errs=[];'
        'window.addEventListener("error",e=>window.__errs.push(String(e.message)));</script>', 1)
    html = html.replace("</body>", f"<script>{VERIFY_JS}</script>\n</body>")

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                     encoding="utf-8") as f:
        f.write(html)
        tmp = f.name
    try:
        r = subprocess.run(
            [browser, "--headless", "--no-sandbox", "--disable-gpu", "--dump-dom",
             "--virtual-time-budget=8000", f"file://{tmp}"],
            capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print("error: browser timed out", file=sys.stderr)
        return 1
    finally:
        Path(tmp).unlink(missing_ok=True)

    m = re.search(r"<title>PGVERIFY(\{.*?\})</title>", r.stdout, re.S)
    if not m:
        print("error: verification probe produced no result "
              "(page failed to boot, or browser printed nothing useful)", file=sys.stderr)
        tail = (r.stderr or "").strip().splitlines()[-3:]
        for line in tail:
            print(f"  browser stderr: {line}", file=sys.stderr)
        return 1

    res = json.loads(m.group(1))
    problems = []
    if res.get("probeError"):
        problems.append(f"probe threw: {res['probeError']}")
    if res.get("errs"):
        problems.append(f"JS errors: {res['errs']}")
    n, distinct = res.get("nodeCount", 0), res.get("distinctPositions", 0)
    if not n:
        problems.append("no graph nodes rendered")
    if res.get("missingTransform"):
        problems.append(f"{res['missingTransform']} node(s) have no transform")
    if res.get("nonFinite"):
        problems.append(f"{res['nonFinite']} node(s) at non-finite coordinates")
    if n and distinct < n * 0.7:
        problems.append(f"nodes stacked: only {distinct} distinct positions for {n} nodes")
    if res.get("invisiblePills"):
        problems.append(f"{res['invisiblePills']} branch pill(s) invisible")
    if res.get("pillOverlaps"):
        problems.append(f"{res['pillOverlaps']} overlapping label pill pair(s)")
    if args.expect_nodes is not None and n != args.expect_nodes:
        problems.append(f"expected {args.expect_nodes} nodes, rendered {n}")

    print(f"browser: {browser}")
    print(f"nodes: {n}  distinct positions: {distinct}  "
          f"branch pills: {res.get('branchPills', 0)}  "
          f"pill overlaps: {res.get('pillOverlaps', 0)}  "
          f"js errors: {len(res.get('errs', []))}")
    print(f"branch labels: {res.get('branchPillLabels')}")

    if problems:
        print("\nFAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("\nOK — layout verified in a real browser engine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
