# ========== MAIN.PY — PART 1/8 (INIT + /start + MAIN MENU) ==========
import os, time, re, json, threading, traceback, requests, random
from datetime import datetime
from collections import defaultdict
from types import SimpleNamespace as SNS

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
# ---------------- PRODUCTS (11 գորգ + ավտո) ----------------
PRODUCTS = {
    "BA100810": {
        "title": "Գորգ – BA100810",
        "price": 1690, "old_price": 2560, "sold": 325,
        "desc": """🌼 Բերեք թարմություն ու հարմարավետություն տուն.
• Չափսը՝ 40×60 սմ
• Միկրոֆիբրե փափուկ մակերես
• Չսահող հիմք՝ անվտանգ քայլք
• Արագ կլանում է ջուրը
• Հեշտ լվացվող՝ մեքենայով/ձեռքով
• Չի կորցնում գույնը հաճախական լվացումից
• Հարմար միջանցք, խոհանոց, լոգասենյակ
• Բնական, հանգիստ գույներ
• Հարմար նվերի համար էլ
• Օրիգինալ փաթեթավորմամբ
""",
        "media": [
            "media/products/BA100810.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg"
        ]
    },
    "BA100811": {
        "title": "Գորգ – BA100811",
        "price": 1690, "old_price": 2560, "sold": 287,
        "desc": """🌸 Մինիմալիստական ձևավորում՝ ջերմ ինտերիերի համար.
• Չափս՝ 40×60 սմ
• Սուպեր փափուկ ու դարբնված կառուցվածք
• Սայթաքում չի՝ հակասահող հիմք
• Ափսորբցում է խոնավությունը վայրկյաններում
• Հարմար մուտքի, ննջասենյակի, լոգասենյակի
• Չի մաշվում եզրերից
• Հեշտ մաքրում՝ փոշեկուլ/լվացում
• Չի դեֆորմացվում չորացումից
• Էկո նյութեր՝ անվտանգ երեխաների համար
• Օգտագործման երկար ժամկետ
""",
        "media": [
            "media/products/BA100811.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg"
        ]
    },
    "BA100812": {
        "title": "Գորգ – BA100812",
        "price": 1690, "old_price": 2560, "sold": 310,
        "desc": """🌿 Բնական երանգներ՝ հանգստացնող մթնոլորտի համար.
• 40×60 սմ կոմպակտ չափ
• Խիտ մանրաթել՝ հրաշալի ներծծում
• Չսահող հիմք՝ սալիկ/լամինատ/պարկետ
• Չի թողնում հետք հատակի վրա
• Մեքենայով լվացվող՝ 30°C
• Շուտ չորացող հյուսք
• Դիմացկուն կարում եզրերին
• Հարմար է կենդանիներ ունեցող տների համար
• Կարելի է օգտագործել նաև որպես նստատեղ
• Տևական որակ, լավ գին
""",
        "media": [
            "media/products/BA100812.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg"
        ]
    },
    "BA100813": {
        "title": "Գորգ – BA100813",
        "price": 1690, "old_price": 2560, "sold": 298,
        "desc": """✨ Գեղեցիկ դիզայն՝ առաջին հայացքից սիրվելու.
• Չափս՝ 40×60 սմ
• Միկրոֆիբրա՝ մաշկին հաճելի
• Կլանում է փոշին ու կեղտը
• Չի սահում, չի ծալվում եզրերից
• Լվացվում է առանց գույն կորցնելու
• Հարմար միջանցքների համար
• Տաքություն է հաղորդում սենյակին
• Ոչ ալերգեն նյութ
• Նուրբ հարդարանքով վերևի շերտ
• Տնային ամենօրյա օգտագործման համար
""",
        "media": [
            "media/products/BA100813.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg"
        ]
    },
    "BA100814": {
        "title": "Գորգ – BA100814",
        "price": 1690, "old_price": 2560, "sold": 341,
        "desc": """🌼 Թեթև, շնչող և պրակտիկ գորգ ամենօրյա վարելու համար.
• 40×60 սմ՝ կոմպակտ
• Կլանում է ջուրը՝ ոտքերը չոր
• Հակասահող հիմք՝ պահում է տեղում
• Չի պահանջում հատուկ խնամք
• Մաշվածակայուն թելեր
• Լավ համադրվում է բաց գույների հետ
• Կոկիկ եզրային կարեր
• Չի բարակում լվացումից
• Ընտիր գին/որակ հարաբերակցություն
• Պատրաստ օգտագործման՝ առանց հոտերի
""",
        "media": [
            "media/products/BA100814.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg"
        ]
    },
    "BA100815": {
        "title": "Գորգ – BA100815",
        "price": 1690, "old_price": 2560, "sold": 260,
        "desc": """🌸 Փափուկ շուռկա՝ հաճելի քայլքի զգացողության համար.
• Չափս՝ 40×60 սմ
• Թավշյա շոշափելիք
• Ջրի արագ ներծծում
• Սահելուց պաշտպանող հիմք
• Հարմար է լոգասենյակ/բալկոն/մուտք
• Հեշտ լվացվող, շուտ չորացող
• Չի հավաքում հոտեր
• Չի գունաթափվում արևից
• Ժամանակակից, սիրուն նախշ
• Պատրաստ նվերի համար
""",
        "media": [
            "media/products/BA100815.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg"
        ]
    },
    "BA100816": {
        "title": "Գորգ – BA100816",
        "price": 1690, "old_price": 2560, "sold": 305,
        "desc": """🍃 Ֆունկցիոնալ գորգ՝ մաքուր տան սիմվոլ.
• 40×60 սմ
• Բարձր խտությամբ մանրաթել
• Մաքրում է կոշիկի մնացորդային փոշին
• Չի սահում՝ վստահ քայլք
• Կարելի է լվանալ 30°C ջրում
• Չի կորցնում ձևը
• Իրական դրամաչափ՝ նկարին՝ նույն գույնը
• Նուրբ կարված եզրեր
• Հարմար ընտանի կենդանիների հետ
• Օգտակար ամեն օր
""",
        "media": [
            "media/products/BA100816.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg"
        ]
    },
    "BA100817": {
        "title": "Գորգ – BA100817",
        "price": 1690, "old_price": 2560, "sold": 278,
        "desc": """✨ Ժամանակակից գույնի համադրություն՝ բոլոր ինտերիերների համար.
• 40×60 սմ չափ
• Միկրոֆիբրա՝ փափուկ շոշափելիք
• Չսահող հիմք՝ EVA
• Կլանում է խոնավությունը ու արագ չորանում
• Դիմացկուն հյուսք՝ երկար կյանք
• Հեշտ խնամք՝ փոշեկուլ/քսուք/լվացում
• Չի թողնում մազիկներ
• Նուրբ գունային փոխանցում
• Ընտիր տարբերակ նվերի
• Արժեքավոր գնում
""",
        "media": [
            "media/products/BA100817.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg"
        ]
    },
    "BA100818": {
        "title": "Գորգ – BA100818",
        "price": 1690, "old_price": 2560, "sold": 299,
        "desc": """🌺 Ընթերցասենյակ, ննջասենյակ, խոհանոց — հավասար հարմար.
• 40×60 սմ
• Չի սահում, չի ծալվում
• Ջրի ներծծման բարձր մակարդակ
• Չի գունաթափվում լվացումից
• Կոկիկ եզրագծային կարեր
• Շունչը չի փակում հատակին
• Փոշոտ միջավայրում էլ լավ է պահում իրեն
• Բարեկարգ տեսք երկար ժամանակ
• Մաքրվում է մեկ շարժումով
• Գին՝ որակ հավասարակշռությամբ
""",
        "media": [
            "media/products/BA100818.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg"
        ]
    },
    "BA100819": {
        "title": "Գորգ – BA100819",
        "price": 1690, "old_price": 2560, "sold": 320,
        "desc": """🌼 Գործնական և գեղեցիկ՝ տան հարմարավետության համար.
• Չափս՝ 40×60 սմ
• Փափուկ, բարձրակշիռ հպում
• Հակասահող հիմք՝ EVA
• Իդեալական է լոգարանից դուրս
• Հեշտ խնամք՝ ջուր/օճառ
• Արագ չորացում՝ րոպեների ընթացքում
• Չի մնում հոտ
• Հարմար փոքրիկների համար
• Հիանալի ընտրություն ամեն օր
• Սիրված մոդել մեր հաճախորդների կողմից
""",
        "media": [
            "media/products/BA100819.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg"
        ]
    },
    "BA100820": {
        "title": "Գորգ – BA100820",
        "price": 1690, "old_price": 2560, "sold": 289,
        "desc": """🌸 Սիրուն նախշերով գորգ՝ հարմար ցանկացած ոճի համար.
• 40×60 սմ
• Միկրոֆիբրե բուրդանման շերտ
• Սահելը բացառված է
• Կլանում է ջուրը ու կեղտը
• Պահպանում է գույները երկար
• Լվացվող մեքենայով՝ առանց ձևի կորուստի
• Հարմար նաև մուտքի հատվածում
• Տաք ու հաճելի ոտքերին
• Նուրբ ավարտում եզրերին
• Գնում, որից չես զղջա
""",
        "media": [
            "media/products/BA100820.jpg",
            "media/products/shared/advantages.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/absorb.jpg"
        ]
    },

    "CAR001": {
        "title": "Ավտոմաքրող սպունգ – CAR001",
        "price": 3580, "old_price": 6480, "sold": 212,
        "desc": """🚗 Մաքուր մեքենա՝ առանց ջանքի.
• Խելացի կոնստրուկցիա՝ հեղուկի պահեստով
• Հեշտ մաքրում՝ առանց քիմիական նյութերի
• Չի քերում լաքը, չի թողնում հետք
• Դիմացկուն սպունգ՝ բազմակի օգտագործման
• Հարմար սալոն/թափք/ապակի
• Էրգոնոմիկ բռնակ՝ չես հոգնում
• Արագ լվացում և չորացում
• Կարելի է օգտագործել տնային մակերեսների վրա
• Տեսանյութը՝ «Տեսանյութ» կոճակով
• Պարզ, պրոֆեսիոնալ արդյունք
""",
        "media": [
            "media/products/car_cleaner/CAR001_1.jpg",
            "media/products/car_cleaner/CAR001_2.jpg",
            "media/products/car_cleaner/CAR001_3.jpg",
            "media/products/car_cleaner/CAR001_4.jpg",
            "media/products/car_cleaner/CAR001_5.jpg",
            "media/products/car_cleaner/video.mp4"
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
        "title": "🚗 Ավտոմեքենայի պարագաներ",
        "products": ["CAR001"]
    }
}
# ---------------- CATEGORIES MENU (Reply Keyboard) ----------------
def categories_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(CATEGORIES["household"]["title"], CATEGORIES["auto"]["title"])
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

# ---------------- PREVIEW (միայն գլխավոր նկար + «Դիտել մանրամասն») ----------------
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

# ---------------- PRODUCT SLIDER (⬅️/➡️ + ▶️ + 🛒 + Վերադարձ) ----------------
def product_caption(p: dict, idx: int) -> str:
    total_imgs = sum(1 for x in p["media"] if not x.lower().endswith(".mp4"))
    page = f"\n\n🖼 Նկար {idx+1}/{total_imgs}" if total_imgs else ""
    return (
        f"<b>{p['title']}</b>\n\n{p['desc']}\n"
        f"— Հին գին՝ {p['old_price']}֏ (−34%)\n"
        f"— Նոր գին՝ {p['price']}֏\n"
        f"— Վաճառված՝ {p['sold']} հատ{page}"
    )

def _images_only(media_list):
    return [p for p in media_list if not p.lower().endswith(".mp4")]

def _has_video(media_list):
    return any(p.lower().endswith(".mp4") for p in media_list)

def _slider_kb(code: str, idx: int, cat_key: str, has_video: bool):
    ikb = types.InlineKeyboardMarkup()
    ikb.row(
        types.InlineKeyboardButton("⬅️ Նախորդ", callback_data=f"prev|{code}|{idx}|{cat_key}"),
        types.InlineKeyboardButton("➡️ Հաջորդ", callback_data=f"next|{code}|{idx}|{cat_key}")
    )
    if has_video:
        ikb.add(types.InlineKeyboardButton("▶️ Տեսանյութ", callback_data=f"video|{code}|{cat_key}"))
    ikb.add(types.InlineKeyboardButton("🛒 Ավելացնել զամբյուղ", callback_data=f"add|{code}|{cat_key}|{idx}"))
    ikb.row(
        types.InlineKeyboardButton("⬅️ Վերադառնալ կատեգորիա", callback_data=f"backcat|{cat_key}"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="mainmenu")
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
            # Եթե հեռացրած/չփոփոխվող հաղորդագրություն է, ուղարկում ենք նորը
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            bot.send_photo(call.message.chat.id, open(imgs[idx], "rb"),
                           caption=product_caption(p, idx), parse_mode="HTML",
                           reply_markup=_slider_kb(code, idx, cat_key, _has_video(p["media"])))
    return idx

@bot.callback_query_handler(func=lambda c: c.data.startswith("view|"))
def cb_view(call: types.CallbackQuery):
    _, code, idx, cat_key = call.data.split("|")
    _edit_photo(call, code, int(idx), cat_key)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("next|"))
def cb_next(call: types.CallbackQuery):
    _, code, idx, cat_key = call.data.split("|")
    _edit_photo(call, code, int(idx) + 1, cat_key)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("prev|"))
def cb_prev(call: types.CallbackQuery):
    _, code, idx, cat_key = call.data.split("|")
    _edit_photo(call, code, int(idx) - 1, cat_key)
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
    show_main_menu(call.message.chat.id, "🏠 Գլխավոր մենյու ✨")
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
# ========== PART 4/8 — CART AS PHOTOS (QTY + VIEW PRODUCT) ==========

# պահենք վերջին ընդհանուր հաղորդագրության id-ը, որ թարմացնենք
CART_SUMMARY_MSG = {}  # {uid: message_id}

def _price_int(code: str) -> int:
    d = PRODUCTS.get(code, {})
    s = str(d.get("price_new", "0"))
    digits = "".join(ch for ch in s if ch.isdigit())
    return int(digits or "0")

def _price_int(code: str) -> int:
    d = PRODUCTS.get(code) or {}
    for key in ("price_new", "price", "new_price", "p"):
        v = d.get(key)
        if v is None:
            continue
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v)
        digits = "".join(ch for ch in s if ch.isdigit())
        if digits:
            return int(digits)
    return 0

def _item_caption(code: str, qty: int) -> str:
    d = PRODUCTS.get(code, {})
    title = d.get("title", code)
    p = _price_int(code)
    subtotal = p * qty
    return (
        f"<b>{title}</b>\n"
        f"{qty} հատ × {p}֏ = <b>{subtotal}֏</b>\n"
        f"Կոդ՝ <code>{code}</code>"
    )
# ---- CART TOTAL + SUMMARY ----
def _cart_total(uid: int) -> int:
    total = 0
    for code, qty in CART.get(uid, {}).items():
        total += _price_int(code) * int(qty)
    return total

def _cart_summary_text(uid: int) -> str:
    items = CART.get(uid, {})
    if not items:
        return "🛒 Զամբյուղը դատարկ է։"
    lines = ["<b>Զամբյուղի ամփոփում</b>"]
    for code, qty in items.items():
        title = PRODUCTS.get(code, {}).get("title", code)
        price = _price_int(code)
        lines.append(f"• {title} — {qty} հատ × {price}֏")
    lines.append(f"\n<b>Ընդհանուր՝ {_cart_total(uid)}֏</b>")
    return "\n".join(lines)

def _send_cart_summary(chat_id: int, uid: int):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Պատվիրել", callback_data="cart:checkout"))
    kb.add(types.InlineKeyboardButton("🧹 Մաքրել զամբյուղը", callback_data="cart:clear"))
    kb.add(
        types.InlineKeyboardButton("⬅️ Կատեգորիաներ", callback_data="cart:back_categories"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="cart:main"),
    )
    bot.send_message(chat_id, _cart_summary_text(uid), reply_markup=kb)


def _item_kb(code: str, qty: int):
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("➖", callback_data=f"cart:dec:{code}"),
        types.InlineKeyboardButton(f"{qty} հատ", callback_data="noop"),
        types.InlineKeyboardButton("➕", callback_data=f"cart:inc:{code}"),
    )
    kb.row(
        types.InlineKeyboardButton("🔎 Դիտել ապրանքը", callback_data=f"detail:{code}"),
        types.InlineKeyboardButton("❌ Հեռացնել", callback_data=f"cart:del:{code}"),
    )
    return kb

def _cart_total(uid: int) -> int:
    total = 0
    for code, qty in CART.get(uid, {}).items():
        total += _price_int(code) * qty
    return total

def _cart_summary_text(uid: int) -> str:
    items = CART.get(uid, {})
    if not items:
        return "🛒 Զամբյուղը դատարկ է։"
    total = _cart_total(uid)
    lines = ["<b>Զամբյուղի ամփոփում</b>"]
    for code, qty in items.items():
        lines.append(f"• {PRODUCTS.get(code,{}).get('title', code)} — {qty} հատ")
    lines.append(f"\nԸնդամենը՝ <b>{total}֏</b>")
    return "\n".join(lines)

def _cart_summary_kb():
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("🧹 Մաքրել զամբյուղը", callback_data="cart:clear"),
        types.InlineKeyboardButton("⬅️ Կատեգորիաներ", callback_data="back:cats"),
    )
    kb.add(types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="mainmenu"))
    kb.add(types.InlineKeyboardButton("✅ Շարունակել պատվերով", callback_data="checkout:start"))  # Part 5-ում
    return kb
types.InlineKeyboardButton("✅ Շարունակել պատվերով", callback_data="checkout_start")

def _send_or_update_summary(chat_id: int, uid: int):
    text = _cart_summary_text(uid)
    kb = _cart_summary_kb()
    msg_id = CART_SUMMARY_MSG.get(uid)
    try:
        if msg_id:
            bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb, parse_mode="HTML")
        else:
            msg = bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
            CART_SUMMARY_MSG[uid] = msg.message_id
    except Exception:
        # եթե չի հաջողվում edit անել (ջնջվել է), ուղարկում ենք նոր
        msg = bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
        CART_SUMMARY_MSG[uid] = msg.message_id

def _product_main_image(code: str):
    d = PRODUCTS.get(code, {})
    media = d.get("media", [])
    for p in media:
        if not p.lower().endswith(".mp4") and os.path.exists(p):
            return p
    return None

# -------- Open Cart from main menu
@bot.message_handler(func=lambda m: m.text == BTN_CART)
def open_cart(m: types.Message):
    uid = m.from_user.id
    items = CART.get(uid, {})
    if not items:
        bot.send_message(m.chat.id, "🛒 Զամբյուղը դատարկ է։", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(BTN_BACK_MAIN, BTN_MAIN))
        return

    for code, qty in list(items.items()):
        img = _product_main_image(code)
        cap = _item_caption(code, qty)
        kb = _item_kb(code, qty)
        if img:
            with open(img, "rb") as ph:
                bot.send_photo(m.chat.id, ph, caption=cap, reply_markup=kb, parse_mode="HTML")
        else:
            bot.send_message(m.chat.id, cap, reply_markup=kb, parse_mode="HTML")
    _send_cart_summary(call.message.chat.id, call.from_user.id)
    _send_cart_summary(m.chat.id, m.from_user.id)

# -------- Cart actions (inc/dec/del/clear/open/add)
@bot.callback_query_handler(func=lambda c: c.data.startswith("cart:") or c.data=="noop")
def cart_actions(call: types.CallbackQuery):
    uid = call.from_user.id
    data = call.data
    if data == "noop":
        bot.answer_callback_query(call.id)
        return

    _, action, *rest = data.split(":")
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    # helpers to refresh this item's caption/keyboard
    def _refresh_item_msg(code):
        qty = CART[uid].get(code, 0)
        if qty <= 0:
            # item removed: delete its message
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception:
                pass
        else:
            try:
                bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=msg_id,
                    caption=_item_caption(code, qty),
                    reply_markup=_item_kb(code, qty),
                    parse_mode="HTML"
                )
            except Exception:
                # if can't edit (e.g., not a photo), send a new message
                bot.send_message(chat_id, _item_caption(code, qty), reply_markup=_item_kb(code, qty), parse_mode="HTML")

        # and update summary
        _send_or_update_summary(chat_id, uid)

    if action == "open":
        bot.answer_callback_query(call.id)
        # resend full cart UI
        fake = types.SimpleNamespace(from_user=types.SimpleNamespace(id=uid), chat=types.SimpleNamespace(id=chat_id), text=BTN_CART)
        open_cart(fake)  # reuse
        return

    if action == "add":
        code = rest[0]
        CART[uid][code] = CART[uid].get(code, 0) + 1
        bot.answer_callback_query(call.id, "Ավելացվեց զամբյուղ")
        _send_or_update_summary(chat_id, uid)
        return

    if action in ("inc", "dec", "del"):
        code = rest[0]
        if action == "inc":
            CART[uid][code] = CART[uid].get(code, 0) + 1
        elif action == "dec":
            q = CART[uid].get(code, 0) - 1
            if q <= 0:
                CART[uid].pop(code, None)
            else:
                CART[uid][code] = q
        elif action == "del":
            CART[uid].pop(code, None)
        bot.answer_callback_query(call.id)
        _refresh_item_msg(code)
        return

    if action == "clear":
        CART[uid].clear()
        bot.answer_callback_query(call.id, "Զամբյուղը մաքրվեց")
        # փորձենք թարմացնել summary-ն
        _send_or_update_summary(chat_id, uid)
        return

# -------- Optional: "Բացել զամբյուղը" detail էջից
@bot.callback_query_handler(func=lambda c: c.data == "cart:open")
def cart_open_from_detail(call: types.CallbackQuery):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    # ուղարկենք ամբողջ զամբյուղը՝ նկարներով
    fake = types.SimpleNamespace(from_user=types.SimpleNamespace(id=uid), chat=types.SimpleNamespace(id=call.message.chat.id), text=BTN_CART)
    open_cart(fake)
@bot.callback_query_handler(func=lambda c: c.data.startswith("cart:"))
def cb_cart_controls(c: types.CallbackQuery):
    uid = c.from_user.id

    if c.data == "cart:clear":
        CART.pop(uid, None)
        bot.answer_callback_query(c.id, "Զամբյուղը մաքրվեց 🧹")
        bot.send_message(c.message.chat.id, "Զամբյուղը դատարկ է։")
        return

    if c.data == "cart:back_categories":
        show_shop_categories(c.message.chat.id)   # ← քո կատեգորիաների ֆունկցիան
        bot.answer_callback_query(c.id)
        return

    if c.data == "cart:main":
        show_main_menu(c.message.chat.id)
        bot.answer_callback_query(c.id)
        return

    if c.data == "cart:checkout":
        bot.answer_callback_query(c.id)
        bot.send_message(c.message.chat.id, "✅ Պատվերի ձևակերպումը կավելացնենք հաջորդ մասում։")
        return
# ========== PART 5/8 — CHECKOUT (COUNTRY→CITY→NAME/ADDR/ZIP→SHIPPING→PAY→SUMMARY) ==========

# -------- Settings / dictionaries --------
try:
    ADMIN_CHAT_ID = int(os.getenv("ADMIN_ID") or "0")
except Exception:
    ADMIN_CHAT_ID = 0

COUNTRIES = {
    "AM": {"name": "Հայաստան", "cities": ["Երևան", "Գյումրի", "Վանաձոր", "Հրազդան", "Աբովյան", "Եղվարդ", "Արմավիր", "Արտաշատ"]},
    "RU": {"name": "Ռուսաստան", "cities": ["Մոսկվա", "Սանկտ-Պետերբուրգ", "Սոչի", "Կրասնոդար", "Եկատերինբուրգ"]},
    "GE": {"name": "Վրաստան", "cities": ["Թբիլիսի", "Բաթումի", "Քութայիսի"]},
}

SHIPPING = {
    "std": {"title": "Ստանդարտ առաքում (անվճար)", "eta": "2–4 աշխատանքային օր", "price": 0},
    "exp": {"title": "Արագացված առաքում", "eta": "1–2 աշխատանքային օր", "price": 1200},
}

PAYMENT = {
    "cash":  {"title": "Կանխիկ՝ առաքման պահին", "hint": "Վճարում եք առաքիչին՝ կանխիկ։"},
    "idram": {"title": "Idram/Bank transfer",      "hint": "Փոխանցում բանկով կամ Idram-ով։", "admin": "IDRAM կամ բանկային տվյալները կուղարկվեն ամրագրման պահին։"},
    "card":  {"title": "Քարտով (հետևից հղում)",   "hint": "Սեղմելով հղումը՝ վճարում եք քարտով։", "admin": "Քարտային հղումը ուղարկվում է ավտոմատ։"},
}

# -------- Validation (use existing if present) --------
if 'NAME_RE' not in globals() or NAME_RE is None:
    NAME_RE = re.compile(r"^[A-Za-z\u0531-\u0556\u0561-\u0587ЁёЪъЫыЭэЙй\s'\-\.]{3,60}$")
ZIP_RE   = re.compile(r"^\d{4,6}$")
ADDR_RE  = re.compile(r"^[\w\u0531-\u0556\u0561-\u0587\s\.,/#\-]{6,120}$")

def _money(n: int) -> str:
    try:
        return f"{int(n)}֏"
    except:  # pragma: no cover
        return "0֏"

# -------- Checkout state helpers --------
def _new_checkout(uid: int) -> dict:
    return {
        "step": 0,               # 0=country,1=city,2=name,3=addr,4=zip,5=ship,6=pay,7=note,8=summary
        "country": None,
        "city": None,
        "fullname": None,
        "address": None,
        "zip": None,
        "ship": None,
        "pay": None,
        "note": None,
        "await": None,          # which text field bot is waiting for
        "msg_id": None,         # last step message to edit
    }

def _cart_lines(uid: int):
    items = CART.get(uid, {})
    lines, total = [], 0
    for code, qty in items.items():
        d = PRODUCTS.get(code, {})
        title = d.get("title", code)
        p = int(''.join(ch for ch in str(d.get("price_new") or d.get("price") or "0") if ch.isdigit()) or "0")
        total += p * qty
        lines.append(f"• {title} — {qty} հատ")
    return lines, total

def _checkout_text(uid: int, s: dict) -> str:
    lines, total = _cart_lines(uid)
    ship_cost = 0 if not s.get("ship") else SHIPPING[s["ship"]]["price"]
    gtotal = total + ship_cost
    country = COUNTRIES.get(s["country"], {}).get("name") if s.get("country") else "—"
    city = s.get("city") or "—"
    payt = PAYMENT.get(s["pay"], {}).get("title") if s.get("pay") else "—"
    shipt = SHIPPING.get(s["ship"], {}).get("title") if s.get("ship") else "—"
    note = s.get("note") or "—"

    return (
        "<b>🧾 Պատվերի ձևավորում</b>\n"
        "— — — — — — — — — —\n"
        f"📍 <b>Երկիր</b>: {country}\n"
        f"🏙 <b>Քաղաք</b>: {city}\n"
        f"👤 <b>Անուն Ազգանուն</b>: {s.get('fullname') or '—'}\n"
        f"🏠 <b>Հասցե</b>: {s.get('address') or '—'}\n"
        f"🏷 <b>Ինդեքս</b>: {s.get('zip') or '—'}\n"
        f"🚚 <b>Առաքում</b>: {shipt}\n"
        f"💳 <b>Վճարում</b>: {payt}\n"
        f"📝 <b>Նշումներ</b>: {note}\n"
        "— — — — — — — — — —\n"
        "<b>Զամբյուղ</b>:\n" + ("\n".join(lines) if lines else "Դատարկ է") + "\n"
        f"\n<b>Ընդամենը</b>: {_money(total)}"
        f"\n<b>Առաքում</b>: {_money(ship_cost)}"
        f"\n<b>Վերջնական</b>: <u>{_money(gtotal)}</u>"
    )

def _step_kb(s: dict) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    st = s["step"]
    # Country
    if st == 0:
        btns = [types.InlineKeyboardButton(COUNTRIES[c]["name"], callback_data=f"chk:country:{c}") for c in COUNTRIES]
        kb.add(*btns)
    # City
    elif st == 1 and s.get("country"):
        btns = [types.InlineKeyboardButton(city, callback_data=f"chk:city:{city}") for city in COUNTRIES[s['country']]["cities"]]
        kb.add(*btns)
    # Name / Address / Zip / Note — text input
    elif st in (2, 3, 4, 7):
        kb.add(types.InlineKeyboardButton("✍️ Մուտքագրել", callback_data="chk:asktype"))
    # Shipping
    elif st == 5:
        for k, v in SHIPPING.items():
            t = f"{v['title']} — {_money(v['price'])} ({v['eta']})"
            kb.add(types.InlineKeyboardButton(t, callback_data=f"chk:ship:{k}"))
    # Payment
    elif st == 6:
        for k, v in PAYMENT.items():
            kb.add(types.InlineKeyboardButton(f"{v['title']}", callback_data=f"chk:pay:{k}"))
    # Summary
    elif st == 8:
        kb.add(
            types.InlineKeyboardButton("✅ Հաստատել պատվերը", callback_data="chk:confirm"),
            types.InlineKeyboardButton("❌ Չեղարկել", callback_data="chk:cancel"),
        )

    # Nav
    if st > 0 and st < 8:
        kb.add(
            types.InlineKeyboardButton("⬅️ Նախորդ քայլ", callback_data="chk:prev"),
            types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="chk:main"),
        )
    else:
        kb.add(types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="chk:main"))
    return kb

def _ask_caption(st: int) -> str:
    return {
        0: "Ընտրեք <b>երկիրը</b> 🌍",
        1: "Ընտրեք <b>քաղաքը</b> 🏙",
        2: "Մուտքագրեք <b>Անուն Ազգանուն</b> (օր.` Անահիտ Հովհաննիսյան)",
        3: "Մուտքագրեք <b>հասցեն</b> (փողոց, տուն/բնակարան, շենք/մուտք)",
        4: "Մուտքագրեք <b>ինդեքսը</b> (4–6 թվանշան)",
        5: "Ընտրեք <b>առաքման եղանակը</b> 🚚",
        6: "Ընտրեք <b>վճարման եղանակը</b> 💳",
        7: "Կցանկանա՞ք ավելացնել <b>նշումներ</b> (ոչ պարտադիր)",
        8: "Ստուգեք տվյալները և հաստատեք ✅",
    }[st]

def _send_checkout_step(chat_id: int, uid: int):
    s = CHECKOUT_STATE[uid]
    text = _checkout_text(uid, s) + "\n\n" + _ask_caption(s["step"])
    kb = _step_kb(s)
    # send or edit one message
    if s.get("msg_id"):
        try:
            bot.edit_message_text(text, chat_id, s["msg_id"], reply_markup=kb, parse_mode="HTML")
            return
        except:
            pass
    msg = bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
    s["msg_id"] = msg.message_id

def _goto(uid: int, delta: int):
    s = CHECKOUT_STATE[uid]
    s["step"] = max(0, min(8, s["step"] + delta))
    s["await"] = None

# -------- Entry point from Cart (button "Շարունակել պատվերով") --------
@bot.callback_query_handler(func=lambda c: c.data == "cart:checkout")
def _start_checkout(call: types.CallbackQuery):
    uid, chat_id = call.from_user.id, call.message.chat.id
    items = CART.get(uid, {})
    if not items:
        bot.answer_callback_query(call.id, "Զամբյուղը դատարկ է։", show_alert=True)
        return
    CHECKOUT_STATE[uid] = _new_checkout(uid)
    _send_checkout_step(chat_id, uid)
    bot.answer_callback_query(call.id)

# -------- Inline flow handlers --------
@bot.callback_query_handler(func=lambda c: c.data.startswith("chk:"))
def _chk_inline(call: types.CallbackQuery):
    uid, chat_id = call.from_user.id, call.message.chat.id
    if uid not in CHECKOUT_STATE:
        bot.answer_callback_query(call.id, "Սկսեք զամբյուղից․ 🛒", show_alert=True); return
    s = CHECKOUT_STATE[uid]
    data = call.data.split(":", 2)

    # Navigation
    if data[1] == "prev":
        _goto(uid, -1); _send_checkout_step(chat_id, uid); bot.answer_callback_query(call.id); return
    if data[1] == "main":
        CHECKOUT_STATE.pop(uid, None); show_main_menu(chat_id, "Գլխավոր մենյու ✨"); bot.answer_callback_query(call.id); return
    if data[1] == "cancel":
        CHECKOUT_STATE.pop(uid, None); bot.answer_callback_query(call.id, "Չեղարկվեց։"); return

    # Country / City
    if data[1] == "country":
        s["country"] = data[2]; s["city"] = None; s["step"] = 1
    elif data[1] == "city":
        s["city"] = data[2]; s["step"] = 2
    # Text ask buttons
    elif data[1] == "asktype":
        s["await"] = {2: "fullname", 3: "address", 4: "zip", 7: "note"}[s["step"]]
        bot.answer_callback_query(call.id, "Ուղարկեք տեքստով 👇", show_alert=True); return
    # Shipping
    elif data[1] == "ship":
        s["ship"] = data[2]; s["step"] = 6
    # Payment
    elif data[1] == "pay":
        s["pay"] = data[2]; s["step"] = 7
    # Confirm
    elif data[1] == "confirm":
        _finish_order(chat_id, uid); bot.answer_callback_query(call.id); return

    _send_checkout_step(chat_id, uid)
    bot.answer_callback_query(call.id)

# -------- Text inputs with validation --------
@bot.message_handler(func=lambda m: CHECKOUT_STATE.get(m.from_user.id, {}).get("await") is not None)
def _chk_text(m: types.Message):
    uid, chat_id = m.from_user.id, m.chat.id
    s = CHECKOUT_STATE.get(uid) or {}
    field = s.get("await")
    val = (m.text or "").strip()

    if field == "fullname":
        if not NAME_RE.match(val):
            bot.reply_to(m, "❗️ Գրեք ճիշտ Անուն Ազգանուն (մին. 3 նշան)։"); return
        s["fullname"] = val; s["step"] = 3
    elif field == "address":
        if not ADDR_RE.match(val):
            bot.reply_to(m, "❗️ Հասցեն պետք է լինի 6–120 նշան։"); return
        s["address"] = val; s["step"] = 4
    elif field == "zip":
        if not ZIP_RE.match(val):
            bot.reply_to(m, "❗️ Ինդեքսը պետք է լինի 4–6 թվանշան։"); return
        s["zip"] = val; s["step"] = 5
    elif field == "note":
        s["note"] = val if val else None; s["step"] = 8

    s["await"] = None
    _send_checkout_step(chat_id, uid)

# -------- Finish order --------
def _finish_order(chat_id: int, uid: int):
    s = CHECKOUT_STATE.get(uid) or {}
    lines, total = _cart_lines(uid)
    if not lines: 
        bot.send_message(chat_id, "Զամբյուղը դատարկ է։"); CHECKOUT_STATE.pop(uid, None); return
    ship = SHIPPING.get(s.get("ship") or "std", {})
    pay = PAYMENT.get(s.get("pay") or "cash", {})
    gtotal = total + int(ship.get("price", 0))

    summary = (
        "✅ <b>Պատվերը հաստատվեց</b>\n"
        "— — — — — — — — — —\n"
        f"👤 {s.get('fullname')}\n"
        f"📍 {COUNTRIES.get(s.get('country'),{}).get('name','—')}, {s.get('city')}\n"
        f"🏠 {s.get('address')} • {s.get('zip')}\n"
        f"🚚 {ship.get('title','')} ({ship.get('eta','')})\n"
        f"💳 {pay.get('title','')}\n"
        f"📝 {s.get('note') or '—'}\n"
        "— — — — — — — — — —\n"
        "<b>Ապրանքներ</b>:\n" + "\n".join(lines) + "\n"
        f"\n<b>Ընդամենը</b>: {_money(total)}"
        f"\n<b>Առաքում</b>: {_money(ship.get('price',0))}"
        f"\n<b>Վերջնական</b>: <u>{_money(gtotal)}</u>"
    )

    bot.send_message(chat_id, summary, parse_mode="HTML")
    if ADMIN_CHAT_ID:
        bot.send_message(ADMIN_CHAT_ID, f"🆕 <b>Նոր պատվեր</b> #{_order_id()}\n" + summary, parse_mode="HTML")

    # Optional: վճարման հուշում
    if pay.get("hint"):
        bot.send_message(chat_id, f"ℹ️ {pay['hint']}", parse_mode="HTML")
    if pay.get("admin") and ADMIN_CHAT_ID:
        bot.send_message(chat_id, "💬 Վաճառողը շուտով կուղարկի վճարման տվյալները։")

    # Cleanup
    ORDERS.append({"uid": uid, "data": s, "sum": gtotal, "items": CART.get(uid, {}).copy(), "ts": time.time()})
    CART.pop(uid, None)
    CHECKOUT_STATE.pop(uid, None)

# ========== END OF PART 5/8 ==========
# --- Handle "checkout_finish" (Պատվիրել) ---
@bot.callback_query_handler(func=lambda c: c.data == "checkout_finish")
def _cb_checkout_finish(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    _finish_order(call.message.chat.id, call.from_user.id)

# ========== RUN ==========
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
# ========== END OF PART 1/8 ==========
