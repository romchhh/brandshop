"""
Cache-Control для GET /api/* — короткий браузерний кеш каталогів (без Redis).
"""
from __future__ import annotations

import re

_PRODUCT_DETAIL = re.compile(r"^/api/products/\d+/?$")


class ApiCacheHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method != "GET":
            return response
        path = request.path
        if path.startswith("/api/catalogs"):
            response["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
        elif path.startswith("/api/promotional-products"):
            response["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
        elif _PRODUCT_DETAIL.match(path):
            response["Cache-Control"] = "public, max-age=30, stale-while-revalidate=120"
        return response
