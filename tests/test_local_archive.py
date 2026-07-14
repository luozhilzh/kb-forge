"""Tests for the offline local-archive adapter + end-to-end ingest."""

from __future__ import annotations

from pathlib import Path

from kbforge.adapters.local_archive import LocalArchiveAdapter
from kbforge.core.archive_ingest import ingest_archive
from kbforge.core.frontmatter import parse


def _make_mini_archive(root: Path) -> Path:
    """Create a tiny archive with zsxq-style inline tags and a missing type."""
    (root / "2026" / "07").mkdir(parents=True, exist_ok=True)
    (root / "2025" / "12").mkdir(parents=True, exist_ok=True)
    p1 = root / "2026" / "07" / "2026-07-02-t82255211218852252.md"
    p1.write_text(
        "---\n"
        "title: '#skill测评 最近在搞sk...'\n"
        "author: 韦东东\n"
        "date: 2026-07-02\n"
        "tags: [RAG/知识库, 评测/Eval]\n"
        "source: https://wx.zsxq.com/topic/82255211218852252\n"
        "group: 企业大模型应用从入门到落地\n"
        "---\n\n"
        "## 正文\n"
        "<e type=\"hashtag\" hid=\"1\" title=\"%23skill%23\" /> 最近在搞skill，"
        "发现这个测试效果是个头疼的事情<e type=\"mention\" uid=\"2\" />。\n",
        encoding="utf-8",
    )
    p2 = root / "2025" / "12" / "2025-12-10-t71111111111111111.md"
    p2.write_text(
        "---\n"
        "title: 旧帖无 type\n"
        "author: 张三\n"
        "date: 2025-12-10\n"
        "tags: [成本控制]\n"
        "---\n\n"
        "## 正文\n旧内容 <e type=\"web\" href=\"x\" title=\"y\" /> 末尾。\n",
        encoding="utf-8",
    )
    return root


def test_adapter_scan_cleans_tags_and_derives_id(tmp_path: Path) -> None:
    arch = _make_mini_archive(tmp_path / "arch")
    adapter = LocalArchiveAdapter(arch)
    topics = adapter.scan()
    assert len(topics) == 2

    by_id = {t.topic_id: t for t in topics}
    assert "82255211218852252" in by_id
    assert "71111111111111111" in by_id

    t = by_id["82255211218852252"]
    assert "<e" not in t.body, "inline tags must be stripped"
    assert "skill" in t.body
    assert t.author == "韦东东"
    assert t.published_at == "2026-07-02"
    assert set(t.tags) == {"RAG/知识库", "评测/Eval"}
    # source layout preserved for replication (use os.sep; Windows uses backslash)
    sp = t.extra["source_path"]
    assert sp.endswith("2026-07-02-t82255211218852252.md")
    assert "2026" in sp and "07" in sp


def test_adapter_scan_year_month_filter(tmp_path: Path) -> None:
    arch = _make_mini_archive(tmp_path / "arch")
    adapter = LocalArchiveAdapter(arch)
    only_2026_07 = adapter.scan(year="2026", month="07")
    assert len(only_2026_07) == 1
    assert only_2026_07[0].topic_id == "82255211218852252"

    only_2026 = adapter.scan(year="2026")
    assert len(only_2026) == 1

    capped = adapter.scan(limit=1)
    assert len(capped) == 1


def test_ingest_archive_builds_wiki(tmp_path: Path) -> None:
    arch = _make_mini_archive(tmp_path / "arch")
    out = tmp_path / "kb"
    report = ingest_archive(arch, out, dry_run=False)

    assert report["ingested_sources"] == 2
    assert report["ingested"] == 2  # run() ingested the normalized copy
    assert (out / "archive" / "2026" / "07" / "2026-07-02-t82255211218852252.md").exists()
    assert (out / "SCHEMA.md").exists()
    # SCHEMA.md is seeded with the discovered tags so validation stays quiet
    schema_txt = (out / "SCHEMA.md").read_text(encoding="utf-8")
    assert "RAG/知识库" in schema_txt
    assert "成本控制" in schema_txt

    wiki = out / "wiki"
    assert (wiki / "index.md").exists()
    assert (wiki / ".graph.json").exists()

    # every wiki page is OKF-compliant (has non-empty type) and tag-free
    pages = [p for p in wiki.glob("*.md") if p.name not in {"index.md", "log.md"}]
    assert len(pages) == 2
    for p in pages:
        meta, body = parse(p.read_text(encoding="utf-8"))
        assert str(meta.get("type", "")).strip(), f"{p.name} missing type"
        assert "<e" not in body, f"{p.name} body still has inline tags"
        # author + published_at survive the ingest passthrough
        assert meta.get("author"), f"{p.name} missing author"

    # real posts have no [[wiki-link]] -> graph edges may be empty; that is OK
    # (query falls back to BM25). We only assert the graph file is valid JSON.
    import json

    graph = json.loads((wiki / ".graph.json").read_text(encoding="utf-8"))
    assert graph["nodes"], "graph must have nodes"


def test_ingest_archive_dry_run_writes_nothing(tmp_path: Path) -> None:
    arch = _make_mini_archive(tmp_path / "arch")
    out = tmp_path / "kb"
    report = ingest_archive(arch, out, dry_run=True)
    assert report["dry_run"] is True
    assert not out.exists() or not any(out.iterdir())


def test_parse_tolerates_illegal_indicator_titles() -> None:
    """Real archive posts may carry unquoted titles starting with a YAML
    indicator (a mention ``@caucy`` or a hashtag ``#评论回复``). These must be
    preserved as strings — not raise ScannerError and not be silently dropped
    as a comment.
    """
    doc_at = (
        "---\n"
        "title: @caucy 关于如何在Dify中落地RAG\n"
        "author: 韦东东\n"
        "tags: [RAG/知识库, 大模型/训练]\n"
        "---\n\n正文\n"
    )
    meta_at, _ = parse(doc_at)
    assert meta_at["title"] == "@caucy 关于如何在Dify中落地RAG"
    assert meta_at["author"] == "韦东东"
    assert set(meta_at["tags"]) == {"RAG/知识库", "大模型/训练"}

    doc_hash = (
        "---\n"
        "title: #评论回复 @caucy 如果在一个知识库有的…\n"
        "author: 韦东东\n"
        "---\n\n正文\n"
    )
    meta_hash, _ = parse(doc_hash)
    assert meta_hash["title"] == "#评论回复 @caucy 如果在一个知识库有的…"
