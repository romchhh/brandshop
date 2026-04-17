import os
import traceback

import telebot
from telebot import types

import config
from admin_handlers import register_admin_handlers
from api import Api
from bot_storage import init_bot_storage, upsert_bot_user
from states import States, get_user_state, reset_user_state, set_user_state

TOKEN = config.TOKEN
if not TOKEN:
    raise SystemExit("Встановіть TELEGRAM_TOKEN або BOT_TOKEN у змінних оточення.")

bot = telebot.TeleBot(TOKEN, threaded=False)

api = Api(config.SERVER_URL)

init_bot_storage()
register_admin_handlers(bot, api)

INSTRUCTION_VIDEO_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "IMG_9825.MP4",
)


@bot.message_handler(commands=["start"], chat_types=["private"])
def start(message: types.Message):
    chat_id = user_id = message.from_user.id
    u = message.from_user
    upsert_bot_user(
        user_id,
        u.username,
        " ".join(filter(None, [u.first_name, u.last_name])).strip() or None,
    )

    if os.path.isfile(INSTRUCTION_VIDEO_PATH):
        bot.send_video(
            chat_id,
            types.InputFile(INSTRUCTION_VIDEO_PATH),
        )

    url = "https://brandshop.in.ua/"

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            "Магазин",
            web_app=types.WebAppInfo(url=url),
        )
    )
    bot.send_message(
        chat_id,
        f"👇🏻 Натисни на цю кнопку, щоб відкрити магазин :)",
        reply_markup=keyboard,
    )
    reset_user_state(chat_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('reply_order_message_'))
def handle_reply_order_message(call):
    try:
        data_parts = call.data.split('_')
        user_id = data_parts[3]
        order_id = data_parts[4]
        user = bot.get_chat(user_id)

        message_text = f"✈️Введіть повідомлення користувачу\n\n@{user.username}\nІдентифікатор: <b>{user_id}</b>"
        set_user_state(call.from_user.id,
                       {'state': States.WAITING_FOR_ADMIN_MESSAGE, 'user_id': user_id, 'order_id': order_id})
        bot.send_message(call.message.chat.id, message_text, parse_mode="HTML")

        bot.answer_callback_query(call.id)
    except IndexError:
        bot.send_message(call.message.chat.id, "Некоректні дані. Спробуйте ще раз.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Сталася помилка: {e}")


@bot.message_handler(
    func=lambda message: get_user_state(message.from_user.id).get('state') == States.WAITING_FOR_ADMIN_MESSAGE)
def handle_user_response(message):
    state = get_user_state(message.from_user.id)
    user_id = state.get('user_id')
    bot.send_message(message.chat.id, f"✅Повідомлення надіслане", parse_mode="HTML")
    bot.send_message(user_id, message.text)
    set_user_state(user_id, {'state': States.WAITING_FOR_CLIENT_MESSAGE})
    reset_user_state(message.from_user.id)


@bot.message_handler(
    func=lambda message: get_user_state(message.from_user.id).get('state') == States.WAITING_FOR_CLIENT_MESSAGE)
def handle_user_response(message):
    user = bot.get_chat(message.from_user.id)
    text = (
        f"Повідомлення від @{user.username}(<b>{user.id}</b>)\n\n{message.text}"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception:
            pass

    reset_user_state(message.from_user.id)

while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        with open("logs.txt", "a", encoding="utf-8") as f:
            f.write(f"{traceback.format_exc()}\n")
        print(e)
"""         try:
            bot.send_message(-1001999436200, traceback.format_exc())
        except:
            pass """
