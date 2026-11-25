from django.apps import AppConfig
from django.contrib import admin
from django.db.models.signals import post_migrate


def _shop_post_migrate(sender, app_config, **kwargs):
    if app_config.name != "shop":
        return
    from shop.beat_setup import ensure_catalog_sync_periodic_tasks

    ensure_catalog_sync_periodic_tasks()


def _hide_noisy_admin():
    """Прибирає з адмінки зайві технічні моделі Celery (розклад лишається в БД)."""
    try:
        from django_celery_beat.models import (
            ClockedSchedule,
            CrontabSchedule,
            IntervalSchedule,
            PeriodicTask,
            SolarSchedule,
        )
    except ImportError:
        return
    for model in (
        PeriodicTask,
        IntervalSchedule,
        CrontabSchedule,
        SolarSchedule,
        ClockedSchedule,
    ):
        try:
            admin.site.unregister(model)
        except admin.sites.NotRegistered:
            pass


class ShopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shop"
    verbose_name = "Магазин"

    def ready(self) -> None:
        post_migrate.connect(
            _shop_post_migrate,
            dispatch_uid="shop_ensure_catalog_beat",
        )
        _hide_noisy_admin()
