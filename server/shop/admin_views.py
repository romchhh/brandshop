import traceback

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect

from shop.catalog_import import run_product_sync


def _can_sync_products(user):
    return (
        user.is_active
        and user.is_staff
        and user.has_perm("shop.change_product")
    )


@user_passes_test(_can_sync_products)
def update_products_from_sheets(request):
    """
    POST: імпорт/оновлення товарів з Google Таблиць (логіка update_products).
    """
    if request.method != "POST":
        messages.error(request, "Використовуйте кнопку «Оновити з Google Таблиць» у списку товарів.")
        return redirect("admin:shop_product_changelist")

    try:
        run_product_sync(log=lambda msg: None)
        messages.success(
            request,
            "Оновлення всіх товарів з Google Таблиць успішно завершено.",
        )
    except Exception as e:
        messages.error(
            request,
            f"Помилка синхронізації: {e}\n{traceback.format_exc()[:2000]}",
        )
    return redirect("admin:shop_product_changelist")
