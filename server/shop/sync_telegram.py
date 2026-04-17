"""
Сповіщення адміну в Telegram про імпорт каталогу з Google Таблиць.
Потрібні BOT_TOKEN (або TELEGRAM_TOKEN) та ADMIN_ID / ADMIN_IDS у змінних оточення.
"""
from __future__ import annotations

import logging
import os
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_MAX_MESSAGE = 4000


def _admin_chat_ids() -> list[int]:
    ids: list[int] = []
    raw_main = getattr(settings, "ADMIN_ID", None) or os.getenv("ADMIN_ID")
    if raw_main is not None and str(raw_main).strip():
        try:
            ids.append(int(str(raw_main).strip()))
        except ValueError:
            pass
    for part in (os.getenv("ADMIN_IDS") or "").split(","):
        p = part.strip()
        if not p:
            continue
        try:
            n = int(p)
            if n not in ids:
                ids.append(n)
        except ValueError:
            continue
    return ids


def _bot_token() -> str | None:
    return (
        (getattr(settings, "BOT_TOKEN", None) or "").strip()
        or (os.getenv("BOT_TOKEN") or "").strip()
        or (os.getenv("TELEGRAM_TOKEN") or "").strip()
        or None
    )


def send_catalog_sync_message(text: str) -> None:
    """Надсилає текст усім адмінам. Безпечно ігнорує помилки мережі, щоб не ламати імпорт."""
    token = _bot_token()
    if not token:
        logger.debug("sync_telegram: немає BOT_TOKEN/TELEGRAM_TOKEN — пропускаємо TG")
        return
    chat_ids = _admin_chat_ids()
    if not chat_ids:
        logger.debug("sync_telegram: немає ADMIN_ID/ADMIN_IDS — пропускаємо TG")
        return
    chunk = text[:TELEGRAM_MAX_MESSAGE]
    for chat_id in chat_ids:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": chunk},
                timeout=25,
            )
            if r.status_code != 200:
                logger.warning(
                    "sync_telegram: Telegram HTTP %s для chat_id=%s: %s",
                    r.status_code,
                    chat_id,
                    r.text[:300],
                )
        except Exception as exc:
            logger.warning("sync_telegram: не вдалося надіслати в TG chat_id=%s: %s", chat_id, exc)


def format_sync_summary(
    *,
    duration_sec: float,
    catalogs_completed: int,
    total_rows_iterated: int,
    row_errors: list[str],
    sheet_errors: list[str],
) -> str:
    lines: list[str] = [
        "📦 Імпорт каталогу (Google Таблиці) завершено",
        f"⏱ Тривалість: {duration_sec:.1f} с",
        f"📂 Блоків каталогу пройдено: {catalogs_completed}",
        f"📄 Рядків успішно створено/оновлено: {total_rows_iterated}",
    ]
    if sheet_errors:
        lines.append("")
        lines.append(f"❌ Помилки читання таблиць ({len(sheet_errors)}):")
        for s in sheet_errors[:8]:
            lines.append(f" • {s[:500]}")
        if len(sheet_errors) > 8:
            lines.append(f" … ще {len(sheet_errors) - 8}")
    if row_errors:
        lines.append("")
        lines.append(f"⚠️ Помилки рядків ({len(row_errors)}):")
        for s in row_errors[:12]:
            lines.append(f" • {s[:400]}")
        if len(row_errors) > 12:
            lines.append(f" … ще {len(row_errors) - 12}")
    if not sheet_errors and not row_errors:
        lines.append("")
        lines.append("✅ Критичних помилок по рядках/таблицях не зафіксовано.")
    return "\n".join(lines)[:TELEGRAM_MAX_MESSAGE]


def notify_sheet_error(catalog_title: str, spreadsheet_id: str, exc: BaseException) -> None:
    msg = (
        "❌ Імпорт: не вдалося прочитати Google Таблицю\n"
        f"Каталог: {catalog_title}\n"
        f"Spreadsheet: {spreadsheet_id}\n"
        f"Помилка: {exc!s}"[:TELEGRAM_MAX_MESSAGE]
    )
    send_catalog_sync_message(msg)


def format_block_start(
    catalog_title: str,
    spreadsheet_id: str,
    sheet_indexes,
    rows_count: int,
) -> str:
    return (
        "📂 Почав обробку блоку каталогу\n"
        f"«{catalog_title}»\n"
        f"Spreadsheet: {spreadsheet_id}\n"
        f"Індекси аркушів: {sheet_indexes}\n"
        f"Рядків у таблиці (сирі): {rows_count}"
    )[:TELEGRAM_MAX_MESSAGE]


def format_block_empty(catalog_title: str, spreadsheet_id: str) -> str:
    return (
        "⚠️ Таблиця порожня або діапазон без даних\n"
        f"«{catalog_title}» · {spreadsheet_id}"
    )[:TELEGRAM_MAX_MESSAGE]


def format_block_done(
    catalog_title: str,
    spreadsheet_id: str,
    rows_ok: int,
    rows_err: int,
    photo_fail: int,
    err_samples: list[str],
) -> str:
    lines = [
        f"✅ Блок «{catalog_title}» завершено",
        f"Spreadsheet: {spreadsheet_id}",
        f"— товарів успішно записано в БД (рядок без винятку): {rows_ok}",
        f"— помилок по рядках: {rows_err}",
        f"— фото не завантажено (посилання було, файл не отримано): {photo_fail}",
    ]
    if err_samples:
        lines.append("")
        lines.append("Приклади помилок рядків:")
        for s in err_samples[:5]:
            lines.append(f" • {s[:350]}")
    return "\n".join(lines)[:TELEGRAM_MAX_MESSAGE]

