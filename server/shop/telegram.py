import html
import os
from decimal import Decimal

import telebot
from telebot import types

from server.settings import BOT_TOKEN, ADMIN_ID
from shop.models import Order, OrderItem

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

PAYMENT_METHOD_LOCALES = {
    'online': 'Картою',
    'imposed_payment': 'Накладений платіж',
    'cryptocurrency': 'Криптовалюта',
}


def _h(text) -> str:
    if text is None:
        return ''
    return html.escape(str(text), quote=True)


def _money(amount) -> str:
    if amount is None:
        return '0'
    if isinstance(amount, Decimal):
        return str(round(amount, 2))
    return str(round(float(amount), 2))


def _order_items_queryset(order: Order):
    return OrderItem.objects.filter(order=order).select_related('product', 'product_property')


def _open_product_photo_file(product):
    if not product.photo:
        return None
    try:
        field = product.photo
        path = getattr(field, 'path', None)
        if path and os.path.isfile(path):
            return open(path, 'rb')
        return field.open('rb')
    except Exception:
        return None


class TelegramAdmin:
    @classmethod
    def create_order_message(cls, order: Order):
        order_id = order.id
        user_id = order.user_id
        total_amount = order.total_amount
        promotion_amount = order.promotion_amount
        promocode_amount = order.promocode_amount
        payment_method = order.payment_method

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "📩 Надіслати повідомлення користувачу",
                callback_data=f"reply_order_message_{user_id}_{order_id}"
            ),
        )

        username_line = ''
        try:
            user = bot.get_chat(user_id)
            if getattr(user, 'username', None):
                username_line = f"@{user.username}\n"
        except Exception:
            pass

        items = list(_order_items_queryset(order))
        lines_goods = []
        for i, oi in enumerate(items, start=1):
            p = oi.product
            art = (p.article or '').strip() or '—'
            if oi.product_property and (oi.product_property.title or '').strip():
                size = (oi.product_property.title or '').strip()
            else:
                size = (p.property_title or '').strip() or '—'
            lines_goods.append(
                f"{i}. {_h(p.title)}\n"
                f"   Артикул: <code>{_h(art)}</code>\n"
                f"   Розмір / тип: {_h(size)}\n"
                f"   Кількість: <b>{oi.quantity}</b> шт.\n"
            )
        block_goods = '\n'.join(lines_goods) if lines_goods else '—\n'

        delivery = (
            f"👤 <b>Клієнт і доставка</b>\n"
            f"ПІБ: {_h(order.full_name)}\n"
            f"Телефон: {_h(order.phone_number)}\n"
            f"Місто: {_h(order.city)}\n"
            f"Відділення / адреса: {_h(order.warehouse)}\n"
        )

        pay_label = PAYMENT_METHOD_LOCALES.get(payment_method) or _h(payment_method)
        to_pay = order.total_amount - order.promotion_amount - order.promocode_amount

        text = (
            f"📯Замовлення №{order_id}\n\n"
            f"Ідентифікатор користувача: <b>{user_id}</b>\n"
            f"{username_line}"
            f"Оплата: <b>{pay_label}</b>\n"
            f"Сума замовлення: <b>{_money(total_amount)} грн</b>\n"
            f"Знижка: <b>{_money(promotion_amount)} грн</b>\n"
            f"Знижка по промокоду: <b>{_money(promocode_amount)} грн</b>\n"
            f"💵Сума до сплати: <b>{_money(to_pay)} грн</b>\n\n"
            f"🛒 <b>Товари</b>\n{block_goods}\n"
            f"{delivery}"
        )

        bot.send_message(ADMIN_ID, text, parse_mode='HTML', reply_markup=keyboard)

        # Фото товарів (Telegram — до 10 медіа в одному альбомі)
        photo_handles = []
        media_batch = []
        try:
            for oi in items:
                fh = _open_product_photo_file(oi.product)
                if not fh:
                    continue
                photo_handles.append(fh)
                media_batch.append(types.InputMediaPhoto(fh))
                if len(media_batch) >= 10:
                    bot.send_media_group(ADMIN_ID, media_batch)
                    for h in photo_handles:
                        try:
                            h.close()
                        except Exception:
                            pass
                    photo_handles = []
                    media_batch = []
            if media_batch:
                bot.send_media_group(ADMIN_ID, media_batch)
        finally:
            for h in photo_handles:
                try:
                    h.close()
                except Exception:
                    pass

    @classmethod
    def create_order_client_message(cls, order: Order):
        order_id = order.id
        user_id = order.user_id
        total_amount = order.total_amount
        promotion_amount = order.promotion_amount
        promocode_amount = order.promocode_amount
        payment_method = order.payment_method

        goods_lines = []
        for oi in _order_items_queryset(order):
            p = oi.product
            art = (p.article or '').strip() or '—'
            if oi.product_property and (oi.product_property.title or '').strip():
                size = (oi.product_property.title or '').strip()
            else:
                size = ((p.property_title or '').strip() or '—')
            variant = f' ({_h(size)})' if size and size != '—' else ''
            goods_lines.append(
                f"📍 {_h(p.title)}{variant}\n"
                f"   Арт.: <code>{_h(art)}</code> ✖️ <b>{oi.quantity}</b> шт.\n"
            )
        goods = ''.join(goods_lines) if goods_lines else '—\n'

        delivery = (
            f"\n📦 <b>Доставка</b>\n"
            f"{_h(order.full_name)}\n"
            f"{_h(order.phone_number)}\n"
            f"{_h(order.city)}, {_h(order.warehouse)}\n"
        )

        pay_label = PAYMENT_METHOD_LOCALES.get(payment_method) or _h(payment_method)
        to_pay = total_amount - promotion_amount - promocode_amount

        bot.send_message(
            user_id,
            (
                f"📯Замовлення №{order_id} створено\n\n"
                f"🛒Товари:\n{goods}\n"
                f"{delivery}\n"
                f"🧮Оплата: <b>{pay_label}</b>\n"
                f"💵Сума до сплати: <b>{_money(to_pay)} грн</b>\n\n"
                f"Очікуйте повідомлення від адміністратора\n"
            ),
            parse_mode='HTML',
        )
