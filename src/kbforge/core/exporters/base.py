"""Exporter base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseExporter(ABC):
    name: str = "base"
    suffix: str = ".out"

    @abstractmethod
    def export(self, pages: list, out_path: Path) -> Path:
        """Render ``pages`` to ``out_path``; return the written path."""
        raise NotImplementedError
