# paper-graph JSON schema

`paper-graph.json` is the contract between the distillation step (Claude) and
the renderer (`render.py` → `template.html`). Extra fields are preserved
inside the JSON but ignored by the renderer unless listed below. All
human-readable text should be in the user's language; reference titles stay
in their original language.

## Top level

```jsonc
{
  "meta": { ... },            // required
  "branches": { ... },        // required: the 4 content groups
  "references": [ ... ],      // required (may be empty): curated key citations
  "future": [ ... ],          // required (may be empty): future-work directions
  "references_all": [ ... ]   // optional: full bibliography (NOT rendered)
}
```

## meta

```jsonc
{
  "title": "...",             // paper title (original language)
  "authors": ["...", "..."],
  "year": 2025,
  "venue": "CVPR 2025",       // or journal / preprint label
  "doi": "10.1234/...",       // optional
  "arxiv_id": "2501.12345",   // optional — enables arXiv link on root node
  "language": "zh",           // language used for labels/details
  "depth": "full-text",       // or "abstract-only" (set when summarizing from abstract alone)
  "generated": "2026-09-11",  // ISO date
  "summary": "one-line gist"  // shown in the page header card
}
```

## branches

Four content keys (`background` / `innovations` / `experiments` /
`conclusions`), each with `label`, `summary` (2–3 sentence description of
that whole branch, shown on hover and in the branch panel), and `points`.
`references` and `future` may also carry `label` + `summary` here (their
nodes live at top level but the renderer reads the branch metadata):

```jsonc
{
  "background":  { "label": "研究背景", "summary": "……本分支概述……",
                   "points": [ { "id": "bg1", "label": "...", "detail": "..." } ] },
  "innovations": { "label": "核心创新", "summary": "……",
                   "points": [ { "id": "inn1", "label": "...", "detail": "..." } ] },
  "experiments": { "label": "实验与结果", "summary": "……",
                   "points": [ { "id": "exp1", "label": "...", "detail": "...", "metrics": "ATE -32% vs FAST-LIO" } ] },
  "conclusions": { "label": "结论", "summary": "……",
                   "points": [ { "id": "con1", "label": "...", "detail": "..." } ] },
  "references":  { "label": "引用网络", "summary": "……" },
  "future":      { "label": "未来方向", "summary": "……" }
}
```

| field     | required | notes                                          |
| --------- | -------- | ---------------------------------------------- |
| `id`      | yes      | stable, unique (`bg1`, `inn2`, `exp1`, `con3`) |
| `label`   | yes      | short node caption (≤ ~20 chars reads best)    |
| `detail`  | yes      | 2–4 sentences shown in the detail panel        |
| `metrics` | no       | concrete numbers; only meaningful on `experiments` |
| `blocks`  | no       | rich content array (below), rendered after detail |

## blocks (rich content)

Optional `blocks` array on any node. Rendered in order after `detail` /
`metrics`. Block types:

```jsonc
[
  { "type": "text",    "text": "普通段落" },
  { "type": "metrics", "text": "ATE 0.02 m（↓32%）" },
  { "type": "formula", "latex": "\\min_{\\{s_i\\}} \\sum ...",
    "caption": "帧级尺度优化目标（论文 Eq.1）" },
  { "type": "image",   "url": "https://arxiv.org/html/<id>v<N>/pipeline.png",
    "caption": "系统管线（论文 Fig.1）" },
  { "type": "table",   "caption": "EuRoC ATE (m)（论文 Table I）",
    "headers": ["方法", "MH01", "MH02"],
    "highlight": "ORB-SLAM3",          // row whose first cell matches gets highlighted
    "rows": [["DA3-Long", "0.348", "0.527"], ["ORB-SLAM3", "0.021", "0.019"]] },
  { "type": "list",    "items": ["……", "……"] }
]
```

- `formula`: KaTeX (CDN) renders it; offline the raw LaTeX is shown in a
  code block — always valid.
- `image`: take the URL from `paper.json`'s `figures[]` (written by
  `get_paper.py`, version-pinned and resolvable) rather than composing it by
  hand. Remote images need network at view time; a friendly fallback note
  replaces them offline.
- `table`: keep ≤ 6 columns; numbers as strings right-align automatically.
- Pull equations/tables/figures **from the paper itself** — a block should
  cite its source (Eq./Table/Fig. number) in the caption.

## artifacts

Optional. Linkable things shipped with the paper — code, dataset, demos,
docs. When non-empty the renderer adds a seventh branch (资源) whose leaves
are these entries, drawn as squares to read as "this goes somewhere else",
and lists them as buttons on the paper (root) node too.

```jsonc
{
  "id": "res1", "type": "artifact",
  "kind": "代码仓库",              // short label for the panel tag
  "label": "ScaRF-SLAM (GitHub)",  // node caption
  "url": "https://github.com/...", // where clicking takes you
  "detail": "官方开源实现（GPL-3.0）……",
  "source": "GitHub README"        // where you learned about it
}
```

Also set `branches.resources = { "label": "资源", "summary": "……" }` so the
branch gets a description like every other. Omit `artifacts` entirely when
the paper ships nothing public — the branch disappears and the graph is the
usual six.

## references

Curated **key** citations only (8–15). Each:

```jsonc
{
  "id": "ref1",
  "type": "ref",
  "title": "FAST-LIO2: ...",        // original language
  "year": 2022,
  "venue": "T-RO",
  "relation": "主要对比基线",         // why this paper cites it — one short phrase
  "matched": true,                   // set by fetch_refs.py
  "s2": {                            // set by fetch_refs.py — do not fabricate
    "s2Id": "...", "title": "...", "year": 2022, "venue": "...",
    "abstract": "... ≤1200 chars ...",
    "citationCount": 1234,
    "externalIds": { "DOI": "...", "ArXiv": "..." }
  },
  "children": [ ... ]                // optional extension: sub-graph (same node shape)
}
```

`matched: false` (queried, no hit) or absent `s2` (never queried / offline)
are both fine — the panel degrades to title + relation only.

## future

```jsonc
{
  "id": "fut1",
  "type": "future",
  "label": "紧耦合视觉-惯导初始化",
  "detail": "论文 §7 指出当前初始化在弱纹理场景退化……",
  "search_query": "visual inertial initialization degenerate low texture",
  "inferred": true,                  // true when this direction is Claude's extrapolation, not stated in the paper
  "children": [ ... ]                // optional extension
}
```

`search_query` should be **English keywords** (arXiv/Scholar search works
best) even when the UI language is Chinese — it powers the one-click
"arXiv 搜索 / Google Scholar" buttons.

## Node shape shared by children (extension)

Any `children` entry uses the same minimal node shape
(`id`, `type` ∈ `ref|future|point`, `label`, `detail`, plus whatever fields
apply). Children render as second-level leaves of their parent and expand the
same way — this is how a cited paper's own graph gets grafted onto the parent
graph.
