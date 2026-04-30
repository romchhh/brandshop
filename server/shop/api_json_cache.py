"""TTL для серверного JSON-кешу списків каталогу / акцій (django.core.cache)."""
from __future__ import annotations

import os


def api_json_cache_ttl_seconds() -> int:
    raw = os.getenv("API_JSON_CACHE_TTL", "180").strip()
    try:
        return max(0, min(3600, int(raw)))
    except ValueError:
        return 180
