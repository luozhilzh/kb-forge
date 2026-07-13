"""kb-forge core: the single source of truth.

All real logic lives here. CLI (A), Skill (B), framework (C), and the expert
package are thin wrappers that call into this package.
"""

from .pipeline import run
from .site import build_site
from .diff import validate_wiki, diff_wiki, WikiSnapshot, DiffReport, Violation
from .enrich import (
    enrich_wiki,
    get_strategy,
    EnrichmentStrategy,
    NoOpStrategy,
    LocalClaimExtractor,
    Claim,
)

__all__ = [
    "run",
    "build_site",
    "validate_wiki",
    "diff_wiki",
    "WikiSnapshot",
    "DiffReport",
    "Violation",
    "enrich_wiki",
    "get_strategy",
    "EnrichmentStrategy",
    "NoOpStrategy",
    "LocalClaimExtractor",
    "Claim",
]
