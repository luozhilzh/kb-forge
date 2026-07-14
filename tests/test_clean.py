"""Tests for core.clean — ingest-time data-noise reduction (## 摘要 cleaning)."""

from __future__ import annotations

from pathlib import Path

from kbforge.core.clean import (
    CleanReport,
    clean_post_body,
    clean_summary_section,
    split_frontmatter,
)
from kbforge.core.exporters.extract import _first_paragraph


# --- fixtures ---------------------------------------------------------------

_POST = (
    "## 摘要\n"
    "球主本人主要熟悉Python和C++，过去8年一直从事一级市场债权产品开发及商务工作"
    "，今年年初从国内某金融大厂科技子离职，投身于大模型在企业应用落地的项目实施和咨询。"
    " 转变的契机来自于23年4月3号的那个晚上，当我搞定科学上网和虚拟信用卡开通了GPT4，"
    "简单问了几个问题后，整个世界观发生了巨大冲击。也就是在那时，感觉应…\n\n"
    "## 正文\n"
    "球主本人主要熟悉Python和C++，过去8年一直从事一级市场债权产品开发及商务工作，"
    "今年年初从国内某金融大厂科技子离职，投身于大模型在企业应用落地的项目实施和咨询。\n\n"
    "转变的契机来自于23年4月3号的那个晚上，当我搞定科学上网和虚拟信用卡开通了GPT-4，"
    "简单问了几个问题后，整个世界观发生了巨大冲击。也就是在那时，感觉应该要寻求一些"
    "工作和生活方式的变化。\n"
)


def _post_with(summary: str, body: str) -> str:
    return f"## 摘要\n{summary}\n\n## 正文\n{body}\n"


# --- clean_summary_section -------------------------------------------------

def test_redundant_truncated_summary_is_removed():
    new, rep = clean_summary_section(_POST)
    assert rep.removed_summary is True
    assert "## 摘要" not in new
    assert "## 正文" in new
    # body content preserved verbatim
    assert "感觉应该要寻求一些" in new


def test_distinct_summary_with_truncation_marker_is_kept_but_stripped():
    # A summary that is NOT a body clipping but ends with an ellipsis.
    post = _post_with(
        "这是一段完全独立的摘要，和正文毫无关系…",
        "正文内容在这里，完全不同的话题。",
    )
    new, rep = clean_summary_section(post)
    assert rep.removed_summary is False
    assert rep.stripped_truncation is True
    assert "## 摘要" in new
    assert "…" not in new.split("## 摘要", 1)[1].split("## 正文")[0]


def test_distinct_complete_summary_is_kept_untouched():
    post = _post_with(
        "这是一段完全独立的、完整的摘要，没有任何省略号。",
        "正文内容在这里，完全不同的话题，而且更长一些用来区分。",
    )
    new, rep = clean_summary_section(post)
    assert rep.removed_summary is False
    assert rep.stripped_truncation is False
    assert new == post


def test_heading_variants_are_recognized():
    for variant in ["## 摘要", "## 摘要：", "## 摘要:", "### 摘要", "## 摘要 ："]:
        post = f"{variant}\n球主熟悉Python…\n\n## 正文\n球主熟悉Python和C++，过去8年从事开发工作，内容更长。\n"
        new, rep = clean_summary_section(post)
        assert rep.removed_summary is True, f"variant not cleaned: {variant!r}"
        assert "## 摘要" not in new


def test_no_summary_section_is_unchanged():
    body = "## 正文\n直接开始的正文，没有摘要段。\n"
    new, rep = clean_summary_section(body)
    assert new == body
    assert rep.removed_summary is False


def test_empty_summary_section_is_removed():
    post = "## 摘要\n\n## 正文\n正文内容。\n"
    new, rep = clean_summary_section(post)
    assert rep.removed_summary is True
    assert "## 摘要" not in new


def test_fuzzy_prefix_match_catches_typo_variant():
    # Summary differs from body opening only by a hyphen — exact containment
    # fails, but it is clearly a clipping and must be removed.
    post = _post_with(
        "No.5 POIRAG项目分享：地理数据与不规范客户信息匹配 项目源码",
        "No.5 POI-RAG项目分享：地理数据与不规范客户信息匹配\n项目源码\n正文继续。",
    )
    new, rep = clean_summary_section(post)
    assert rep.removed_summary is True
    assert "## 摘要" not in new


def test_cleaning_is_idempotent():
    new1, _ = clean_post_body(_POST)
    new2, rep2 = clean_post_body(new1)
    assert new1 == new2
    assert rep2.removed_summary is False


def test_clean_post_body_delegates():
    new, rep = clean_post_body(_POST)
    assert isinstance(rep, CleanReport)
    assert "## 摘要" not in new


# --- split_frontmatter -----------------------------------------------------

def test_split_frontmatter_preserves_block():
    doc = "---\ntitle: X\nauthor: 韦东东\n---\n\n## 正文\n正文。\n"
    fm, body = split_frontmatter(doc)
    assert fm.startswith("---")
    assert "title: X" in fm
    assert body.strip() == "## 正文\n正文。"


def test_split_frontmatter_no_fm():
    doc = "## 正文\n没有 frontmatter 的纯文本。\n"
    fm, body = split_frontmatter(doc)
    assert fm == ""
    assert body == doc


# --- _first_paragraph (export summary quality) -----------------------------

def test_first_paragraph_skips_heading_lines():
    body = "## 正文\n球主本人主要熟悉Python和C++，过去8年从事开发。\n\n第二段。\n"
    assert _first_paragraph(body) == "球主本人主要熟悉Python和C++，过去8年从事开发。"


def test_first_paragraph_skips_bare_image_lines():
    body = "![](https://img/x.png)\n球主本人主要熟悉Python。\n"
    assert _first_paragraph(body) == "球主本人主要熟悉Python。"


def test_first_paragraph_respects_limit_with_ellipsis():
    body = "这是一段很长很长很长很长很长很长很长很长很长很长很长很长很长很长的正文内容。\n"
    out = _first_paragraph(body, limit=20)
    assert out.endswith("…")
    assert len(out) == 20


# --- adapter integration ---------------------------------------------------

def test_adapter_clean_body_removes_summary():
    from kbforge.adapters.local_archive import _clean_body

    raw = "## 摘要\n球主熟悉Python…\n\n## 正文\n球主熟悉Python和C++，过去8年从事开发工作，内容更长些。\n"
    cleaned = _clean_body(raw)
    assert "## 摘要" not in cleaned
    assert "球主熟悉Python和C++" in cleaned
