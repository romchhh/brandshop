"""
HTTP-кеш для публічних GET API (каталоги, акції). Не чіпає /api/products/ — там userId і лічильник переглядів.
"""
import os

from django.utils.cache import patch_cache_control


def _max_age() -> int:
    raw = os.getenv("API_PUBLIC_CACHE_MAX_AGE", "300").strip()
    try:
        return max(0, min(86400, int(raw)))
    except ValueError:
        return 300


def _stale_while_revalidate() -> int:
    raw = os.getenv("API_PUBLIC_CACHE_STALE_WHILE_REVALIDATE", "600").strip()
    try:
        return max(0, min(86400, int(raw)))
    except ValueError:
        return 600


class ApiCacheControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method != "GET" or response.status_code != 200:
            return response
        path = request.path
        if path.startswith("/api/products/"):
            return response
        if path.startswith("/api/user/"):
            return response
        if path.startswith("/api/catalogs") or path.startswith("/api/promotional-products"):
            patch_cache_control(
                response,
                public=True,
                max_age=_max_age(),
                stale_while_revalidate=_stale_while_revalidate(),
            )
        return response
