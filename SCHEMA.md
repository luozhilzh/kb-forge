# SCHEMA.md — kb-forge OKF 规范说明

> 本文件是 `kb-forge` 仓库内对 **Open Knowledge Format (OKF) v0.1**（Apache-2.0，
> GoogleCloudPlatform/knowledge-catalog）的规范说明，作为 wiki 产物的硬契约。
> 它与 `docs/design.md` §5（OKF contract）同源；`ingest` / `ingest-archive` 在编译
> 用户 wiki 时，会按扫描到的标签自动播种一份 `SCHEMA.md` 到该 wiki 根，与此处规范一致。

## 1. 页面格式

每个 wiki 页 = **Markdown + YAML frontmatter**，链接即知识图谱：

```yaml
---
type: concept            # 必填；见 §2 类型
title: 召回率
topic_id: "101"          # 可选；平台原始帖子 id
content_hash: a1b2c3…    # 必填；正文 body-only 的 sha256（见 §4）
sources:                 # 可选；来源溯源
  - archive/2026/07/01-t101.md
tags: [RAG, 评估]
author: 张三             # 可选；真实帖透传
published_at: 2026-07-01
---
正文……可用 [[other-slug]] 或 [[other-slug|显示文本]] 做双链。
```

## 2. 页面类型（`type`）

默认类型集（可在 `config.yaml` 的 `classify.types` 中自定义）：

| 类型 | 含义 |
|------|------|
| `concept` | 概念 / 原理页 |
| `entity` | 实体页（工具 / 框架 / 产品等具体对象） |
| `case` | 案例 / 落地实践页 |
| `pitfall` | 踩坑 / 反模式页 |
| `scheme` | 方案 / 架构 / 规范页 |
| `comparison` | 对比 / 选型页 |
| `post` | 原始帖页（无明确信号时的兜底类型） |

> 真实 archive 接入时，源帖最初多为 `post`；运行 **`kbforge classify`** 会按
> 标签 + 标题/小标题结构信号 + 可配置词典，把它们自动归类进上表（entity 仅当
> 标题/小标题/标签显式点名某工具才命中，避免正文顺带提及就被误判）。分类后
> `index.md` 按类型重建，`export` 的 `--types` 才能按类型抽取。

> 消费端**容错**：未知 `type`、缺失可选字段、断链均为**警告而非硬错**（见 §5）。

## 3. 保留文件

- `index.md` — 枢纽页（按 type 分组的落地页）。
- `log.md` — 变更史。
- `SCHEMA.md` — 主题 / 标签清单（**建议性 / advisory**），由 `schema.py` 解析；
  用于校验时比对标签，缺失不报错。

## 4. `content_hash`

- 计算对象 = **正文 body-only**（剥去易变的 frontmatter，改时间戳不误报）。
- 在 `ingest` 落盘前计算；用于跨平台去重、变更检测、幂等跳过。
- `content_hash` 变化会触发 `diff` 重跑。

## 5. 校验（OKF 防漂移守卫）

`validate_wiki(wiki_dir)`（`core/diff.py`）单态合规校验：

- 每页须带 `type` + `content_hash`；
- 每条 `[[wiki-link]]` 须可解析到存在的页（未知 slug 保留原样、不报错）；
- 断链 / 缺字段 → 记为 `Violation`（警告级，不阻断）。

`tests/test_okf_compliance.py` 定义 3 条硬合规 golden 断言（type 必填、链接可解析、
容错消费），作为回归基线。

## 6. 引用

- 设计契约详见 `docs/design.md` §5（OKF contract）。
- 规划溯源详见 `docs/知识星球整理工具集_开源方案.md`。
