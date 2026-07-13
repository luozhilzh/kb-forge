"""kb-forge core: the single source of truth.

All real logic lives here. CLI (A), Skill (B), framework (C), and the expert
package are thin wrappers that call into this package.
"""

from .pipeline import run

__all__ = ["run"]
