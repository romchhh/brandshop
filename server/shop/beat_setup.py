"""
Створення записів django-celery-beat для імпорту каталогу за розкладом.

Celery beat запускається з DatabaseScheduler — без рядків у БД розклад порожній.
Виклик: після migrate (сигнал post_migrate у shop.apps) та з docker-entrypoint.sh.
"""
from __future__ import annotations

import logging
import sys
from typing import FrozenSet

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)

PERIODIC_TASK_NAME = 'catalog-sync-from-google-sheets'
SYNC_TASK = 'shop.tasks.sync_products_from_sheets'

_SKIP_ARGV: FrozenSet[str] = frozenset(
    {
        'migrate',
        'makemigrations',
        'test',
        'collectstatic',
        'flush',
        'shell',
    }
)


def ensure_catalog_sync_periodic_tasks() -> None:
    if _SKIP_ARGV.intersection(sys.argv):
        return
    try:
        from django_celery_beat.models import CrontabSchedule, PeriodicTask
    except ImportError:
        return

    hours = getattr(settings, 'CATALOG_SYNC_CRON_HOURS', (10, 14, 18, 20))
    hour_csv = ','.join(str(h) for h in hours)
    tz = getattr(settings, 'CELERY_TIMEZONE', 'Europe/Kyiv')

    try:
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour=hour_csv,
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone=tz,
        )
        PeriodicTask.objects.update_or_create(
            name=PERIODIC_TASK_NAME,
            defaults={
                'task': SYNC_TASK,
                'crontab': schedule,
                'interval': None,
                'solar': None,
                'clocked': None,
                'enabled': True,
                'queue': 'default',
            },
        )
    except (ProgrammingError, OperationalError) as exc:
        logger.debug('beat_setup skipped (DB not ready): %s', exc)
