# ========== MAIN.PY — PART 1/8 (INIT + /start + MAIN MENU) ==========
import os, time, re, json, threading, traceback, requests, random
from datetime import datetime
from collections import defaultdict

from telebot import TeleBot, types, apihelper
from telebot.types import InputMediaPhoto
from dotenv import load_dotenv, find_dotenv

# ---------------- ENV & TOKEN ----------------
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"

load_dotenv()
ENV_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
print("dotenv path:", find_dotenv())
print("BOT_TOKEN len:", len(ENV_TOKEN))
if not ENV_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is empty. Put it in your .env")

# ---------------- DIRS ----------------
DATA_DIR = "data"
MEDIA_DIR = "media"
def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(os.path.join(MEDIA_DIR, "products"), exist_ok=True)
    os.makedirs(os.path.join(MEDIA_DIR, "exchange"), exist_ok=True)
ensure_dirs()

# ---------------- BOT ----------------
bot = TeleBot(ENV_TOKEN, parse_mode="HTML")

# ---------------- RUNTIME STORAGE ----------------
CART = defaultdict(dict)      # {user_id: {code: qty}}
CHECKOUT_STATE = {}           # {user_id: {step, order}}
ORDERS = []                   # demo orders

# ---------------- VALIDATION ----------------
NAME_RE  = re.compile(r"^[A-Za-z\u0531-\u0556\u0561-\u0587ЁёЪъЫыЭэЙй\s'\-\.]{3,60}$")
PHONE_RE = re.compile(r"^(\+374|0)\d{8}$")

def _order_id():
    return f"BA{int(time.time()) % 1000000}"

def _cart_total(uid: int) -> int:
    try:
        return sum(int(PRODUCTS[c]["price"]) * q for c, q in CART[uid].items())
    except Exception:
        return 0

def _check_stock(uid: int):
    for code, qty in CART[uid].items():
        st = PRODUCTS.get(code, {}).get("stock")
        if isinstance(st, int) and qty > st:
            return False, code, st
    return True, None, None

# ---------------- MENU LABELS (exactly as you asked) ----------------
BTN_SHOP      = "🛍 Խանութ"
BTN_CART      = "🛒 Զամբյուղ"
BTN_EXCHANGE  = "💱 Փոխարկումներ"
BTN_THOUGHTS  = "💡 Խոհուն մտքեր"
BTN_RATES     = "📊 Օրվա կուրսեր"
BTN_PROFILE   = "🧍 Իմ էջը"
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

# ---------------- WELCOME ----------------
def welcome_text(customer_no: int) -> str:
    return (
        "🐰🌸 <b>Բարի գալուստ StarLegen</b> 🛍✨\n\n"
        "💖 Շնորհակալ ենք, որ միացել եք մեր սիրելի համայնքին ❤️\n"
        f"Դուք այժմ մեր սիրելի հաճախորդն եք №{customer_no} ✨\n\n"
        "Մեր խանութում կարող եք գտնել ամեն օր օգտակար ապրանքների գեղեցիկ և մատչելի առաջարկներ։\n\n"
        "📊 <b>Փոխարժեքի ծառայություններ</b>\n"
        "• PI ➜ USDT (շուկայական կուրս +20% սպասարկում)\n"
        "• FTN ➜ AMD (միայն 10% սպասարկում)\n"
        "• Alipay լիցքավորում (1 CNY = 58֏)\n\n"
        "✨ Ընտրեք բաժինները ներքևում 👇"
    )

# պահենք պարզ՝ counter-ը հիշվող ֆայլով
COUNTER_FILE = os.path.join(DATA_DIR, "counter.json")
def _load_counter():
    if os.path.exists(COUNTER_FILE):
        try:
            return json.load(open(COUNTER_FILE,"r",encoding="utf-8")).get("customer_counter", 1007)
        except:
            return 1007
    return 1007

def _save_counter(v:int):
    try:
        json.dump({"customer_counter": v}, open(COUNTER_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    except:
        pass

customer_counter = _load_counter()

@bot.message_handler(commands=['start'])
def on_start(m: types.Message):
    if getattr(m.chat, "type", "") != "private":
        return

    global customer_counter
    customer_counter += 1
    _save_counter(customer_counter)

    # send bunny image if exists
    bunny_path = os.path.join(MEDIA_DIR, "bunny.jpg")
    if os.path.exists(bunny_path):
        try:
            with open(bunny_path, "rb") as ph:
                bot.send_photo(m.chat.id, ph)
        except:
            pass

    # welcome + menu
    bot.send_message(m.chat.id, welcome_text(customer_counter), reply_markup=main_menu_kb())

@bot.message_handler(commands=['menu'])
def on_menu(m: types.Message):
    show_main_menu(m.chat.id)

# Գլխավորին հետ
@bot.message_handler(func=lambda m: m.text in (BTN_BACK_MAIN, BTN_MAIN))
def back_main_msg(m: types.Message):
    try:
        CHECKOUT_STATE.pop(m.from_user.id, None)
    except:
        pass
    show_main_menu(m.chat.id, "Վերադարձաք գլխավոր մենյու։ ✨")

# Stub handlers so buttons don't feel broken (կաշխատեն իսկականով հաջորդ մասերում)
@bot.message_handler(func=lambda m: m.text == BTN_EXCHANGE)
def stub_exchange(m: types.Message):
    bot.send_message(m.chat.id, "💱 Փոխարկումներ — կավելացնենք հաջորդ մասում։")

@bot.message_handler(func=lambda m: m.text == BTN_THOUGHTS)
def stub_thoughts(m: types.Message):
    bot.send_message(m.chat.id, "💡 Խոհուն մտքեր — կավելացնենք հաջորդ մասում։")

@bot.message_handler(func=lambda m: m.text == BTN_RATES)
def stub_rates(m: types.Message):
    bot.send_message(m.chat.id, "📊 Օրվա կուրսեր — կավելացնենք հաջորդ մասում։")

@bot.message_handler(func=lambda m: m.text == BTN_PROFILE)
def stub_profile(m: types.Message):
    bot.send_message(m.chat.id, "🧍 Իմ էջը — կավելացնենք հաջորդ մասում։")

@bot.message_handler(func=lambda m: m.text == BTN_FEEDBACK)
def stub_feedback(m: types.Message):
    bot.send_message(m.chat.id, "💬 Կապ մեզ հետ — կավելացնենք հաջորդ մասում։")

@bot.message_handler(func=lambda m: m.text == BTN_PARTNERS)
def stub_partners(m: types.Message):
    bot.send_message(m.chat.id, "🤝 Բիզնես գործընկերներ — կավելացնենք հաջորդ մասում։")

@bot.message_handler(func=lambda m: m.text == BTN_SEARCH)
def stub_search(m: types.Message):
    bot.send_message(m.chat.id, "🔍 Ապրանքի որոնում — կավելացնենք հաջորդ մասում։")

@bot.message_handler(func=lambda m: m.text == BTN_INVITE)
def stub_invite(m: types.Message):
    bot.send_message(m.chat.id, "👥 Հրավերի հղումը և referral-ը — կավելացնենք հաջորդ մասում։")
# ---------------- PRODUCTS ----------------
PRODUCTS = {
    "BA100810": {
        "title": "Գորգ – BA100810",
        "price": 1690,
        "old_price": 2560,
        "sold": 325,
        "desc": """✨ Բերեք ձեր տան մեջ նուրբ հմայք այս գեղեցիկ ծաղկային գորգով։
✔️ Չափս՝ 40×60սմ
✔️ Կոմպակտ ու հարմար ցանկացած սենյակի համար
✔️ Հեշտ լվացվող, սայթաքում չի առաջացնում
✔️ Ավելացնում է ջերմություն և թարմություն ինտերիերին""",
        "media": [
            "media/products/BA100810.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg",
        ]
    },
    "BA100811": {
        "title": "Գորգ – BA100811",
        "price": 1690,
        "old_price": 2560,
        "sold": 287,
        "desc": """🌸 Թարմացրեք ինտերիերը այս գեղեցիկ գորգով։
✔️ Չափս՝ 40×60սմ
✔️ Հարմար միջանցքի, ննջասենյակի կամ հյուրասենյակի համար
✔️ Միկրոֆիբրե նյութ՝ հեշտ լվացվող""",
        "media": [
            "media/products/BA100811.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg",
        ]
    },
    "BA100812": {
        "title": "Գորգ – BA100812",
        "price": 1690,
        "old_price": 2560,
        "sold": 310,
        "desc": """🌼 Բարձր որակի գորգ՝ յուրահատուկ դիզայնով։
✔️ Չափս՝ 40×60սմ
✔️ Բնական գույներ, հարմար է բոլոր ինտերիերներին
✔️ Չսահող հիմք՝ ապահով օգտագործման համար""",
        "media": [
            "media/products/BA100812.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg",
        ]
    },
    "BA100813": {
        "title": "Գորգ – BA100813",
        "price": 1690,
        "old_price": 2560,
        "sold": 298,
        "desc": """🌺 Բերեք ջերմություն և հարմարավետություն ձեր սենյակ։
✔️ Չափս՝ 40×60սմ
✔️ Հեշտ մաքրում
✔️ Կլանում է փոշին և կեղտը""",
        "media": [
            "media/products/BA100813.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg",
        ]
    },
    "BA100814": {
        "title": "Գորգ – BA100814",
        "price": 1690,
        "old_price": 2560,
        "sold": 341,
        "desc": """🌿 Բնական գույների գորգ՝ գեղեցիկ դիզայնով։
✔️ Չափս՝ 40×60սմ
✔️ Կլանում է խոնավությունը
✔️ Իդեալական է խոհանոց կամ միջանցք""",
        "media": [
            "media/products/BA100814.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg",
        ]
    },
    "BA100815": {
        "title": "Գորգ – BA100815",
        "price": 1690,
        "old_price": 2560,
        "sold": 260,
        "desc": """🌸 Դարձրեք տունը ավելի հարմարավետ։
✔️ Չափս՝ 40×60սմ
✔️ Դիմացկուն և որակյալ նյութ
✔️ Գեղեցիկ ծաղկային պատկեր""",
        "media": [
            "media/products/BA100815.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg",
        ]
    },
    "BA100816": {
        "title": "Գորգ – BA100816",
        "price": 1690,
        "old_price": 2560,
        "sold": 305,
        "desc": """🌼 Հարմարավետ և գեղեցիկ գորգ՝ տանը ջերմ մթնոլորտի համար։
✔️ Չափս՝ 40×60սմ
✔️ Հեշտ լվացվող
✔️ Չսահող հիմք""",
        "media": [
            "media/products/BA100816.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg",
        ]
    },
    "BA100817": {
        "title": "Գորգ – BA100817",
        "price": 1690,
        "old_price": 2560,
        "sold": 278,
        "desc": """🌺 Տնային հարմարավետության լավագույն ընտրությունը։
✔️ Չափս՝ 40×60սմ
✔️ Բնական գույներ
✔️ Թարմացնում է ինտերիերը""",
        "media": [
            "media/products/BA100817.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg",
        ]
    },
    "BA100818": {
        "title": "Գորգ – BA100818",
        "price": 1690,
        "old_price": 2560,
        "sold": 299,
        "desc": """🌸 Սիրուն դիզայն, որ համապատասխանում է ցանկացած սենյակի։
✔️ Չափս՝ 40×60սմ
✔️ Դիմացկուն նյութ
✔️ Գեղեցիկ ծաղկային պատկեր""",
        "media": [
            "media/products/BA100818.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg",
        ]
    },
    "BA100819": {
        "title": "Գորգ – BA100819",
        "price": 1690,
        "old_price": 2560,
        "sold": 320,
        "desc": """🌼 Գեղեցիկ և որակյալ գորգ՝ ձեր տան հարմարավետության համար։
✔️ Չափս՝ 40×60սմ
✔️ Հեշտ լվացվող
✔️ Ավելացնում է ջերմություն""",
        "media": [
            "media/products/BA100819.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg",
        ]
    },
    "BA100820": {
        "title": "Գորգ – BA100820",
        "price": 1690,
        "old_price": 2560,
        "sold": 289,
        "desc": """🌺 Հարմարավետ և գեղեցիկ գորգ, որը դարձնում է տունը յուրահատուկ։
✔️ Չափս՝ 40×60սմ
✔️ Դիմացկուն նյութ
✔️ Սահող չի, հեշտ մաքրվում է""",
        "media": [
            "media/products/BA100820.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg",
        ]
    },
    "CAR001": {
        "title": "Ավտոմաքրող սպունգ – CAR001",
        "price": 3580,
        "old_price": 6480,
        "sold": 212,
        "desc": """🚗 Պահպանիր մեքենադ մաքուր ու փայլուն՝ մեր նորարարական ավտոմաքրիչով։
✔️ Հեշտ մաքրում՝ առանց քիմիական նյութերի
✔️ Դիմացկուն և բազմակի օգտագործման
✔️ Սպունգ + հեղուկ պահեստի հարմարավետություն""",
        "media": [
            "media/products/car_cleaner/CAR001_1.jpg",
            "media/products/car_cleaner/CAR001_2.jpg",
            "media/products/car_cleaner/CAR001_3.jpg",
            "media/products/car_cleaner/CAR001_4.jpg",
            "media/products/car_cleaner/CAR001_5.jpg",
            "media/products/car_cleaner/video.mp4",
        ]
    }
}

# ---------------- CATEGORIES ----------------
CATEGORIES = {
    "household": {
        "title": "🏡 Կենցաղային պարագաներ",
        "products": [
            "BA100810","BA100811","BA100812","BA100813","BA100814",
            "BA100815","BA100816","BA100817","BA100818","BA100819","BA100820"
        ]
    },
    "auto": {
        "title": "🚗 Ավտոմեքենաների պարագաներ",
        "products": ["CAR001"]
    }
}

# ---------------- CATEGORIES MENU ----------------
def categories_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for key, cat in CATEGORIES.items():
        kb.add(cat["title"])
    kb.add(BTN_BACK_MAIN, BTN_MAIN)
    return kb

@bot.message_handler(func=lambda m: m.text == BTN_SHOP)
def shop_menu(m: types.Message):
    bot.send_message(m.chat.id, "🛍 Ընտրեք կատեգորիա", reply_markup=categories_kb())

def _cat_key_by_title(title: str):
    for k, c in CATEGORIES.items():
        if c["title"] == title:
            return k
    return None

# ---------------- PREVIEW (միայն գլխավոր նկար + կոճակ) ----------------
def _first_image_path(p: dict) -> str:
    for path in p["media"]:
        if not path.lower().endswith(".mp4"):
            return path
    return None

def _preview_kb(code: str, cat_key: str):
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("🔎 Դիտել մանրամասն", callback_data=f"view|{code}|0|{cat_key}"))
    ikb.add(
        types.InlineKeyboardButton("⬅️ Վերադառնալ", callback_data=f"backcat|{cat_key}"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="mainmenu")
    )
    return ikb

def send_preview(chat_id: int, code: str, cat_key: str):
    p = PRODUCTS[code]
    cover = _first_image_path(p)
    caption = f"<b>{p['title']}</b>\n💵 {p['price']}֏   <s>{p['old_price']}֏</s>\n👉 Սեղմեք «Դիտել մանրամասն»"
    if cover and os.path.exists(cover):
        with open(cover, "rb") as ph:
            bot.send_photo(chat_id, ph, caption=caption, parse_mode="HTML", reply_markup=_preview_kb(code, cat_key))
    else:
        bot.send_message(chat_id, caption, reply_markup=_preview_kb(code, cat_key), parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text in [c["title"] for c in CATEGORIES.values()])
def on_category(m: types.Message):
    cat_key = _cat_key_by_title(m.text)
    if not cat_key:
        return
    CHECKOUT_STATE.pop(m.from_user.id, None)

    bot.send_message(m.chat.id, f"{CATEGORIES[cat_key]['title']}\n— ընտրեք ապրանքը պատկերից։")
    for code in CATEGORIES[cat_key]["products"]:
        send_preview(m.chat.id, code, cat_key)

# ---------------- PRODUCT SLIDER ----------------
def product_caption(p: dict, idx: int) -> str:
    total_imgs = sum(1 for x in p["media"] if not x.lower().endswith(".mp4"))
    page = f"\n\n🖼 Նկար {idx+1}/{total_imgs}" if total_imgs else ""
    return (
        f"<b>{p['title']}</b>\n\n{p['desc']}\n\n"
        f"Հին գին — {p['old_price']}֏ (−34%)\n"
        f"Նոր գին — {p['price']}֏\n"
        f"Վաճառված՝ {p['sold']} հատ{page}"
    )

def _images_only(media_list):
    return [p for p in media_list if not p.lower().endswith(".mp4")]

def _has_video(media_list):
    return any(p.lower().endswith(".mp4") for p in media_list)

def _slider_kb(code: str, idx: int, cat_key: str, has_video: bool):
    ikb = types.InlineKeyboardMarkup()
    row = []
    row.append(types.InlineKeyboardButton("⬅️ Նախորդ", callback_data=f"prev|{code}|{idx}|{cat_key}"))
    row.append(types.InlineKeyboardButton("➡️ Հաջորդ", callback_data=f"next|{code}|{idx}|{cat_key}"))
    ikb.row(*row)
    if has_video:
        ikb.add(types.InlineKeyboardButton("▶️ Տեսանյութ", callback_data=f"video|{code}|{cat_key}"))
    ikb.add(types.InlineKeyboardButton("🛒 Ավելացնել զամբյուղ", callback_data=f"add|{code}|{cat_key}|{idx}"))
    ikb.add(
        types.InlineKeyboardButton("⬅️ Վերադառնալ կատեգորիա", callback_data=f"backcat|{cat_key}"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="mainmenu"),
    )
    return ikb

def _edit_photo(call, code: str, idx: int, cat_key: str):
    p = PRODUCTS[code]
    imgs = _images_only(p["media"])
    if not imgs:
        bot.answer_callback_query(call.id, "Նկար չի գտնվել")
        return
    total = len(imgs)
    idx = (idx + total) % total
    with open(imgs[idx], "rb") as ph:
        media = types.InputMediaPhoto(ph, caption=product_caption(p, idx), parse_mode="HTML")
        try:
            bot.edit_message_media(
                media=media,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=_slider_kb(code, idx, cat_key, _has_video(p["media"]))
            )
        except Exception:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_photo(call.message.chat.id, open(imgs[idx], "rb"),
                           caption=product_caption(p, idx), parse_mode="HTML",
                           reply_markup=_slider_kb(code, idx, cat_key, _has_video(p["media"])))
    return idx

@bot.callback_query_handler(func=lambda c: c.data.startswith("view|"))
def cb_view(call: types.CallbackQuery):
    _, code, idx, cat_key = call.data.split("|")
    idx = int(idx)
    _edit_photo(call, code, idx, cat_key)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("next|"))
def cb_next(call: types.CallbackQuery):
    _, code, idx, cat_key = call.data.split("|")
    idx = int(idx) + 1
    _edit_photo(call, code, idx, cat_key)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("prev|"))
def cb_prev(call: types.CallbackQuery):
    _, code, idx, cat_key = call.data.split("|")
    idx = int(idx) - 1
    _edit_photo(call, code, idx, cat_key)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("video|"))
def cb_video(call: types.CallbackQuery):
    _, code, cat_key = call.data.split("|")
    p = PRODUCTS[code]
    vids = [v for v in p["media"] if v.lower().endswith(".mp4")]
    if vids and os.path.exists(vids[0]):
        with open(vids[0], "rb") as vf:
            bot.send_video(call.message.chat.id, vf, caption=f"{p['title']} — տեսանյութ")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("add|"))
def cb_add_cart(call: types.CallbackQuery):
    _, code, cat_key, idx = call.data.split("|")
    uid = call.from_user.id
    CART[uid][code] = CART[uid].get(code, 0) + 1
    bot.answer_callback_query(call.id, text="Ավելացվեց զամբյուղ 🛒", show_alert=False)

@bot.callback_query_handler(func=lambda c: c.data == "mainmenu")
def cb_main_menu(call: types.CallbackQuery):
    show_main_menu(call.message.chat.id, "🏠 Գլխավոր մենյու")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("backcat|"))
def cb_back_cat(call: types.CallbackQuery):
    _, cat_key = call.data.split("|")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, f"{CATEGORIES[cat_key]['title']}\n— ընտրեք ապրանքը պատկերից։",
                     reply_markup=categories_kb())
    for code in CATEGORIES[cat_key]["products"]:
        send_preview(call.message.chat.id, code, cat_key)
    bot.answer_callback_query(call.id)

# ========== RUN ==========
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
# ========== END OF PART 1/8 ==========
