"""OmniRoute web plugin — registers the search/extract backend."""

from __future__ import annotations

from .provider import OmniRouteWebProvider


def register(ctx) -> None:
    ctx.register_web_search_provider(OmniRouteWebProvider())
