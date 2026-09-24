# Working_Skill

IF-A-CAT 自写与改造的 Claude Code skills 集合。以 Claude Code 插件市场（marketplace）形式发布，可以整仓安装，也可以只装其中一个插件。

## 装了有什么

| 插件 | 干什么 | 来源 |
|---|---|---|
| [`paper-graph`](plugins/paper-graph) | 把一篇论文拆成可交互知识图谱网页：背景、核心创新、实验与结果、结论，外加精选引用网络、可点开的未来方向、资源分支。支持 arXiv 链接或本地 PDF。 | 原创 |
| [`thesis-polish`](plugins/thesis-polish) | 中文理工科研究生毕业论文的写作风格约束与审校。60 多条规则、两个核心自检问题、基于范例论文风格指纹的对照工作流，另有一层可本地化的论文专属约束。 | 派生自 [lmcggg/graduate-thesis-polish-and-write-skill](https://github.com/lmcggg/graduate-thesis-polish-and-write-skill)，见 [NOTICE.md](NOTICE.md) |

## 装

```shell
# 添加本市场
/plugin marketplace add IF-A-CAT/Working_Skill

# 装其中一个
/plugin install paper-graph@working-skill
/plugin install thesis-polish@working-skill

# 两个都装
/plugin install paper-graph@working-skill
/plugin install thesis-polish@working-skill
```

命令行等价写法：

```shell
claude plugin marketplace add IF-A-CAT/Working_Skill
claude plugin install paper-graph@working-skill
```

本地克隆后用绝对路径添加也行，方便改着用：

```shell
git clone https://github.com/IF-A-CAT/Working_Skill.git
/plugin marketplace add /path/to/Working_Skill
```

## 用

装完直接说人话，不用记命令：

```
帮我把这篇论文做成知识图谱：https://arxiv.org/abs/2511.10647
```

```
读一下 /path/to/paper.pdf，出一张图
```

```
审一下 chapters/chapter3.tex
```

```
按 thesis-polish 的规则帮我写 4.1 节的引言
```

## thesis-polish 用之前要先做一件事

这个 skill 的设计是「通用规则 + 论文专属约束」两层。装完直接能跑，但只跑通用层。要发挥全部效果，先把约束层填了：

打开 `plugins/thesis-polish/skills/thesis-polish/local-constraints.md`，把里面的 `<...>` 占位符换成你论文的真实值——题目、术语禁用表、LaTeX 保护规则、章节地图。填完之后，审校就从「中文毕业论文通用」收紧到「你这篇论文专用」。

再配一本范例论文，效果最好。对话里说一句就行：

```
参考论文是 /path/to/some_thesis.pdf
```

skill 会读一次原文，抽出 5–10 KB 的「风格指纹」存下来；此后只吃指纹，不再碰原文，省 token。不配也能跑，退化成纯规则模式。

## 目录结构

```
Working_Skill/
├── .claude-plugin/
│   └── marketplace.json          # 市场清单，唯一必需的入口文件
├── plugins/
│   ├── paper-graph/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/paper-graph/
│   └── thesis-polish/
│       ├── .claude-plugin/plugin.json
│       ├── LICENSE               # 上游 MIT 许可，原样保留
│       └── skills/thesis-polish/
├── LICENSE
├── NOTICE.md
└── README.md
```

## 自己加一个

在 `plugins/` 下建目录，放 `skills/<skill-name>/SKILL.md`（`SKILL.md` 的 frontmatter 只要求 `description`，`name` 缺省取目录名），然后在 `.claude-plugin/marketplace.json` 的 `plugins` 数组里加一条：

```json
{
  "name": "your-skill",
  "source": "./plugins/your-skill",
  "description": "一句话说明",
  "category": "writing"
}
```

改完校验一下再提交：

```shell
claude plugin validate .
```

## 许可

本仓库原创部分为 MIT，见 [LICENSE](LICENSE)。

`thesis-polish` 派生自 lmcgg 的 MIT 作品，上游许可全文原样保留在 `plugins/thesis-polish/LICENSE`。第三方来源说明见 [NOTICE.md](NOTICE.md)。
