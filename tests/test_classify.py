"""Tests for the OKF five-class auto-classification (feature ③)."""

from __future__ import annotations

from pathlib import Path

import pytest

from kbforge.core.classify import (
    ClassifyConfig,
    LocalClassifier,
    classify_wiki,
    get_strategy,
)
from kbforge.core.frontmatter import parse

_RESERVVED = {"index.md", "log.md"}


def _page(path: Path, title: str, tags: list[str], body: str, ptype: str = "post") -> None:
    tag_yaml = "[" + ", ".join(tags) + "]" if tags else "[]"
    text = f"---\ntype: {ptype}\ntitle: {title}\ntags: {tag_yaml}\n---\n\n{body}\n"
    path.write_text(text, encoding="utf-8")


def _make_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    # case: heading + tag
    _page(wiki / "p_case.md", "某制造企业 RAG 落地案例", ["业务落地"],
          "## 案例分享\n我们如何把知识库用到了客服。")
    # pitfall: heading
    _page(wiki / "p_pitfall.md", "RAG 常见踩坑", [],
          "## 踩坑实录\n向量库召回不准的三大原因。")
    # scheme: heading
    _page(wiki / "p_scheme.md", "企业知识库方案设计", [],
          "## 方案设计\n整体架构与分层存储。")
    # comparison: heading + title
    _page(wiki / "p_cmp.md", "向量库选型对比", [],
          "## 对比分析\nMilvus 与 pgvector 的差异。")
    # concept: title cue
    _page(wiki / "p_concept.md", "什么是 RAG 的核心概念", [],
          "正文解释检索增强生成的原理。")
    # entity: title names a generic tool-class cue (no competing cue)
    _page(wiki / "p_entity.md", "LangChain 框架解析", [],
          "## 正文\n介绍该框架的能力与局限。")
    # post: no signal
    _page(wiki / "p_post.md", "本周社群闲聊", [],
          "大家讨论了最近的行业新闻，没有结论。")
    return wiki


def test_local_classifier_signals(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    clf = LocalClassifier(ClassifyConfig())
    expectations = {
        "p_case": "case",
        "p_pitfall": "pitfall",
        "p_scheme": "scheme",
        "p_cmp": "comparison",
        "p_concept": "concept",
        "p_entity": "entity",
        "p_post": "post",
    }
    for slug, expected in expectations.items():
        meta, body = parse((wiki / f"{slug}.md").read_text(encoding="utf-8"))
        got = clf.classify(slug, str(meta.get("title", slug)),
                           [str(t) for t in meta.get("tags", [])], body)
        assert got == expected, f"{slug}: expected {expected}, got {got}"


def test_lexicon_override(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    cfg = ClassifyConfig(lexicon={"case": ["独家信号词"], "pitfall": [], "scheme": [],
                                  "comparison": [], "concept": [], "entity": []})
    clf = LocalClassifier(cfg)
    # a page whose body contains the custom cue must become 'case'
    _page(wiki / "p_custom.md", "普通标题", [], "这里提到了独家信号词。")
    meta, body = parse((wiki / "p_custom.md").read_text(encoding="utf-8"))
    assert clf.classify("p_custom", meta["title"], [], body) == "case"


def test_classify_wiki_real_run_writes_types(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    rep = classify_wiki(wiki, ClassifyConfig(), dry_run=False)
    assert rep["dry_run"] is False
    assert rep["total"] == 7
    # types written back into frontmatter
    meta, _ = parse((wiki / "p_case.md").read_text(encoding="utf-8"))
    assert meta.get("type") == "case"
    # index.md rebuilt with per-type grouping
    idx = (wiki / "index.md").read_text(encoding="utf-8")
    assert "## case" in idx and "[[p_case]]" in idx


def test_idempotent(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    r1 = classify_wiki(wiki, ClassifyConfig(), dry_run=False)
    r2 = classify_wiki(wiki, ClassifyConfig(), dry_run=False)
    assert r1["distribution"] == r2["distribution"]


def test_llm_falls_back_without_key(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    cfg = ClassifyConfig(strategy="llm", llm={})  # no api_key → local fallback
    strat = get_strategy("llm", cfg)
    # exercising a page must not raise and must return a valid type
    assert strat.classify("p_case", "某制造企业 RAG 落地案例", ["业务落地"],
                          "## 案例分享\n正文。") == "case"


def test_cli_dry_run_without_config(tmp_path: Path, monkeypatch) -> None:
    wiki = _make_wiki(tmp_path)
    from kbforge.cli import cli
    from click.testing import CliRunner

    monkeypatch.chdir(tmp_path)  # no config.yaml here
    result = CliRunner().invoke(cli, ["classify", "--wiki-dir", str(wiki), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "case" in result.output and "dry-run" in result.output
    # dry-run must not write types
    meta, _ = parse((wiki / "p_case.md").read_text(encoding="utf-8"))
    assert meta.get("type") == "post"
