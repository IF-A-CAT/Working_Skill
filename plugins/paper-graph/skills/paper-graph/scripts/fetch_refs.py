#!/usr/bin/env python3
"""Enrich paper-graph.json references with Semantic Scholar metadata.

For each entry in data["references"] that lacks an "s2" dict, queries the
Semantic Scholar Graph API paper-match endpoint by title and stores the best
match's year / venue / abstract / citationCount / externalIds under ref["s2"],
setting ref["matched"] accordingly. Rate-limits itself and retries on 429.
Exits 0 with a warning when the network is unavailable — callers should
proceed with whatever metadata they already have (offline fallback).

Usage:
    python3 fetch_refs.py paper-graph.json [--top 15] [--timeout 10]
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.semanticscholar.org/graph/v1/paper/search/match"
FIELDS = "title,year,venue,abstract,citationCount,externalIds"
ABSTRACT_MAX = 1200
PAUSE_S = 1.3          # between successful calls (unauthenticated rate limit)
RETRY_DELAYS = (5, 15, 30)


def query_s2(title: str, timeout: float) -> dict | None:
    """Return best-match metadata dict, {} when no match, None on network error."""
    url = f"{API}?query={urllib.parse.quote(title)}&fields={FIELDS}"
    req = urllib.request.Request(url, headers={"User-Agent": "paper-graph-skill/1.0"})
    for attempt, delay in enumerate((0,) + RETRY_DELAYS):
        if delay:
            print(f"    rate-limited, retrying in {delay}s ...", file=sys.stderr)
            time.sleep(delay)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.load(resp)
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < len(RETRY_DELAYS):
                continue
            if e.code == 404:
                return {}
            print(f"    HTTP {e.code}", file=sys.stderr)
            return None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"    network error: {e}", file=sys.stderr)
            return None
    data = payload.get("data") or []
    if not data:
        return {}
    best = data[0]
    abstract = best.get("abstract") or ""
    return {
        "s2Id": best.get("paperId"),
        "title": best.get("title"),
        "year": best.get("year"),
        "venue": best.get("venue"),
        "abstract": abstract[:ABSTRACT_MAX] if abstract else None,
        "citationCount": best.get("citationCount"),
        "externalIds": best.get("externalIds") or {},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("json_file")
    ap.add_argument("--top", type=int, default=15, help="max refs to query")
    ap.add_argument("--timeout", type=float, default=10.0)
    args = ap.parse_args()

    with open(args.json_file, encoding="utf-8") as f:
        data = json.load(f)

    refs = data.get("references") or []
    todo = [r for r in refs if isinstance(r, dict) and not r.get("s2")][: args.top]
    if not todo:
        print("nothing to do: all references already enriched (or none listed)")
        return 0

    matched = unmatched = failed = 0
    for i, ref in enumerate(todo):
        title = (ref.get("title") or "").strip()
        if not title:
            continue
        print(f"[{i + 1}/{len(todo)}] {title[:70]}")
        result = query_s2(title, args.timeout)
        time.sleep(PAUSE_S)
        if result is None:            # network trouble — stop trying, stay offline-safe
            failed = len(todo) - i
            break
        if result:
            ref["s2"] = result
            ref["matched"] = True
            ref.setdefault("year", result.get("year"))
            ref.setdefault("venue", result.get("venue"))
            matched += 1
            cc = result.get("citationCount")
            print(f"    matched (citations: {cc if cc is not None else '?'})")
        else:
            ref["matched"] = False
            unmatched += 1
            print("    no match")

    with open(args.json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\ndone: {matched} matched, {unmatched} unmatched, {failed} skipped "
          f"(offline) — saved to {args.json_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
