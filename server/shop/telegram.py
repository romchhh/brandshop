import telebot
from telebot import types

from server.settings import BOT_TOKEN, ADMIN_ID
from shop.models import OrderItem

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

PAYMENT_METHOD_LOCALES = {
    'online': 'Картою',
    'imposed_payment': 'Накладений платіж',
    'cryptocurrency': 'Криптовалюта',
}

class TelegramAdmin:
    @classmethod
    def create_order_message(cls, order_id, user_id, total_amount, promotion_amount, promocode_amount, payment_method):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "📩 Надіслати повідомлення користувачу",
                callback_data=f"reply_order_message_{user_id}_{order_id}"
            ),
        )
        user = bot.get_chat(user_id)

        bot.send_message(
            ADMIN_ID,
            (
                f"📯Замовлення №{order_id}\n\n"
                f"Ідентифікатор користувача: <b>{user_id}</b>\n"
                f"Оплата: <b>{PAYMENT_METHOD_LOCALES.get(payment_method)}</b>\n"
                f"Сума замовлення: <b>{round(total_amount, 2)} грн</b>\n"
                f"Знижка: <b>{round(promotion_amount, 2)} грн</b>\n"
                f"Знижка по промокоду: <b>{round(promocode_amount, 2)} грн</b>\n"
                f"💵Сума до сплати: <b>{round(total_amount - promotion_amount - promocode_amount ,2)} грн</b>\n\n"
                f"@{user.username}"
            ),
            parse_mode='HTML',
            reply_markup=keyboard
        )

    @classmethod
    def create_order_client_message(cls, order_id, user_id, total_amount, promotion_amount, promocode_amount, payment_method):
        goods = ''.join([f"📍 {order_item.product.title}{f' <i>{order_item.product_property.title}</i>' if order_item.product_property else ''}✖️{order_item.quantity} шт.\n" for order_item in OrderItem.objects.filter(order_id=order_id)])
        bot.send_message(
            user_id,
            (
                f"📯Замовлення №{order_id} створено\n\n"
                f"🛒Товари:\n{goods}\n"
                f"🧮Оплата: <b>{PAYMENT_METHOD_LOCALES.get(payment_method)}</b>\n"
                f"💵Сума до сплати: <b>{round(total_amount - promotion_amount - promocode_amount, 2)} грн</b>\n\n"
                f"Очікуйте повідомлення від адміністратора\n"
            ),
            parse_mode='HTML',
        )