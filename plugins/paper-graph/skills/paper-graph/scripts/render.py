#!/usr/bin/env python3
"""Validate a paper-graph JSON and render it into the self-contained HTML page.

Usage:
    python3 render.py paper-graph.json [-o out.html] [--template TEMPLATE]

Writes <json-stem>.html next to the JSON by default. Exits non-zero on
structural errors; prints warnings for missing-but-optional fields.
"""

import argparse
import json
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"
PLACEHOLDER = "__GRAPH_DATA__"
REQUIRED_BRANCHES = ("background", "innovations", "experiments", "conclusions")


def warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


def validate(data: dict) -> None:
    meta = data.get("meta") or {}
    if not meta.get("title"):
        warn("meta.title missing — graph header will be empty")
    branches = data.get("branches") or {}
    for key in REQUIRED_BRANCHES:
        b = branches.get(key)
        if not b or not isinstance(b.get("points"), list) or not b["points"]:
            warn(f"branches.{key}.points missing or empty — branch renders bare")
    for key in ("background", "innovations", "experiments", "conclusions"):
        for i, p in enumerate((branches.get(key) or {}).get("points") or []):
            if not p.get("id"):
                warn(f"branches.{key}.points[{i}] has no id")
    refs = data.get("references") or []
    for i, r in enumerate(refs):
        if not r.get("id"):
            warn(f"references[{i}] has no id")
        if not r.get("title"):
            warn(f"references[{i}] has no title")
    for i, fnode in enumerate(data.get("future") or []):
        if not fnode.get("id"):
            warn(f"future[{i}] has no id")
        if not fnode.get("search_query"):
            warn(f"future[{i}] has no search_query — no one-click literature search")
    exp = (branches.get("experiments") or {}).get("points") or []
    if exp and not any(p.get("metrics") for p in exp):
        warn("no experiments point carries metrics — concrete numbers make the graph useful")
    for i, a in enumerate(data.get("artifacts") or []):
        if not a.get("id"):
            warn(f"artifacts[{i}] has no id")
        if not a.get("url"):
            warn(f"artifacts[{i}] has no url — it renders as a dead node")
        if not a.get("label"):
            warn(f"artifacts[{i}] has no label")
    if (data.get("artifacts") or []) and not (branches.get("resources") or {}).get("summary"):
        warn("artifacts present but branches.resources.summary is missing")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("json_file")
    ap.add_argument("-o", "--output", help="output HTML path (default: <json-stem>.html)")
    ap.add_argument("--template", default=str(TEMPLATE))
    args = ap.parse_args()

    src = Path(args.json_file)
    data = json.loads(src.read_text(encoding="utf-8"))
    validate(data)

    template = Path(args.template).read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        print(f"error: template must contain exactly one {PLACEHOLDER}", file=sys.stderr)
        return 2

    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")  # keep </script> out of inline JS
    html = template.replace(PLACEHOLDER, payload)

    out = Path(args.output) if args.output else src.with_suffix(".html")
    out.write_text(html, encoding="utf-8")

    n_points = sum(len(((data.get("branches") or {}).get(k) or {}).get("points") or [])
                   for k in REQUIRED_BRANCHES)
    n_refs = len(data.get("references") or [])
    n_matched = len([r for r in data.get("references") or [] if r.get("matched")])
    n_fut = len(data.get("future") or [])
    n_res = len(data.get("artifacts") or [])
    print(f"rendered {out}  ({n_points} content points, {n_refs} refs [{n_matched} matched], "
          f"{n_fut} future directions, {n_res} resources)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
