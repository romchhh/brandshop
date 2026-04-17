from django.core.management.base import BaseCommand

from shop.catalog_import import run_product_sync


class Command(BaseCommand):
    def handle(self, *args, **options):
        def log(msg):
            self.stdout.write(msg if msg.endswith("\n") else msg + "\n")

        run_product_sync(log=log)
