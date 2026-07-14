---
topic_id: "105"
title: Milvus 与 pgvector 的选型对比
tags: [向量库选型, 对比]
published_at: "2026-09-18"
---

向量库怎么选，取决于团队现状。

## 对比

Milvus 适合超大规模、需要独立部署与调优的团队；pgvector 适合已经在用 Postgres、想要零运维成本的团队。

## 选型建议

小规模先用 pgvector 验证链路，规模上来再迁 Milvus。不要为了"先进"提前上重架构。

检索策略参考 [[t102-chunk-strategy]]。
