"""XML-фід каталогів і товарів (генерується з БД при кожному запиті)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from xml.dom import minidom

from django.conf import settings
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from django.utils.dateformat import format as django_format

from shop.models import Catalog, Product, ProductProperty


def _shop_site_url() -> str:
    return (getattr(settings, "SHOP_SITE_URL", "") or getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")


def _media_public_url(file_field, request) -> str:
    if not file_field:
        return ""
    path = (getattr(file_field, "url", None) or "").strip()
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = _shop_site_url()
    if not base and request is not None:
        return request.build_absolute_uri(path)
    if not base:
        return path
    return f"{base}{path}" if path.startswith("/") else f"{base}/{path}"


def _shop_page_url(path: str) -> str:
    base = _shop_site_url()
    if not base:
        return path
    return f"{base}{path}" if path.startswith("/") else f"{base}/{path}"


def _fmt_dt(value) -> str:
    if not value:
        return ""
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return django_format(value, "c")


def _fmt_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def _sub(parent: ET.Element, tag: str, text: str | None = None, **attrib) -> ET.Element:
    el = ET.SubElement(parent, tag, {k: str(v) for k, v in attrib.items() if v is not None and v != ""})
    if text is not None and text != "":
        el.text = text
    return el


def _cdata_sub(parent: ET.Element, tag: str, text: str) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = text or ""
    return el


def build_shop_feed_xml(request) -> tuple[bytes, datetime | None]:
    catalogs = list(
        Catalog.objects.filter(active=True)
        .annotate(products_count=Count("products", filter=Q(products__active=True)))
        .order_by("priority", "id")
    )
    products = list(
        Product.objects.filter(active=True, catalog__active=True)
        .select_related("catalog")
        .prefetch_related(
            Prefetch(
                "product_properties",
                queryset=ProductProperty.objects.filter(active=True).order_by("id"),
            )
        )
        .order_by("catalog__priority", "catalog_id", "-priority", "-updated_at", "-id")
    )

    last_modified: datetime | None = None
    for obj in catalogs + products:
        ts = getattr(obj, "updated_at", None)
        if ts and (last_modified is None or ts > last_modified):
            last_modified = ts

    root = ET.Element(
        "catalog",
        {
            "version": "1.0",
            "generated": _fmt_dt(timezone.now()),
            "shop-url": _shop_site_url(),
        },
    )

    shop = _sub(root, "shop")
    _sub(shop, "name", getattr(settings, "SHOP_FEED_NAME", "BrandShop"))
    _sub(shop, "url", _shop_site_url() or "/")
    _sub(shop, "currency", "UAH")

    cats_el = _sub(root, "categories")
    for cat in catalogs:
        cat_el = _sub(
            cats_el,
            "category",
            id=str(cat.id),
            active="true" if cat.active else "false",
            priority=str(cat.priority),
            url=_shop_page_url(f"/catalog/{cat.id}"),
        )
        _sub(cat_el, "title", cat.title)
        _sub(cat_el, "photo", _media_public_url(cat.photo, request))
        _sub(cat_el, "photo_banner", _media_public_url(cat.photo_banner, request))
        _sub(cat_el, "created_at", _fmt_dt(cat.created_at))
        _sub(cat_el, "updated_at", _fmt_dt(cat.updated_at))
        _sub(cat_el, "products_count", str(cat.products_count))

    prods_el = _sub(root, "products", count=str(len(products)))
    for product in products:
        catalog = product.catalog
        sale_price = product.promotional_price
        has_sale = sale_price is not None and sale_price > 0

        prod_el = _sub(
            prods_el,
            "product",
            id=str(product.id),
            catalog_id=str(catalog.id),
            active="true",
            available="true",
            url=_shop_page_url(f"/products/{product.id}"),
        )
        _sub(prod_el, "title", product.title)
        _sub(prod_el, "article", product.article or "")
        _sub(prod_el, "catalog_title", catalog.title if catalog else "")
        _cdata_sub(prod_el, "description", product.description or "")
        _sub(prod_el, "photo", _media_public_url(product.photo, request))
        _sub(prod_el, "price", _fmt_decimal(product.price))
        _sub(prod_el, "currency", "UAH")
        if has_sale:
            _sub(prod_el, "promotional_price", _fmt_decimal(sale_price))
            _sub(prod_el, "oldprice", _fmt_decimal(product.price))
        _sub(prod_el, "property_title", product.property_title or "")
        _sub(prod_el, "priority", str(product.priority))
        _sub(prod_el, "created_at", _fmt_dt(product.created_at))
        _sub(prod_el, "updated_at", _fmt_dt(product.updated_at))
        if product.photo_import_source:
            _sub(prod_el, "photo_import_source", product.photo_import_source)

        props_el = _sub(prod_el, "properties")
        for prop in product.product_properties.all():
            prop_el = _sub(
                props_el,
                "property",
                id=str(prop.id),
                active="true" if prop.active else "false",
            )
            _sub(prop_el, "title", prop.title)
            _sub(prop_el, "photo", _media_public_url(prop.photo, request))
            _sub(prop_el, "created_at", _fmt_dt(prop.created_at))
            _sub(prop_el, "updated_at", _fmt_dt(prop.updated_at))

    rough = ET.tostring(root, encoding="unicode")
    parsed = minidom.parseString(f'<?xml version="1.0" encoding="UTF-8"?>{rough}')
    xml_bytes = parsed.toprettyxml(indent="  ", encoding="UTF-8")
    return xml_bytes, last_modified