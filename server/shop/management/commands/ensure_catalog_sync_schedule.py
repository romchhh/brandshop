from django.core.management.base import BaseCommand

from shop.beat_setup import ensure_catalog_sync_periodic_tasks


class Command(BaseCommand):
    help = (
        "Створює/оновлює django-celery-beat PeriodicTask для імпорту каталогу "
        "(shop.tasks.sync_products_from_sheets). Запустіть один раз на сервері після деплою, "
        "якщо в адмінці немає задачі catalog-sync-from-google-sheets."
    )

    def handle(self, *args, **options):
        ensure_catalog_sync_periodic_tasks()
        self.stdout.write(self.style.SUCCESS("Розклад каталогу в django-celery-beat оновлено."))
