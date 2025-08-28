# -*- coding: utf-8 -*-
import os, json, time, threading, traceback, re
import requests
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv, find_dotenv
from telebot import TeleBot, types
from telebot import apihelper
from telebot.types import InputMediaPhoto

# ---------------- TELEGRAM API URL (фикс՝ 401/409 խնդիրների առումով) ------------
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"

# ---------------- .env / TOKEN ---------------------------------------------------
load_dotenv()
ENV_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
ADMIN_ID = int(os.getenv("ADMIN_ID", "6822052289"))  # քո admin ID

print("dotenv path:", find_dotenv())
print("BOT_TOKEN raw:", repr(ENV_TOKEN))
print("BOT_TOKEN len:", len(ENV_TOKEN))

if not ENV_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is empty. Put it into .env as TELEGRAM_BOT_TOKEN=...")

# ---------------- STORAGE PATHS --------------------------------------------------
DATA_DIR = "data"
MEDIA_DIR = "media"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(os.path.join(MEDIA_DIR, "products"), exist_ok=True)

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
THOUGHTS_FILE = os.path.join(DATA_DIR, "thoughts.json")
ADS_FILE = os.path.join(DATA_DIR, "ads.json")
RATES_FILE = os.path.join(DATA_DIR, "rates.json")

def _load_json(path, default):
    try:
        if not os.path.exists(path):
            _save_json(path, default)
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        print("JSON load error:", path)
        return default

def _save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        print("JSON save error:", path)
        return False

SETTINGS = _load_json(SETTINGS_FILE, {
    "customer_counter": 1007,
    "bot_username": "YourBotUsernameHere"
})
USERS      = _load_json(USERS_FILE, {})
ORDERS     = _load_json(ORDERS_FILE, [])
THOUGHTS   = _load_json(THOUGHTS_FILE, [])
ADS_STORE  = _load_json(ADS_FILE, [])
RATES_CACHE = _load_json(RATES_FILE, {"rates": {}, "updated_at": None, "error": None})

# ---------------- BOT INIT -------------------------------------------------------
bot = TeleBot(ENV_TOKEN, parse_mode="HTML")

# ---------------- GLOBALS (Runtime) ---------------------------------------------
START_TS = time.time()

def uptime():
    sec = int(time.time() - START_TS)
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    m, s  = divmod(sec, 60)
    out = []
    if d: out.append(f"{d} օր")
    if h: out.append(f"{h} ժ")
    if m: out.append(f"{m}  ր")
    out.append(f"{s} վ")
    return " ".join(out)

# =========================
# BUTTON LABELS / MAIN MENU
# =========================
BTN_SHOP     = "🛍 Խանութ"
BTN_CART     = "🛒 Զամբյուղ"
BTN_EXCHANGE = "💱 Փոխարկումներ"
BTN_THOUGHTS = "💡 Խոհուն մտքեր"
BTN_RATES    = "📈 Օրվա կուրսեր"
BTN_PROFILE  = "🧍 Իմ էջը"
BTN_FEEDBACK = "💬 Կապ մեզ հետ"
BTN_PARTNERS = "📢 Բիզնես գործընկերներ"
BTN_SEARCH   = "🔍 Ապրանքի որոնում"
BTN_INVITE   = "👥 Հրավիրել ընկերների"
BTN_BACK_MAIN= "⬅️ Վերադառնալ գլխավոր մենյու"
BTN_BACK_SHOP= "⬅️ Վերադառնալ խանութ"

def build_main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_SHOP, BTN_CART)
    kb.add(BTN_EXCHANGE, BTN_THOUGHTS)
    kb.add(BTN_RATES, BTN_PROFILE)
    kb.add(BTN_FEEDBACK, BTN_PARTNERS)
    kb.add(BTN_SEARCH, BTN_INVITE)
    return kb

def show_main_menu(chat_id, text="Գլխավոր մենյու ✨"):
    bot.send_message(chat_id, text, reply_markup=build_main_menu())

# =========================
# WELCOME / START
# =========================
def welcome_text(customer_no: int) -> str:
    # ⚠️ ՉԵՄ ՓՈԽԵԼ ոճը՝ պահել ենք քոնը
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
        "✨ Ընտրեք ներքևից բաժին 👇"
    )

def bot_link_with_ref(user_id: int) -> str:
    uname = SETTINGS.get("bot_username") or "YourBotUsernameHere"
    return f"https://t.me/{uname}?start={user_id}"

@bot.message_handler(commands=["start"])
def cmd_start(m: types.Message):
    # referral
    try:
        parts = (m.text or "").split(maxsplit=1)
        if len(parts) == 2 and parts[1].isdigit():
            uid = m.from_user.id
            ref_id = int(parts[1])
            if uid != ref_id:
                USERS.setdefault(str(uid), {})
                if "referrer_id" not in USERS[str(uid)]:
                    USERS[str(uid)]["referrer_id"] = ref_id
                    _save_json(USERS_FILE, USERS)
    except:
        pass

    SETTINGS["customer_counter"] = int(SETTINGS.get("customer_counter", 1007)) + 1
    _save_json(SETTINGS_FILE, SETTINGS)
    customer_no = SETTINGS["customer_counter"]

    # bunny
    bunny_path = os.path.join(MEDIA_DIR, "bunny.jpg")
    if os.path.exists(bunny_path):
        try:
            with open(bunny_path, "rb") as ph:
                bot.send_photo(m.chat.id, ph)
        except:
            pass

    bot.send_message(m.chat.id, welcome_text(customer_no), reply_markup=build_main_menu())

@bot.message_handler(commands=["menu"])
def cmd_menu(m: types.Message):
    show_main_menu(m.chat.id)

# =========================
# ADMIN PANEL (քեզ մոտ արդեն կար՝ պահել ենք լայթ տարբերակ)
# =========================
def _is_admin(uid: int) -> bool:
    return int(uid) == int(ADMIN_ID)

@bot.message_handler(commands=["admin"])
def cmd_admin(m: types.Message):
    if not _is_admin(m.from_user.id):
        return bot.reply_to(m, "❌ Դուք ադմին չեք։")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📊 Վիճակագրություն", callback_data="adm:stats"))
    kb.add(types.InlineKeyboardButton("👥 Օգտատերեր", callback_data="adm:users"))
    kb.add(types.InlineKeyboardButton("♻️ Reload", callback_data="adm:reload"))
    bot.send_message(m.chat.id, "🛠 Ադմին պանել", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm:"))
def on_admin(c: types.CallbackQuery):
    if not _is_admin(c.from_user.id):
        return bot.answer_callback_query(c.id, "Ոչ ադմին")
    act = c.data.split(":")[1]
    if act == "stats":
        txt = (f"📊 Վիճակագրություն\n"
               f"Users: {len(USERS)}\n"
               f"Orders: {len(ORDERS)}\n"
               f"Uptime: {uptime()}\n")
        bot.answer_callback_query(c.id)
        bot.edit_message_text(txt, c.message.chat.id, c.message.message_id)
    elif act == "users":
        bot.answer_callback_query(c.id)
        lines = []
        for uid, u in list(USERS.items())[:20]:
            lines.append(f"• id={uid}, ref={u.get('referrer_id','—')}")
        if not lines: lines = ["Դեռ օգտատեր չկա։"]
        bot.edit_message_text("👥 Վերջին օգտատերեր\n" + "\n".join(lines),
                              c.message.chat.id, c.message.message_id)
    elif act == "reload":
        global SETTINGS, USERS, ORDERS, THOUGHTS, ADS_STORE
        SETTINGS = _load_json(SETTINGS_FILE, SETTINGS)
        USERS    = _load_json(USERS_FILE, USERS)
        ORDERS   = _load_json(ORDERS_FILE, ORDERS)
        THOUGHTS = _load_json(THOUGHTS_FILE, THOUGHTS)
        ADS_STORE= _load_json(ADS_FILE, ADS_STORE)
        bot.answer_callback_query(c.id, "Reloaded ✅")

# =========================
# SHOP / PRODUCTS
# =========================
PRODUCTS = {
    # քո 11 գորգերը 그대로 (BA100810..BA100820)
    "BA100810": {
        "title": "Գորգ – BA100810","category":"home",
        "images": [
            "media/products/BA100810.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/absorb.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 320, "best": True,
        "bullets":[
            "Չսահող հիմք՝ անվտանգ քայլք սահուն մակերեսների վրա",
            "Թանձր, փափուկ շերտ՝ հարմարավետ քայլքի զգացողություն",
            "Հեշտ մաքրվում՝ ձեռքով կամ լվացքի մեքենայում մինչև 30°",
            "Գույնի կայունություն՝ չի խամրում և չի թափվում",
        ],
        "long_desc":"Թիթեռ–ծաղիկ 3D դիզայն..."
    },
    "BA100811": {
        "title":"Գորգ – BA100811","category":"home",
        "images":[
            "media/products/BA100811.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/absorb.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price":2560,"price":1690,"size":"40×60 սմ",
        "sold":295,"best":True,
        "bullets":[
            "Խիտ գործվածք՝ երկար ծառայության համար",
            "Անհոտ և անվտանգ նյութեր ողջ ընտանիքի համար",
            "Արագ չորացում՝ խոնավ տարածքներին հարմար",
        ],
        "long_desc":"Մինիմալիստական գույներ..."
    },
    "BA100812": {
        "title":"Գորգ – BA100812","category":"home",
        "images":[
            "media/products/BA100812.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price":2560,"price":1690,"size":"40×60 սմ",
        "sold":241,"best":False,
        "bullets":[
            "Կոկիկ եզրեր՝ պրեմիում տեսք",
            "Ձևը չի փոխում՝ կանոնավոր լվացումից հետո էլ",
        ],
        "long_desc":"Էսթետիկ կոմպոզիցիա՝ նուրբ դետալներով..."
    },
    "BA100813": {
        "title":"Գորգ – BA100813","category":"home",
        "images":[
            "media/products/BA100813.jpg",
            "media/products/shared/absorb.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/interior.jpg",
        ],
        "old_price":2560,"price":1690,"size":"40×60 սմ",
        "sold":198,"best":False,
        "bullets":[
            "Հարմար ծանրաբեռնված անցուղիների համար",
            "Չի ծալվում, չի սահում՝ շնորհիվ հիմքի կառուցվածքի",
        ],
        "long_desc":"Գործնական և դիմացկուն տարբերակ..."
    },
    "BA100814": {
        "title":"Գորգ – BA100814","category":"home",
        "images":[
            "media/products/BA100814.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price":2560,"price":1690,"size":"40×60 սմ",
        "sold":175,"best":False,
        "bullets":[
            "Փափուկ մակերես՝ հաճելի հպում",
            "Գունային կայունություն՝ երկարատև օգտագործման ընթացքում",
        ],
        "long_desc":"Բնական երանգներ՝ հանգիստ միջավայր..."
    },
    "BA100815": {
        "title":"Գորգ – BA100815","category":"home",
        "images":[
            "media/products/BA100815.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price":2560,"price":1690,"size":"40×60 սմ",
        "sold":210,"best":False,
        "bullets":[
            "Խիտ շերտ՝ բարձր դիմացկունություն",
            "Եզրերը չեն փշրվում",
        ],
        "long_desc":"Հարմար է ինչպես բնակարանի, այնպես էլ օֆիսի համար..."
    },
    "BA100816": {
        "title":"Գորգ – BA100816","category":"home",
        "images":[
            "media/products/BA100816.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/absorb.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price":2560,"price":1690,"size":"40×60 սմ",
        "sold":233,"best":False,
        "bullets":[
            "Դեկորատիվ եզրագծեր",
            "Չսահող հիմք՝ առավել անվտանգություն",
        ],
        "long_desc":"Էլեգանտ շեշտադրում ցանկացած ինտերիերում..."
    },
    "BA100817": {
        "title":"Գորգ – BA100817","category":"home",
        "images":[
            "media/products/BA100817.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/interior.jpg",
        ],
        "old_price":2560,"price":1690,"size":"40×60 սմ",
        "sold":221,"best":False,
        "bullets":[
            "Իդեալ է խոհանոցի և մուտքի համար",
            "Արագ չորացում՝ առանց հետքերի",
        ],
        "long_desc":"Գործնական լուծում՝ գեղեցիկ դետալներով..."
    },
    "BA100818": {
        "title":"Գորգ – BA100818","category":"home",
        "images":[
            "media/products/BA100818.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price":2560,"price":1690,"size":"40×60 սմ",
        "sold":187,"best":False,
        "bullets":[
            "Կոմպակտ չափ՝ հեշտ տեղադրում",
            "Թեթև քաշ՝ հարմար տեղափոխել",
        ],
        "long_desc":"Կոկիկ տարբերակ փոքր տարածքների համար..."
    },
    "BA100819": {
        "title":"Գորգ – BA100819","category":"home",
        "images":[
            "media/products/BA100819.jpg",
            "media/products/shared/absorb.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price":2560,"price":1690,"size":"40×60 սմ",
        "sold":205,"best":False,
        "bullets":[
            "Կոկիկ տեսք՝ մաքուր եզրերով",
            "Հակասահող հիմք՝ կայուն դիրք",
        ],
        "long_desc":"Գեղեցիկ լուծում միջանցքի և լոգարանի համար..."
    },
    "BA100820": {
        "title":"Գորգ – BA100820","category":"home",
        "images":[
            "media/products/BA100820.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price":2560,"price":1690,"size":"40×60 սմ",
        "sold":199,"best":False,
        "bullets":[
            "Էսթետիկ կոմպոզիցիա՝ բնական երանգներ",
            "Դիմացկուն հիմք՝ երկար սպասարկում",
        ],
        "long_desc":"Թարմ դիզայն, որը հեշտ է համադրել ցանկացած ինտերիերի հետ..."
    },
}

def codes_by_cat(cat):
    return [k for k, p in PRODUCTS.items() if p.get("category") == cat]

# ============== SHOP MENU
@bot.message_handler(func=lambda m: m.text == BTN_SHOP)
def shop_main(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🏠 Կենցաղային պարագաներ")
    kb.add(BTN_BACK_MAIN)
    bot.send_message(m.chat.id, "🛍 Խանութ — ընտրեք կատեգորիա 👇", reply_markup=kb)

# ============== HOME category cards
@bot.message_handler(func=lambda m: m.text == "🏠 Կենցաղային պարագաներ")
def home_category(m: types.Message):
    codes = codes_by_cat("home")
    sent = 0
    for code in codes:
        p = PRODUCTS[code]
        imgs = p.get("images") or []
        main_img = imgs[0] if imgs else None
        discount = int(round(100 - (p["price"] * 100 / p["old_price"])))
        best = "🔥 Լավագույն վաճառվող\n" if p.get("best") else ""
        caption = (
            f"{best}<b>{p['title']}</b>\n"
            f"Չափս՝ {p['size']}\n"
            f"Հին գին — {p['old_price']}֏ (−{discount}%)\n"
            f"Նոր գին — <b>{p['price']}֏</b>\n"
            f"Կոդ՝ <code>{code}</code>"
        )
        ikb = types.InlineKeyboardMarkup()
        ikb.add(types.InlineKeyboardButton("👀 Դիտել ամբողջությամբ", callback_data=f"p:{code}"))
        try:
            if main_img and os.path.exists(main_img):
                with open(main_img, "rb") as ph:
                    bot.send_photo(m.chat.id, ph, caption=caption, reply_markup=ikb)
            else:
                bot.send_message(m.chat.id, caption, reply_markup=ikb)
        except Exception:
            bot.send_message(m.chat.id, caption, reply_markup=ikb)
        sent += 1
        time.sleep(0.1)

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_BACK_SHOP, BTN_BACK_MAIN)
    bot.send_message(m.chat.id, "📎 Վերևում տեսեք բոլոր քարտիկները։", reply_markup=kb)

# ============== PRODUCT PAGE with SLIDER + CART buttons
def _product_images(code):
    raw = PRODUCTS.get(code, {}).get("images") or []
    return [p for p in raw if os.path.exists(p)]

def _slider_kb(code: str, idx: int, total: int):
    if total <= 0:
        total = 1
    left  = types.InlineKeyboardButton("◀️", callback_data=f"slider:{code}:{(idx-1)%total}")
    right = types.InlineKeyboardButton("▶️", callback_data=f"slider:{code}:{(idx+1)%total}")
    kb = types.InlineKeyboardMarkup()
    kb.row(left, right)
    kb.row(
        types.InlineKeyboardButton("➕ Ավելացնել զամբյուղ", callback_data=f"cart:add:{code}"),
        types.InlineKeyboardButton("🧺 Դիտել զամբյուղ", callback_data="cart:show")
    )
    kb.row(
        types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="go_home")
    )
    return kb

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("p:"))
def on_product(c: types.CallbackQuery):
    code = c.data.split(":", 1)[1]
    p = PRODUCTS.get(code)
    if not p:
        return bot.answer_callback_query(c.id, "Չգտնվեց")
    discount = int(round(100 - (p["price"] * 100 / p["old_price"])))
    bullets = "\n".join([f"✅ {b}" for b in p.get("bullets", [])])
    caption = (
        f"🌸 <b>{p['title']}</b>\n"
        f"✔️ Չափս՝ {p['size']}\n"
        f"{bullets}\n\n"
        f"{p.get('long_desc','')}\n\n"
        f"Հին գին — {p['old_price']}֏ (−{discount}%)\n"
        f"Նոր գին — <b>{p['price']}֏</b>\n"
        f"Վաճառված — {p.get('sold',0)} հատ\n"
        f"Կոդ՝ <code>{code}</code>"
    )
    imgs = _product_images(code)
    try:
        if imgs:
            with open(imgs[0], "rb") as ph:
                bot.send_photo(c.message.chat.id, ph, caption=caption, reply_markup=_slider_kb(code, 0, len(imgs)))
        else:
            bot.send_message(c.message.chat.id, caption, reply_markup=_slider_kb(code, 0, 1))
    except Exception:
        bot.send_message(c.message.chat.id, caption, reply_markup=_slider_kb(code, 0, max(1, len(imgs))))
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("slider:"))
def on_slider(c: types.CallbackQuery):
    try:
        _, code, idx_s = c.data.split(":")
        idx = int(idx_s)
    except:
        return bot.answer_callback_query(c.id)
    p = PRODUCTS.get(code, {})
    discount = int(round(100 - (p.get("price",1) * 100 / p.get("old_price",1))))
    bullets = "\n".join([f"✅ {b}" for b in p.get("bullets", [])])
    caption = (
        f"🌸 <b>{p.get('title','')}</b>\n"
        f"✔️ Չափս՝ {p.get('size','')} \n"
        f"{bullets}\n\n"
        f"{p.get('long_desc','')}\n\n"
        f"Հին գին — {p.get('old_price',0)}֏ (−{discount}%)\n"
        f"Նոր գին — <b>{p.get('price',0)}֏</b>\n"
        f"Վաճառված — {p.get('sold',0)} հատ\n"
        f"Կոդ՝ <code>{code}</code>"
    )
    imgs = _product_images(code)
    total = len(imgs)
    if total == 0:
        # no images: just update caption in a new message
        bot.send_message(c.message.chat.id, caption, reply_markup=_slider_kb(code, 0, 1))
        return bot.answer_callback_query(c.id)
    idx = idx % total
    try:
        with open(imgs[idx], "rb") as ph:
            media = InputMediaPhoto(ph, caption=caption, parse_mode="HTML")
            bot.edit_message_media(media=media,
                                   chat_id=c.message.chat.id,
                                   message_id=c.message.message_id,
                                   reply_markup=_slider_kb(code, idx, total))
    except Exception:
        # fallback – send new photo instead of edit (409 safe)
        with open(imgs[idx], "rb") as ph:
            bot.send_photo(c.message.chat.id, ph, caption=caption, reply_markup=_slider_kb(code, idx, total))
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data in ("back:home_list", "go_home"))
def on_backs(c: types.CallbackQuery):
    if c.data == "back:home_list":
        msg = c.message
        # բացում ենք Home category-ը
        home_category(msg)
    else:
        show_main_menu(c.message.chat.id)
    bot.answer_callback_query(c.id)

# =========================
# CART + CHECKOUT
# =========================
CART = defaultdict(dict)  # uid -> {code: qty}
CHECKOUT_STATE = {}       # uid -> {"step":..., "order":{...}}

def cart_text(uid: int) -> str:
    if not CART[uid]:
        return "🧺 Զամբյուղը դատարկ է"
    total = 0
    lines = []
    for code, qty in CART[uid].items():
        p = PRODUCTS[code]
        sub = p["price"] * qty
        total += sub
        lines.append(f"• {p['title']} × {qty} — {sub}֏")
    lines.append(f"\nԸնդամենը՝ <b>{total}֏</b>")
    return "\n".join(lines)

def cart_total(uid: int) -> int:
    return sum(PRODUCTS[c]["price"] * q for c, q in CART[uid].items())

def check_stock(uid: int):
    for code, qty in CART[uid].items():
        st = PRODUCTS[code].get("stock")
        if isinstance(st, int) and qty > st:
            return False, code, st
    return True, None, None

@bot.message_handler(func=lambda m: m.text == BTN_CART)
def open_cart_from_menu(m: types.Message):
    _send_cart_ui(m.chat.id, m.from_user.id)

def _send_cart_ui(chat_id: int, uid: int):
    ikb = types.InlineKeyboardMarkup()
    for code, qty in list(CART[uid].items())[:6]:
        title = PRODUCTS[code]["title"]
        ikb.row(types.InlineKeyboardButton(f"🛒 {title} ({qty})", callback_data="noop"))
        ikb.row(
            types.InlineKeyboardButton("➖", callback_data=f"cart:dec:{code}"),
            types.InlineKeyboardButton("➕", callback_data=f"cart:inc:{code}"),
            types.InlineKeyboardButton("🗑", callback_data=f"cart:rm:{code}"),
        )
    ikb.row(
        types.InlineKeyboardButton("❌ Մաքրել", callback_data="cart:clear"),
        types.InlineKeyboardButton("🧾 Ճանապարհել պատվեր", callback_data="checkout:start"),
    )
    ikb.row(
        types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="go_home"),
    )
    bot.send_message(chat_id, cart_text(uid), reply_markup=ikb)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("cart:"))
def on_cart_cb(c: types.CallbackQuery):
    uid = c.from_user.id
    parts = c.data.split(":")
    action = parts[1]
    code = parts[2] if len(parts) > 2 else None

    if action == "add" and code:
        st = PRODUCTS[code].get("stock")
        new_q = CART[uid].get(code, 0) + 1
        if isinstance(st, int) and new_q > st:
            return bot.answer_callback_query(c.id, "Պահեստում բավարար քանակ չկա")
        CART[uid][code] = new_q
        bot.answer_callback_query(c.id, "Ավելացվեց ✅")

    elif action == "inc" and code:
        st = PRODUCTS[code].get("stock")
        new_q = CART[uid].get(code, 0) + 1
        if isinstance(st, int) and new_q > st:
            return bot.answer_callback_query(c.id, "Պահեստի սահմանը")
        CART[uid][code] = new_q
        bot.answer_callback_query(c.id)

    elif action == "dec" and code:
        q = CART[uid].get(code, 0)
        if q <= 1:
            CART[uid].pop(code, None)
        else:
            CART[uid][code] = q - 1
        bot.answer_callback_query(c.id)

    elif action == "rm" and code:
        CART[uid].pop(code, None)
        bot.answer_callback_query(c.id)

    elif action == "clear":
        CART[uid].clear()
        bot.answer_callback_query(c.id, "Մաքրվեց")

    if action in ("show","add","inc","dec","rm","clear"):
        _send_cart_ui(c.message.chat.id, uid)

# ===== CHECKOUT FLOW =====
NAME_RE  = re.compile(r"^[A-Za-z\u0531-\u0556\u0561-\u0587ЁёЪъЫыЭэЙй\s'\-\.]{3,60}$")
PHONE_RE = re.compile(r"^(\+374|0)\d{8}$")

COUNTRIES = ["Հայաստան", "Ռուսաստան"]
CITIES = ["Երևան","Գյումրի","Վանաձոր","Աբովյան","Արտաշատ","Արմավիր","Հրազդան","Մասիս","Աշտարակ","Եղվարդ","Չարենցավան"]

def _order_id():
    return "ORD-" + datetime.now().strftime("%Y%m%d-%H%M%S")

@bot.callback_query_handler(func=lambda c: c.data == "checkout:start")
def checkout_start(c: types.CallbackQuery):
    uid = c.from_user.id
    if not CART[uid]:
        bot.answer_callback_query(c.id, "Զամբյուղը դատարկ է")
        return
    ok, code, st = check_stock(uid)
    if not ok:
        bot.answer_callback_query(c.id, "Պահեստում բավարար քանակ չկա")
        bot.send_message(c.message.chat.id, f"⚠️ {PRODUCTS[code]['title']} — հասանելի՝ {st} հատ")
        return

    order_id = _order_id()
    CHECKOUT_STATE[uid] = {
        "step": "name",
        "order": {
            "order_id": order_id,
            "user_id": uid,
            "username": c.from_user.username,
            "fullname": "",
            "phone": "",
            "country": "",
            "city": "",
            "address": "",
            "comment": "",
            "items": [{"code": code, "qty": qty} for code, qty in CART[uid].items()],
            "total": cart_total(uid),
            "status": "Draft",
            "created_at": datetime.utcnow().isoformat()
        }
    }
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(BTN_BACK_MAIN)
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, f"🧾 Պատվեր {order_id}\n✍️ Գրեք ձեր <b>Անուն Ազգանուն</b>:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.from_user.id in CHECKOUT_STATE)
def checkout_flow(m: types.Message):
    uid = m.from_user.id
    st = CHECKOUT_STATE.get(uid)
    if not st:
        return
    step  = st["step"]
    order = st["order"]

    # BACK MAIN
    if m.text == BTN_BACK_MAIN:
        CHECKOUT_STATE.pop(uid, None)
        show_main_menu(m.chat.id, "Վերադարձաք գլխավոր մենյու։")
        return

    if step == "name":
        txt = (m.text or "").strip()
        if not NAME_RE.match(txt):
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            kb.add(BTN_BACK_MAIN)
            return bot.send_message(m.chat.id, "❗ Անուն/Ազգանուն՝ միայն տառերով (3–60).", reply_markup=kb)
        order["fullname"] = txt
        st["step"] = "phone"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(types.KeyboardButton("📱 Ուղարկել կոնտակտ", request_contact=True))
        kb.add(BTN_BACK_MAIN)
        return bot.send_message(m.chat.id, "📞 Մուտք արա հեռախոսահամարը (+374xxxxxxxx կամ 0xxxxxxxx) կամ սեղմիր՝ «📱 Ուղարկել կոնտակտ».", reply_markup=kb)

    if step == "phone":
        phone = None
        if m.contact and m.contact.phone_number:
            phone = m.contact.phone_number.replace(" ", "")
            if not phone.startswith("+"):
                phone = "+" + phone
        else:
            phone = (m.text or "").replace(" ", "")
        if not PHONE_RE.match(phone):
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            kb.add(types.KeyboardButton("📱 Ուղարկել կոնտակտ", request_contact=True))
            kb.add(BTN_BACK_MAIN)
            return bot.send_message(m.chat.id, "❗ Սխալ հեռախոսահամար. օրինակ՝ +374441112233 կամ 0441112233։", reply_markup=kb)
        order["phone"] = phone
        st["step"] = "country"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for ctry in COUNTRIES:
            kb.add(ctry)
        kb.add(BTN_BACK_MAIN)
        return bot.send_message(m.chat.id, "🌍 Ընտրեք երկիրը՝", reply_markup=kb)

    if step == "country":
        if m.text not in COUNTRIES:
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for ctry in COUNTRIES: kb.add(ctry)
            kb.add(BTN_BACK_MAIN)
            return bot.send_message(m.chat.id, "Խնդրում ենք ընտրել առաջարկվող կոճակներից։", reply_markup=kb)
        order["country"] = m.text
        st["step"] = "city"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for i in range(0, len(CITIES), 2):
            row = [types.KeyboardButton(x) for x in CITIES[i:i+2]]
            kb.row(*row)
        kb.add(BTN_BACK_MAIN)
        return bot.send_message(m.chat.id, "🏙️ Ընտրեք քաղաքը՝", reply_markup=kb)

    if step == "city":
        if m.text not in CITIES:
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for i in range(0, len(CITIES), 2):
                kb.row(*[types.KeyboardButton(x) for x in CITIES[i:i+2]])
            kb.add(BTN_BACK_MAIN)
            return bot.send_message(m.chat.id, "Խնդրում ենք ընտրել առաջարկվող քաղաքից։", reply_markup=kb)
        order["city"] = m.text
        st["step"] = "address"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(BTN_BACK_MAIN)
        return bot.send_message(m.chat.id, "🏡 Գրեք հասցեն (փողոց, տուն, մուտք, բնակարան)․", reply_markup=kb)

    if step == "address":
        txt = (m.text or "").strip()
        if len(txt) < 5:
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            kb.add(BTN_BACK_MAIN)
            return bot.send_message(m.chat.id, "❗ Գրեք ավելի մանր հասցե (առնվազն 5 նիշ)։", reply_markup=kb)
        order["address"] = txt
        st["step"] = "comment"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add("—")
        kb.add(BTN_BACK_MAIN)
        return bot.send_message(m.chat.id, "📝 Լրացուցիչ մեկնաբանություն (կամ գրեք «—», եթե չկա)։", reply_markup=kb)

    if step == "comment":
        order["comment"] = "" if (m.text or "").strip() in {"", "—", "-"} else (m.text or "").strip()
        order["status"] = "Pending"
        order["created_at"] = datetime.utcnow().isoformat()
        ORDERS.append(order)
        _save_json(ORDERS_FILE, ORDERS)
        CART[uid].clear()
        CHECKOUT_STATE.pop(uid, None)
        bot.send_message(
            m.chat.id,
            f"✅ Պատվերը գրանցվեց։ Մեր օպերատորը շուտով կկապվի։\nՊատվերի ID: {order['order_id']}",
            reply_markup=types.ReplyKeyboardRemove()
        )
        show_main_menu(m.chat.id)  # ավտոմատ բացում ենք Գլխավոր մենյուն
        return

# =========================
# RATES (օրվա կուրսեր) — թարմացում 10 րոպեանոց թելով
# =========================
def fetch_rates():
    try:
        url = "https://api.exchangerate.host/latest"
        symbols = ["USD", "EUR", "RUB", "GBP", "CNY"]
        r = requests.get(url, params={"base": "AMD", "symbols": ",".join(symbols)}, timeout=10)
        data = r.json()
        raw = data.get("rates", {})
        converted = {}
        for k, v in raw.items():
            if v:
                converted[k] = round(1.0 / v, 4)  # 1 FX = ? AMD
        RATES_CACHE["rates"] = converted
        RATES_CACHE["updated_at"] = datetime.utcnow().isoformat() + "Z"
        RATES_CACHE["error"] = None
        _save_json(RATES_FILE, RATES_CACHE)
    except Exception as e:
        RATES_CACHE["error"] = str(e)
        _save_json(RATES_FILE, RATES_CACHE)

def _rates_thread():
    while True:
        fetch_rates()
        time.sleep(600)

threading.Thread(target=_rates_thread, daemon=True).start()
fetch_rates()

@bot.message_handler(func=lambda m: m.text == BTN_RATES)
def on_rates(m: types.Message):
    cache = _load_json(RATES_FILE, RATES_CACHE)
    err = cache.get("error")
    rates = cache.get("rates", {})
    if err or not rates:
        return bot.send_message(m.chat.id, "❗️Քաշումը ձախողվեց, փորձիր քիչ հետո։")
    flags = {"USD":"🇺🇸","EUR":"🇪🇺","RUB":"🇷🇺","GBP":"🇬🇧","CNY":"🇨🇳"}
    order = ["USD","EUR","RUB","GBP","CNY"]
    lines = ["📈 <b>Օրվա կուրսեր</b> (AMD)", ""]
    for ccy in order:
        if ccy in rates:
            lines.append(f"{flags.get(ccy,'')} 1 {ccy} = <b>{rates[ccy]} AMD</b>")
    lines.append("")
    lines.append(f"🕒 Թարմացվել է (UTC): {cache.get('updated_at','-')}")
    bot.send_message(m.chat.id, "\n".join(lines))

# =========================
# ԽՈՀՈՒՆ ՄՏՔԵՐ (լայթ տարբերակ՝ approve only admin)
# =========================
PENDING_THOUGHT = {}

@bot.message_handler(func=lambda m: m.text == BTN_THOUGHTS)
def thoughts_menu(m: types.Message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Ավելացնել միտք", callback_data="t_add"))
    kb.add(types.InlineKeyboardButton("📚 Դիտել վերջինները", callback_data="t_list"))
    bot.send_message(m.chat.id, "«Խոհուն մտքեր» բաժին ✨", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ("t_add","t_list"))
def on_thoughts_cb(c: types.CallbackQuery):
    if c.data == "t_add":
        PENDING_THOUGHT[c.from_user.id] = True
        bot.answer_callback_query(c.id)
        bot.send_message(c.message.chat.id, "✍️ Ուղարկեք ձեր միտքը (տեքստ)։ Ադմինը պետք է հաստատի։")
    else:
        arr = THOUGHTS or []
        if not arr:
            bot.answer_callback_query(c.id, "Դեռ չկա", show_alert=True); return
        text = "💡 Վերջին մտքեր\n\n" + "\n\n".join(arr[-5:])
        bot.answer_callback_query(c.id)
        bot.send_message(c.message.chat.id, text)

@bot.message_handler(func=lambda m: PENDING_THOUGHT.get(m.from_user.id, False))
def t_collect(m: types.Message):
    PENDING_THOUGHT[m.from_user.id] = False
    txt = (m.text or "").strip()
    if not txt:
        return bot.reply_to(m, "Դատարկ է 🤔")
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Հաստատել", callback_data=f"t_ok::{m.chat.id}"),
        types.InlineKeyboardButton("❌ Մերժել", callback_data=f"t_no::{m.chat.id}")
    )
    bot.send_message(ADMIN_ID, f"Նոր միտք՝\n\n{txt}", reply_markup=kb)
    bot.reply_to(m, "✅ Ուղարկվեց ադմինին հաստատման։")

@bot.callback_query_handler(func=lambda c: c.data.startswith("t_ok::") or c.data.startswith("t_no::"))
def t_moderate(c: types.CallbackQuery):
    if not _is_admin(c.from_user.id):
        return bot.answer_callback_query(c.id, "Միայն ադմին")
    action, chat_id = c.data.split("::", 1)
    chat_id = int(chat_id)
    msg = c.message.text.replace("Նոր միտք՝\n\n", "")
    if action == "t_ok":
        THOUGHTS.append(msg)
        _save_json(THOUGHTS_FILE, THOUGHTS)
        bot.send_message(chat_id, "✅ Քո միտքը հրապարակվեց, շնորհակալ ենք!")
    else:
        bot.send_message(chat_id, "❌ Ադմինը մերժեց այս միտքը։")
    bot.answer_callback_query(c.id, "Կատարված է")

# =========================
# ԳՈՐԾԸՆԿԵՐՆԵՐ
# =========================
@bot.message_handler(func=lambda m: m.text == BTN_PARTNERS)
def on_partners(m: types.Message):
    arr = ADS_STORE or []
    if not arr:
        return bot.send_message(m.chat.id, "Այս պահին գործընկերների հայտարարություններ չկան։")
    lines = ["📢 Բիզնես գործընկերներ\n"]
    for ad in arr[-5:]:
        lines.append(f"🏪 {ad.get('title','')} — {ad.get('desc','')}")
    bot.send_message(m.chat.id, "\n".join(lines))

# =========================
# INVITE FRIENDS
# =========================
@bot.message_handler(func=lambda m: m.text == BTN_INVITE)
def on_invite(m: types.Message):
    link = bot_link_with_ref(m.from_user.id)
    bot.send_message(m.chat.id, f"👥 Կիսվեք բոտով և ստացեք բոնուսներ\n\nՁեր հրավերի հղումը՝\n{link}")

# =========================
# BACK TO SHOP / MAIN via reply keys
# =========================
@bot.message_handler(func=lambda m: m.text == BTN_BACK_MAIN)
def back_main(m: types.Message):
    CHECKOUT_STATE.pop(m.from_user.id, None)
    show_main_menu(m.chat.id, "Վերադարձաք գլխավոր մենյու։")

@bot.message_handler(func=lambda m: m.text == BTN_BACK_SHOP)
def back_shop(m: types.Message):
    shop_main(m)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
