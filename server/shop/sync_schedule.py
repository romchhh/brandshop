"""
Один розклад імпорту каталогу + стан останнього запуску.
Час «наступного» рахується з CATALOG_SYNC_CRON_HOURS, не з купи crontab-записів.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


def _tz():
    name = getattr(settings, "CELERY_TIMEZONE", "Europe/Kyiv") or "Europe/Kyiv"
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("Europe/Kyiv")


def cron_hours() -> tuple[int, ...]:
    hours = getattr(settings, "CATALOG_SYNC_CRON_HOURS", (10, 18))
    clean = tuple(int(h) for h in hours if 0 <= int(h) <= 23)
    return clean or (10, 18)


def next_sync_at(now: datetime | None = None) -> datetime:
    tz = _tz()
    current = now.astimezone(tz) if now else datetime.now(tz)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    candidates: list[datetime] = []
    for hour in cron_hours():
        slot = current.replace(hour=hour, minute=0, second=0, microsecond=0)
        if slot <= current:
            slot += timedelta(days=1)
        candidates.append(slot)
    return min(candidates)


def schedule_label() -> str:
    hours = ", ".join(f"{h:02d}:00" for h in cron_hours())
    return f"щодня о {hours} ({getattr(settings, 'CELERY_TIMEZONE', 'Europe/Kyiv')})"


def get_sync_state():
    from shop.models import CatalogSyncState

    obj, _ = CatalogSyncState.objects.get_or_create(pk=1)
    return obj


def mark_sync_started(trigger: str) -> bool:
    """False — уже виконується (і запуск не старший за 3 год)."""
    from django.db import transaction

    from shop.models import CatalogSyncState

    with transaction.atomic():
        obj, _ = CatalogSyncState.objects.select_for_update().get_or_create(pk=1)
        if obj.status == CatalogSyncState.STATUS_RUNNING and obj.started_at:
            age = timezone.now() - obj.started_at
            if age < timedelta(hours=3):
                return False
        obj.status = CatalogSyncState.STATUS_RUNNING
        obj.trigger = trigger
        obj.started_at = timezone.now()
        obj.finished_at = None
        obj.rows_ok = 0
        obj.message = "Виконується…"
        obj.save()
    return True


def mark_sync_finished(*, ok: bool, rows_ok: int, message: str) -> None:
    from shop.models import CatalogSyncState

    obj = get_sync_state()
    obj.status = CatalogSyncState.STATUS_OK if ok else CatalogSyncState.STATUS_ERROR
    obj.finished_at = timezone.now()
    obj.rows_ok = rows_ok
    obj.message = (message or "")[:4000]
    obj.save()
