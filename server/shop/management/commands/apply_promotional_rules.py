from django.core.management.base import BaseCommand

from shop.promotional_rules import apply_last_active_variant_promotional_prices


class Command(BaseCommand):
    help = (
        "Застосувати акційні ціни для товарів з одним активним розміром (−10%, округлення вниз до 50 грн); "
        "скинути promotional_price, якщо розмірів більше одного."
    )

    def handle(self, *args, **options):
        n = apply_last_active_variant_promotional_prices()
        self.stdout.write(self.style.SUCCESS(f"Оновлено записів Product: {n}"))
