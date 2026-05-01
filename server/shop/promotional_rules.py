"""
Правила «акційної» ціни для розділу promotional-products.

Якщо в товару лишився лише один активний розмір/варіант (ProductProperty) —
ставимо promotional_price: −10% від ціни, далі округлення вниз до кратного 50 грн.
Якщо активних варіантів 0 або більше 1 — promotional_price скидається (акція лише для «останнього» розміру).

Автоакція не застосовується до аксесуарів (назви каталогів як у імпорті):
Ремені, Окуляри, Сумки, Гаманці — для них promotional_price завжди скидається.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_FLOOR

from django.db.models import Count, Q

from shop.models import Product

STEP = Decimal("50")
TEN_PCT = Decimal("0.9")

# Каталоги-аксесуари: знижка «останній розмір» не діє (одяг/взуття — як раніше).
_CATALOG_TITLES_NO_LAST_VARIANT_PROMO = frozenset(
    {
        "Ремені",
        "Окуляри",
        "Сумки",
        "Гаманці",
    }
)


def catalog_excluded_from_auto_promotional(catalog_title: str) -> bool:
    """True — не рахуємо promotional_price за правилом останнього розміру."""
    if not catalog_title:
        return False
    return catalog_title.strip() in _CATALOG_TITLES_NO_LAST_VARIANT_PROMO


def floor_money_to_step(amount: Decimal, step: Decimal = STEP) -> Decimal:
    """Округлення суми вниз до кратного step (грн)."""
    if amount <= 0:
        return Decimal("0")
    floored = (amount / step).to_integral_value(rounding=ROUND_FLOOR) * step
    if floored >= step:
        return floored.quantize(Decimal("0.01"))
    if amount >= step:
        return step
    return amount.quantize(Decimal("0.01"), rounding=ROUND_FLOOR)


def compute_auto_promotional_price(price: Decimal) -> Decimal | None:
    """10% знижка від ціни, потім округлення вниз до кратного 50 грн."""
    if price is None or price <= 0:
        return None
    discounted = (price * TEN_PCT).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    promo = floor_money_to_step(discounted)
    if promo <= 0:
        return None
    if promo >= price:
        below = price - STEP
        if below <= 0:
            return None
        promo = floor_money_to_step(below)
        if promo >= price or promo <= 0:
            return None
    return promo


def _promo_equal(a: Decimal | None, b: Decimal | None) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return a.quantize(Decimal("0.01")) == b.quantize(Decimal("0.01"))


def apply_last_active_variant_promotional_prices() -> int:
    """
    Оновлює Product.promotional_price за правилом «останній розмір».
    Повертає кількість записів, у яких поле змінилося.
    """
    changed = 0
    qs = (
        Product.objects.filter(active=True)
        .select_related("catalog")
        .annotate(
            _ac=Count("product_properties", filter=Q(product_properties__active=True))
        )
    )
    batch: list[Product] = []
    for p in qs.iterator(chunk_size=400):
        n = int(p._ac)
        title = getattr(p.catalog, "title", "") or ""
        if catalog_excluded_from_auto_promotional(title):
            new_promo = None
        elif n == 1:
            new_promo = compute_auto_promotional_price(p.price)
        else:
            new_promo = None
        if _promo_equal(p.promotional_price, new_promo):
            continue
        p.promotional_price = new_promo
        batch.append(p)
        if len(batch) >= 500:
            Product.objects.bulk_update(batch, ["promotional_price"])
            changed += len(batch)
            batch = []
    if batch:
        Product.objects.bulk_update(batch, ["promotional_price"])
        changed += len(batch)
    return changed
