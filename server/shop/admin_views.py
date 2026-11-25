import logging
import threading

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET, require_POST

from shop.catalog_import import run_product_sync
from shop.models import CatalogSyncState
from shop.sync_schedule import get_sync_state

logger = logging.getLogger(__name__)
_lock = threading.Lock()


def _can_sync_products(user):
    return user.is_active and user.is_staff and user.has_perm("shop.change_product")


def _run_in_background():
    try:
        run_product_sync(log=lambda m: logger.info(str(m).rstrip("\n")), trigger="manual")
    except Exception:
        logger.exception("manual catalog sync failed")
    finally:
        _lock.release()


@staff_member_required
@require_POST
def update_products_from_sheets(request):
    """
    POST: ставить імпорт у фоновий потік цього процесу.
    Не чекає закінчення (інакше gunicorn обриває довгий запит) і не залежить від Celery.
    """
    if not _can_sync_products(request.user):
        messages.error(request, "Немає права оновлювати товари.")
        return redirect("admin:shop_product_changelist")

    state = get_sync_state()
    if state.status == "running":
        messages.warning(request, "Оновлення вже виконується. Зачекайте й оновіть сторінку.")
        return redirect("admin:shop_product_changelist")

    if not _lock.acquire(blocking=False):
        messages.warning(request, "Оновлення вже запущене в цьому процесі.")
        return redirect("admin:shop_product_changelist")

    threading.Thread(target=_run_in_background, name="catalog-sync-manual", daemon=True).start()
    messages.success(
        request,
        "Оновлення запущено. Прогрес видно на цій сторінці.",
    )
    return redirect("admin:shop_product_changelist")


@staff_member_required
@require_GET
def catalog_sync_status(request):
    """JSON для смуги прогресу на списку товарів."""
    if not _can_sync_products(request.user):
        return JsonResponse({"detail": "forbidden"}, status=403)
    state = get_sync_state()
    total = state.progress_total or 1000
    done = state.progress_done or 0
    return JsonResponse(
        {
            "running": state.status == CatalogSyncState.STATUS_RUNNING,
            "status": state.status,
            "done": done,
            "total": total,
            "percent": int(done * 100 / total) if total else 0,
            "message": (state.message or "")[:240],
            "rows": state.rows_ok or 0,
        }
    )
