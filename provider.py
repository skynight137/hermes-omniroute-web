"""OmniRoute web search + extract backend for Hermes.

``web_search``  -> OmniRoute ``POST /api/v1/search``  (results[]: title/url/snippet)
``web_extract`` -> OmniRoute ``POST /api/v1/web/fetch`` (content, metadata)

OmniRoute owns the upstream credentials and provider rotation; this plugin
only needs the gateway URL and key. Env: ``OMNIROUTE_API_URL`` (base incl.
``/v1``), ``OMNIROUTE_API_KEY``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from plugins.web._common import (
    BaseWebSearchProvider,
    document,
    page_error,
    provider_env,
    search_fail,
    search_ok,
    setup_schema,
    titled_rows,
)

logger = logging.getLogger(__name__)

_SEARCH_CAP = 20  # OmniRoute search accepts up to 20 results per request (matches vendor cap)
# Upstream pins, selected by env so you can switch without a code change. Values are OmniRoute provider ids.
_SEARCH_PROVIDER = os.environ.get("OMNIROUTE_SEARCH_PROVIDER", "serper-search")
_FETCH_PROVIDER = os.environ.get("OMNIROUTE_FETCH_PROVIDER", "firecrawl")


def _gateway_root() -> str:
    """OmniRoute root without the trailing ``/v1``; the search/fetch routes live under ``/api/v1``."""
    url = provider_env("OMNIROUTE_API_URL").rstrip("/")
    return url[: -len("/v1")] if url.endswith("/v1") else url


def _post(path: str, body: Dict[str, Any], timeout: float = 20.0) -> Dict[str, Any]:
    """POST JSON to OmniRoute. Returns the parsed body, or raises ``RuntimeError`` with a readable message."""
    import httpx

    try:
        resp = httpx.post(
            f"{_gateway_root()}{path}",
            json=body,
            headers={
                "Authorization": f"Bearer {provider_env('OMNIROUTE_API_KEY')}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"OmniRoute {path} HTTP {exc.response.status_code}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"OmniRoute {path} failed: {exc}") from exc


class OmniRouteWebProvider(BaseWebSearchProvider):
    """Search and extract routed through an OmniRoute gateway."""

    NAME = "omniroute"
    DISPLAY_NAME = "OmniRoute"
    KEY_ENV = "OMNIROUTE_API_KEY"
    EXTRACT = True

    def is_available(self) -> bool:
        # Cheap and offline: both settings present. Never a network call (runs on every `hermes tools` paint).
        return bool(provider_env("OMNIROUTE_API_URL") and provider_env("OMNIROUTE_API_KEY"))

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        if not self.is_available():
            return search_fail("OMNIROUTE_API_URL and OMNIROUTE_API_KEY must be set")
        try:
            data = _post("/api/v1/search", {
                "query": query,
                "count": max(1, min(int(limit), _SEARCH_CAP)),
                "provider": _SEARCH_PROVIDER,
            })
        except RuntimeError as exc:
            return search_fail(str(exc))
        raw = data.get("results") or []
        web = titled_rows(raw[:limit], "snippet")
        logger.info("OmniRoute search %r via %s: %d results", query, data.get("provider"), len(web))
        return search_ok(web)

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for url in urls:
            try:
                data = _post("/api/v1/web/fetch", {"url": url, "provider": _FETCH_PROVIDER})
            except RuntimeError as exc:
                out.append(page_error(url, str(exc)))
                continue
            meta = data.get("metadata")
            title = str(meta.get("title", "") or "") if isinstance(meta, dict) else ""
            content = str(data.get("content", "") or "")
            if not content.strip():
                out.append(page_error(url, "OmniRoute returned no content for this URL"))
                continue
            out.append(document(url, title, content))
        return out

    def get_setup_schema(self) -> Dict[str, Any]:
        return setup_schema(
            "OmniRoute", "gateway",
            "Search and fetch through your OmniRoute gateway (provider keys live in OmniRoute).",
            "OMNIROUTE_API_KEY", "OmniRoute API key", "",
        )
