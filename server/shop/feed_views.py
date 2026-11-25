from django.http import HttpResponse
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.utils.http import http_date
from rest_framework.views import APIView

from shop.feed_xml import build_shop_feed_xml


class ShopFeedXmlView(APIView):
    """Повний XML-фід категорій і товарів; дані з БД на кожному запиті."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        xml_bytes, last_modified = build_shop_feed_xml(request)
        response = HttpResponse(xml_bytes, content_type="application/xml; charset=utf-8")
        if last_modified:
            ts = last_modified
            if timezone.is_naive(ts):
                ts = timezone.make_aware(ts)
            response["Last-Modified"] = http_date(ts.timestamp())
        patch_cache_control(response, public=True, max_age=120, must_revalidate=True)
        return response