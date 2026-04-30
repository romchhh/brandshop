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


def get_admin_notify_chat_ids() -> list[int]:
    """Унікальні Telegram chat_id для сповіщень адмінам: ADMIN_ID + ADMIN_IDS (через кому)."""
    return _admin_chat_ids()


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
    total_photo_fail: int = 0,
    total_photo_unrecognized: int = 0,
) -> str:
    lines: list[str] = [
        "📦 Імпорт каталогу (Google Таблиці) завершено",
        f"⏱ Тривалість: {duration_sec:.1f} с",
        f"📂 Блоків каталогу пройдено: {catalogs_completed}",
        f"📄 Рядків успішно створено/оновлено: {total_rows_iterated}",
    ]
    photo_critical = total_photo_fail > 0 or total_photo_unrecognized > 0
    if photo_critical:
        lines.append("")
        lines.append(
            "🔴 КРИТИЧНО — фото товарів:\n"
            f"— фото не завантажено (посилання було, файл не отримано): {total_photo_fail}\n"
            f"— комірка фото не схожа на URL / не розпізнано: {total_photo_unrecognized}\n"
            "Перевір доступ service account до файлів у Google Drive і формат посилань у таблиці."
        )
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
    if not sheet_errors and not row_errors and not photo_critical:
        lines.append("")
        lines.append("✅ Критичних проблем (рядки / таблиці / фото) не зафіксовано.")
    elif not sheet_errors and not row_errors and photo_critical:
        lines.append("")
        lines.append("⚠️ Рядки/таблиці без збоїв, але є критичні проблеми з фото (див. вище).")
    return "\n".join(lines)[:TELEGRAM_MAX_MESSAGE]


def format_sync_telegram_finish_notice(
    *,
    row_errors: list[str],
    sheet_errors: list[str],
    total_photo_fail: int = 0,
    total_photo_unrecognized: int = 0,
) -> str:
    """
    Одне коротке повідомлення адміну в Telegram після імпорту (замість довгого format_sync_summary).
    """
    photo_bad = (total_photo_fail or 0) > 0 or (total_photo_unrecognized or 0) > 0
    if not sheet_errors and not row_errors and not photo_bad:
        return "✅ Товари були успішно оновлені."
    bits: list[str] = []
    if sheet_errors:
        bits.append(f"помилки таблиць: {len(sheet_errors)}")
    if row_errors:
        bits.append(f"помилки рядків: {len(row_errors)}")
    if photo_bad:
        bits.append(
            f"фото (не завантажено / не URL): {int(total_photo_fail)} / {int(total_photo_unrecognized)}"
        )
    return "⚠️ Оновлення завершено з проблемами: " + ", ".join(bits) + ". Деталі — у логах сервера."


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
    photo_cell_unrecognized: int = 0,
    photo_fail_samples: list[str] | None = None,
    photo_unrecognized_samples: list[str] | None = None,
) -> str:
    photo_critical = photo_fail > 0 or photo_cell_unrecognized > 0
    lines = []
    if photo_critical:
        lines.append(
            "🔴 КРИТИЧНО — фото: не всі товари отримали зображення з таблиці. "
            f"Збій завантаження: {photo_fail}; комірка не URL: {photo_cell_unrecognized}."
        )
    lines.extend(
        [
            (
                f"⚠️ Блок «{catalog_title}» завершено"
                if photo_critical
                else f"✅ Блок «{catalog_title}» завершено"
            ),
            f"Spreadsheet: {spreadsheet_id}",
            f"— товарів успішно записано в БД (рядок без винятку): {rows_ok}",
            f"— помилок по рядках: {rows_err}",
            f"— фото не завантажено (посилання було, файл не отримано): {photo_fail}",
            f"— у колонці фото є текст, але не URL / не розпізнано: {photo_cell_unrecognized}",
        ]
    )
    if err_samples:
        lines.append("")
        lines.append("Приклади помилок рядків:")
        for s in err_samples[:5]:
            lines.append(f" • {s[:350]}")
    if photo_fail_samples:
        lines.append("")
        lines.append("Приклади (що було в таблиці → чому не вдалось завантажити файл):")
        for s in photo_fail_samples[:5]:
            lines.append(f" • {s[:380]}")
    if photo_unrecognized_samples:
        lines.append("")
        lines.append("Приклади (що прийшло з комірки фото — не схоже на посилання):")
        for s in photo_unrecognized_samples[:5]:
            lines.append(f" • {s[:380]}")
    return "\n".join(lines)[:TELEGRAM_MAX_MESSAGE]

