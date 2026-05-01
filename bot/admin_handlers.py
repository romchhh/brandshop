import html
import json
import logging
import threading
import time
from datetime import datetime

import telebot
from telebot import types

import config
from admin_stats import format_statistics_message
from api import Api
from bot_storage import (
    add_broadcast_delivery,
    count_broadcasts,
    create_broadcast,
    delete_broadcast_record,
    finalize_broadcast_stats,
    get_bot_user_counts,
    get_broadcast,
    get_broadcast_deliveries,
    get_broadcast_recipient_ids,
    list_broadcasts_page,
    mark_bot_user_blocked,
)
from states import States, get_user_state, reset_user_state, set_user_state

logger = logging.getLogger(__name__)

BROADCAST_PENDING_KEY = "broadcast_pending"

ADMIN_PANEL_TITLE = "🛠 <b>Адмін-панель</b>"
ADMIN_PANEL_SUBTITLE = "Оберіть дію нижче — кожна кнопка в окремому рядку, зручніше натискати з телефону."


def _is_admin(user_id: int) -> bool:
    return user_id in getattr(config, "ADMIN_IDS", [])


def _admin_menu_keyboard() -> types.InlineKeyboardMarkup:
    """Окремий ряд на кнопку — краща ціль для торкання в Telegram."""
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton(
            "📊 Статистика бота та магазину",
            callback_data="adm_stats",
        )
    )
    kb.row(
        types.InlineKeyboardButton(
            "📣 Розсилка підписникам",
            callback_data="adm_mail",
        )
    )
    kb.row(
        types.InlineKeyboardButton(
            "📂 Архів розсилок",
            callback_data="adm_arc_0",
        )
    )
    kb.row(
        types.InlineKeyboardButton(
            "🔄 Оновити каталог з Google Таблиць",
            callback_data="adm_sync_products",
        )
    )
    return kb


def _admin_panel_message() -> str:
    return f"{ADMIN_PANEL_TITLE}\n\n{ADMIN_PANEL_SUBTITLE}"


def _back_to_menu_keyboard(callback_data: str = "adm_menu") -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton(
            "🏠 Назад до меню",
            callback_data=callback_data,
        )
    )
    return kb


def _clear_broadcast_pending(admin_id: int) -> None:
    from states import redis_client

    redis_client.delete(f"{BROADCAST_PENDING_KEY}:{admin_id}")


def _set_broadcast_pending(admin_id: int, from_chat_id: int, message_id: int) -> None:
    from states import redis_client

    redis_client.set(
        f"{BROADCAST_PENDING_KEY}:{admin_id}",
        json.dumps({"from_chat_id": from_chat_id, "message_id": message_id}),
        ex=3600,
    )


def _get_broadcast_pending(admin_id: int) -> dict | None:
    from states import redis_client

    raw = redis_client.get(f"{BROADCAST_PENDING_KEY}:{admin_id}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _extract_copied_message_id(sent) -> int | None:
    """
    copyMessage у Bot API повертає лише message_id (у pyTelegramBotAPI — types.MessageID).
    Не покладаємось на один формат: інколи в середовищі може бути dict або повний Message.
    """
    if sent is None:
        return None
    if isinstance(sent, bool):
        return None
    if isinstance(sent, int):
        return sent

    mid = getattr(sent, "message_id", None)
    if mid is not None:
        try:
            return int(mid)
        except (TypeError, ValueError):
            pass

    if isinstance(sent, dict):
        v = sent.get("message_id")
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
        inner = sent.get("result")
        if isinstance(inner, dict):
            v = inner.get("message_id")
            if v is not None:
                try:
                    return int(v)
                except (TypeError, ValueError):
                    pass
    return None


BROADCAST_ARCHIVE_PAGE_SIZE = 7


def _format_broadcast_row_short(row) -> str:
    try:
        dt = datetime.fromisoformat(row["created_at"])
        dstr = dt.strftime("%d.%m %H:%M")
    except (TypeError, ValueError):
        dstr = str(row["created_at"])[:16]
    return (
        f"№{row['id']} · {dstr} · ✓{row['delivered_count']} ✗{row['failed_count']}"
    )


def _archive_keyboard(page: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    total = count_broadcasts()
    max_page = max(0, (total - 1) // BROADCAST_ARCHIVE_PAGE_SIZE) if total else 0
    page = min(max(0, page), max_page)
    offset = page * BROADCAST_ARCHIVE_PAGE_SIZE
    rows = list_broadcasts_page(offset, BROADCAST_ARCHIVE_PAGE_SIZE)
    for row in rows:
        kb.row(
            types.InlineKeyboardButton(
                _format_broadcast_row_short(row),
                callback_data=f"adm_brd_{int(row['id'])}",
            )
        )
    nav = []
    max_page = max(0, (total - 1) // BROADCAST_ARCHIVE_PAGE_SIZE) if total else 0
    if page > 0:
        nav.append(
            types.InlineKeyboardButton("«", callback_data=f"adm_arc_{page - 1}")
        )
    if page < max_page:
        nav.append(
            types.InlineKeyboardButton("»", callback_data=f"adm_arc_{page + 1}")
        )
    if nav:
        kb.row(*nav)
    kb.row(
        types.InlineKeyboardButton(
            "🏠 Назад до меню",
            callback_data="adm_menu",
        )
    )
    return kb


def _broadcast_detail_text(bid: int) -> str:
    row = get_broadcast(bid)
    if not row:
        return "Розсилку не знайдено."
    n_stored = len(get_broadcast_deliveries(bid))
    try:
        dt = datetime.fromisoformat(row["created_at"])
        dstr = dt.strftime("%d.%m.%Y %H:%M UTC")
    except (TypeError, ValueError):
        dstr = str(row["created_at"])
    return (
        f"📂 <b>Розсилка №{bid}</b>\n"
        f"Час: <code>{dstr}</code>\n"
        f"Адмін ID: <code>{row['admin_id']}</code>\n"
        f"Шаблон: чат <code>{row['source_chat_id']}</code>, "
        f"msg <code>{row['source_message_id']}</code>\n"
        f"На етапі відправки: доставлено <b>{row['delivered_count']}</b>, "
        f"помилок <b>{row['failed_count']}</b>\n"
        f"Збережено пар (користувач → message_id): <b>{n_stored}</b>\n\n"
        "Нижче можна <b>видалити повідомлення цієї розсилки у всіх</b>, "
        "у кого вони ще є в чаті з ботом (Telegram <code>deleteMessage</code>)."
    )


def register_admin_handlers(bot: telebot.TeleBot, api: Api) -> None:
    @bot.message_handler(commands=["admin"], chat_types=["private"])
    def cmd_admin(message: types.Message):
        uid = message.from_user.id
        if not _is_admin(uid):
            bot.send_message(message.chat.id, "⛔️ Немає доступу.")
            return
        reset_user_state(uid)
        _clear_broadcast_pending(uid)
        bot.send_message(
            message.chat.id,
            _admin_panel_message(),
            parse_mode="HTML",
            reply_markup=_admin_menu_keyboard(),
        )

    @bot.callback_query_handler(func=lambda c: c.data == "adm_stats")
    def cb_stats(call: types.CallbackQuery):
        if not _is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Немає доступу", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        bot_counts = get_bot_user_counts()
        shop = api.get_shop_statistics()
        text = format_statistics_message(bot_counts, shop)
        kb = _back_to_menu_keyboard("adm_menu")
        try:
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=kb,
            )
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=kb)

    @bot.callback_query_handler(func=lambda c: c.data == "adm_sync_products")
    def cb_sync_products(call: types.CallbackQuery):
        if not _is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Немає доступу", show_alert=True)
            return
        bot.answer_callback_query(call.id, "Оновлення запущено на сервері…")
        chat_id = call.message.chat.id

        def _run_sync():
            ok, msg = api.sync_products_from_sheets()
            line = f"✅ {msg}" if ok else f"❌ {msg}"
            try:
                bot.send_message(
                    chat_id,
                    line,
                    reply_markup=_admin_menu_keyboard(),
                )
            except Exception:
                pass

        threading.Thread(target=_run_sync, daemon=True).start()

    @bot.callback_query_handler(func=lambda c: c.data == "adm_menu")
    def cb_menu(call: types.CallbackQuery):
        if not _is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Немає доступу", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                _admin_panel_message(),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=_admin_menu_keyboard(),
            )
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(
                call.message.chat.id,
                _admin_panel_message(),
                parse_mode="HTML",
                reply_markup=_admin_menu_keyboard(),
            )

    @bot.callback_query_handler(func=lambda c: c.data == "adm_mail")
    def cb_mail(call: types.CallbackQuery):
        if not _is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Немає доступу", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        set_user_state(call.from_user.id, {"state": States.ADMIN_BROADCAST_WAITING})
        _clear_broadcast_pending(call.from_user.id)
        kb = _back_to_menu_keyboard("adm_menu_cancel")
        mail_intro = (
            "📣 <b>Розсилка</b>\n\n"
            "Надішліть <b>одне</b> повідомлення — його отримають усі, хто колись натискав "
            "<code>/start</code> у боті.\n\n"
            "✅ Текст, фото, відео, документ, GIF — форматування зберігається.\n"
            "↩️ Щоб вийти без відправки — натисніть «Назад до меню» або знову <code>/admin</code>."
        )
        try:
            bot.edit_message_text(
                mail_intro,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=kb,
            )
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(
                call.message.chat.id,
                mail_intro,
                parse_mode="HTML",
                reply_markup=kb,
            )

    @bot.callback_query_handler(func=lambda c: c.data == "adm_menu_cancel")
    def cb_mail_cancel_to_menu(call: types.CallbackQuery):
        if not _is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Немає доступу", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        reset_user_state(call.from_user.id)
        _clear_broadcast_pending(call.from_user.id)
        try:
            bot.edit_message_text(
                _admin_panel_message(),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=_admin_menu_keyboard(),
            )
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(
                call.message.chat.id,
                _admin_panel_message(),
                parse_mode="HTML",
                reply_markup=_admin_menu_keyboard(),
            )

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm_brdok_"))
    def cb_broadcast_delete_execute(call: types.CallbackQuery):
        if not _is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Немає доступу", show_alert=True)
            return
        try:
            bid = int(call.data.replace("adm_brdok_", "", 1))
        except ValueError:
            bot.answer_callback_query(call.id, "Некоректний ID", show_alert=True)
            return
        bot.answer_callback_query(call.id, "Видалення…")
        chat_id = call.message.chat.id

        def _run_delete():
            deliveries = get_broadcast_deliveries(bid)
            ok = 0
            bad = 0
            first_err: str | None = None
            if not deliveries:
                logger.warning(
                    "broadcast delete #%s: у БД немає пар user_id→message_id — "
                    "у клієнтів нічого не видаляємо через API (лише запис архіву).",
                    bid,
                )
            for uid, mid in deliveries:
                try:
                    bot.delete_message(chat_id=uid, message_id=mid)
                    ok += 1
                except Exception as exc:
                    bad += 1
                    if first_err is None:
                        first_err = repr(exc)
                        logger.warning(
                            "broadcast delete #%s: перша помилка deleteMessage uid=%s mid=%s: %s",
                            bid,
                            uid,
                            mid,
                            first_err,
                        )
                time.sleep(0.04)
            delete_broadcast_record(bid)
            extra = ""
            if not deliveries:
                extra = (
                    "\n\n⚠️ Для цієї розсилки не було збережено жодного "
                    "<code>message_id</code> отримувачів — масове видалення в Telegram неможливе. "
                    "Перевірте, що в контейнері встановлено лише <code>pyTelegramBotAPI</code> "
                    "(пакет <code>telebot</code> з PyPI не встановлювати — він ламає імпорт)."
                )
            elif first_err and ok == 0:
                err_safe = html.escape(first_err[:200])
                extra = (
                    "\n\n⚠️ Telegram відхилив видалення (наприклад, повідомлення старіші за "
                    "обмеження API або чат недоступний). Перша помилка: "
                    f"<code>{err_safe}</code>"
                )
            try:
                bot.send_message(
                    chat_id,
                    f"🗑 Розсилку №{bid} прибрано з архіву.\n"
                    f"Видалено в Telegram: <b>{ok}</b>\n"
                    f"Не вдалося (вже видалено / недоступно): <b>{bad}</b>"
                    f"{extra}",
                    parse_mode="HTML",
                    reply_markup=_admin_menu_keyboard(),
                )
            except Exception:
                pass

        threading.Thread(target=_run_delete, daemon=True).start()

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm_brdel_"))
    def cb_broadcast_delete_confirm(call: types.CallbackQuery):
        if not _is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Немає доступу", show_alert=True)
            return
        try:
            bid = int(call.data.replace("adm_brdel_", "", 1))
        except ValueError:
            bot.answer_callback_query(call.id, "Некоректний ID", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton(
                "✅ Так, видалити всім",
                callback_data=f"adm_brdok_{bid}",
            )
        )
        kb.row(
            types.InlineKeyboardButton(
                "↩️ Ні, назад",
                callback_data=f"adm_brd_{bid}",
            )
        )
        try:
            bot.edit_message_text(
                f"⚠️ Видалити розсилку <b>№{bid}</b> у <b>всіх</b> користувачів?\n\n"
                "Буде викликано <code>deleteMessage</code> для кожного збереженого "
                "повідомлення (лише ті, що бот ще може видалити).",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=kb,
            )
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(
                call.message.chat.id,
                f"⚠️ Підтвердження видалення розсилки №{bid}",
                parse_mode="HTML",
                reply_markup=kb,
            )

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm_brd_"))
    def cb_broadcast_detail(call: types.CallbackQuery):
        if not _is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Немає доступу", show_alert=True)
            return
        try:
            bid = int(call.data.replace("adm_brd_", "", 1))
        except ValueError:
            bot.answer_callback_query(call.id, "Некоректний ID", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        kb = types.InlineKeyboardMarkup()
        if get_broadcast(bid):
            kb.row(
                types.InlineKeyboardButton(
                    "🗑 Видалити у всіх отримувачів",
                    callback_data=f"adm_brdel_{bid}",
                )
            )
        kb.row(
            types.InlineKeyboardButton(
                "« Архів",
                callback_data="adm_arc_0",
            )
        )
        kb.row(
            types.InlineKeyboardButton(
                "🏠 Меню",
                callback_data="adm_menu",
            )
        )
        try:
            bot.edit_message_text(
                _broadcast_detail_text(bid),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=kb,
            )
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(
                call.message.chat.id,
                _broadcast_detail_text(bid),
                parse_mode="HTML",
                reply_markup=kb,
            )

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm_arc_"))
    def cb_broadcast_archive(call: types.CallbackQuery):
        if not _is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Немає доступу", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        try:
            page = int(call.data.replace("adm_arc_", "", 1))
        except ValueError:
            page = 0
        total = count_broadcasts()
        max_page = max(0, (total - 1) // BROADCAST_ARCHIVE_PAGE_SIZE) if total else 0
        page = min(max(0, page), max_page)
        head = (
            f"📂 <b>Архів розсилок</b> (стор. {page + 1}/{max_page + 1})\n"
            f"Усього записів: <b>{total}</b>\n\n"
            "Оберіть розсилку — можна переглянути збережені message_id та "
            "видалити повідомлення у всіх отримувачів."
        )
        if total == 0:
            head = (
                "📂 <b>Архів розсилок</b>\n\n"
                "Поки що немає збережених розсилок — після першої підтвердженої "
                "розсилки записи з'являться тут."
            )
        try:
            bot.edit_message_text(
                head,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=_archive_keyboard(page),
            )
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(
                call.message.chat.id,
                head,
                parse_mode="HTML",
                reply_markup=_archive_keyboard(page),
            )

    @bot.callback_query_handler(func=lambda c: c.data == "adm_mail_confirm")
    def cb_mail_confirm(call: types.CallbackQuery):
        if not _is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Немає доступу", show_alert=True)
            return
        pending = _get_broadcast_pending(call.from_user.id)
        if not pending:
            bot.answer_callback_query(call.id, "Немає збереженого повідомлення", show_alert=True)
            return
        bot.answer_callback_query(call.id, "Розсилка запущена…")

        from_chat_id = pending["from_chat_id"]
        message_id = pending["message_id"]
        recipients = get_broadcast_recipient_ids()
        sent = 0
        failed = 0

        broadcast_id = create_broadcast(
            call.from_user.id, from_chat_id, message_id
        )
        stored_ids = 0

        for rid in recipients:
            try:
                copied = bot.copy_message(
                    chat_id=rid,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                )
                mid = _extract_copied_message_id(copied)
                if mid is not None:
                    add_broadcast_delivery(broadcast_id, rid, mid)
                    stored_ids += 1
                else:
                    logger.warning(
                        "broadcast #%s: copy_message ok але message_id не витягнуто "
                        "uid=%s type=%s repr=%s",
                        broadcast_id,
                        rid,
                        type(copied).__name__,
                        repr(copied)[:200],
                    )
                sent += 1
            except Exception as e:
                failed += 1
                err = str(e).lower()
                if "blocked" in err or "deactivated" in err or "forbidden" in err or "chat not found" in err:
                    mark_bot_user_blocked(rid)
            time.sleep(0.05)

        finalize_broadcast_stats(broadcast_id, sent, failed)

        reset_user_state(call.from_user.id)
        _clear_broadcast_pending(call.from_user.id)

        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except telebot.apihelper.ApiTelegramException:
            pass

        warn = ""
        if sent > 0 and stored_ids < sent:
            warn = (
                "\n\n⚠️ Збережено менше <code>message_id</code>, ніж успішних copy — "
                "пізніше «видалити всім» може не охопити всіх. Перевірте залежності бота "
                "(лише <code>pyTelegramBotAPI</code>)."
            )
        bot.send_message(
            call.message.chat.id,
            f"✅ Розсилку завершено — запис <b>№{broadcast_id}</b> у архіві.\n"
            f"Успішних відправок (copy): <b>{sent}</b>\n"
            f"Помилок / пропущено: <b>{failed}</b>\n"
            f"Збережено пар user → message_id у БД: <b>{stored_ids}</b> "
            f"(для видалення розсилки у всіх через архів)."
            f"{warn}",
            parse_mode="HTML",
            reply_markup=_admin_menu_keyboard(),
        )

    @bot.callback_query_handler(func=lambda c: c.data == "adm_mail_abort")
    def cb_mail_abort(call: types.CallbackQuery):
        if not _is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "Немає доступу", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        reset_user_state(call.from_user.id)
        _clear_broadcast_pending(call.from_user.id)
        try:
            bot.edit_message_text(
                "Розсилку скасовано.",
                call.message.chat.id,
                call.message.message_id,
            )
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(call.message.chat.id, "Розсилку скасовано.")
        bot.send_message(
            call.message.chat.id,
            _admin_panel_message(),
            parse_mode="HTML",
            reply_markup=_admin_menu_keyboard(),
        )

    @bot.message_handler(
        func=lambda m: get_user_state(m.from_user.id).get("state") == States.ADMIN_BROADCAST_WAITING,
        content_types=["text", "photo", "video", "document", "animation"],
        chat_types=["private"],
    )
    def on_broadcast_content(message: types.Message):
        if not _is_admin(message.from_user.id):
            return
        if message.content_type == "text" and message.text and message.text.startswith("/"):
            return
        _set_broadcast_pending(message.from_user.id, message.chat.id, message.message_id)
        reset_user_state(message.from_user.id)

        n = len(get_broadcast_recipient_ids())
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton(
                f"✅ Надіслати всім ({n})",
                callback_data="adm_mail_confirm",
            )
        )
        kb.row(
            types.InlineKeyboardButton(
                "❌ Скасувати розсилку",
                callback_data="adm_mail_abort",
            )
        )

        bot.send_message(
            message.chat.id,
            "✔️ <b>Попередній перегляд збережено</b>\n\n"
            f"Отримувачів у базі: <b>{n}</b>.\n"
            "Перевірте повідомлення вище й підтвердіть дію кнопками.",
            parse_mode="HTML",
            reply_markup=kb,
        )
