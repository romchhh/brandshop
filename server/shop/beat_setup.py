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

# Не пропускати 'migrate' / 'shell': post_migrate викликається під час migrate (argv містить migrate),
# а docker-entrypoint викликає ensure через manage.py shell — інакше periodic task ніколи не з’являється в БД.
_SKIP_ARGV: FrozenSet[str] = frozenset(
    {
        'makemigrations',
        'test',
        'collectstatic',
        'flush',
    }
)


def ensure_catalog_sync_periodic_tasks() -> None:
    if _SKIP_ARGV.intersection(sys.argv):
        return
    try:
        from django_celery_beat.models import CrontabSchedule, PeriodicTask
    except ImportError:
        return

    hours = getattr(settings, 'CATALOG_SYNC_CRON_HOURS', (10, 18))
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
        logger.info(
            'django-celery-beat: periodic task %r -> %s (crontab hour=%s tz=%s)',
            PERIODIC_TASK_NAME,
            SYNC_TASK,
            hour_csv,
            tz,
        )
    except (ProgrammingError, OperationalError) as exc:
        logger.warning('beat_setup skipped (DB not ready): %s', exc)
