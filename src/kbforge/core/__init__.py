"""kb-forge core: the single source of truth.

All real logic lives here. CLI (A), Skill (B), framework (C), and the expert
package are thin wrappers that call into this package.
"""

from .pipeline import run
from .site import build_site

__all__ = ["run", "build_site"]
