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
# =============== SHOP / CATEGORIES / PRODUCTS (FULL) ===============
# Կատեգորիաների ցուցակ (ցուցադրվում է «🛍 Խանութ»-ում)
CATEGORIES = {
    "rugs":        "🌸 Գորգեր (ծաղիկ)",
    "car_access":  "🚗 Ավտոմեքենայի պարագաներ",
    "smartwatch":  "⌚️ Սմարթ ժամացույցներ (Շուտով)",
    "pc_access":   "💻 Համակարգչային աքսեսուարներ (Շուտով)",
    "household":   "🏠 Կենցաղային պարագաներ (Շուտով)",
    "kitchen":     "🍳 Խոհանոցային տեխնիկա (Շուտով)",
    "care":        "🧴 Խնամքի պարագաներ (Շուտով)",
    "ecig":        "💨 Էլեկտրոնային ծխախոտ (Շուտով)",
    "women":       "👩 Կանացի (Շուտով)",
    "men":         "👨 Տղամարդու (Շուտով)",
    "kids":        "🧒 Մանկական (Շուտով)"
}

# Ընդհանուր նկարագրության հիմք՝ գորգերի համար
def _rug_desc(extra_line: str) -> str:
    return (
        "✔️ Թավշյա փափուկ մակերես՝ հաճելի քայլքի համար\n"
        "✔️ Հակասահ հիմք՝ ապահով կպչում հատակին\n"
        "✔️ Հեշտ մաքրում՝ փոշեկուլ/նուրբ լվացում 30°֊ում\n"
        "✔️ Չի գունաթափվում, չի փոքրանում լվացումից հետո\n"
        "✔️ Հարմար է միջանցք, խոհանոց, սանհանգույց, ննջարան\n"
        "✔️ Ընտանիքներին և երեխաներին հարմար, հիգիենիկ\n"
        "✔️ Թեթև և ծալվող՝ պահեստավորումը հեշտ է\n"
        f"✔️ {extra_line}\n"
        "✔️ Չափս՝ 40×60սմ\n"
        "✔️ Գին/որակ լավագույն հարաբերակցություն\n"
    )

PRODUCTS = {
    # -------------------- ԳՈՐԳԵՐ — BA100810…BA100820 --------------------
    "BA100810": {
        "cat": "rugs",
        "title": "Գորգ – BA100810 (40×60սմ)",
        "price": 1690, "old_price": 2560,
        "img": "media/products/BA100810.jpg",
        "stock": 50, "sold": 198,
        "desc": _rug_desc("Էլեգանտ ծաղկային դիզայն՝ նուրբ սերուցքային երանգներով") + "Կոդ՝ BA100810"
    },
    "BA100811": {
        "cat": "rugs",
        "title": "Գորգ – BA100811 (40×60սմ)",
        "price": 1690, "old_price": 2560,
        "img": "media/products/BA100811.jpg",
        "stock": 50, "sold": 202,
        "desc": _rug_desc("Տաք բեժ-շոկոլադ երանգավորում՝ սենյակին հարմարավետ շունչ") + "Կոդ՝ BA100811"
    },
    "BA100812": {
        "cat": "rugs",
        "title": "Գորգ – BA100812 (40×60սմ)",
        "price": 1690, "old_price": 2560,
        "img": "media/products/BA100812.jpg",
        "stock": 50, "sold": 215,
        "desc": _rug_desc("Բեկորային թիթեռնիկ-ծաղիկ կոմպոզիցիա՝ ժամանակակից ինտերիերի համար") + "Կոդ՝ BA100812"
    },
    "BA100813": {
        "cat": "rugs",
        "title": "Գորգ – BA100813 (40×60սմ)",
        "price": 1690, "old_price": 2560,
        "img": "media/products/BA100813.jpg",
        "stock": 50, "sold": 207,
        "desc": _rug_desc("Նուրբ վանիլ-սև կոնտրաստ՝ տեսքի մաքրություն և ճաշակ") + "Կոդ՝ BA100813"
    },
    "BA100814": {
        "cat": "rugs",
        "title": "Գորգ – BA100814 (40×60սմ)",
        "price": 1690, "old_price": 2560,
        "img": "media/products/BA100814.jpg",
        "stock": 50, "sold": 190,
        "desc": _rug_desc("Փափուկ պաստելային գույներ՝ ջերմ ինտերիերի սիրահարների համար") + "Կոդ՝ BA100814"
    },
    "BA100815": {
        "cat": "rugs",
        "title": "Գորգ – BA100815 (40×60սմ)",
        "price": 1690, "old_price": 2560,
        "img": "media/products/BA100815.jpg",
        "stock": 50, "sold": 199,
        "desc": _rug_desc("Թեթև փայլատ մակերես՝ ժամանակակից մինիմալիստական ոճին") + "Կոդ՝ BA100815"
    },
    "BA100816": {
        "cat": "rugs",
        "title": "Գորգ – BA100816 (40×60սմ)",
        "price": 1690, "old_price": 2560,
        "img": "media/products/BA100816.jpg",
        "stock": 50, "sold": 221,
        "desc": _rug_desc("Արևոտ երանգներով դիզայն՝ բարձրացնում է տրամադրությունը") + "Կոդ՝ BA100816"
    },
    "BA100817": {
        "cat": "rugs",
        "title": "Գորգ – BA100817 (40×60սմ)",
        "price": 1690, "old_price": 2560,
        "img": "media/products/BA100817.jpg",
        "stock": 50, "sold": 213,
        "desc": _rug_desc("Դեկորատիվ ծաղկաթերթեր՝ դառնում է սենյակի առանցքային ակցենտ") + "Կոդ՝ BA100817"
    },
    "BA100818": {
        "cat": "rugs",
        "title": "Գորգ – BA100818 (40×60սմ)",
        "price": 1690, "old_price": 2560,
        "img": "media/products/BA100818.jpg",
        "stock": 50, "sold": 205,
        "desc": _rug_desc("Շքեղ ֆլորալ կոմպոզիցիա՝ մոդեռն ինտերիերների համար") + "Կոդ՝ BA100818"
    },
    "BA100819": {
        "cat": "rugs",
        "title": "Գորգ – BA100819 (40×60սմ)",
        "price": 1690, "old_price": 2560,
        "img": "media/products/BA100819.jpg",
        "stock": 50, "sold": 208,
        "desc": _rug_desc("Մեղմ ու հարթ մակերես՝ հեշտ խնամք և երկար ծառայություն") + "Կոդ՝ BA100819"
    },
    "BA100820": {
        "cat": "rugs",
        "title": "Գորգ – BA100820 (40×60սմ)",
        "price": 1690, "old_price": 2560,
        "img": "media/products/BA100820.jpg",
        "stock": 50, "sold": 199,
        "desc": _rug_desc("Էսթետիկ տեսք՝ համադրվում է տարբեր գունային լուծումների հետ") + "Կոդ՝ BA100820"
    },

    # -------------------- Ավտոմեքենայի պարագաներ --------------------
    "CAR001": {
        "cat": "car_access",  # ← ՓՈԽԵՑԻՆՔ՝ auto → car_access
        "title": "Հուլդուի/Յուղային փայլի մաքրիչ (ակնթարթային)",
        "price": 3580, "old_price": 6480,
        "img": "media/products/CAR001.jpg",
        "stock": 30, "sold": 120,
        "desc": (
            "✔️ Հեռացնում է յուղային թաղանթը և փայլը ապակուց\n"
            "✔️ Թափանցիկություն՝ 1 րոպեում, ավելի անվտանգ վարում\n"
            "✔️ Հիդրոֆոբ էֆեկտ՝ կաթիլները սահում են անձրևին\n"
            "✔️ Նվազեցնում է լուսարձակների շողարձակումը գիշերը\n"
            "✔️ Չի վնասում ապակին, չի թողնում հետքեր\n"
            "✔️ Թեթև հոտ, անվտանգ ֆորմուլա\n"
            "✔️ Սրբիչ/սպունգով՝ շրջանաձև շարժումներով կիրառեք\n"
            "✔️ Առաջարկվող հաճախականություն՝ շաբաթը 1 անգամ\n"
            "✔️ Խնայողություն՝ մեկ շիշը բավարար է ամիսներով\n"
            "✔️ Կոդ՝ CAR001"
        )
    }
}
# ============================================================
# ========= SHOP ENTRY =========
@bot.message_handler(func=lambda m: m.text == "🛍 Խանութ")
def shop_entry(m: types.Message):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for cid, label in CATEGORIES.items():
        kb.add(types.InlineKeyboardButton(label, callback_data=f"shop:cat:{cid}"))
    kb.add(types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="shop:home"))
    bot.send_message(m.chat.id, "🛍 Խանութ — Ընտրեք կատեգորիան 👇", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "shop:home")
def shop_home(c: types.CallbackQuery):
    bot.answer_callback_query(c.id)
    show_main_menu(c.message.chat.id)
def _product_caption(p: dict, code: str) -> str:
    title = p.get("title", "")
    old_p = p.get("old_price")
    new_p = p.get("price")
    sold  = p.get("sold", 0)
    desc  = p.get("desc", "")
    cap = (
        f"**{title}**\n\n"
        f"{desc}\n\n"
    )
    if old_p:
        cap += f"Հին գին — {old_p}֏  (−{int((old_p - new_p) * 100 / old_p)}%)\n"
    cap += f"Նոր գին — {new_p}֏\nՎաճառված — {sold} հատ"
    # Եթե չեք ուզում կոդը երևա, հանեք հաջորդ տողը
    cap += f"\nԿոդ՝ {code}"
    return cap

def send_product_card(chat_id: int, code: str):
    p = PRODUCTS.get(code, {})
    img = p.get("img")
    cap = _product_caption(p, code)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("➕ Ավելացնել զամբյուղ", callback_data=f"cart:add:{code}"),
        types.InlineKeyboardButton("🧺 Դիտել զամբյուղ", callback_data="cart:show")
    )
    kb.add(
        types.InlineKeyboardButton("🏬 Վերադառնալ խանութ", callback_data="shop:back"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="shop:home"),
    )
    try:
        with open(img, "rb") as ph:
            bot.send_photo(chat_id, ph, caption=cap, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        bot.send_message(chat_id, cap, reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("shop:cat:"))
def open_category(c: types.CallbackQuery):
    cid = c.data.split(":")[2]
    bot.answer_callback_query(c.id)
    # հավաքում ենք կատեգորիայի ապրանքները
    codes = [code for code, p in PRODUCTS.items() if p.get("cat") == cid]
    if not codes:
        bot.send_message(c.message.chat.id, "Այս բաժնում ապրանք դեռ չկա։")
        return
    bot.send_message(c.message.chat.id, f"📦 {CATEGORIES.get(cid, 'Կատեգորիա')} — ապրանքներ՝")
    for code in codes:
        send_product_card(c.message.chat.id, code)

@bot.callback_query_handler(func=lambda c: c.data == "shop:back")
def shop_back(c: types.CallbackQuery):
    bot.answer_callback_query(c.id)
    # նորից ցույց ենք տալիս կատեգորիաների ցանկը
    kb = types.InlineKeyboardMarkup(row_width=1)
    for cid, label in CATEGORIES.items():
        kb.add(types.InlineKeyboardButton(label, callback_data=f"shop:cat:{cid}"))
    kb.add(types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="shop:home"))
    bot.send_message(c.message.chat.id, "🔙 Վերադարձ դեպի խանութի բաժինները", reply_markup=kb)

# ========== RUN ==========
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
# ========== END OF PART 1/8 ==========
