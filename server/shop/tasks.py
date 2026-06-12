import logging

from celery import shared_task

from shop.catalog_import import (
    create_product,
    get_catalog_data,
    run_product_sync,
    update_product,
)
from shop.catalog_sheet_sources import iter_catalog_import_jobs
from shop.models import Product


@shared_task(
    queue="default",
    time_limit=7200,
    soft_time_limit=7000,
    ignore_result=True,
)
def sync_products_from_sheets():
    """Повний імпорт/оновлення товарів з Google Таблиць (як manage.py update_products)."""
    _runlog = logging.getLogger(__name__)
    _runlog.info("Celery: sync_products_from_sheets started")
    try:
        run_product_sync(log=lambda m: _runlog.info(m.rstrip("\n")))
    except Exception:
        _runlog.exception("Celery: sync_products_from_sheets failed")
        raise
    _runlog.info("Celery: sync_products_from_sheets finished OK")


@shared_task(queue="default")
def process_catalog_data():
    for catalog_title, spreadsheet_id, fields in iter_catalog_import_jobs():
        range_name = fields["sheet"]
        if not isinstance(range_name, list):
            range_name = [range_name]

        rows = get_catalog_data(spreadsheet_id, range_name)
        if len(rows) == 0:
            print("Таблиця порожня або діапазон не знайдено.")
        else:
            ind = 1
            for row in rows:
                print(f"{ind} / {len(rows)}")
                ind += 1
                if fields["article"] >= len(row) or row[fields["article"]] == "":
                    continue

                if not Product.objects.filter(article=row[fields["article"]]).exists():
                    create_product(row, fields, catalog_title)
                else:
                    update_product(row, fields)
