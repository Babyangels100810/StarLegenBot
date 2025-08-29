# ========== MAIN.PY — PART 1/6 (CLEAN SKELETON) ==========
# -*- coding: utf-8 -*-
import os, time, json, re
from collections import defaultdict
from datetime import datetime

from telebot import TeleBot, types, apihelper
from dotenv import load_dotenv, find_dotenv

# -------- API base (թող նույնը մնա) --------
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"

# -------- ENV & TOKEN --------
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
print("dotenv:", find_dotenv())
print("token len:", len(BOT_TOKEN))
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN բացակայում է .env-ում")

# -------- DIRS --------
DATA_DIR = "data"
MEDIA_DIR = "media"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)

# -------- BOT --------
bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# -------- RUNTIME (քո բիզնես լոգիկան հետո կավելացնենք) --------
CART = defaultdict(dict)   # {uid: {code: qty}}
CHECKOUT_STATE = {}        # {uid: {...}}
ORDERS = []                # demo

# -------- Օգնականները --------
def welcome_text(no:int)->str:
    return (
        "🐰🌸 <b>Բարի գալուստ StarLegen</b> 🛍✨\n\n"
        "💖 Շնորհակալ ենք, որ միացել եք մեր համայնքին ❤️\n"
        f"Դուք այժմ մեր սիրելի հաճախորդն եք №{no} ✨\n\n"
        "Մեր խանութում կգտնեք ամեն օր օգտակար ապրանքների գեղեցիկ առաջարկներ։\n\n"
        "📊 <b>Փոխարժեքի ծառայություններ</b>\n"
        "• PI ➜ USDT\n• FTN ➜ AMD\n• Alipay լիցքավորում\n\n"
        "✨ Ընտրեք բաժինները ներքևում 👇"
    )

BTN_SHOP      = "🛍 Խանութ"
BTN_CART      = "🛒 Զամբյուղ"
BTN_EXCHANGE  = "💱 Փոխարկումներ"
BTN_THOUGHTS  = "💡 Խոհուն մտքեր"
BTN_RATES     = "📊 Օրվա կուրսեր"
BTN_PROFILE   = "👤 Իմ էջը"
BTN_FEEDBACK  = "💬 Կապ մեզ հետ"
BTN_PARTNERS  = "🤝 Բիզնես գործընկերներ"
BTN_SEARCH    = "🔍 Ապրանքի որոնում"
BTN_INVITE    = "👥 Հրավիրել ընկերների"
BTN_MAIN      = "🏠 Գլխավոր մենյու"
BTN_BACK_MAIN = "⬅️ Վերադառնալ գլխավոր մենյու"

def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_SHOP, BTN_CART)
    kb.add(BTN_EXCHANGE, BTN_THOUGHTS)
    kb.add(BTN_RATES, BTN_PROFILE)
    kb.add(BTN_FEEDBACK, BTN_PARTNERS)
    kb.add(BTN_SEARCH, BTN_INVITE)
    kb.add(BTN_MAIN)
    return kb

def show_main_menu(chat_id, text="Գլխավոր մենյու ✨"):
    bot.send_message(chat_id, text, reply_markup=main_menu_kb())

# -------- Հաճախորդի սերիական համարը ֆայլով --------
COUNTER_FILE = os.path.join(DATA_DIR, "counter.json")

def _load_counter():
    try:
        if os.path.exists(COUNTER_FILE):
            return json.load(open(COUNTER_FILE,"r",encoding="utf-8")).get("customer_counter", 1000)
    except: pass
    return 1000

def _save_counter(v:int):
    try:
        json.dump({"customer_counter": v}, open(COUNTER_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    except: pass

customer_counter = _load_counter()

# -------- Handlers --------
@bot.message_handler(commands=["start"])
def on_start(m: types.Message):
    if getattr(m.chat, "type", "") != "private":
        return
    # counter
    global customer_counter
    customer_counter += 1
    _save_counter(customer_counter)

    # optional photo
    bunny = os.path.join(MEDIA_DIR, "bunny.jpg")
    if os.path.exists(bunny):
        try:
            bot.send_photo(m.chat.id, open(bunny, "rb"))
        except: pass

    bot.send_message(m.chat.id, welcome_text(customer_counter), reply_markup=main_menu_kb())

@bot.message_handler(commands=["menu"])
def on_menu(m: types.Message):
    show_main_menu(m.chat.id)

# սրանք հիմա միայն stub են, իրական ֆունկցիոնալը կգա Part 2/3-ում
@bot.message_handler(func=lambda m: m.text in (BTN_BACK_MAIN, BTN_MAIN))
def back_main(m: types.Message):
    CHECKOUT_STATE.pop(m.from_user.id, None)
    show_main_menu(m.chat.id, "Վերադարձաք գլխավոր մենյու ✨")

@bot.message_handler(func=lambda m: m.text == BTN_SHOP)
def stub_shop(m: types.Message):
    bot.send_message(m.chat.id, "🛍 Խանութ — կավելացնենք Part 2-ում։")

@bot.message_handler(func=lambda m: m.text == BTN_CART)
def stub_cart(m: types.Message):
    bot.send_message(m.chat.id, "🛒 Զամբյուղ — կավելացնենք Part 4-ում։")

@bot.message_handler(func=lambda m: m.text in (BTN_EXCHANGE, BTN_THOUGHTS, BTN_RATES, BTN_PROFILE,
                                               BTN_FEEDBACK, BTN_PARTNERS, BTN_SEARCH, BTN_INVITE))
def stubs(m: types.Message):
    bot.send_message(m.chat.id, "Քարտը կավելացնենք հաջորդ մասում 🙂")

# -------- RUN --------
if __name__ == "__main__":
    print("Bot is running…")
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
# ========== END PART 1/6 ==========
