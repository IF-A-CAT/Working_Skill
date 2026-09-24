---
name: paper-graph
description: >
  Summarize an academic paper (background, core innovations, experiments &
  results, conclusions) into an interactive, expandable knowledge-graph web
  page (single self-contained HTML + structured JSON). The graph includes a
  curated citation network (enriched online via Semantic Scholar, with an
  offline fallback), future-work direction nodes that link out to arXiv /
  Google Scholar searches, and a resources branch collecting the paper's
  code repo, dataset, demo videos and docs. Use this skill whenever the user asks to summarize
  a paper, digest a PDF or arXiv paper, make a paper mind-map / knowledge
  graph / 智能图 / 论文图谱 / 思维导图, visualize a paper's structure, or
  explore a paper's references and future directions — even if they just paste
  an arXiv link or a PDF path with no other explanation. Also use when asked
  to "读一下这篇论文" if the user wants a visual, structured result.
---

# Paper Graph

Turn one paper into an interactive graph: center node = the paper, six branch
groups (background / innovations / experiments / conclusions / key references /
future directions), leaf nodes carry the actual content, clicking opens a
detail panel. Output is always **two files**: a structured `paper-graph.json`
(the durable, re-usable artifact) and a self-contained `paper-graph.html`
(rendered from it). The JSON is the contract — other pipelines can consume it.

Full JSON field reference: `references/schema.md`. Read it before writing data
by hand; after that, the workflow below shows the shape.

## Workflow

Steps run in order, each writing a file the next one reads. Scripts live in
this skill's `scripts/` (call them by absolute path). Every step is
re-runnable and skips work already done, so interrupting and resuming is
safe — pick up wherever the artifacts say you left off.

### 1. Acquire the paper

```bash
mkdir -p paper-graph-<slug> && cd paper-graph-<slug>
python3 <skill-dir>/scripts/get_paper.py 2606.00307 --out .
```

Accepts an arXiv id, an arXiv URL, or a local PDF path. It writes:

- `paper.txt` — full text, layout preserved (read this to distill)
- `paper.json` — metadata (title/authors/abstract/venue/doi via the arXiv
  API) plus `figures[]`: every figure's hosted URL and caption
- `paper.pdf` — the downloaded PDF (arXiv input only)

Use `paper.json`'s figure URLs verbatim for `image` blocks — they are
version-pinned and verified resolvable. If `figures` is empty (paper has no
arXiv HTML rendering), skip image blocks and lean on `formula` / `table`.

If the download fails (offline, paywalled, no arXiv version), ask the user
for the PDF and pass its path to `get_paper.py`. Summarizing from the
abstract alone is a last resort: only with the user's agreement, and then
set `meta.depth: "abstract-only"` so the page shows a warning.

Then read `paper.txt`. For long papers prioritize: Abstract, Introduction,
the contributions list, Method overview, experiment tables (the numbers),
Limitations, Conclusion. Skim related work — reference titles come from the
bibliography at the end.

### 2. Distill into JSON

Write `paper-graph.json` following `references/schema.md`. Quality bar:

- **Language**: labels, details, and all human-readable text follow the
  language the user is speaking (default to Chinese for 中文 users). Titles of
  referenced papers stay in their original language.
- **Branch summaries**: every branch (including `references` / `future`)
  gets a `summary` — 2–3 sentences describing that whole aspect of the
  paper. It appears on branch hover and atop the branch panel, and anchors
  the reader before they dive into leaves.
- **Rich blocks** (`blocks` array, see `references/schema.md`): where the
  paper has the material, back nodes with more than text — key equations as
  `formula` (KaTeX), comparison/ablation numbers as `table`, and figures as
  `image` (for arXiv papers, figure URLs come from
  `https://arxiv.org/html/<id>v<N>/`). Cite the source (Eq./Table/Fig.
  number) in each caption. Not every node needs blocks — background and
  conclusion points are usually well-served by prose alone, while method
  and experiment nodes benefit most.
- **background** (3–6 points): what problem, why it matters, what the prior
  state of the art could not do. Each point is one claim + 2–4 sentence
  detail — a `detail` of one short sentence is too thin to justify a node.
- **innovations** (2–6 points): the paper's actual contributions, stated
  specifically (mechanism, not vibes). "提出 X 模块，通过 Y 解决 Z" beats
  "提出了一种新方法".
- **experiments** (3–6 points): datasets/benchmarks, baselines compared, and
  **concrete numbers** (metrics, %, latency) pulled from tables. A point
  without a number should still carry the qualitative finding in `detail`.
- **conclusions** (2–4 points): takeaways + stated limitations.
- **references**: curate **8–15 key references** — the ones the paper's story
  actually builds on or directly compares against (baselines, foundational
  methods, directly competing work), not the full 40-entry bibliography. For
  each, fill `relation` in one short phrase: why this paper cites it (e.g.
  "主要对比基线", "开创性工作", "同任务 SOTA"). Optionally keep the complete
  list in `references_all` — the graph only renders the curated set.
- **future** (3–6 nodes): directions the authors state (limitations → future
  work) plus 1–2 reasonable extrapolations you infer, clearly derivable from
  the paper. Each needs a `search_query` — a good English keyword query for
  finding follow-up work (it becomes a one-click arXiv/Scholar search in the
  page). Mark your own extrapolations with `"inferred": true`.
- Every point gets a stable `id` (`bg1`, `inn2`, `exp1`, `ref3`, `fut2`, ...).
- Truncate any `abstract` you embed to ≤1200 chars.

### 2b. Supplement from project sources

Papers usually ship with public artifacts. Find them and record them in two
places: as evidence inside content nodes, and as entries in `artifacts[]`
(rendered as a seventh "资源" branch — see schema).

- **Code repo README**: for the paper's own repo (from the paper, or found
  via search), fetch
  `https://raw.githubusercontent.com/<org>/<repo>/main/README.md` (try
  `master` too). Extract what the paper doesn't say: supported systems /
  hardware, install & usage structure (wiki/sections), dataset download
  links, demo videos, license, release status.
- **Project page** (if linked) and **dataset landing page** for papers that
  contribute data — same treatment.

Then write `artifacts` — one entry per linkable thing the user would
actually want to click: code repo, dataset, demo video(s), docs/wiki,
project page, paper page. Give each a `label` (short, recognizable), `kind`
(代码仓库 / 数据集 / 演示视频 / 文档 / 论文页面 …), the `url`, and a `detail`
of 1–3 sentences saying what it is and what you'd go there for. Give the
branch itself a `summary` like any other. If the paper has no public
artifacts, omit `artifacts` entirely — the resources branch then simply
does not exist, and the graph stays at six branches.

Also work findings into the content nodes where they belong: practical-usage
info strengthens innovation/experiment nodes. Tag any node whose content
goes beyond the paper with `"source": "GitHub README"` (or the page name) —
the detail panel renders it as an origin note, so readers can tell paper
claims from repo claims.

### 3. Enrich references online (skip gracefully offline)

```bash
python3 <skill-dir>/scripts/fetch_refs.py paper-graph.json --top 15
```

Matches each curated reference by title against the Semantic Scholar API and
fills in `s2` (year, venue, abstract, citationCount, externalIds). It rate-
limits itself and retries on 429. If the network is down it exits cleanly
with a warning — proceed; the page falls back to whatever metadata was
extracted from the paper's own bibliography (title/year from the reference
list, no abstract).

### 4. Render

```bash
python3 <skill-dir>/scripts/render.py paper-graph.json
# → paper-graph.html next to the JSON (or -o out.html)
```

Validates the JSON structure, warns about thin branches and missing metrics,
then injects the data into the bundled template. Re-running is idempotent —
render as often as the JSON changes.

### 5. Verify

```bash
python3 <skill-dir>/scripts/verify.py paper-graph.html
```

Opens the page in a real browser engine and checks the invariants a visual
glance can miss: every node has a finite, distinct position (node-stacking /
NaN layout bugs render as a nearly empty canvas), no label pills overlap, no
branch pill is invisible, no JS errors during boot. Exit code 1 means the
page is structurally broken — fix and re-render before delivering.

It auto-detects a headless browser (playwright's chromium, or a system
chrome/chromium; `PAPER_GRAPH_CHROME=/path/to/chrome` to force one) and
exits 0 with a "skip" note if none is installed, so it never blocks
delivery on a machine without a browser.

Do not deliver on the strength of the exit code alone — also open the page
and look at it. Verification catches structural breakage; it cannot tell you
the graph is *about* the right things.

### 6. Deliver

- Default output directory: `paper-graph-<paper-slug>/` under the current
  working directory (slug = first meaningful words of the title, kebab-case),
  unless the user names a location.
- Tell the user both file paths. The HTML opens in any browser — no server,
  no network needed after generation. Mention `verify.py`'s result and that
  the JSON is the reusable artifact.
- Briefly report what the graph contains: N background points, N innovations,
  ..., how many references were matched online with abstracts.

## Reproducibility

The pipeline is a chain of files on disk, not a single session's memory —
re-running any step is safe and costs only what changed:

| Artifact | Produced by | Re-run when |
| -------- | ----------- | ----------- |
| `paper.txt` / `paper.json` | `get_paper.py` | paper version changed |
| `paper-graph.json` | you (distillation) | content needs revision |
| `s2` fields in refs | `fetch_refs.py` | more refs added (skips enriched ones) |
| `paper-graph.html` | `render.py` | any JSON edit |

Two habits keep a run reproducible:

- **Cite the source inside the data.** Every block caption names its origin
  (Eq./Table/Fig. number, or the README for repo-sourced facts), and every
  node that leans on an external source carries `source`. A reader — or a
  later run — can then tell paper claims from inference from repo claims.
- **Never fabricate a field.** If a figure URL, metric, or citation could
  not be fetched, leave it out rather than filling it plausibly. The
  renderer degrades gracefully on missing data (formulas fall back to raw
  LaTeX, images to a placeholder note, refs to title-only), so an honest gap
  costs less than a wrong number.

## Interaction model (what the user gets)

- Static deterministic radial layout (no physics): center = paper, colored
  sector wedges sized by content (six, or seven when the paper ships public
  artifacts), branch nodes with count badges, leaves on alternating rings.
  Positions are computed once — the graph can never collapse or drift.
- Label pills: content/future nodes carry wrapped (≤2-line) pill labels;
  reference nodes are dots that show their title as a floating pill on
  hover (keeps the citation sector decluttered). Resource links are squares,
  marking them as things that open elsewhere.
- Click a branch node → collapse/expand its sector (double-click also
  toggles); the legend is gone by design, as branch pills carry their own
  labels and counts.
- Click any leaf → right-side detail panel: full detail text, metrics,
  abstracts for references (year / venue / citation count), source badges
  (e.g. "来源：GitHub README"), and for future-direction nodes a one-click
  "arXiv 搜索 / Google Scholar" action.
- Toolbar: expand/collapse all, search filter (dims non-matches),
  dark/light toggle, fit-to-view. Zoom (wheel), pan (drag background),
  double-click = fit.

## Extending

The JSON is the contract for extension, not the HTML:

- Re-run this skill on a cited paper, then merge its `root`/branches into the
  parent's `references` entry as children — the renderer draws any depth of
  nesting under a reference node (children of a reference node appear when
  that node is expanded).
- `future[].search_query` is deliberately a *query*, not a paper list: it
  stays valid as new literature appears. If the user wants actual papers now,
  run the query against arXiv/Semantic Scholar and attach results as
  `children` with `type: "ref"`.
- Downstream pipelines (e.g. a literature-map site) should consume the JSON
  directly; the HTML is just one rendering.
