# 第三方来源说明

本仓库中 `paper-graph` 为原创作品。`thesis-polish` 派生自他人作品，说明如下。

---

## thesis-polish

- **上游**：https://github.com/lmcggg/graduate-thesis-polish-and-write-skill
- **上游作者**：lmcgg
- **上游许可**：MIT License，Copyright (c) 2026 lmcgg
- **上游许可全文**：见 `plugins/thesis-polish/LICENSE`（原样保留，未改动）

### 本副本做了什么

上游是一个通用的中文理工科毕业论文写作风格 skill。本副本做了两类改动：

1. **通用化改写**。上游的 `description`、`SKILL.md` 正文曾指向一个具体的
   学位论文实例；本副本把那些指向改回通用表述，使 skill 可被任何人用于
   自己的论文。
2. **补上约束层模板**。新增 `local-constraints.md`，作为「把通用规则本地化到
   某一篇具体论文」的模板与范例，含术语禁用表、题目口径、LaTeX 保护规则、
   章节地图四类内容。出厂状态为占位符模板。

### 未包含的内容

上游使用者的**范例论文配置与其风格指纹未包含在本副本内**。本副本的
`reference-thesis.md` 与 `reference-thesis-fingerprint.md` 均为空白模板，
不含任何第三方论文的原文片段或身份信息。使用者需自行指定范例论文。

### 如果你要再分发

按 MIT 要求保留 `plugins/thesis-polish/LICENSE` 即可。若你基于本副本继续修改，
建议同时更新本文件，写清你改了什么，便于下游追溯。
