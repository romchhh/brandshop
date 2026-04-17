from datetime import datetime
from typing import Any, Dict, Optional


def format_statistics_message(bot_counts: dict, shop: Optional[Dict[str, Any]]) -> str:
    b = bot_counts
    shop = shop or {}

    shop_ok = bool(shop.get("ok"))

    if shop_ok:
        unique = shop.get("unique_shop_users", 0)
        ordered = shop.get("users_with_orders", 0)
        only_activity = shop.get("users_only_browsing", 0)
        orders_total = shop.get("orders_total", 0)
        orders_today = shop.get("orders_today", 0)
        orders_week = shop.get("orders_week", 0)
        orders_month = shop.get("orders_month", 0)
        active_shop_today = shop.get("active_shop_users_today", 0)
        active_shop_week = shop.get("active_shop_users_week", 0)

        shop_block = (
            f"<b>◼ МАГАЗИН (WEB APP)</b>\n"
            f"• Унікальних користувачів: <b>{unique}</b>\n"
            f"• Робили замовлення: <b>{ordered}</b>\n"
            f"• Лише переглядали (без замовлень): <b>{only_activity}</b>\n"
            f"• Активних сьогодні (перегляд/замовлення): <b>{active_shop_today}</b>\n"
            f"• Активних за 7 днів: <b>{active_shop_week}</b>\n\n"
            f"<b>◼ ЗАМОВЛЕННЯ</b>\n"
            f"• Всього: <b>{orders_total}</b>\n"
            f"• Сьогодні: <b>{orders_today}</b>\n"
            f"• За тиждень: <b>{orders_week}</b>\n"
            f"• За місяць: <b>{orders_month}</b>\n\n"
        )
    else:
        shop_block = (
            "<b>◼ МАГАЗИН (WEB APP)</b>\n"
            "<i>Немає зв’язку з API (перевірте SERVER_URL у боті).</i>\n\n"
        )

    sub_pct = (b["active"] / b["total"] * 100) if b["total"] > 0 else 0
    unsub_pct = (b["blocked"] / b["total"] * 100) if b["total"] > 0 else 0

    return (
        f"<b>📊 СТАТИСТИКА</b>\n\n"
        f"<b>◼ TELEGRAM-БОТ</b>\n"
        f"• Натиснули /start (база бота): <b>{b['total']}</b>\n"
        f"• Можна розіслати зараз: <b>{b['active']}</b> ({sub_pct:.1f}%)\n"
        f"• Заблокували бота / недоступні: <b>{b['blocked']}</b> ({unsub_pct:.1f}%)\n"
        f"  <i>(оцінка «відписки» від повідомлень бота)</i>\n\n"
        f"<b>◼ НОВІ В БОТІ (перший /start)</b>\n"
        f"• Сьогодні: <b>{b['new_today']}</b>\n"
        f"• За тиждень: <b>{b['new_week']}</b>\n"
        f"• За місяць: <b>{b['new_month']}</b>\n\n"
        f"<b>◼ АКТИВНІСТЬ У БОТІ (повторний /start)</b>\n"
        f"• Сьогодні: <b>{b['active_today']}</b>\n"
        f"• За тиждень: <b>{b['active_week']}</b>\n"
        f"• За місяць: <b>{b['active_month']}</b>\n\n"
        f"{shop_block}"
        f"<i>Оновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"
    )
