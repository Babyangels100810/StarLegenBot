# -*- coding: utf-8 -*-
# ========== StarLegen — CLEAN SKELETON (Start + Menu + Categories + Cart Summary) ==========
import os, json, time
from collections import defaultdict

from telebot import TeleBot, types, apihelper
from dotenv import load_dotenv, find_dotenv

# ---------- API & ENV ----------
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
print("dotenv:", find_dotenv())
print("token len:", len(BOT_TOKEN))
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN բացակայում է .env-ում")

# ---------- DIRS ----------
DATA_DIR  = "data"
MEDIA_DIR = "media"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)

# ---------- BOT ----------
bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# ---------- GLOBAL RUNTIME ----------
CART = defaultdict(dict)      # {uid: {code: qty}}
ORDERS = []                   # future use
CHECKOUT_STATE = {}           # future use

# ---------- MENU LABELS (չփոխել) ----------
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

# ---------- CUSTOMER COUNTER ----------
COUNTER_FILE = os.path.join(DATA_DIR, "counter.json")
def _load_counter():
    try:
        if os.path.exists(COUNTER_FILE):
            return json.load(open(COUNTER_FILE, "r", encoding="utf-8")).get("customer_counter", 1000)
    except: pass
    return 1000

def _save_counter(v:int):
    try:
        json.dump({"customer_counter": v}, open(COUNTER_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    except: pass

customer_counter = _load_counter()

# ---------- CALLBACK KEYS (մի անգամ ու վերջ) ----------
from types import SimpleNamespace
CB = SimpleNamespace(
    product   = "product:",        # f"{CB.product}{code}"
    inc       = "cart:inc:",       # f"{CB.inc}{code}"
    dec       = "cart:dec:",       # f"{CB.dec}{code}"
    open      = "cart:open",       # open cart summary
    clear     = "cart:clear",      # clear cart
    main      = "mainmenu",        # go main
    back_cats = "backcats",        # back to categories
    checkout  = "checkout_start"   # start checkout
)

# ---------- CATEGORIES (լիքը) ----------
CATEGORIES = [
    ("home",     "🏡 Կենցաղային ապրանքներ"),
    ("rugs",     "🧼 Գորգեր (տան)"),
    ("auto",     "🚗 Ավտոմեքենաների ապրանքներ"),
    ("car_mats", "🚘 Ավտոգորգեր"),
    ("kitchen",  "🍳 Խոհանոց / կենցաղ"),
    ("phone",    "📱 Բջջային աքսեսուարներ"),
    ("smart",    "⌚ Սմարթ ժամացույցներ"),
    ("pc",       "💻 Համակարգչային աքսեսուարներ"),
    ("beauty",   "💄 Գեղեցկություն/խնամք"),
    ("kids",     "👶 Մանկական"),
    ("bags",     "🧳 Պայուսակներ"),
    ("pet",      "🐾 Կենդանիների համար"),
]
CAT_LABELS = {label: key for key, label in CATEGORIES}

def cats_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    row = []
    for _, label in CATEGORIES:
        row.append(label)
        if len(row) == 2:
            kb.add(*row); row = []
    if row: kb.add(*row)
    kb.add(BTN_BACK_MAIN, BTN_MAIN)
    return kb

def show_shop_categories(chat_id, text="Ընտրեք կատեգորիան 👇"):
    bot.send_message(chat_id, text, reply_markup=cats_kb())

# ---------- WELCOME TEXT (քո տեքստով) ----------
def welcome_text(no:int)->str:
    return (
        "🐰🌸 <b>Բարի գալուստ BabyAngels</b> 🛍️\n\n"
        "💖 Շնորհակալ ենք, որ ընտրել եք մեզ ❤️\n"
        f"Դուք արդեն մեր սիրելի հաճախորդն եք №{no}։\n\n"
        "🎁 Առաջին պատվերի համար ունեք 5% զեղչ — կտեսնեք վճարման պահին։\n\n"
        "📦 Ինչ կգտնեք մեզ մոտ․\n"
        "• Ժամանակակից ու օգտակար ապրանքներ ամեն օր թարմացվող տեսականու մեջ\n"
        "• Գեղեցիկ դիզայն և անմիջական օգտագործում\n"
        "• Անվճար առաքում ամբողջ Հայաստանով\n\n"
        "💱 Բացի խանութից՝ տրամադրում ենք նաև փոխանակման ծառայություններ․\n"
        "PI ➝ USDT | FTN ➝ AMD | Alipay ➝ CNY\n\n"
        "👇 Ընտրեք բաժին և սկսեք գնումները հիմա"
    )

# ---------- CART SUMMARY (միշտ կա «Շարունակել պատվերով») ----------
def _cart_summary_text(uid:int)->str:
    items = CART.get(uid, {})
    if not items:
        return "🛒 Զամբյուղը դատարկ է։\n\nՍեղմեք «✅ Շարունակել պատվերով»՝ փորձేందుకు checkout-ը (demo)."
    lines = ["🧾 <b>Զամբյուղի ամփոփում</b>"]
    total = 0
    for code, qty in items.items():
        # Skeleton — հիմա ապրանքների բազա չկա, դրա համար ցույց ենք տալիս միայն կոդն ու քանակը
        lines.append(f"• Կոդ՝ {code} — {qty} հատ")
        # total += price*qty  # Part 3/4-ում կավելացնես գների հաշվարկը
    lines.append(f"\n<b>Ընդամենը</b>՝ {total}֏")
    return "\n".join(lines)

def _cart_summary_kb():
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("🧹 Մաքրել զամբյուղը", callback_data=CB.clear),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data=CB.main),
    )
    kb.row(types.InlineKeyboardButton("✅ Շարունակել պատվերով", callback_data=CB.checkout))
    return kb

def send_cart_summary(chat_id:int, uid:int):
    bot.send_message(chat_id, _cart_summary_text(uid), reply_markup=_cart_summary_kb(), parse_mode="HTML")

# ---------- HANDLERS ----------
@bot.message_handler(commands=["start"])
def on_start(m: types.Message):
    if getattr(m.chat, "type", "") != "private":
        return
    global customer_counter
    customer_counter += 1
    _save_counter(customer_counter)

    bunny = os.path.join(MEDIA_DIR, "bunny.jpg")
    if os.path.exists(bunny):
        try:
            with open(bunny, "rb") as ph:
                bot.send_photo(m.chat.id, ph)
        except: pass

    bot.send_message(m.chat.id, welcome_text(customer_counter), reply_markup=main_menu_kb())

@bot.message_handler(commands=["menu"])
def on_menu(m: types.Message):
    show_main_menu(m.chat.id)

@bot.message_handler(func=lambda m: m.text in (BTN_BACK_MAIN, BTN_MAIN))
def back_main(m: types.Message):
    show_main_menu(m.chat.id, "Վերադարձաք գլխավոր մենյու ✨")

# --- SHOP -> Categories ---
@bot.message_handler(func=lambda m: m.text == BTN_SHOP)
def on_shop(m: types.Message):
    show_shop_categories(m.chat.id)

@bot.message_handler(func=lambda m: m.text in CAT_LABELS)
def on_any_category(m: types.Message):
    label = m.text
    bot.send_message(m.chat.id, f"«{label}» բաժնի ապրանքները կավելացնենք հաջորդ քայլում (Part 3).", reply_markup=cats_kb())

# --- CART button (always shows summary + checkout button) ---
@bot.message_handler(func=lambda m: m.text == BTN_CART)
def on_cart(m: types.Message):
    uid = m.from_user.id
    send_cart_summary(m.chat.id, uid)

# --- Inline callbacks for cart summary / navigation ---
@bot.callback_query_handler(func=lambda c: c.data == CB.clear)
def cb_clear_cart(c: types.CallbackQuery):
    CART.pop(c.from_user.id, None)
    bot.answer_callback_query(c.id, "Զամբյուղը մաքրվեց 🧹")
    send_cart_summary(c.message.chat.id, c.from_user.id)

@bot.callback_query_handler(func=lambda c: c.data == CB.main)
def cb_main(c: types.CallbackQuery):
    bot.answer_callback_query(c.id)
    show_main_menu(c.message.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == CB.back_cats)
def cb_back_cats(c: types.CallbackQuery):
    bot.answer_callback_query(c.id)
    show_shop_categories(c.message.chat.id, "Վերադարձ կատեգորիաներ 👇")

@bot.callback_query_handler(func=lambda c: c.data == CB.checkout)
def cb_checkout_start(c: types.CallbackQuery):
    bot.answer_callback_query(c.id)
    uid = c.from_user.id
    if not CART.get(uid):
        bot.send_message(c.message.chat.id, "🛒 Զամբյուղը դատարկ է, բայց checkout-ը կավելացնենք Part 5-ում։")
        return
    bot.send_message(c.message.chat.id, "✅ Checkout flow-ը կավելացվի Part 5-ում (երկիր→քաղաք→անուն→հասցե→վճարում).")

# --- Stubs for other menu buttons (չեն խանգարում) ---
@bot.message_handler(func=lambda m: m.text in (BTN_EXCHANGE, BTN_THOUGHTS, BTN_RATES, BTN_PROFILE,
                                               BTN_FEEDBACK, BTN_PARTNERS, BTN_SEARCH, BTN_INVITE))
def stubs(m: types.Message):
    bot.send_message(m.chat.id, "Այս բաժինը կավելացվի հաջորդ մասերում 🙂", reply_markup=main_menu_kb())

# ---------- RUN ----------
if __name__ == "__main__":
    print("Bot is running…")
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
