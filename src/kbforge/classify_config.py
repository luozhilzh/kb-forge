"""Classification configuration contract (leaf module, no core imports).

Kept dependency-free so both :mod:`kbforge.config` and
:mod:`kbforge.core.classify` can import it without a circular import.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# OKF default type set. ``post`` is the fallback for "no clear signal".
DEFAULT_TYPES = [
    "concept",
    "entity",
    "case",
    "pitfall",
    "scheme",
    "comparison",
    "post",
]

# Default lexicon: type -> list of cue phrases. User-overridable in config.
DEFAULT_LEXICON: dict[str, list[str]] = {
    "concept": ["概念", "定义", "是什么", "原理", "本质", "核心", "理解", "辨析", "区别", "基础"],
    "entity": ["工具", "框架", "平台", "产品", "模型", "公司", "项目", "库", "服务", "引擎", "系统"],
    "case": ["案例", "落地", "实践", "实战", "经验", "实施", "应用", "效果", "成效", "成果", "场景", "样例"],
    "pitfall": ["踩坑", "坑", "误区", "失败", "避坑", "风险", "教训", "反例", "注意", "血泪"],
    "scheme": ["方案", "架构", "设计", "规范", "标准", "最佳实践", "流程", "方法论", "策略", "指南", "建议"],
    "comparison": ["对比", "比较", "vs", "VS", "差异", "区别", "选型", "异同", "优缺点", "优劣"],
}

# Default structural rules: a heading containing any of these → that type.
DEFAULT_STRUCTURAL_RULES: dict[str, list[str]] = {
    "case": ["案例", "落地实践", "实战", "经验分享", "项目实践", "实践"],
    "pitfall": ["踩坑", "坑", "误区", "失败", "避坑", "风险", "教训"],
    "scheme": ["方案", "架构", "设计", "规范", "标准", "最佳实践", "流程", "方法论"],
    "comparison": ["对比", "比较", "vs", "差异", "区别", "选型"],
    "concept": ["概念", "定义", "原理", "本质", "是什么", "基础"],
}


@dataclass
class ClassifyConfig:
    """User-configurable classification settings (``classify:`` in config.yaml)."""

    types: list[str] = field(default_factory=lambda: list(DEFAULT_TYPES))
    strategy: str = "local"  # local (default, zero-dep) | llm (optional)
    lexicon: dict[str, list[str]] = field(default_factory=lambda: dict(DEFAULT_LEXICON))
    structural_rules: dict[str, list[str]] = field(
        default_factory=lambda: dict(DEFAULT_STRUCTURAL_RULES)
    )
    llm: dict[str, Any] = field(default_factory=dict)  # api_key, base_url, model

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClassifyConfig":
        data = data or {}
        types = data.get("types") or list(DEFAULT_TYPES)
        # Merge user lexicon over defaults (so users extend, not replace).
        lexicon = dict(DEFAULT_LEXICON)
        for k, v in (data.get("lexicon") or {}).items():
            lexicon[k] = list(v)
        rules = dict(DEFAULT_STRUCTURAL_RULES)
        for k, v in (data.get("structural_rules") or {}).items():
            rules[k] = list(v)
        return cls(
            types=list(types),
            strategy=data.get("strategy", "local"),
            lexicon=lexicon,
            structural_rules=rules,
            llm=data.get("llm") or {},
        )
