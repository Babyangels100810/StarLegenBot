# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
import telebot
from telebot import types

# .env ONLY
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN չի գտնվել (.env ֆայլը main.py-ի կողքին է, և մեջը կա BOT_TOKEN=...)")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ——— Ողջույնի խոսք (քո հաստատած) ———
GREETING_TEXT = (
    "🐰🌸 Բարի գալուստ BabyAngels 🛍️\n\n"
    "💖 Շնորհակալ ենք, որ ընտրել եք մեզ ❤️ Դուք արդեն մեր սիրելի հաճախորդն եք №{customer_no}։\n\n"
    "🎁 Լավ լուր․ առաջին պատվերի համար ունեք 5% զեղչ — կգտնեք վարկածի ավարտին վճարման պահին։\n\n"
    "📦 Ի՞նչ կգտնեք մեզ մոտ․\n"
    "• Ժամանակակից ու օգտակար ապրանքներ ամեն օր թարմացվող տեսականու մեջ\n"
    "• Գեղեցիկ դիզայն և անմիջական օգտագործում\n"
    "• Անվճար առաքում ամբողջ Հայաստանով\n\n"
    "💱 Բացի խանութից՝ տրամադրում ենք նաև հուսալի և արագ փոխանակման ծառայություններ․  \n"
    "PI ➝ USDT | FTN ➝ AMD | Alipay ➝ CNY\n\n"
    "👇 Ընտրեք բաժին և սկսեք գնումները հիմա"
)

# ——— Քո մենյուն՝ բառացի ———
MENU_ROWS = [
    ["🛍 Խանութ", "🛒 Զամբյուղ"],
    ["💱 Փոխարկումներ", "👤 Իմ էջը"],
    ["📊 Օրվա կուրսեր", "🏆 Լավագույններ"],
    ["💬 Կապ մեզ հետ", "🤝 Բիզնես գործընկերներ"],
    ["🔍 Ապրանքի որոնում", "👥 Հրավիրել ընկերների"],
    ["🏠 Գլխավոր մենյու"]
]

# ——— Հաճախորդի համար ———
_customer = 1007
def next_customer():
    global _customer
    _customer += 1
    return _customer

def send_main_menu(chat_id: int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MENU_ROWS:
        kb.row(*row)
    bot.send_message(chat_id, "Մենյուից ընտրեք բաժին 👇", reply_markup=kb)

@bot.message_handler(commands=['start'])
def start(message: types.Message):
    cid = next_customer()
    photo_path = os.path.join("media", "bunny.jpg")
    if os.path.exists(photo_path):
        with open(photo_path, "rb") as p:
            bot.send_photo(message.chat.id, p, caption=GREETING_TEXT.format(customer_no=cid))
    else:
        bot.send_message(message.chat.id, GREETING_TEXT.format(customer_no=cid))
    send_main_menu(message.chat.id)

# ——— Մնացած կոճակներին տալիս եմ placeholder, որ բոտը հանգիստ աշխատի ———
ALL_BTNS = {
    "🛍 Խանութ","🛒 Զամբյուղ","💱 Փոխարկումներ","👤 Իմ էջը","📊 Օրվա կուրսեր",
    "🏆 Լավագույններ","💬 Կապ մեզ հետ","🤝 Բիզնես գործընկերներ",
    "🔍 Ապրանքի որոնում","👥 Հրավիրել ընկերների","🏠 Գլխավոր մենյու"
}
@bot.message_handler(func=lambda m: m.text in ALL_BTNS)
def buttons_placeholder(m: types.Message):
    if m.text == "🏠 Գլխավոր մենյու":
        send_main_menu(m.chat.id)
    else:
        bot.send_message(m.chat.id, f"{m.text} — կառուցման մեջ է։")

print("🤖 Running…  /start")
bot.infinity_polling(timeout=60, long_polling_timeout=30)
