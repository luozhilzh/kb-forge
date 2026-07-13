"""kb-forge: forge community posts into an OKF-compatible knowledge base.

One core (the single source of truth) wrapped by thin shells:
  * A - CLI (``kbforge ...``)
  * B - WorkBuddy Skill (``B-workbuddy-skill/``)
  * C - importable package + ``adapters/`` for cross-platform
  * Expert - WorkBuddy expert package reusing core's orchestrator
"""

__version__ = "0.1.0"
