"""Generate a synthetic (fake) knowledge base for tests and demos.

No real posts or attachments are ever written — content is fictional and the
group id is the placeholder ``planet_demo_001``. Regenerate with
``python -m kbforge make-fixtures``.
"""

from __future__ import annotations

from pathlib import Path

# Fictional content only. ------------------------------------------------- #
_SCHEMA = """\
# 知识库主题

## RAG评估
## 成本控制
"""

_POSTS: dict[str, str] = {
    "2026/07/t101-rag-eval.md": (
        "---\ntopic_id: \"101\"\ntype: case\ntitle: RAG 评测为什么不能只看准确率\n"
        "tags: [RAG评估]\npublished_at: \"2026-07-08\"\n---\n\n"
        "我们做 RAG 评测时不能只看准确率。召回率和上下文噪声同样关键。\n\n"
        "相关方法见 [[t102-chunk-strategy]]，成本上要算清 [[t103-gpu-cost]]。\n"
    ),
    "2026/07/t102-chunk-strategy.md": (
        "---\ntopic_id: \"102\"\ntype: concept\ntitle: 分块策略对召回的影响\n"
        "tags: [RAG评估]\npublished_at: \"2026-07-09\"\n---\n\n"
        "分块太碎会让语义断裂，太粗会引入噪声。需要按语义边界切分。\n\n"
        "成本角度参考 [[t103-gpu-cost]]。\n"
    ),
    "2026/08/t103-gpu-cost.md": (
        "---\ntopic_id: \"103\"\ntype: pitfall\ntitle: 推理成本被忽视的坑\n"
        "tags: [成本控制]\npublished_at: \"2026-08-02\"\n---\n\n"
        "长上下文直接丢给大模型会爆 GPU 成本。先用检索收窄再推理。\n\n"
        "回顾 [[t101-rag-eval]] 的评测结论。\n"
    ),
}


def generate(out_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "SCHEMA.md").write_text(_SCHEMA, encoding="utf-8")

    for rel, content in _POSTS.items():
        path = out_dir / "archive" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    # A fake attachment placeholder (structure only, no real file).
    att = out_dir / "_attachments" / "planet_demo_001" / "2026" / "07" / "t101-rag-eval" / "demo.pdf"
    att.parent.mkdir(parents=True, exist_ok=True)
    att.write_text("synthetic attachment placeholder\n", encoding="utf-8")
