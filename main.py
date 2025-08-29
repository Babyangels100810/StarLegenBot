# -*- coding: utf-8 -*-
# Part 1 — Base bot (ENV token, /start, welcome text, main menu)

import os, json
from telebot import TeleBot, types

# ----- Token from ENV -----
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN env variable is missing. Set it and run again.")
bot = TeleBot(TOKEN, parse_mode="HTML")

# ----- Simple customer counter (saved to file) -----
COUNTER_FILE = "counter.json"
def _load_counter() -> int:
    try:
        with open(COUNTER_FILE, "r", encoding="utf-8") as f:
            return int(json.load(f).get("no", 1000))
    except Exception:
        return 1000

def _save_counter(no: int) -> None:
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        json.dump({"no": no}, f, ensure_ascii=False)

customer_no = _load_counter()

# ----- Main menu buttons (only layout; handlers կդնենք Part 2-ում) -----
BTN_SHOP      = "🛍️ Խանութ"
BTN_CART      = "🛒 Զամբյուղ"
BTN_EXCHANGE  = "💱 Փոխանակումներ"
BTN_THOUGHTS  = "💡 Խոհուն մտքեր"
BTN_RATES     = "📊 Օրվա կուրսեր"
BTN_PROFILE   = "👤 Իմ էջը"
BTN_FEEDBACK  = "💬 Կապ մեզ հետ"
BTN_PARTNERS  = "🤝 Բիզնես գործընկերներ"
BTN_SEARCH    = "🔎 Ապրանքի որոնում"
BTN_INVITE    = "🧑‍🤝‍🧑 Հրավիրել ընկերների"

def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_SHOP, BTN_CART)
    kb.add(BTN_EXCHANGE, BTN_THOUGHTS)
    kb.add(BTN_RATES, BTN_PROFILE)
    kb.add(BTN_FEEDBACK, BTN_PARTNERS)
    kb.add(BTN_SEARCH, BTN_INVITE)
    return kb

# ----- Welcome text (քո տեքստը անփոփոխ) -----
def welcome_text(no: int) -> str:
    return (
        "🐰🌸 Բարի գալուստ BabyAngels 🛍️\n\n"
        f"💖 Շնորհակալ ենք, որ ընտրել եք մեզ ❤️ Դուք արդեն մեր սիրելի հաճախորդն եք №{no}։\n\n"
        "🎁 Առաջին պատվերի համար ունեք 5% զեղչ — կգտնեք վճարման պահին։\n\n"
        "📦 Մեզ մոտ կգտնեք․\n"
        "• Ժամանակակից ու օգտակար ապրանքներ ամեն օր թարմացվող տեսականու մեջ\n"
        "• Գեղեցիկ դիզայն և անմիջական օգտագործում\n"
        "• Անվճար առաքում ամբողջ Հայաստանով\n\n"
        "💱 Բացի խանութից՝ տրամադրում ենք նաև փոխանակման ծառայություններ․\n"
        "PI ➝ USDT | FTN ➝ AMD | Alipay ➝ CNY\n\n"
        "👇 Ընտրեք բաժին և սկսեք գնումները հիմա"
    )

# ----- /start -----
@bot.message_handler(commands=["start"])
def on_start(m: types.Message):
    global customer_no
    customer_no += 1
    _save_counter(customer_no)

    # ուղարկենք նապաստակի նկարը, եթե կա (ոչ պարտադիր)
    bunny = os.path.join("media", "bunny.jpg")
    if os.path.exists(bunny):
        with open(bunny, "rb") as ph:
            bot.send_photo(m.chat.id, ph)

    bot.send_message(m.chat.id, welcome_text(customer_no), reply_markup=main_menu_kb())

# ----- Run -----
if __name__ == "__main__":
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
