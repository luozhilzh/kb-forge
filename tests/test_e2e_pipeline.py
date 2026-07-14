"""End-to-end pipeline test.

Forges a real-ish knowledge base from the bundled ``sample_kb`` archive and
asserts the *whole* chain works as one flow:

    ingest-archive  ->  classify  ->  enrich  ->  export  ->  query  ->  validate

This is the outsider's path: clone, point at an archive, and get a structured,
queryable, exportable, OKF-compliant KB. Every step is pure-local (no network,
no platform API, no model key) so it runs in CI on every push.

Unit tests prove each capability in isolation; this test proves they *compose*
into a working product. That integration gap is exactly what unit tests miss.
"""

from __future__ import annotations

from pathlib import Path

from kbforge.classify_config import ClassifyConfig
from kbforge.core.archive_ingest import ingest_archive
from kbforge.core.classify import classify_wiki
from kbforge.core.diff import validate_wiki
from kbforge.core.enrich import enrich_wiki, get_strategy as get_enrich_strategy
from kbforge.core.exporters import extract_bundles, get_exporter
from kbforge.core.query import query_wiki

SAMPLE_ARCHIVE = Path(__file__).parent / "fixtures" / "sample_kb" / "archive"


def _wiki_pages(wiki: Path) -> list[Path]:
    return [
        p
        for p in wiki.glob("*.md")
        if p.name not in {"index.md", "log.md", "SCHEMA.md"}
    ]


def test_e2e_pipeline(tmp_path: Path) -> None:
    out = tmp_path / "kb"

    # 1) ingest offline archive -> self-contained KB (archive/ + wiki/)
    report = ingest_archive(SAMPLE_ARCHIVE, out)
    assert report["ingested_sources"] >= 1

    wiki = out / "wiki"
    assert wiki.is_dir(), "ingest must compile a wiki dir"
    assert (wiki / ".graph.json").exists(), "ingest must build the knowledge graph"

    pages = _wiki_pages(wiki)
    assert len(pages) == report["ingested_sources"]
    # every compiled page must carry the OKF contract fields up front
    assert all((p.read_text(encoding="utf-8").split("\n", 1)[0].strip() == "---")
               for p in pages)

    # 2) classify into the OKF five-class structure (default local scorer)
    cls = classify_wiki(wiki, ClassifyConfig(), strategy_name="local")
    assert cls["total"] == len(pages), "every page must be classified"
    assert sum(cls["distribution"].values()) == cls["total"]
    # the classifier must add value: at least one page gets a typed class,
    # not the bare "post" fallback.
    assert any(t != "post" for t in cls["distribution"]), (
        "classifier assigned no typed class — pipeline produces only 'post'"
    )
    # the bundled sample_kb must exercise the main OKF types, so an outsider
    # cloning the repo sees a representative demo KB (not just one or two).
    expected_types = {"case", "pitfall", "scheme", "comparison", "concept", "entity"}
    assert expected_types.issubset(set(cls["distribution"])), (
        f"sample_kb should cover the main OKF types; missing: "
        f"{expected_types - set(cls['distribution'])}"
    )

    # 3) enrich: extract claim-level source anchors (local, zero-dep)
    claims = enrich_wiki(wiki, strategy=get_enrich_strategy("local"))
    assert sum(len(v) for v in claims.values()) > 0, "enrich must extract claims"

    # 4) export the classified pages to Markdown
    types = frozenset(cls["distribution"].keys())
    bundles = extract_bundles(wiki, types=types)
    assert len(bundles) >= 1, "export must find at least one bundle"
    written = get_exporter("md").export(bundles, tmp_path / "export.md")
    assert written.exists() and written.stat().st_size > 0, "export wrote nothing"

    # 5) query the compiled wiki (graph retriever, Personalized PageRank)
    results = query_wiki(wiki, "RAG 评测", top_k=3, backend="graph")
    assert len(results) >= 1, "query must return at least one hit"
    assert all(r.score >= 0 for r in results)

    # 6) the end result is OKF-compliant (no contract violations)
    violations = validate_wiki(wiki)
    assert violations == [], f"OKF violations: {violations}"
