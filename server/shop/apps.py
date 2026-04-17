from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _shop_post_migrate(sender, app_config, **kwargs):
    if app_config.name != "shop":
        return
    from shop.beat_setup import ensure_catalog_sync_periodic_tasks

    ensure_catalog_sync_periodic_tasks()


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'
    verbose_name = 'Магазин'

    def ready(self) -> None:
        post_migrate.connect(
            _shop_post_migrate,
            dispatch_uid="shop_ensure_catalog_beat",
        )
