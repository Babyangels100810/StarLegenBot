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
# ========== MAIN.PY — PART 2/8 (SHOP + 12 PRODUCTS) ==========
# Նկարները अपेում ենք media/products/ մեջ.
# Գորգերի հիմնական նկարները՝ BA100810.jpg ... BA100820.jpg
# Այլ ընդհանուր նկարներ (եթե ունես) կարող ես դնել media/products/shared/ care.jpg,layers.jpg,absorb.jpg,universal.jpg,interior.jpg,advantages.jpg
# Ավտոմաքրիչի նկարը՝ media/products/car_cleaner.jpg (կամ քո ֆայլը)

def _p(*parts):
    import os
    return os.path.join(*parts)

PRODUCTS = {
    # 11 ԳՈՐԳ — BA100810..BA100820
    "BA100810": {
        "title": "🌸 Գորգ – BA100810 (40×60սմ)",
        "price": 1690, "old_price": 2560, "stock": 25,
        "photos": [
            _p("media","products","BA100810.jpg"),
            _p("media","products","shared","care.jpg"),
            _p("media","products","shared","layers.jpg"),
            _p("media","products","shared","absorb.jpg"),
            _p("media","products","shared","interior.jpg"),
        ],
        "desc": "✔️ Չսահող հիմք • ✔️ Արագ չորանում է • ✔️ Հեշտ լվացվող"
    },
    "BA100811": {
        "title": "🌸 Գորգ – BA100811 (40×60սմ)",
        "price": 1690, "old_price": 2560, "stock": 24,
        "photos": [
            _p("media","products","BA100811.jpg"),
            _p("media","products","shared","absorb.jpg"),
            _p("media","products","shared","advantages.jpg"),
        ],
        "desc": "✔️ Խիտ վերին շերտ • ✔️ Գույնը չի խամրում • ✔️ Կոկիկ եզրեր"
    },
    "BA100812": {
        "title": "🌸 Գորգ – BA100812 (40×60սմ)",
        "price": 1690, "old_price": 2560, "stock": 22,
        "photos": [
            _p("media","products","BA100812.jpg"),
            _p("media","products","shared","layers.jpg"),
            _p("media","products","shared","universal.jpg"),
        ],
        "desc": "✔️ Տան ցանկացած հատվածի համար • ✔️ Դիմացկուն"
    },
    "BA100813": {
        "title": "🌸 Գորգ – BA100813 (40×60սմ)",
        "price": 1690, "old_price": 2560, "stock": 26,
        "photos": [
            _p("media","products","BA100813.jpg"),
            _p("media","products","shared","interior.jpg"),
            _p("media","products","shared","advantages.jpg"),
        ],
        "desc": "✔️ Հարմար ինտենսիվ օգտագործման համար • ✔️ Չի սահում"
    },
    "BA100814": {
        "title": "🌸 Գորգ – BA100814 (40×60սմ)",
        "price": 1690, "old_price": 2560, "stock": 20,
        "photos": [
            _p("media","products","BA100814.jpg"),
            _p("media","products","shared","care.jpg"),
            _p("media","products","shared","advantages.jpg"),
        ],
        "desc": "✔️ Փափուկ, հաճելի հպում • ✔️ Կոկիկ եզրեր"
    },
    "BA100815": {
        "title": "🌸 Գորգ – BA100815 (40×60սմ)",
        "price": 1690, "old_price": 2560, "stock": 25,
        "photos": [
            _p("media","products","BA100815.jpg"),
            _p("media","products","shared","absorb.jpg"),
            _p("media","products","shared","interior.jpg"),
        ],
        "desc": "✔️ Խիտ շերտ • ✔️ Չի ձևախեղվում լվացումից հետո"
    },
    "BA100816": {
        "title": "🌸 Գորգ – BA100816 (40×60սմ)",
        "price": 1690, "old_price": 2560, "stock": 18,
        "photos": [
            _p("media","products","BA100816.jpg"),
            _p("media","products","shared","layers.jpg"),
            _p("media","products","shared","advantages.jpg"),
        ],
        "desc": "✔️ Էլեգանտ դիզայն • ✔️ Դիմացկուն հիմք"
    },
    "BA100817": {
        "title": "🌸 Գորգ – BA100817 (40×60սմ)",
        "price": 1690, "old_price": 2560, "stock": 23,
        "photos": [
            _p("media","products","BA100817.jpg"),
            _p("media","products","shared","universal.jpg"),
            _p("media","products","shared","care.jpg"),
        ],
        "desc": "✔️ Խոհանոց/մուտք • ✔️ Արագ չորացում"
    },
    "BA100818": {
        "title": "🌸 Գորգ – BA100818 (40×60սմ)",
        "price": 1690, "old_price": 2560, "stock": 21,
        "photos": [
            _p("media","products","BA100818.jpg"),
            _p("media","products","shared","advantages.jpg"),
        ],
        "desc": "✔️ Թեթև, կոմպակտ • ✔️ Հեշտ տեղադրվող"
    },
    "BA100819": {
        "title": "🌸 Գորգ – BA100819 (40×60սմ)",
        "price": 1690, "old_price": 2560, "stock": 19,
        "photos": [
            _p("media","products","BA100819.jpg"),
            _p("media","products","shared","interior.jpg"),
            _p("media","products","shared","absorb.jpg"),
        ],
        "desc": "✔️ Կոկիկ ու համադրվող • ✔️ Հակասահող հիմք"
    },
    "BA100820": {
        "title": "🌸 Գորգ – BA100820 (40×60սմ)",
        "price": 1690, "old_price": 2560, "stock": 20,
        "photos": [
            _p("media","products","BA100820.jpg"),
            _p("media","products","shared","universal.jpg"),
            _p("media","products","shared","advantages.jpg"),
        ],
        "desc": "✔️ Թարմ դիզայն • ✔️ Հեշտ մաքրվող"
    },

    # 1 ԱՎՏՈՄԵՔԵՆԱՅԻ ՄԱՔՐԻՉ
    "AUTO001": {
        "title": "🚘 Յուղային ֆիլմ մաքրիչ (կարմիր, սպունգով)",
        "price": 3580, "old_price": 6480, "stock": 25,
        "photos": [
            _p("media","products","car_cleaner.jpg"),  # ← դիր քո ֆայլի անունը
            _p("media","products","promo_auto1.jpg"),  # եթե չկա՝ կանցնի առանց դրա
        ],
        "desc": "✔️ Հեռացնում է յուղային կեղտը ապակուց • ✔️ Բարձր թափանցիկություն • ✔️ Հեշտ կիրառություն"
    },
}

# ========== INLINE KEYBOARDS ==========
def product_inline_kb(code: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Ավելացնել զամբյուղ", callback_data=f"cart:add:{code}"))
    kb.add(
        types.InlineKeyboardButton("🛒 Դիտել զամբյուղ", callback_data="cart:show"),
        types.InlineKeyboardButton("🏠 Գլխավոր", callback_data="go_home")
    )
    return kb

# ========== SHOP LIST + PRODUCT VIEW ==========
@bot.message_handler(func=lambda m: m.text == "🛍 Խանութ")
def open_shop(m: types.Message):
    kb = types.InlineKeyboardMarkup()
    # Ցուցադրում ենք բոլոր 12 ապրանքները inline սեղմվող կոճակներով
    for code, prod in PRODUCTS.items():
        kb.add(types.InlineKeyboardButton(prod["title"], callback_data=f"prod:{code}"))
    bot.send_message(m.chat.id, "🛍 Խանութ — Ընտրեք ապրանքը ⬇️", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("prod:"))
def show_product(c: types.CallbackQuery):
    code = c.data.split(":")[1]
    prod = PRODUCTS.get(code)
    if not prod:
        bot.answer_callback_query(c.id, "Ապրանքը չի գտնվել")
        return

    # Սլայդ/մեդիա խումբ
    media_paths = [p for p in prod["photos"] if os.path.exists(p)]
    if media_paths:
        try:
            media = [InputMediaPhoto(open(p, "rb")) for p in media_paths]
            bot.send_media_group(c.message.chat.id, media)
        except Exception as e:
            # եթե media_group չստացվեց, գոնե առաջին նկարը ուղարկենք
            try:
                with open(media_paths[0], "rb") as ph:
                    bot.send_photo(c.message.chat.id, ph)
            except:
                pass

    # Ապրանքի caption + գործողության կոճակներ
    caption = (
        f"<b>{prod['title']}</b>\n\n"
        f"{prod['desc']}\n\n"
        f"Հին գին — {prod['old_price']}֏\n"
        f"Նոր գին — <b>{prod['price']}֏</b>"
    )
    bot.send_message(c.message.chat.id, caption, reply_markup=product_inline_kb(code), parse_mode="HTML")
    bot.answer_callback_query(c.id)

# ⬅️ “Գլխավոր” inline կոճակին արձագանք
@bot.callback_query_handler(func=lambda c: c.data == "go_home")
def cb_go_home(c: types.CallbackQuery):
    show_main_menu(c.message.chat.id)
    bot.answer_callback_query(c.id)

# ========== RUN ==========
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
# ========== END OF PART 1/8 ==========
