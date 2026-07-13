"""Configuration contract for kb-forge.

Loads ``config.yaml`` (non-secret, committed as ``config.default.yaml`` /
``config.example.yaml``) merged with secrets from ``.env``. All real logic reads
a :class:`KbForgeConfig`; nothing hardcodes paths or group ids.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


# --------------------------------------------------------------------------- #
# Config dataclasses (the contract everything else depends on)
# --------------------------------------------------------------------------- #
@dataclass
class OutputConfig:
    enabled: bool = True
    formats: list[str] = field(default_factory=lambda: ["pptx", "md"])


@dataclass
class EnrichConfig:
    enabled: bool = False
    model: str = ""


@dataclass
class WikiConfig:
    schema_path: str = "SCHEMA.md"
    slug_style: str = "kebab"
    page_char_limit: int = 4000
    enrich: EnrichConfig = field(default_factory=EnrichConfig)


@dataclass
class FetchConfig:
    page_size: int = 50
    long_tail_guard: int = 5
    incremental: bool = False


@dataclass
class PathsConfig:
    raw: str = "raw"
    wiki: str = "wiki"
    archive: str = "archive"
    cases: str = "cases"
    attachments: str = "_attachments"


@dataclass
class QueryConfig:
    backend: str = "graph"  # graph (PPR, zero-dep) | embedding (optional, OFF)


@dataclass
class KbForgeConfig:
    # --- resolved at load time ---
    root: Path = field(default_factory=Path)  # absolute knowledge-base root
    # --- non-secret (from config.yaml) ---
    group_id: str = "planet_demo_001"
    platform: str = "zsxq"
    local_attach_dir: str = "_attachments_src"
    zsxq_cli_path: str = "zsxq-cli"
    output: OutputConfig = field(default_factory=OutputConfig)
    wiki: WikiConfig = field(default_factory=WikiConfig)
    fetch: FetchConfig = field(default_factory=FetchConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    query: QueryConfig = field(default_factory=QueryConfig)
    # --- secrets (from .env only, never serialized) ---
    llm_api_key: str = ""
    zsxq_token: str = ""

    # ------------------------------------------------------------------ #
    def resolve(self, relative: str) -> Path:
        """Join a configured relative path against the knowledge-base root."""
        return (self.root / relative).resolve()

    def path(self, key: str) -> Path:
        """Resolve one of the known ``paths.*`` keys against the root."""
        rel = getattr(self.paths, key)
        return self.resolve(rel)

    @classmethod
    def from_dict(cls, data: dict[str, Any], base_dir: Path) -> "KbForgeConfig":
        kb_root_raw = data.get("kb_root", ".")
        kb_root = (base_dir / kb_root_raw).resolve() if not Path(kb_root_raw).is_absolute() else Path(kb_root_raw).resolve()

        cfg = cls(
            root=kb_root,
            group_id=data.get("group_id", "planet_demo_001"),
            platform=data.get("platform", "zsxq"),
            local_attach_dir=data.get("local_attach_dir", "_attachments_src"),
            zsxq_cli_path=data.get("zsxq_cli_path", "zsxq-cli"),
            output=OutputConfig(**data.get("output", {})),
            wiki=WikiConfig(
                schema_path=data.get("wiki", {}).get("schema_path", "SCHEMA.md"),
                slug_style=data.get("wiki", {}).get("slug_style", "kebab"),
                page_char_limit=data.get("wiki", {}).get("page_char_limit", 4000),
                enrich=EnrichConfig(**data.get("wiki", {}).get("enrich", {})),
            ),
            fetch=FetchConfig(**data.get("fetch", {})),
            paths=PathsConfig(**data.get("paths", {})),
            query=QueryConfig(**data.get("query", {})),
        )
        return cfg


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #
def _find_config_file(explicit: Path | None, profile: str | None, start: Path) -> Path | None:
    if explicit is not None:
        return explicit
    if profile is not None:
        cand = start / f"config.{profile}.yaml"
        if cand.exists():
            return cand
    for name in ("config.yaml", "config.default.yaml"):
        cand = start / name
        if cand.exists():
            return cand
    return None


def load_config(
    config_path: Path | None = None,
    profile: str | None = None,
    env_path: Path | None = None,
    start_dir: Path | None = None,
) -> KbForgeConfig:
    """Load configuration from a YAML file + ``.env`` secrets.

    Resolution order: ``config_path`` > ``config.<profile>.yaml`` > ``config.yaml``
    > ``config.default.yaml`` (searched from ``start_dir``).
    """
    start_dir = start_dir or Path.cwd()
    cfg_file = _find_config_file(config_path, profile, start_dir)
    if cfg_file is None:
        raise FileNotFoundError(
            f"No kb-forge config found in {start_dir} (looked for config.yaml / "
            f"config.default.yaml / config.{profile}.yaml)"
        )
    with open(cfg_file, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    cfg = KbForgeConfig.from_dict(data, base_dir=cfg_file.parent)

    # Secrets from .env (never committed). .env lives next to config or at kb_root.
    for dotenv_cand in (env_path, cfg_file.parent / ".env", cfg.root / ".env"):
        if dotenv_cand and Path(dotenv_cand).exists():
            load_dotenv(dotenv_cand, override=False)
            break
    cfg.llm_api_key = os.getenv("LLM_API_KEY", "")
    cfg.zsxq_token = os.getenv("ZSXQ_TOKEN", "")
    return cfg
