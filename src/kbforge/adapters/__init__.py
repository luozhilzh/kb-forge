"""Platform adapters. Import the one you need; add new ones as subclasses of base.PlatformAdapter."""

from .base import Attachment, FetchResult, PlatformAdapter, Topic
from .mock import MockAdapter
from .zsxq import ZsxqAdapter

__all__ = [
    "Attachment",
    "FetchResult",
    "PlatformAdapter",
    "Topic",
    "MockAdapter",
    "ZsxqAdapter",
]

# Registry used by config.platform -> adapter class.
ADAPTERS: dict[str, type[PlatformAdapter]] = {
    "zsxq": ZsxqAdapter,
    # "wechat": WechatAdapter,  # see example_wechat.py
}


def get_adapter(name: str, **kwargs: object) -> PlatformAdapter:
    if name not in ADAPTERS:
        raise KeyError(f"Unknown platform adapter '{name}'. Known: {sorted(ADAPTERS)}")
    return ADAPTERS[name](**kwargs)  # type: ignore[arg-type]
