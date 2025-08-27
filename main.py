# =========================
# StarLegenBot — main.py
# PART 1/3  (paste at the very TOP of your file)
# =========================

import os
import re
import json
import time
import random
import threading
import traceback
from datetime import datetime
from collections import defaultdict

import requests
from telebot import TeleBot, types
from telebot import apihelper
from telebot.types import InputMediaPhoto
from dotenv import load_dotenv, find_dotenv

# ---- Telegram API host (պահում ենք default) ----
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"

# ---- .env ----
load_dotenv()
ENV_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
ADMIN_ID = int(os.getenv("ADMIN_ID", "6822052289"))

print("dotenv path:", find_dotenv())
print("BOT_TOKEN raw:", repr(ENV_TOKEN))
print("BOT_TOKEN len:", len(ENV_TOKEN))

# ------------------- FILES / DIRS -------------------
DATA_DIR   = "data"
MEDIA_DIR  = "media"
SET_FILE   = os.path.join(DATA_DIR, "settings.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

THOUGHTS_FILE = os.path.join(DATA_DIR, "thoughts.json")
PARTNERS_FILE = os.path.join(DATA_DIR, "partners.json")
ORDERS_FILE   = os.path.join(DATA_DIR, "orders.json")
RATES_FILE    = os.path.join(DATA_DIR, "rates.json")

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(os.path.join(MEDIA_DIR, "products"), exist_ok=True)
    os.makedirs(os.path.join(MEDIA_DIR, "exchange"), exist_ok=True)

ensure_dirs()

# ------------------- JSON helpers -------------------
def load_json(path, default):
    try:
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        print("load_json ERROR", path)
        print(traceback.format_exc())
        return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        print("save_json ERROR", path)
        print(traceback.format_exc())
        return False

# ------------------- RUNTIME STORE -------------------
SETTINGS = load_json(SET_FILE, {
    "bot_token": ENV_TOKEN or "PASTE_YOUR_BOT_TOKEN_HERE",
    "admin_id": ADMIN_ID,
    "customer_counter": 1007,
    "bot_username": "YourBotUsernameHere",
})

# allow settings override
if isinstance(SETTINGS.get("admin_id"), int):
    ADMIN_ID = SETTINGS["admin_id"]

USERS = load_json(USERS_FILE, {})        # user_id -> {referrer_id, ...}
GOOD_THOUGHTS = load_json(THOUGHTS_FILE, [])
PARTNERS = load_json(PARTNERS_FILE, [])  # text entries
ORDERS = load_json(ORDERS_FILE, [])

def persist_settings():
    save_json(SET_FILE, SETTINGS)

def persist_users():
    save_json(USERS_FILE, USERS)

def persist_thoughts():
    save_json(THOUGHTS_FILE, GOOD_THOUGHTS)

def persist_partners():
    save_json(PARTNERS_FILE, PARTNERS)

def persist_orders():
    save_json(ORDERS_FILE, ORDERS)

# ------------------- BUTTON LABELS -------------------
BTN_SHOP      = "🛍 Խանութ"
BTN_CART      = "🛒 Զամբյուղ"
BTN_EXCHANGE  = "💱 Փոխարկումներ"
BTN_THOUGHTS  = "💡 Խոհուն մտքեր"
BTN_RATES     = "📈 Օրվա կուրսեր"
BTN_PROFILE   = "🧍 Իմ էջը"
BTN_FEEDBACK  = "💬 Հետադարձ կապ"
BTN_PARTNERS  = "📢 Բիզնես գործընկերներ"
BTN_SEARCH    = "🔍 Ապրանքի որոնում"
BTN_INVITE    = "👥 Հրավիրել ընկերների"
BTN_HOME      = "🏠 Վերադառնալ գլխավոր մենյու"

# ------------------- BOT INIT -------------------
BOT_TOKEN = SETTINGS.get("bot_token") or ENV_TOKEN
if not BOT_TOKEN:
    raise RuntimeError("BOT TOKEN is empty")

bot = TeleBot(BOT_TOKEN, parse_mode=None)

# ------------------- UTILS -------------------
def ts() -> int:
    return int(time.time())

def bot_link_with_ref(user_id: int) -> str:
    uname = SETTINGS.get("bot_username") or "YourBotUsernameHere"
    return f"https://t.me/{uname}?start={user_id}"

def send_home_menu(chat_id: int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_SHOP, BTN_CART)
    kb.add(BTN_EXCHANGE, BTN_THOUGHTS)   # ← ճիշտ անունը
    kb.add(BTN_RATES, BTN_PROFILE)       # ← ճիշտ անունը
    kb.add(BTN_FEEDBACK, BTN_SEARCH)
    kb.add(BTN_HOME)
    bot.send_message(chat_id, "🏠 Գլխավոր մենյու", reply_markup=kb)


def welcome_text(customer_no: int) -> str:
    return (
        "🐰🌸 <b>Բարի գալուստ StarLegen</b> 🛍✨\n\n"
        "💖 Շնորհակալ ենք, որ միացել եք մեր սիրելի համայնքին ❤️\n"
        f"Դուք այժմ մեր սիրելի հաճախորդն եք №{customer_no} ✨\n\n"
        "Մեր խանութում կարող եք գտնել ամեն օր օգտակար ապրանքների գեղեցիկ լացակազմ գները։\n\n"
        "🎁 <b>Ավելի շատի՝</b> առցանց գնման դեպքում կարող եք օգտվել մինչև 10% զեղչ կուպոնների համակարգից։\n\n"
        "📦 Ի՞նչ կգտնեք այստեղ․\n"
        "• Ժամանակակից և օգտակար ապրանքներ ամեն օրվա համար\n"
        "• Լավագույն և տարբերակված Telegram առաջարկություններ\n"
        "• Համապատասխան և արագ առաքում 🚚\n\n"
        "📊 <b>Փոխարժեքի ծառայություններ</b>\n"
        "• PI ➔ USDT (շուկայական կուրս, +20% սպասարկում)\n"
        "• FTN ➔ AMD (միայն 10% սպասարկում)\n"
        "• Alipay լիցքավորում (1 CNY = 58֏)\n\n"
        "✨ Ավելին արդեն պատրաստված ու օգտվելու համար ընտրեք ներքևի բաժինները 👇"
    )

# ------------------- /start -------------------
@bot.message_handler(commands=["start"])
def on_start(m: types.Message):
    # only private
    if getattr(m.chat, "type", "") != "private":
        return

    uid = m.from_user.id

    # capture referral
    try:
        parts = (m.text or "").split(maxsplit=1)
        if len(parts) == 2 and parts[1].isdigit():
            ref = int(parts[1])
            if ref != uid:
                rec = USERS.setdefault(str(uid), {})
                rec.setdefault("referrer_id", ref)
                persist_users()
    except Exception:
        pass

    # customer counter
    try:
        SETTINGS["customer_counter"] = int(SETTINGS.get("customer_counter", 1007)) + 1
    except Exception:
        SETTINGS["customer_counter"] = 1008
    persist_settings()
    no = SETTINGS["customer_counter"]

    # bunny image (if exists)
    bunny = os.path.join(MEDIA_DIR, "bunny.jpg")
    if os.path.exists(bunny):
        try:
            with open(bunny, "rb") as ph:
                bot.send_photo(m.chat.id, ph)
        except Exception:
            pass

    bot.send_message(
        m.chat.id,
        welcome_text(no),
        reply_markup=build_main_menu(),
        parse_mode="HTML"
    )

# ------------------- '🏠 Վերադառնալ գլխավոր մենյու' -------------------
@bot.message_handler(func=lambda m: m.text == BTN_HOME or m.text in ("/menu", "Գլխավոր մենյու"))
def go_home(m: types.Message):
    bot.send_message(m.chat.id, "Գլխավոր մենյու ✨", reply_markup=build_main_menu())

# ------------------- Invite -------------------
@bot.message_handler(func=lambda m: m.text == BTN_INVITE)
def invite_link(m: types.Message):
    link = bot_link_with_ref(m.from_user.id)
    bot.send_message(
        m.chat.id,
        f"👥 <b>Կիսվեք բոտով և ստացեք բոնուսներ</b>\n\nՁեր հղումը՝\n{link}",
        parse_mode="HTML"
    )

# ------------------- Thoughts (խոհուն մտքեր) -------------------
@bot.message_handler(func=lambda m: m.text == BTN_THOUGHTS)
def thoughts_menu(m: types.Message):
    if not GOOD_THOUGHTS:
        bot.send_message(m.chat.id, "Այս պահին հրապարակված մտքեր չկան։")
        return
    text = "💡 <b>Վերջին մտքեր</b>\n\n" + "\n\n".join(GOOD_THOUGHTS[-5:])
    bot.send_message(m.chat.id, text, parse_mode="HTML")

# ------------------- Partners -------------------
@bot.message_handler(func=lambda m: m.text == BTN_PARTNERS)
def partners_list(m: types.Message):
    if not PARTNERS:
        bot.send_message(m.chat.id, "Այս պահին գործընկերների հայտարարություններ չկան։")
        return
    text = "📢 <b>Բիզնես գործընկերներ</b>\n\n" + "\n\n".join(PARTNERS[-5:])
    bot.send_message(m.chat.id, text, parse_mode="HTML")

# ------------------- Daily Rates (Ավտոմատ թարմացում) -------------------
RATES_CACHE = {"rates": {}, "updated_at": None, "error": None}

def fetch_rates():
    try:
        url = "https://api.exchangerate.host/latest"
        symbols = ["USD", "EUR", "RUB", "GBP", "CNY"]
        r = requests.get(url, params={"base": "AMD", "symbols": ",".join(symbols)}, timeout=10)
        data = r.json()
        raw = (data or {}).get("rates", {})
        converted = {}
        for k, v in raw.items():
            if v:
                converted[k] = round(1.0 / v, 4)  # 1 FX = ? AMD
        RATES_CACHE["rates"] = converted
        RATES_CACHE["updated_at"] = datetime.utcnow().isoformat() + "Z"
        RATES_CACHE["error"] = None
        save_json(RATES_FILE, RATES_CACHE)
    except Exception as e:
        RATES_CACHE["error"] = str(e)

def rates_loop():
    while True:
        fetch_rates()
        time.sleep(600)  # 10 րոպե

# start background refresher
threading.Thread(target=rates_loop, daemon=True).start()
fetch_rates()

@bot.message_handler(func=lambda m: m.text == BTN_RATES)
def show_rates(m: types.Message):
    try:
        cache = load_json(RATES_FILE, RATES_CACHE)
    except Exception:
        cache = RATES_CACHE
    err = cache.get("error")
    rates = cache.get("rates", {})
    if err or not rates:
        bot.send_message(m.chat.id, "❗️ Չհաջողվեց ստանալ կուրսերը, փորձեք քիչ հետո։")
        return
    flags = {"USD":"🇺🇸","EUR":"🇪🇺","RUB":"🇷🇺","GBP":"🇬🇧","CNY":"🇨🇳"}
    order = ["USD","EUR","RUB","GBP","CNY"]
    lines = ["📈 <b>Օրվա կուրսեր</b> (AMD)", ""]
    for ccy in order:
        if ccy in rates:
            lines.append(f"{flags.get(ccy,'')} 1 {ccy} = <b>{rates[ccy]}</b> AMD")
    lines.append("")
    lines.append(f"🕒 Թարմացվել է (UTC): {cache.get('updated_at','-')}")
    bot.send_message(m.chat.id, "\n".join(lines), parse_mode="HTML")

# ------------------- Exchange (stub menu) -------------------
@bot.message_handler(func=lambda m: m.text == BTN_EXCHANGE)
def exchange_menu(m: types.Message):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("PI ➜ USDT", callback_data="ex:pi"),
        types.InlineKeyboardButton("FTN ➜ AMD", callback_data="ex:ftn"),
    )
    kb.add(types.InlineKeyboardButton("Alipay լիցքավորում", callback_data="ex:ali"))
    bot.send_message(m.chat.id, "💱 Ընտրեք փոխարկման ծառայությունը 👇", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("ex:"))
def on_exchange_cb(c: types.CallbackQuery):
    typ = c.data.split(":", 1)[1]
    if typ == "pi":
        text = ("📌 PI ➜ USDT\n"
                "Մենք կատարում ենք PI–ից USDT փոխարկում՝ շուկայական կուրս + ծառայության վճար։\n"
                "Կապնվեք ադմինի հետ՝ մանրամասների համար։")
    elif typ == "ftn":
        text = ("📌 FTN ➜ AMD\n"
                "FTN-ը փոխանցում եք մեր հաշվին, ստանում եք AMD՝ 10% սպասարկման վճարով։")
    else:
        text = ("📌 Alipay լիցքավորում\n"
                "1 CNY = 58֏ (տեղեկատվական), մանրամասների համար գրեք ադմինին։")
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, text)

# ------------------- Shop (Categories) -------------------
@bot.message_handler(func=lambda m: m.text == BTN_SHOP)
def shop_menu(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⌚ Սմարթ ժամացույցներ", "💻 Համակարգչային աքսեսուարներ")
    kb.add("🚗 Ավտոմեքենայի պարագաներ", "🏠 Կենցաղային պարագաներ")
    kb.add("🍳 Խոհանոցային տեխնիկա", "💅 Խնամքի պարագաներ")
    kb.add("🚬 Էլեկտրոնային ծխախոտ", "👩 Կանացի (շուտով)")
    kb.add("👨 Տղամարդու (շուտով)", "🧒 Մանկական (շուտով)")
    kb.add("⬅️ Վերադառնալ խանութ", BTN_HOME)
    bot.send_message(m.chat.id, "🛍 Խանութ — ընտրեք կատեգորիա 👇", reply_markup=kb)

# back to shop button
@bot.message_handler(func=lambda m: m.text == "⬅️ Վերադառնալ խանութ")
def back_to_shop(m: types.Message):
    shop_menu(m)

# ------------------- Category stubs (empty) -------------------
@bot.message_handler(func=lambda m: m.text == "⌚ Սմարթ ժամացույցներ")
def cat_watches(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Վերադառնալ խանութ", BTN_HOME)
    bot.send_message(m.chat.id, "⌚ Այստեղ կլինեն Սմարթ ժամացույցների ապրանքները։", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "💻 Համակարգչային աքսեսուարներ")
def cat_pc(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Վերադառնալ խանութ", BTN_HOME)
    bot.send_message(m.chat.id, "💻 Այստեղ կլինեն Համակարգչային աքսեսուարները։", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🚗 Ավտոմեքենայի պարագաներ")
def cat_car(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Վերադառնալ խանութ", BTN_HOME)
    bot.send_message(m.chat.id, "🚗 Այստեղ կլինեն Ավտոմեքենայի պարագաները։", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🍳 Խոհանոցային տեխնիկա")
def cat_kitchen(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Վերադառնալ խանութ", BTN_HOME)
    bot.send_message(m.chat.id, "🍳 Այստեղ կլինեն Խոհանոցային տեխնիկայի ապրանքները։", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "💅 Խնամքի պարագաներ")
def cat_care(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Վերադառնալ խանութ", BTN_HOME)
    bot.send_message(m.chat.id, "💅 Այստեղ կլինեն Խնամքի պարագաները։", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🚬 Էլեկտրոնային ծխախոտ")
def cat_ecig(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Վերադառնալ խանութ", BTN_HOME)
    bot.send_message(m.chat.id, "🚬 Այստեղ կլինեն Էլեկտրոնային ծխախոտի ապրանքները։", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "👩 Կանացի (շուտով)")
def cat_women(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Վերադառնալ խանութ", BTN_HOME)
    bot.send_message(m.chat.id, "👩 Կանացի ապրանքները հասանելի կլինեն շուտով։", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "👨 Տղամարդու (շուտով)")
def cat_men(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Վերադառնալ խանութ", BTN_HOME)
    bot.send_message(m.chat.id, "👨 Տղամարդու ապրանքները հասանելի կլինեն շուտով։", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🧒 Մանկական (շուտով)")
def cat_kids(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Վերադառնալ խանութ", BTN_HOME)
    bot.send_message(m.chat.id, "🧒 Մանկական ապրանքները հասանելի կլինեն շուտով։", reply_markup=kb)

# ------------------- Household (will show 11 cards from PRODUCTS)
# PRODUCTS dict and product handlers will be added in PART 2/3
@bot.message_handler(func=lambda m: m.text == "🏠 Կենցաղային պարագաներ")
def cat_household(m: types.Message):
    bot.send_message(m.chat.id, "⏳ Բեռնավորում ենք ապրանքները…")
    # Actual listing is in PART 2/3 once PRODUCTS are defined
    # After paste Part 2/3, this handler will send cards automatically.

# =========================
#   END OF PART 1/3
#   (Wait for PART 2/3 — products + slider + add-to-cart buttons)
# =========================
# =========================
# StarLegenBot — main.py
# PART 2/3  (paste directly below Part 1/3)
# =========================
@bot.message_handler(commands=['debug'])
def cmd_debug(m: types.Message):
    bot.send_message(m.chat.id, f"Products: {len(PRODUCTS)}\nUsers: {len(USERS)}\nOrders: {len(ORDERS)}")

# ------------------- PRODUCTS -------------------
PRODUCTS = {
    "BA100810": {
        "title": "Գորգ «Ծաղկային դիզայն»",
        "size": "40×60 սմ",
        "price": 1690,
        "old_price": 2560,
        "sold": 325,
        "stock": 99,
        "category": "home",
        "img": "media/products/BA100810.jpg",
        "images": [
            "media/products/BA100810.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
        ],
        "bullets": [
            "Հարմար է մուտքի, խոհանոցի և լոգասենյակի համար",
            "Հեշտ լվացվող և արագ չորացող",
            "Գեղեցիկ թարմացված դիզայն"
        ],
        "long_desc": "🌸 Մեր ծաղկային դիզայնով գորգը կզարդարի ձեր տունը։"
    },
    "BA100811": {
        "title": "Գորգ «Թիթեռներով»",
        "size": "40×60 սմ",
        "price": 1690,
        "old_price": 2560,
        "sold": 278,
        "stock": 80,
        "category": "home",
        "img": "media/products/BA100811.jpg",
        "images": [
            "media/products/BA100811.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
        ],
        "bullets": [
            "Նուրբ դիզայն թիթեռներով",
            "Հեշտ լվացվող և դիմացկուն"
        ],
        "long_desc": "🦋 Թեթև ու նուրբ գորգ, որը ջերմություն կհաղորդի ձեր ինտերիերին։"
    },
    "BA100812": {
        "title": "Գորգ «Վարդագույն փուշ»",
        "size": "40×60 սմ",
        "price": 1690,
        "old_price": 2560,
        "sold": 315,
        "stock": 77,
        "category": "home",
        "img": "media/products/BA100812.jpg",
        "images": [
            "media/products/BA100812.jpg",
            "media/products/shared/interior.jpg",
        ],
        "bullets": [
            "Կոմպակտ չափս",
            "Հարմար տեղադրելու համար"
        ],
        "long_desc": "🌺 Հիանալի տարբերակ՝ տունը կոկիկ ու հարմարավետ դարձնելու համար։"
    },
    "BA100813": {
        "title": "Գորգ «Նուրբ ծաղկային»",
        "size": "40×60 սմ",
        "price": 1690,
        "old_price": 2560,
        "sold": 292,
        "stock": 88,
        "category": "home",
        "img": "media/products/BA100813.jpg",
        "images": [
            "media/products/BA100813.jpg",
            "media/products/shared/care.jpg",
        ],
        "bullets": [
            "Դիմացկուն շերտավոր կառուցվածք",
            "Հեշտ մաքրվող"
        ],
        "long_desc": "🌷 Կոկիկ գորգ, որը կդառնա ինտերիերի գեղեցիկ հավելում։"
    },
    "BA100814": {
        "title": "Գորգ «Բաց մանուշակագույն»",
        "size": "40×60 սմ",
        "price": 1690,
        "old_price": 2560,
        "sold": 341,
        "stock": 65,
        "category": "home",
        "img": "media/products/BA100814.jpg",
        "images": [
            "media/products/BA100814.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/layers.jpg",
        ],
        "bullets": [
            "Սահադիմացկուն հիմք",
            "Գեղեցիկ գույն"
        ],
        "long_desc": "💜 Թարմացրու տունը մանուշակագույն գեղեցկությամբ։"
    },
    "BA100815": {
        "title": "Գորգ «Ծաղիկներ և թիթեռներ»",
        "size": "40×60 սմ",
        "price": 1690,
        "old_price": 2560,
        "sold": 289,
        "stock": 73,
        "category": "home",
        "img": "media/products/BA100815.jpg",
        "images": [
            "media/products/BA100815.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/interior.jpg",
        ],
        "bullets": [
            "Նուրբ դիզայն թիթեռներով",
            "Կենցաղային հարմարավետություն"
        ],
        "long_desc": "🦋🌸 Թիթեռների ու ծաղիկների ներդաշնակություն։"
    },
    "BA100816": {
        "title": "Գորգ «Թեթև սևապատ»",
        "size": "40×60 սմ",
        "price": 1690,
        "old_price": 2560,
        "sold": 300,
        "stock": 92,
        "category": "home",
        "img": "media/products/BA100816.jpg",
        "images": [
            "media/products/BA100816.jpg",
        ],
        "bullets": [
            "Սևավուն նուրբ երանգ",
            "Հեշտ լվացվող"
        ],
        "long_desc": "🖤 Կոնտրաստային գորգ՝ ժամանակակից ինտերիերի համար։"
    },
    "BA100817": {
        "title": "Գորգ «Նուրբ վարդագույն երանգ»",
        "size": "40×60 սմ",
        "price": 1690,
        "old_price": 2560,
        "sold": 276,
        "stock": 85,
        "category": "home",
        "img": "media/products/BA100817.jpg",
        "images": [
            "media/products/BA100817.jpg",
            "media/products/shared/interior.jpg",
        ],
        "bullets": [
            "Գեղեցիկ վարդագույն երանգ",
            "Տաք ու հարմարավետ"
        ],
        "long_desc": "💕 Սիրուն գորգ, որը ջերմություն կհաղորդի ձեր սենյակին։"
    },
    "BA100818": {
        "title": "Գորգ «Նուրբ դիզայն»",
        "size": "40×60 սմ",
        "price": 1690,
        "old_price": 2560,
        "sold": 310,
        "stock": 79,
        "category": "home",
        "img": "media/products/BA100818.jpg",
        "images": [
            "media/products/BA100818.jpg",
            "media/products/shared/layers.jpg",
        ],
        "bullets": [
            "Դիմացկուն և գեղեցիկ",
            "Հեշտ մաքրվող"
        ],
        "long_desc": "🌸 Ձեր տան համար իդեալական նուրբ դիզայնի գորգ։"
    },
    "BA100819": {
        "title": "Գորգ «Թիթեռներով դիզայն»",
        "size": "40×60 սմ",
        "price": 1690,
        "old_price": 2560,
        "sold": 298,
        "stock": 88,
        "category": "home",
        "img": "media/products/BA100819.jpg",
        "images": [
            "media/products/BA100819.jpg",
            "media/products/shared/interior.jpg",
        ],
        "bullets": [
            "Հեշտ տեղադրվող",
            "Հարմարավետություն ամենօրյա օգտագործման համար"
        ],
        "long_desc": "🦋 Ծաղկային դիզայն թիթեռներով՝ գեղեցիկ ինտերիերի համար։"
    },
    "BA100820": {
        "title": "Գորգ «Գունավոր ծաղիկներ»",
        "size": "40×60 սմ",
        "price": 1690,
        "old_price": 2560,
        "sold": 350,
        "stock": 70,
        "category": "home",
        "img": "media/products/BA100820.jpg",
        "images": [
            "media/products/BA100820.jpg",
            "media/products/shared/care.jpg",
        ],
        "bullets": [
            "Բազմագույն դիզայն",
            "Հարմար է ցանկացած սենյակի"
        ],
        "long_desc": "🌼 Բազմագույն ծաղիկներով գորգ՝ ձեր տան ուրախ տրամադրության համար։"
    },
}

# ------------------- PRODUCT SLIDER & CART BUTTONS -------------------
def _product_images(code):
    p = PRODUCTS.get(code, {})
    raw = p.get("images") or [p.get("img")]
    return [x for x in raw if x and os.path.exists(x)]

def _slider_kb(code: str, idx: int, total: int):
    left  = types.InlineKeyboardButton("◀️", callback_data=f"slider:{code}:{(idx-1)%total}")
    right = types.InlineKeyboardButton("▶️", callback_data=f"slider:{code}:{(idx+1)%total}")

    row_cart = [
        types.InlineKeyboardButton("➕ Ավելացնել զամբյուղ", callback_data=f"cart:add:{code}"),
        types.InlineKeyboardButton("🧺 Դիտել զամբյուղ", callback_data="cart:show"),
    ]
    row_nav = [
        types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="go_home"),
    ]

    kb = types.InlineKeyboardMarkup()
    kb.row(left, right)
    kb.row(*row_cart)
    kb.row(*row_nav)
    return kb

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("p:"))
def show_product(c: types.CallbackQuery):
    code = c.data.split(":",1)[1]
    p = PRODUCTS.get(code, {})
    if not p:
        return bot.answer_callback_query(c.id, "Ապրանքը չի գտնվել")

    imgs = _product_images(code)
    total = max(1, len(imgs))
    idx = 0

    discount = int(round(100 - (p["price"] * 100 / p["old_price"])))
    bullets = "\n".join([f"✅ {b}" for b in (p.get("bullets") or [])])
    caption = (
        f"🌸 **{p.get('title','')}**\n"
        f"✔️ Չափս՝ {p.get('size','')}\n"
        f"{bullets}\n\n"
        f"{p.get('long_desc','')}\n\n"
        f"Հին գին — {p.get('old_price',0)}֏ (−{discount}%)\n"
        f"Նոր գին — **{p.get('price',0)}֏**\n"
        f"Վաճառված — {p.get('sold',0)} հատ\n"
        f"Կոդ՝ `{code}`"
    )

    if imgs:
        with open(imgs[idx], "rb") as ph:
            bot.send_photo(
                c.message.chat.id, ph, caption=caption, parse_mode="Markdown",
                reply_markup=_slider_kb(code, idx, total)
            )
    else:
        bot.send_message(c.message.chat.id, caption, parse_mode="Markdown", reply_markup=_slider_kb(code, idx, total))

    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("slider:"))
def product_slider(c: types.CallbackQuery):
    _, code, idx_str = c.data.split(":")
    idx = int(idx_str)
    p = PRODUCTS.get(code, {})
    imgs = _product_images(code)
    total = max(1, len(imgs))
    idx = idx % total

    discount = int(round(100 - (p["price"] * 100 / p["old_price"])))
    bullets = "\n".join([f"✅ {b}" for b in (p.get("bullets") or [])])
    caption = (
        f"🌸 **{p.get('title','')}**\n"
        f"✔️ Չափս՝ {p.get('size','')}\n"
        f"{bullets}\n\n"
        f"{p.get('long_desc','')}\n\n"
        f"Հին գին — {p.get('old_price',0)}֏ (−{discount}%)\n"
        f"Նոր գին — **{p.get('price',0)}֏**\n"
        f"Վաճառված — {p.get('sold',0)} հատ\n"
        f"Կոդ՝ `{code}`"
    )

    if imgs:
        with open(imgs[idx], "rb") as ph:
            media = InputMediaPhoto(ph, caption=caption, parse_mode="Markdown")
            bot.edit_message_media(media, chat_id=c.message.chat.id, message_id=c.message.message_id,
                                   reply_markup=_slider_kb(code, idx, total))
    else:
        bot.edit_message_caption(caption, chat_id=c.message.chat.id,
                                 message_id=c.message.message_id, parse_mode="Markdown",
                                 reply_markup=_slider_kb(code, idx, total))
    bot.answer_callback_query(c.id)

# =========================
#   END OF PART 2/3
#   (Next: Part 3/3 — Cart handlers, Checkout, Orders, Admin panel)
# =========================
# =========================
# --------- UNIFIED HOME SENDER (put above MAIN LOOP) ----------
def send_home_menu(chat_id: int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_SHOP, BTN_CART)
    kb.add(BTN_EXCHANGE, BTN_IDEAS)
    kb.add(BTN_ORDERS, BTN_PROFILE)
    kb.add(BTN_FEEDBACK, BTN_SEARCH)
    bot.send_message(chat_id, "🏠 Գլխավոր մենյու", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == BTN_BACK_HOME)
def back_home_from_text(m: types.Message):
    send_home_menu(m.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "go_home")
def back_home_from_cb(c: types.CallbackQuery):
    try:
        # remove inline under previous message to avoid extra clicks
        bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=None)
    except:
        pass
    send_home_menu(c.message.chat.id)
    bot.answer_callback_query(c.id, "Գլխավոր մենյու")

# StarLegenBot — main.py
# PART 3/3  (paste below Part 2/3)
# =========================

# ------------------- CART HANDLERS -------------------
CART = defaultdict(dict)  # user_id -> {code: qty}

def _cart_text(uid: int) -> str:
    items = CART[uid]
    if not items:
        return "🛒 Զամբյուղը դատարկ է։"
    lines = ["🛒 <b>Ձեր զամբյուղը</b>", ""]
    total = 0
    for code, qty in items.items():
        p = PRODUCTS[code]
        line = f"{p['title']} — {qty} հատ × {p['price']}֏"
        lines.append(line)
        total += p['price'] * qty
    lines.append("")
    lines.append(f"Ընդամենը՝ <b>{total}֏</b>")
    return "\n".join(lines)

@bot.message_handler(func=lambda m: m.text == BTN_CART)
def open_cart_from_menu(m: types.Message):
    uid = m.from_user.id
    kb = types.InlineKeyboardMarkup()
    for code, qty in list(CART[uid].items())[:6]:
        title = PRODUCTS[code]["title"]
        kb.row(types.InlineKeyboardButton(f"🛒 {title} ({qty})", callback_data="noop"))
        kb.row(
            types.InlineKeyboardButton("➖", callback_data=f"cart:dec:{code}"),
            types.InlineKeyboardButton("➕", callback_data=f"cart:inc:{code}"),
            types.InlineKeyboardButton("🗑", callback_data=f"cart:rm:{code}"),
        )
    kb.row(
        types.InlineKeyboardButton("❌ Մաքրել", callback_data="cart:clear"),
        types.InlineKeyboardButton("🧾 Ավարտել պատվերը", callback_data="checkout:start"),
    )
    kb.row(
        types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="go_home"),
    )
    bot.send_message(m.chat.id, _cart_text(uid), reply_markup=kb, parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("cart:"))
def cart_callbacks(c: types.CallbackQuery):
    uid = c.from_user.id
    parts = c.data.split(":")
    action = parts[1]
    code = parts[2] if len(parts) > 2 else None

    if action == "add" and code:
        CART[uid][code] = CART[uid].get(code, 0) + 1
        bot.answer_callback_query(c.id, "Ավելացվեց զամբյուղում ✅")

    elif action == "inc" and code:
        CART[uid][code] = CART[uid].get(code, 0) + 1

    elif action == "dec" and code:
        q = CART[uid].get(code, 0)
        CART[uid][code] = max(0, q - 1)
        if CART[uid][code] == 0:
            CART[uid].pop(code, None)

    elif action == "rm" and code:
        CART[uid].pop(code, None)

    elif action == "clear":
        CART[uid].clear()

    if action in ("show", "add", "inc", "dec", "rm", "clear"):
        kb = types.InlineKeyboardMarkup()
        for code, qty in list(CART[uid].items())[:6]:
            title = PRODUCTS[code]["title"]
            kb.row(types.InlineKeyboardButton(f"🛒 {title} ({qty})", callback_data="noop"))
            kb.row(
                types.InlineKeyboardButton("➖", callback_data=f"cart:dec:{code}"),
                types.InlineKeyboardButton("➕", callback_data=f"cart:inc:{code}"),
                types.InlineKeyboardButton("🗑", callback_data=f"cart:rm:{code}"),
            )
        kb.row(
            types.InlineKeyboardButton("❌ Մաքրել", callback_data="cart:clear"),
            types.InlineKeyboardButton("🧾 Ավարտել պատվերը", callback_data="checkout:start"),
        )
        kb.row(
            types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
            types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="go_home"),
        )
        bot.edit_message_text(_cart_text(uid), chat_id=c.message.chat.id,
                              message_id=c.message.message_id,
                              reply_markup=kb, parse_mode="HTML")
        bot.answer_callback_query(c.id)

# ------------------- CHECKOUT -------------------
CHECKOUT_STATE = {}  # uid -> step

@bot.callback_query_handler(func=lambda c: c.data == "checkout:start")
def checkout_start(c: types.CallbackQuery):
    uid = c.from_user.id
    if not CART[uid]:
        return bot.answer_callback_query(c.id, "Զամբյուղը դատարկ է։")
    CHECKOUT_STATE[uid] = {"step": "name", "data": {}}
    bot.send_message(c.message.chat.id, "✍️ Մուտքագրեք ձեր անունը։")
    bot.answer_callback_query(c.id)

@bot.message_handler(func=lambda m: m.from_user.id in CHECKOUT_STATE)
def checkout_steps(m: types.Message):
    uid = m.from_user.id
    state = CHECKOUT_STATE[uid]
    step = state["step"]
    if step == "name":
        state["data"]["name"] = m.text.strip()
        state["step"] = "phone"
        return bot.send_message(m.chat.id, "📞 Մուտքագրեք ձեր հեռախոսահամարը։")

    if step == "phone":
        state["data"]["phone"] = m.text.strip()
        state["step"] = "address"
        return bot.send_message(m.chat.id, "🏠 Մուտքագրեք ձեր հասցեն։")

    if step == "address":
        state["data"]["address"] = m.text.strip()
        # save order
        order = {
            "user": uid,
            "items": CART[uid],
            "info": state["data"],
            "created": datetime.utcnow().isoformat()+"Z",
        }
        ORDERS.append(order)
        persist_orders()
        # send to admin
        bot.send_message(ADMIN_ID, f"📦 Նոր պատվեր {uid}\n{json.dumps(order, ensure_ascii=False, indent=2)}")
        # clear
        CART[uid].clear()
        del CHECKOUT_STATE[uid]
        return bot.send_message(m.chat.id, "✅ Պատվերը ուղարկվեց ադմինին։ Շնորհակալություն։")

# ------------------- PROFILE (Իմ էջը) -------------------
@bot.message_handler(func=lambda m: m.text == BTN_PROFILE)
def my_profile(m: types.Message):
    uid = m.from_user.id
    orders = [o for o in ORDERS if o["user"] == uid]
    lines = ["🧍 <b>Իմ էջը</b>", ""]
    if orders:
        lines.append("📦 Պատվերների քանակ՝ " + str(len(orders)))
        for o in orders[-3:]:
            lines.append(f"- {o['created']} ({len(o['items'])} ապրանք)")
    else:
        lines.append("Դեռ պատվերներ չունեք։")
    bot.send_message(m.chat.id, "\n".join(lines), parse_mode="HTML")

# ------------------- FEEDBACK -------------------
@bot.message_handler(func=lambda m: m.text == BTN_FEEDBACK)
def feedback(m: types.Message):
    bot.send_message(m.chat.id, "✍️ Գրեք ձեր հաղորդագրությունը, այն կուղարկվի ադմինին։")
    bot.register_next_step_handler(m, feedback_step)

def feedback_step(m: types.Message):
    bot.send_message(ADMIN_ID, f"💬 Feedback {m.from_user.id}: {m.text}")
    bot.send_message(m.chat.id, "✅ Ձեր հաղորդագրությունը ուղարկվեց ադմինին։")

# ------------------- SEARCH -------------------
@bot.message_handler(func=lambda m: m.text == BTN_SEARCH)
def product_search(m: types.Message):
    bot.send_message(m.chat.id, "Որոնման համար մուտքագրեք ապրանքի անվանում կամ կոդ։")
    bot.register_next_step_handler(m, do_search)

def do_search(m: types.Message):
    term = m.text.strip().lower()
    found = []
    for code, p in PRODUCTS.items():
        if term in code.lower() or term in p["title"].lower():
            found.append(code)
    if not found:
        return bot.send_message(m.chat.id, "Չգտնվեց։")
    for code in found[:5]:
        bot.send_message(m.chat.id, f"Գտնվեց՝ {PRODUCTS[code]['title']}", reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("👀 Դիտել", callback_data=f"p:{code}")
        ))

# ------------------- ADMIN PANEL -------------------
@bot.message_handler(commands=["admin"])
def admin_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 Վիճակագրություն", "👥 Վերջին օգտատերեր")
    kb.add("🧾 Վերջին հաղորդագրություններ", "⬇️ Ներբեռնել logs")
    kb.add("📣 Broadcast", "🔎 Փնտրել օգտատիրոջը")
    kb.add("↩️ Փակել")
    bot.send_message(m.chat.id, "🔐 Ադմին պանել", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "📊 Վիճակագրություն" and m.from_user.id == ADMIN_ID)
def admin_stats(m: types.Message):
    bot.send_message(m.chat.id, f"Օգտատերեր: {len(USERS)}\nՊատվերներ: {len(ORDERS)}")

@bot.message_handler(func=lambda m: m.text == "👥 Վերջին օգտատերեր" and m.from_user.id == ADMIN_ID)
def admin_users(m: types.Message):
    lines = []
    for uid in list(USERS.keys())[-10:]:
        lines.append(uid)
    bot.send_message(m.chat.id, "\n".join(lines))

@bot.message_handler(func=lambda m: m.text == "🧾 Վերջին հաղորդագրություններ" and m.from_user.id == ADMIN_ID)
def admin_msgs(m: types.Message):
    try:
        with open("messages.log","r",encoding="utf-8") as f:
            lines = f.readlines()[-20:]
        bot.send_message(m.chat.id, "".join(lines))
    except Exception as e:
        bot.send_message(m.chat.id, str(e))

@bot.message_handler(func=lambda m: m.text == "⬇️ Ներբեռնել logs" and m.from_user.id == ADMIN_ID)
def admin_logs(m: types.Message):
    try:
        with open("messages.log","rb") as f:
            bot.send_document(m.chat.id, f)
    except: pass
    try:
        with open("errors.log","rb") as f:
            bot.send_document(m.chat.id, f)
    except: pass

@bot.message_handler(func=lambda m: m.text == "📣 Broadcast" and m.from_user.id == ADMIN_ID)
def admin_broadcast(m: types.Message):
    bot.send_message(m.chat.id, "✍️ Գրեք հաղորդագրությունը բոլորին ուղարկելու համար։")
    bot.register_next_step_handler(m, do_broadcast)

def do_broadcast(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    for uid in USERS.keys():
        try:
            bot.send_message(int(uid), m.text)
        except: pass
    bot.send_message(m.chat.id, "✅ Ուղարկվեց։")

# ------------------- MAIN LOOP -------------------
if __name__ == "__main__":
    try:
        bot.remove_webhook()
    except: pass
    print("🤖 Bot is running...")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)

