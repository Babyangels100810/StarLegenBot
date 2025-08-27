# main.py — ONE PIECE, CLEAN
# ---------------------------------------------
# Works with: pyTelegramBotAPI (telebot)
# pip install pytelegrambotapi python-dotenv requests

import os, json, time, threading, traceback, re
from datetime import datetime
import requests
from telebot import TeleBot, types, apihelper
from telebot.types import InputMediaPhoto
from dotenv import load_dotenv, find_dotenv
from collections import defaultdict

# ---------- BASIC INIT ----------
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"
load_dotenv()
ENV_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ENV_ADMIN = os.getenv("ADMIN_ID", "").strip()

DATA_DIR  = "data"
MEDIA_DIR = "media"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(os.path.join(MEDIA_DIR, "products"), exist_ok=True)
os.makedirs(os.path.join(MEDIA_DIR, "exchange"), exist_ok=True)

SETTINGS_FILE           = os.path.join(DATA_DIR, "settings.json")
USERS_FILE              = os.path.join(DATA_DIR, "users.json")
ORDERS_FILE             = os.path.join(DATA_DIR, "orders.json")
THOUGHTS_FILE           = os.path.join(DATA_DIR, "thoughts.json")
PENDING_THOUGHTS_FILE   = os.path.join(DATA_DIR, "pending_thoughts.json")
ADS_FILE                = os.path.join(DATA_DIR, "ads.json")
PENDING_ADS_FILE        = os.path.join(DATA_DIR, "pending_ads.json")
PARTNERS_FILE           = os.path.join(DATA_DIR, "partners.json")
RATES_FILE              = os.path.join(DATA_DIR, "rates.json")

def load_json(p, default):
    try:
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
            return default
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(p, data):
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

SETTINGS = load_json(SETTINGS_FILE, {
    "bot_token": ENV_TOKEN or "PASTE_YOUR_BOT_TOKEN_HERE",
    "admin_id": int(ENV_ADMIN) if ENV_ADMIN.isdigit() else 6822052289,
    "customer_counter": 1007,
    "bot_username": "YourBotUsernameHere",
    "alipay_rate_amd": 58
})

BOT_TOKEN = SETTINGS.get("bot_token", "")
if not BOT_TOKEN or "PASTE_YOUR_BOT_TOKEN_HERE" in BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is empty. Put it in .env or settings.json")

ADMIN_ID = int(SETTINGS.get("admin_id", 6822052289))

bot = TeleBot(BOT_TOKEN, parse_mode=None)

# Remove webhook to avoid 409 conflict when polling
try:
    bot.remove_webhook()
except:
    pass

# ---------- GLOBALS ----------
USERS            = load_json(USERS_FILE, {})            # user_id -> {referrer_id,...}
GOOD_THOUGHTS    = load_json(THOUGHTS_FILE, [])
PENDING_THOUGHTS = load_json(PENDING_THOUGHTS_FILE, {}) # id -> dict
ADS_STORE        = load_json(ADS_FILE, [])
PENDING_ADS      = load_json(PENDING_ADS_FILE, {})
ORDERS           = load_json(ORDERS_FILE, [])
RATES_CACHE      = load_json(RATES_FILE, {"rates":{}, "updated_at": None, "error": None})

NEXT_THOUGHT_ID = (max([x.get("id",1000) for x in GOOD_THOUGHTS], default=1000) + 1) if GOOD_THOUGHTS else 1001
if PENDING_THOUGHTS:
    NEXT_THOUGHT_ID = max(NEXT_THOUGHT_ID, max(int(k) for k in PENDING_THOUGHTS.keys())+1)

NEXT_AD_ID = (max([x.get("id",5000) for x in ADS_STORE], default=5000) + 1) if ADS_STORE else 5001
if PENDING_ADS:
    NEXT_AD_ID = max(NEXT_AD_ID, max(int(k) for k in PENDING_ADS.keys())+1)

# ---------- MENU LABELS (քո կառուցվածքը) ----------
BTN_SHOP     = "🛍 Խանութ"
BTN_CART     = "🛒 Զամբյուղ"
BTN_EXCHANGE = "💱 Փոխարկումներ"
BTN_THOUGHTS = "💡 Խոհուն մտքեր"
BTN_RATES    = "📈 Օրվա կուրսեր"
BTN_PROFILE  = "🧍 Իմ էջ"
BTN_FEEDBACK = "💬 Հետադարձ կապ"
BTN_PARTNERS = "📢 Բիզնես գործընկերներ"
BTN_SEARCH   = "🔍 Ապրանքի որոնում"
BTN_INVITE   = "👥 Հրավիրել ընկերների"
BTN_MAIN     = "🏠 Գլխավոր մենյու"

def build_main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(BTN_SHOP, BTN_CART)
    kb.add(BTN_EXCHANGE, BTN_THOUGHTS)
    kb.add(BTN_RATES, BTN_PROFILE)
    kb.add(BTN_FEEDBACK, BTN_PARTNERS)
    kb.add(BTN_SEARCH, BTN_INVITE)
    kb.add(BTN_MAIN)
    return kb

# ---------- WELCOME ----------
def welcome_text(customer_no: int) -> str:
    # թողնում եմ քո ոճը — կարող ես փոփոխել միայն տեքստը
    return (
        "🐰🌸 <b>Բարի գալուստ StarLegen</b> 🛍✨\n\n"
        "💖 Շնորհակալ ենք, որ միացել եք մեր սիրելի համայնքին ❤️\n"
        f"Դուք այժմ մեր սիրելի հաճախորդն եք №{customer_no} ✨\n\n"
        "Մեր խանութում կարող եք գտնել ամեն օր օգտակար ապրանքների գեղեցիկ լացակազմ գները։\n\n"
        "🎁 Կուպոնների և զեղչերի համակարգը հասանելի է գնման ժամանակ։\n\n"
        "✨ Ընտրեք բաժին 👇"
    )

def bot_link_with_ref(user_id: int) -> str:
    uname = SETTINGS.get("bot_username", "YourBotUsernameHere")
    return f"https://t.me/{uname}?start={user_id}"

# ---------- START ----------
@bot.message_handler(commands=["start"])
def on_start(m: types.Message):
    if getattr(m.chat, "type", "") != "private":
        return

    # referral
    try:
        parts = (m.text or "").split(maxsplit=1)
        if len(parts) == 2 and parts[1].isdigit():
            uid = str(m.from_user.id)
            ref = int(parts[1])
            if int(uid) != ref:
                USERS.setdefault(uid, {})
                if "referrer_id" not in USERS[uid]:
                    USERS[uid]["referrer_id"] = ref
                    save_json(USERS_FILE, USERS)
    except:
        pass

    # customer counter
    SETTINGS["customer_counter"] = int(SETTINGS.get("customer_counter", 1007)) + 1
    save_json(SETTINGS_FILE, SETTINGS)
    customer_no = SETTINGS["customer_counter"]

    # bunny photo (optional)
    bunny = os.path.join(MEDIA_DIR, "bunny.jpg")
    if os.path.exists(bunny):
        try:
            with open(bunny, "rb") as ph:
                bot.send_photo(m.chat.id, ph)
        except: pass

    bot.send_message(m.chat.id, welcome_text(customer_no), parse_mode="HTML", reply_markup=build_main_menu())

@bot.message_handler(commands=["menu"])
def on_menu(m: types.Message):
    bot.send_message(m.chat.id, "Գլխավոր մենյու ✨", reply_markup=build_main_menu())

# ---------- INVITE ----------
@bot.message_handler(func=lambda msg: msg.text == BTN_INVITE)
def invite_handler(m: types.Message):
    uid = m.from_user.id
    link = bot_link_with_ref(uid)
    txt = (
        "👥 <b>Կիսվեք բոտով</b>\n\n"
        f"Ձեր հրավերի հղումը՝\n{link}\n\n"
        "Ուղարկեք սա ընկերներին 🌸"
    )
    bot.send_message(m.chat.id, txt, parse_mode="HTML")

# ---------- DAILY RATES ----------
def fetch_rates():
    try:
        r = requests.get("https://api.exchangerate.host/latest", params={"base":"AMD","symbols":"USD,EUR,RUB,GBP,CNY"}, timeout=10)
        data = r.json() if r.ok else {}
        raw = data.get("rates", {})
        conv = {}
        for k,v in raw.items():
            if v: conv[k] = round(1.0/v, 4)  # 1 FX = ? AMD
        RATES_CACHE["rates"] = conv
        RATES_CACHE["updated_at"] = datetime.utcnow().isoformat() + "Z"
        RATES_CACHE["error"] = None
        save_json(RATES_FILE, RATES_CACHE)
    except Exception as e:
        RATES_CACHE["error"] = str(e)
        save_json(RATES_FILE, RATES_CACHE)

def rates_loop():
    while True:
        fetch_rates()
        time.sleep(600)

threading.Thread(target=rates_loop, daemon=True).start()
fetch_rates()

@bot.message_handler(func=lambda m: m.text == BTN_RATES)
def show_rates(m: types.Message):
    rates = RATES_CACHE.get("rates", {})
    if not rates:
        return bot.send_message(m.chat.id, "❗️ Կուրսերը հասանելի չեն հիմա, փորձիր ուշ")
    flags = {"USD":"🇺🇸","EUR":"🇪🇺","RUB":"🇷🇺","GBP":"🇬🇧","CNY":"🇨🇳"}
    order = ["USD","EUR","RUB","GBP","CNY"]
    lines = ["📈 <b>Օրվա կուրսեր (AMD)</b>", ""]
    for c in order:
        if c in rates:
            lines.append(f"{flags.get(c,'')} 1 {c} = <b>{rates[c]} AMD</b>")
    lines.append("")
    lines.append(f"🕒 Թարմացվել է (UTC): {RATES_CACHE.get('updated_at','—')}")
    bot.send_message(m.chat.id, "\n".join(lines), parse_mode="HTML")

# ---------- PARTNERS ----------
@bot.message_handler(func=lambda m: m.text == BTN_PARTNERS)
def show_partners(m: types.Message):
    arr = load_json(PARTNERS_FILE, [])
    if not arr:
        return bot.send_message(m.chat.id, "Այս պահին գործընկերների հայտարարություններ չկան։")
    text = "📢 Բիզնես գործընկերներ\n\n" + "\n\n".join(arr[-5:])
    bot.send_message(m.chat.id, text)

# ---------- THOUGHTS (with admin moderation) ----------
STATE = {}
FORM  = {}
RL = defaultdict(dict)

def rate_limited(uid: int, key: str, sec: int) -> bool:
    last = RL[uid].get(key, 0)
    now  = int(time.time())
    if now - last < sec: return True
    RL[uid][key] = now
    return False

GT_TEXT, GT_AUTHOR = "GT_TEXT", "GT_AUTHOR"

@bot.message_handler(func=lambda m: m.text == BTN_THOUGHTS)
def thoughts_menu(m: types.Message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Ավելացնել միտք", callback_data="gt:new"))
    if GOOD_THOUGHTS:
        kb.add(types.InlineKeyboardButton("📚 Դիտել վերջինները", callback_data="gt:list:1"))
    bot.send_message(m.chat.id, "«Խոհուն մտքեր» ✨", reply_markup=kb)

def render_thoughts_page(page: int):
    total = len(GOOD_THOUGHTS)
    if total == 0:
        return "Այս պահին ասույթներ չկան։", None
    page = max(1, min(page, total))
    item = GOOD_THOUGHTS[page-1]
    txt = f"🧠 <b>Լավ միտք</b>\n\n{item['text']}\n\n— Էջ {page}/{total}"
    kb = types.InlineKeyboardMarkup()
    nav = []
    if page>1: nav.append(types.InlineKeyboardButton("⬅️ Նախորդ", callback_data=f"gt:list:{page-1}"))
    if page<total: nav.append(types.InlineKeyboardButton("Այժմոք ➡️", callback_data=f"gt:list:{page+1}"))
    if nav: kb.row(*nav)
    kb.add(types.InlineKeyboardButton("🏠 Գլխավոր", callback_data="go_home"))
    return txt, kb

@bot.callback_query_handler(func=lambda c: c.data.startswith("gt:"))
def gt_cb(c: types.CallbackQuery):
    parts = c.data.split(":")
    action = parts[1]
    if action == "new":
        if rate_limited(c.from_user.id, "gt_submit", 180):
            return bot.answer_callback_query(c.id, "Խնդրում ենք փորձել ավելի ուշ")
        STATE[c.from_user.id] = GT_TEXT
        FORM[c.from_user.id] = {}
        bot.answer_callback_query(c.id)
        bot.send_message(c.message.chat.id, "✍️ Գրեք ձեր մտածումը (մինչև 400 նիշ)։")
    elif action == "list" and len(parts)==3:
        p = int(parts[2])
        txt, kb = render_thoughts_page(p)
        bot.edit_message_text(txt, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)
        bot.answer_callback_query(c.id)

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id) == GT_TEXT)
def gt_collect_text(m: types.Message):
    t = (m.text or "").strip()
    if not t:
        return bot.send_message(m.chat.id, "Դատարկ է 🤔")
    if len(t) > 400:
        return bot.send_message(m.chat.id, "Կրճատեք մինչև 400 նիշ։")
    FORM[m.from_user.id]["text"] = t
    STATE[m.from_user.id] = GT_AUTHOR
    bot.send_message(m.chat.id, "✍️ Նշեք հեղինակին (կամ «—»)")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id) == GT_AUTHOR)
def gt_collect_author(m: types.Message):
    global NEXT_THOUGHT_ID
    author = (m.text or "—").strip() or "—"
    text = FORM.get(m.from_user.id, {}).get("text", "")
    th_id = NEXT_THOUGHT_ID; NEXT_THOUGHT_ID += 1
    sub = m.from_user.username or f"id{m.from_user.id}"
    PENDING_THOUGHTS[str(th_id)] = {
        "id": th_id,
        "text": f"{text}\n\n— {author}",
        "submitter_id": m.from_user.id,
        "submitter_name": sub,
        "created_at": datetime.utcnow().isoformat()
    }
    save_json(PENDING_THOUGHTS_FILE, PENDING_THOUGHTS)
    STATE[m.from_user.id] = None; FORM.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "✅ Ուղարկված է ադմինին հաստատման։")

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Հաստատել", callback_data=f"gtadm:ok:{th_id}"),
        types.InlineKeyboardButton("❌ Մերժել", callback_data=f"gtadm:no:{th_id}")
    )
    bot.send_message(ADMIN_ID, f"🧠 Նոր միտք #{th_id}\n\n{text}\n\n— {author}", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("gtadm:"))
def gt_admin(c: types.CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return bot.answer_callback_query(c.id, "Միայն ադմինը")
    _, act, th = c.data.split(":")
    item = PENDING_THOUGHTS.get(th)
    if not item:
        return bot.answer_callback_query(c.id, "Չի գտնվել")
    if act == "ok":
        GOOD_THOUGHTS.append({
            "id": item["id"],
            "text": item["text"],
            "posted_by": "@"+item["submitter_name"]
        })
        save_json(THOUGHTS_FILE, GOOD_THOUGHTS)
        PENDING_THOUGHTS.pop(th, None)
        save_json(PENDING_THOUGHTS_FILE, PENDING_THOUGHTS)
        bot.answer_callback_query(c.id, "Հաստատվեց")
    else:
        PENDING_THOUGHTS.pop(th, None)
        save_json(PENDING_THOUGHTS_FILE, PENDING_THOUGHTS)
        bot.answer_callback_query(c.id, "Մերժվեց")

# ---------- ADS (简化 ցուցադրում + submit–approve) ----------
AD_BNAME, AD_DESC, AD_WEB, AD_TG, AD_VIBER, AD_WA, AD_PHONE, AD_ADDR, AD_HOURS, AD_CTA_TEXT, AD_CTA_URL, AD_CONFIRM = range(12)

@bot.message_handler(func=lambda m: m.text == BTN_PARTNERS)
def partners(m: types.Message):
    txt, kb = render_ads_list(1)
    bot.send_message(m.chat.id, txt, parse_mode="HTML", reply_markup=kb)

def render_ads_list(page=1, per=5):
    active = [a for a in ADS_STORE if a.get("active")]
    total = len(active)
    if total==0:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("➕ Դառնալ գովազդատու", callback_data="ads:new"))
        kb.add(types.InlineKeyboardButton("🏠 Գլխավոր", callback_data="go_home"))
        return "Այս պահին առաջարկներ չկան։", kb
    page = max(1, min(page, (total+per-1)//per))
    s, e = (page-1)*per, (page-1)*per+per
    chunk = active[s:e]
    lines = ["📣 <b>Գովազդային առաջարկներ</b>", ""]
    kb = types.InlineKeyboardMarkup()
    for ad in chunk:
        lines.append(f"🏪 <b>{ad.get('title')}</b>")
        lines.append(f"📝 {ad.get('desc','')}")
        if ad.get("website"): lines.append(f"🌐 {ad['website']}")
        lines.append(f"Telegram: {ad.get('telegram','—')}")
        lines.append(f"Viber: {ad.get('viber','—')} | WhatsApp: {ad.get('whatsapp','—')}")
        lines.append(f"☎️ {ad.get('phone','—')} | 📍 {ad.get('address','—')}")
        lines.append("— — —")
        if ad.get("url"):
            kb.add(types.InlineKeyboardButton(ad.get("cta","Դիտել"), url=ad["url"]))
    nav=[]
    if s>0: nav.append(types.InlineKeyboardButton("⬅️ Նախորդ", callback_data=f"ads:page:{page-1}"))
    if e<total: nav.append(types.InlineKeyboardButton("Այժմոք ➡️", callback_data=f"ads:page:{page+1}"))
    if nav: kb.row(*nav)
    kb.add(types.InlineKeyboardButton("➕ Դառնալ գովազդատու", callback_data="ads:new"))
    kb.add(types.InlineKeyboardButton("🏠 Գլխավոր", callback_data="go_home"))
    return "\n".join(lines), kb

@bot.callback_query_handler(func=lambda c: c.data.startswith("ads:"))
def ads_cb(c: types.CallbackQuery):
    parts=c.data.split(":")
    if parts[1]=="page":
        p=int(parts[2]); txt,kb=render_ads_list(p)
        bot.edit_message_text(txt, c.message.chat.id, c.message.message_id, parse_mode="HTML", reply_markup=kb)
        bot.answer_callback_query(c.id)
    elif parts[1]=="new":
        STATE[c.from_user.id]=AD_BNAME; FORM[c.from_user.id]={}
        bot.answer_callback_query(c.id)
        bot.send_message(c.message.chat.id,"🏪 Գրեք խանութի/ծառայության անունը:")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id)==AD_BNAME)
def ad_bname(m: types.Message):
    FORM[m.from_user.id]["business_name"]=(m.text or "").strip()
    STATE[m.from_user.id]=AD_DESC
    bot.send_message(m.chat.id,"📝 Մարկետինգային նկարագրությունը (կարճ):")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id)==AD_DESC)
def ad_desc(m: types.Message):
    FORM[m.from_user.id]["desc"]=(m.text or "").strip()
    STATE[m.from_user.id]=AD_WEB
    bot.send_message(m.chat.id,"🌐 Վեբսայթ (կամ «—»):")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id)==AD_WEB)
def ad_web(m: types.Message):
    FORM[m.from_user.id]["website"]=(m.text or "").strip()
    STATE[m.from_user.id]=AD_TG
    bot.send_message(m.chat.id,"📲 Telegram (կամ «—»):")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id)==AD_TG)
def ad_tg(m: types.Message):
    FORM[m.from_user.id]["telegram"]=(m.text or "").strip()
    STATE[m.from_user.id]=AD_VIBER
    bot.send_message(m.chat.id,"📞 Viber (կամ «—»):")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id)==AD_VIBER)
def ad_viber(m: types.Message):
    FORM[m.from_user.id]["viber"]=(m.text or "").strip()
    STATE[m.from_user.id]=AD_WA
    bot.send_message(m.chat.id,"📞 WhatsApp (կամ «—»):")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id)==AD_WA)
def ad_wa(m: types.Message):
    FORM[m.from_user.id]["whatsapp"]=(m.text or "").strip()
    STATE[m.from_user.id]=AD_PHONE
    bot.send_message(m.chat.id,"☎️ Հեռախոս (կամ «—»):")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id)==AD_PHONE)
def ad_phone(m: types.Message):
    FORM[m.from_user.id]["phone"]=(m.text or "").strip()
    STATE[m.from_user.id]=AD_ADDR
    bot.send_message(m.chat.id,"📍 Հասցե (կամ «—»):")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id)==AD_ADDR)
def ad_addr(m: types.Message):
    FORM[m.from_user.id]["address"]=(m.text or "").strip()
    STATE[m.from_user.id]=AD_HOURS
    bot.send_message(m.chat.id,"🕒 Աշխ. ժամեր (կամ «—»):")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id)==AD_HOURS)
def ad_hours(m: types.Message):
    FORM[m.from_user.id]["hours"]=(m.text or "").strip()
    STATE[m.from_user.id]=AD_CTA_TEXT
    bot.send_message(m.chat.id,"🔘 CTA տեքստ (օր. «Պատվիրել»):")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id)==AD_CTA_TEXT)
def ad_cta_text(m: types.Message):
    FORM[m.from_user.id]["cta_text"]=(m.text or "Դիտել").strip() or "Դիտել"
    STATE[m.from_user.id]=AD_CTA_URL
    bot.send_message(m.chat.id,"🔗 CTA URL (կամ «—»):")

@bot.message_handler(func=lambda m: STATE.get(m.from_user.id)==AD_CTA_URL)
def ad_cta_url(m: types.Message):
    FORM[m.from_user.id]["cta_url"]=(m.text or "").strip()
    STATE[m.from_user.id]=AD_CONFIRM
    d=FORM[m.from_user.id]
    prev=(
        f"📣 <b>Գովազդի հայտ — նախադիտում</b>\n\n"
        f"🏪 {d.get('business_name')}\n"
        f"📝 {d.get('desc')}\n"
        f"🌐 {d.get('website')}\n"
        f"Telegram: {d.get('telegram')} | Viber: {d.get('viber')} | WhatsApp: {d.get('whatsapp')}\n"
        f"☎️ {d.get('phone')} | 📍 {d.get('address')} | 🕒 {d.get('hours')}\n"
        f"🔘 {d.get('cta_text')} → {d.get('cta_url')}\n\n"
        f"✅ Հաստատե՞լ ադմինին ուղարկելը:"
    )
    kb=types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Ուղարկել ադմինին", callback_data="ad:send"))
    kb.add(types.InlineKeyboardButton("❌ Չեղարկել", callback_data="ad:cancel"))
    bot.send_message(m.chat.id, prev, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ("ad:send","ad:cancel"))
def ad_send(c: types.CallbackQuery):
    if c.data=="ad:cancel":
        STATE[c.from_user.id]=None; FORM.pop(c.from_user.id, None)
        bot.answer_callback_query(c.id, "Չեղարկվեց")
        try: bot.edit_message_text("Չեղարկվեց", c.message.chat.id, c.message.message_id)
        except: pass
        return
    d=FORM.get(c.from_user.id, {})
    if not d:
        return bot.answer_callback_query(c.id,"Տվյալներ չկան")
    global NEXT_AD_ID
    ad_id=NEXT_AD_ID; NEXT_AD_ID+=1
    PENDING_ADS[str(ad_id)] = {
        "id": ad_id, "submitter_id": c.from_user.id,
        "submitter_name": c.from_user.username or f"id{c.from_user.id}",
        **d, "created_at": datetime.utcnow().isoformat()
    }
    save_json(PENDING_ADS_FILE, PENDING_ADS)
    STATE[c.from_user.id]=None; FORM.pop(c.from_user.id, None)
    bot.answer_callback_query(c.id,"Ուղարկվեց ադմինին")
    try: bot.edit_message_text("✅ Ուղարկվեց ադմինին հաստատման", c.message.chat.id, c.message.message_id)
    except: pass

    kb=types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Հաստատել", callback_data=f"adadm:ok:{ad_id}"))
    kb.add(types.InlineKeyboardButton("❌ Մերժել", callback_data=f"adadm:no:{ad_id}"))
    a=PENDING_ADS[str(ad_id)]
    admin_txt=(f"📣 Նոր գովազդ #{ad_id}\n\n"
               f"🏪 {a.get('business_name')}\n📝 {a.get('desc')}\n🌐 {a.get('website')}\n"
               f"TG:{a.get('telegram')} | Viber:{a.get('viber')} | WA:{a.get('whatsapp')}\n"
               f"☎️ {a.get('phone')} | 📍 {a.get('address')} | 🕒 {a.get('hours')}\n"
               f"🔘 {a.get('cta_text')} → {a.get('cta_url')}")
    bot.send_message(ADMIN_ID, admin_txt, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adadm:"))
def ad_admin(c: types.CallbackQuery):
    if c.from_user.id!=ADMIN_ID:
        return bot.answer_callback_query(c.id,"Միայն ադմինը")
    _,act,aid=c.data.split(":")
    item=PENDING_ADS.get(aid)
    if not item: return bot.answer_callback_query(c.id,"Չի գտնվել")
    if act=="ok":
        ADS_STORE.append({
            "id": item["id"], "title": item["business_name"],
            "desc": item["desc"], "website": item["website"],
            "telegram": item["telegram"], "viber": item["viber"], "whatsapp": item["whatsapp"],
            "phone": item["phone"], "address": item["address"], "hours": item["hours"],
            "cta": item["cta_text"] or "Դիտել", "url": item["cta_url"] or "", "active": True
        })
        save_json(ADS_FILE, ADS_STORE)
        PENDING_ADS.pop(aid, None); save_json(PENDING_ADS_FILE, PENDING_ADS)
        bot.answer_callback_query(c.id,"Հաստատվեց")
    else:
        PENDING_ADS.pop(aid, None); save_json(PENDING_ADS_FILE, PENDING_ADS)
        bot.answer_callback_query(c.id,"Մերժվեց")

# ---------- SHOP + PRODUCTS + SLIDER + CART ----------
PRODUCTS = {
    # Demo items (you can extend)
    "BA100810": {
        "title": "Գորգ – BA100810", "category": "home",
        "images": [
            "media/products/BA100810.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 320, "best": True,
        "bullets": ["Չսահող հիմք", "Հեշտ լվացվող", "Արագ չորացում"],
        "long_desc": "Թիթեռ–ծաղիկ 3D դիզայն, հարմար մուտք/լոգարան/խոհանոց։",
        "stock": 999
    },
    "BA100811": {
        "title": "Գորգ – BA100811", "category": "home",
        "images": [
            "media/products/BA100811.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 295, "best": True,
        "bullets": ["Խիտ գործվածք", "Անհոտ նյութեր"],
        "long_desc": "Մինիմալիստական գույներ՝ ցանկացած ինտերիերի համար։",
        "stock": 999
    },
}

def shop_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⌚ Սմարթ ժամացույցներ", "💻 Համակարգչային աքսեսուարներ")
    kb.add("🚗 Ավտոմեքենայի պարագաներ", "🏠 Կենցաղային պարագաներ")
    kb.add("🍳 Խոհանոցային տեխնիկա", "💅 Խնամքի պարագաներ")
    kb.add("🚬 Էլեկտրոնային ծխախոտ", "👩 Կանացի (շուտով)")
    kb.add("👨 Տղամարդու (շուտով)", "🧒 Մանկական (շուտով)")
    kb.add(BTN_MAIN)
    return kb

@bot.message_handler(func=lambda m: m.text == BTN_SHOP)
def shop_menu(m: types.Message):
    bot.send_message(m.chat.id, "🛍 Խանութ — ընտրեք կատեգորիա 👇", reply_markup=shop_keyboard())

def codes_by_category(cat):
    return [code for code,p in PRODUCTS.items() if p.get("category")==cat]

@bot.message_handler(func=lambda m: m.text == "🏠 Կենցաղային պարագաներ")
def home_cat(m: types.Message):
    for code in codes_by_category("home"):
        p = PRODUCTS[code]
        main_img = (p.get("images") or [None])[0]
        discount = int(round(100 - (p["price"]*100/p["old_price"])))
        best = "🔥 Լավագույն վաճառվող\n" if p.get("best") else ""
        caption = (
            f"{best}<b>{p['title']}</b>\n"
            f"Չափս՝ {p['size']}\n"
            f"Հին գին — {p['old_price']}֏ (−{discount}%)\n"
            f"Նոր գին — <b>{p['price']}֏</b>\n"
            f"Կոդ՝ <code>{code}</code>"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("👀 Դիտել ամբողջությամբ", callback_data=f"p:{code}"))
        try:
            if main_img and os.path.exists(main_img):
                with open(main_img,"rb") as ph:
                    bot.send_photo(m.chat.id, ph, caption=caption, parse_mode="HTML", reply_markup=kb)
            else:
                bot.send_message(m.chat.id, caption, parse_mode="HTML", reply_markup=kb)
        except:
            bot.send_message(m.chat.id, caption, parse_mode="HTML", reply_markup=kb)
        time.sleep(0.15)
    back = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back.add("⬅️ Վերադառնալ խանութ", BTN_MAIN)
    bot.send_message(m.chat.id, "📎 Վերևում տեսեք քարտիկները։", reply_markup=back)

@bot.message_handler(func=lambda m: m.text == "⬅️ Վերադառնալ խանութ")
def back_to_shop(m: types.Message):
    shop_menu(m)

@bot.callback_query_handler(func=lambda c: c.data.startswith("p:"))
def show_product(c: types.CallbackQuery):
    code = c.data.split(":",1)[1]
    p = PRODUCTS.get(code)
    if not p:
        return bot.answer_callback_query(c.id, "Չի գտնվել")
    discount = int(round(100 - (p["price"]*100/p["old_price"])))
    bullets = "\n".join([f"✅ {b}" for b in p.get("bullets",[])])
    caption = (
        f"🌸 <b>{p['title']}</b>\n"
        f"✔️ Չափս՝ {p['size']}\n"
        f"{bullets}\n\n{p.get('long_desc','')}\n\n"
        f"Հին գին — {p['old_price']}֏ (−{discount}%)\n"
        f"Նոր գին — <b>{p['price']}֏</b>\n"
        f"Վաճառված — {p.get('sold',0)} հատ\n"
        f"Կոդ՝ <code>{code}</code>"
    )
    imgs = [x for x in p.get("images",[]) if x and os.path.exists(x)]
    kb = slider_kb(code, 0, max(1,len(imgs)))
    if imgs:
        with open(imgs[0],"rb") as ph:
            bot.send_photo(c.message.chat.id, ph, caption=caption, parse_mode="HTML", reply_markup=kb)
    else:
        bot.send_message(c.message.chat.id, caption, parse_mode="HTML", reply_markup=kb)
    bot.answer_callback_query(c.id)

def slider_kb(code, idx, total):
    kb = types.InlineKeyboardMarkup()
    if total>1:
        kb.row(
            types.InlineKeyboardButton("◀️", callback_data=f"slider:{code}:{(idx-1)%total}"),
            types.InlineKeyboardButton("▶️", callback_data=f"slider:{code}:{(idx+1)%total}")
        )
    kb.row(
        types.InlineKeyboardButton("➕ Ավելացնել զամբյուղ", callback_data=f"cart:add:{code}"),
        types.InlineKeyboardButton("🧺 Դիտել զամբյուղ", callback_data="cart:show")
    )
    kb.row(
        types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="go_home")
    )
    return kb

@bot.callback_query_handler(func=lambda c: c.data.startswith("slider:"))
def product_slider(c: types.CallbackQuery):
    _, code, idx_str = c.data.split(":")
    p = PRODUCTS.get(code,{})
    imgs = [x for x in p.get("images",[]) if x and os.path.exists(x)]
    total = max(1, len(imgs))
    idx = int(idx_str) % total
    discount = int(round(100 - (p.get("price",0)*100/max(1,p.get("old_price",1)))))
    bullets = "\n".join([f"✅ {b}" for b in p.get("bullets",[])])
    caption = (
        f"🌸 <b>{p.get('title','')}</b>\n"
        f"✔️ Չափս՝ {p.get('size','')}\n"
        f"{bullets}\n\n{p.get('long_desc','')}\n\n"
        f"Հին գին — {p.get('old_price',0)}֏ (−{discount}%)\n"
        f"Նոր գին — <b>{p.get('price',0)}֏</b>\n"
        f"Վաճառված — {p.get('sold',0)} հատ\n"
        f"Կոդ՝ <code>{code}</code>"
    )
    try:
        if imgs:
            with open(imgs[idx], "rb") as ph:
                media = InputMediaPhoto(ph, caption=caption, parse_mode="HTML")
                bot.edit_message_media(media=media, chat_id=c.message.chat.id, message_id=c.message.message_id,
                                       reply_markup=slider_kb(code, idx, total))
        else:
            bot.edit_message_caption(chat_id=c.message.chat.id, message_id=c.message.message_id,
                                     caption=caption, parse_mode="HTML",
                                     reply_markup=slider_kb(code, idx, total))
    except:
        # fallback send new
        if imgs:
            with open(imgs[idx],"rb") as ph:
                bot.send_photo(c.message.chat.id, ph, caption=caption, parse_mode="HTML",
                               reply_markup=slider_kb(code, idx, total))
        else:
            bot.send_message(c.message.chat.id, caption, parse_mode="HTML",
                             reply_markup=slider_kb(code, idx, total))
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data in ("back:home_list","go_home"))
def back_buttons(c: types.CallbackQuery):
    if c.data=="back:home_list":
        # show home category again
        msg = types.SimpleNamespace(chat=c.message.chat)  # fake object with chat
        home_cat(msg)
    else:
        bot.send_message(c.message.chat.id, "Գլխավոր մենյու ✨", reply_markup=build_main_menu())
    bot.answer_callback_query(c.id)

# ---------- CART & CHECKOUT ----------
CART = defaultdict(dict)  # uid -> {code: qty}
CHECKOUT = {}             # uid -> {"step":..., "order":...}

def cart_text(uid:int)->str:
    if not CART[uid]: return "🧺 Զամբյուղը դատարկ է"
    total=0; lines=[]
    for code,qty in CART[uid].items():
        p=PRODUCTS[code]; sub=int(p["price"])*qty; total+=sub
        lines.append(f"• {p['title']} × {qty} — {sub}֏")
    lines.append(f"\nԸնդամենը՝ <b>{total}֏</b>")
    return "\n".join(lines), total

@bot.message_handler(func=lambda m: m.text == BTN_CART)
def open_cart_menu(m: types.Message):
    show_cart(m.chat.id)

def show_cart(chat_id: int):
    # inline controls
    uid = chat_id
    kb = types.InlineKeyboardMarkup()
    for code,qty in list(CART[uid].items())[:6]:
        title = PRODUCTS[code]["title"]
        kb.row(types.InlineKeyboardButton(f"🛒 {title} ({qty})", callback_data="noop"))
        kb.row(
            types.InlineKeyboardButton("➖", callback_data=f"cart:dec:{code}"),
            types.InlineKeyboardButton("➕", callback_data=f"cart:inc:{code}"),
            types.InlineKeyboardButton("🗑", callback_data=f"cart:rm:{code}")
        )
    kb.row(
        types.InlineKeyboardButton("❌ Մաքրել", callback_data="cart:clear"),
        types.InlineKeyboardButton("🧾 Ավարտել պատվերը", callback_data="checkout:start")
    )
    kb.row(
        types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="go_home")
    )
    txt,_ = cart_text(uid)
    bot.send_message(chat_id, txt, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cart:") or c.data=="cart:show")
def cart_cb(c: types.CallbackQuery):
    uid = c.from_user.id
    if c.data=="cart:show":
        show_cart(c.message.chat.id); return bot.answer_callback_query(c.id)
    parts=c.data.split(":")
    act = parts[1] if len(parts)>1 else None
    code = parts[2] if len(parts)>2 else None
    if act=="add" and code:
        st = PRODUCTS[code].get("stock")
        new_q = CART[uid].get(code, 0) + 1
        if isinstance(st,int) and new_q>st:
            return bot.answer_callback_query(c.id,"Պահեստում բավարար քանակ չկա")
        CART[uid][code] = new_q
        bot.answer_callback_query(c.id, "Ավելացվեց ✅")
    elif act=="inc" and code:
        st = PRODUCTS[code].get("stock")
        new_q = CART[uid].get(code, 0) + 1
        if isinstance(st,int) and new_q>st:
            return bot.answer_callback_query(c.id,"Պահեստի սահման")
        CART[uid][code] = new_q
    elif act=="dec" and code:
        q=CART[uid].get(code,0)
        if q<=1: CART[uid].pop(code, None)
        else: CART[uid][code]=q-1
    elif act=="rm" and code:
        CART[uid].pop(code, None)
    elif act=="clear":
        CART[uid].clear()

    # refresh cart
    kb = types.InlineKeyboardMarkup()
    for code,qty in list(CART[uid].items())[:6]:
        title = PRODUCTS[code]["title"]
        kb.row(types.InlineKeyboardButton(f"🛒 {title} ({qty})", callback_data="noop"))
        kb.row(
            types.InlineKeyboardButton("➖", callback_data=f"cart:dec:{code}"),
            types.InlineKeyboardButton("➕", callback_data=f"cart:inc:{code}"),
            types.InlineKeyboardButton("🗑", callback_data=f"cart:rm:{code}")
        )
    kb.row(
        types.InlineKeyboardButton("❌ Մաքրել", callback_data="cart:clear"),
        types.InlineKeyboardButton("🧾 Ավարտել պատվերը", callback_data="checkout:start")
    )
    kb.row(
        types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="go_home")
    )
    txt,_ = cart_text(uid)
    bot.send_message(c.message.chat.id, txt, parse_mode="HTML", reply_markup=kb)
    bot.answer_callback_query(c.id)

def order_id():
    return "ORD-" + datetime.utcnow().strftime("%Y%m%d-%H%M%S")

COUNTRIES=["Հայաստան"]
CITIES=["Երևան","Գյումրի","Վանաձոր","Աբովյան","Արտաշատ","Արմավիր","Հրազդան","Մասիս","Աշտարակ","Եղվարդ","Չարենցավան"]

@bot.callback_query_handler(func=lambda c: c.data=="checkout:start")
def checkout_start(c: types.CallbackQuery):
    uid=c.from_user.id
    if not CART[uid]:
        bot.answer_callback_query(c.id,"Զամբյուղը դատարկ է"); return
    total=sum(int(PRODUCTS[k]["price"])*q for k,q in CART[uid].items())
    oid=order_id()
    CHECKOUT[uid]={
        "step":"name",
        "order":{
            "order_id": oid, "user_id": uid, "username": c.from_user.username,
            "fullname":"", "phone":"", "country":"", "city":"", "address":"", "comment":"",
            "items":[{"code":k,"qty":q} for k,q in CART[uid].items()],
            "total": total, "status":"Draft",
            "payment":{"method":"","amount":0,"tx":"","state":"Pending"},
            "created_at": datetime.utcnow().isoformat()
        }
    }
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, f"🧾 Պատվեր {oid}\nԳրեք Ձեր <b>Անուն Ազգանուն</b>։", parse_mode="HTML")

@bot.message_handler(func=lambda m: CHECKOUT.get(m.from_user.id,{}).get("step")=="name")
def ch_name(m: types.Message):
    CHECKOUT[m.from_user.id]["order"]["fullname"]=(m.text or "").strip()
    CHECKOUT[m.from_user.id]["step"]="phone"
    bot.send_message(m.chat.id,"📞 Գրեք Ձեր <b>հեռախոսահամարը</b>։", parse_mode="HTML")

@bot.message_handler(func=lambda m: CHECKOUT.get(m.from_user.id,{}).get("step")=="phone")
def ch_phone(m: types.Message):
    t="".join(ch for ch in (m.text or "") if ch.isdigit())
    if len(t)<8: return bot.send_message(m.chat.id,"❗ Թվերի քանակը քիչ է, փորձեք կրկին")
    CHECKOUT[m.from_user.id]["order"]["phone"]=t
    CHECKOUT[m.from_user.id]["step"]="country"
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for c in COUNTRIES: kb.add(c)
    bot.send_message(m.chat.id,"🌍 Ընտրեք <b>երկիր</b>:", parse_mode="HTML", reply_markup=kb)

@bot.message_handler(func=lambda m: CHECKOUT.get(m.from_user.id,{}).get("step")=="country")
def ch_country(m: types.Message):
    CHECKOUT[m.from_user.id]["order"]["country"]=m.text.strip()
    CHECKOUT[m.from_user.id]["step"]="city"
    kb=types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for c in CITIES: kb.add(c)
    bot.send_message(m.chat.id,"🏙 Ընտրեք <b>քաղաք</b>:", parse_mode="HTML", reply_markup=kb)

@bot.message_handler(func=lambda m: CHECKOUT.get(m.from_user.id,{}).get("step")=="city")
def ch_city(m: types.Message):
    CHECKOUT[m.from_user.id]["order"]["city"]=m.text.strip()
    CHECKOUT[m.from_user.id]["step"]="address"
    bot.send_message(m.chat.id,"📦 Գրեք <b>հասցե/մասնաճյուղ</b>:", parse_mode="HTML")

@bot.message_handler(func=lambda m: CHECKOUT.get(m.from_user.id,{}).get("step")=="address")
def ch_addr(m: types.Message):
    CHECKOUT[m.from_user.id]["order"]["address"]=m.text.strip()
    CHECKOUT[m.from_user.id]["step"]="comment"
    bot.send_message(m.chat.id,"✍️ Մեկնաբանություն (ըստ ցանկության)՝ գրեք կամ «—»")

@bot.message_handler(func=lambda m: CHECKOUT.get(m.from_user.id,{}).get("step")=="comment")
def ch_comment(m: types.Message):
    CHECKOUT[m.from_user.id]["order"]["comment"] = (m.text.strip() if m.text.strip()!="—" else "")
    CHECKOUT[m.from_user.id]["step"]="paymethod"
    kb=types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Քարտ", callback_data="paym:CARD"),
           types.InlineKeyboardButton("TelCell", callback_data="paym:TELCELL"))
    kb.add(types.InlineKeyboardButton("Idram", callback_data="paym:IDRAM"),
           types.InlineKeyboardButton("Fastshift", callback_data="paym:FASTSHIFT"))
    bot.send_message(m.chat.id,"💳 Ընտրեք <b>վճարման եղանակը</b>:", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("paym:"))
def choose_method(c: types.CallbackQuery):
    method=c.data.split(":")[1]
    s=CHECKOUT.get(c.from_user.id)
    if not s: return bot.answer_callback_query(c.id,"Սկսեք նորից")
    s["order"]["payment"]["method"]=method
    s["step"]="payamount"
    details = {
        "CARD":"💳 Քարտ՝ 5355 **** **** 1234\nՍտացող՝ Your Name",
        "TELCELL":"🏧 TelCell՝ Account: 123456",
        "IDRAM":"📱 Idram ID: 123456789",
        "FASTSHIFT":"💠 Fastshift Wallet: fast_shift_acc",
    }.get(method,"Մանրամասները ճշտեք ադմինից")
    total = s["order"]["total"]
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id,
        f"{details}\n\nՍտանդարտ գումարը՝ <b>{total}֏</b>\n"
        f"✅ Կարող եք ուղարկել ավելին, տարբերությունը կհաշվվի որպես Wallet.\n\n"
        f"Գրեք ուղարկած գումարը՝ թվերով (֏):",
        parse_mode="HTML")

@bot.message_handler(func=lambda m: CHECKOUT.get(m.from_user.id,{}).get("step")=="payamount")
def ch_amount(m: types.Message):
    try:
        amount = int("".join(ch for ch in (m.text or "") if ch.isdigit()))
    except:
        return bot.send_message(m.chat.id,"Մուտքագրեք գումարը՝ օրինակ 1300")
    s=CHECKOUT[m.from_user.id]
    s["order"]["payment"]["amount"]=amount
    s["step"]="confirm"
    kb=types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Հաստատել պատվերը", callback_data="order:confirm"))
    kb.add(types.InlineKeyboardButton("❌ Չեղարկել", callback_data="order:cancel"))
    t = s["order"]
    items = "\n".join([f"• {PRODUCTS[i['code']]['title']} × {i['qty']}" for i in t["items"]])
    bot.send_message(m.chat.id,
        f"🧾 <b>Պատվերի ամփոփում</b>\n\n{items}\n\n"
        f"Ընդամենը՝ <b>{t['total']}֏</b>\n"
        f"Վճարում՝ {t['payment']['method']} | Գումար՝ {t['payment']['amount']}֏",
        parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("order:"))
def order_confirm(c: types.CallbackQuery):
    s=CHECKOUT.get(c.from_user.id)
    if not s: return bot.answer_callback_query(c.id,"Սկսեք նորից")
    act=c.data.split(":")[1]
    if act=="cancel":
        CHECKOUT.pop(c.from_user.id, None)
        bot.answer_callback_query(c.id,"Չեղարկվեց")
        return
    # confirm
    order=s["order"]
    order["status"]="Awaiting Admin Confirm"
    ORDERS.append(order); save_json(ORDERS_FILE, ORDERS)
    # admin notify
    items = "\n".join([f"• {PRODUCTS[i['code']]['title']} × {i['qty']}" for i in order["items"]])
    admin_txt=(f"🆕 Նոր պատվեր {order['order_id']}\n"
               f"👤 {order['fullname']} | 📞 {order['phone']}\n"
               f"📍 {order['country']}, {order['city']} | {order['address']}\n"
               f"🛒\n{items}\n"
               f"💰 Ընդամենը՝ {order['total']}֏ | Վճարել է՝ {order['payment']['amount']}֏\n"
               f"💳 {order['payment']['method']}\n"
               f"📝 {order['comment'] or '—'}\n"
               f"user @{order['username'] or '—'} (id {order['user_id']})")
    bot.send_message(ADMIN_ID, admin_txt)
    # user
    CART[c.from_user.id].clear()
    CHECKOUT.pop(c.from_user.id, None)
    bot.answer_callback_query(c.id,"Գրանցվեց")
    bot.send_message(c.message.chat.id,"✅ Պատվերը գրանցվեց։ Ադմինը շուտով կհաստատի։")

# ---------- SIMPLE PROFILE / FEEDBACK ----------
@bot.message_handler(func=lambda m: m.text == BTN_PROFILE)
def my_page(m: types.Message):
    bot.send_message(m.chat.id, "👤 Իմ էջը\n(շուտով՝ պատվերների պատմություն, վաուչերներ, և այլն)")

@bot.message_handler(func=lambda m: m.text == BTN_FEEDBACK)
def feedback(m: types.Message):
    bot.send_message(m.chat.id, "✉️ Կապ՝ @your_contact կամ գրեք այստեղ՝ մենք կպատասխանենք։")

# ---------- EXCHANGE PLACEHOLDER ----------
@bot.message_handler(func=lambda m: m.text == BTN_EXCHANGE)
def exchange_menu(m: types.Message):
    bot.send_message(m.chat.id, "💱 Փոխարկումներ — PI➝USDT, FTN➝AMD, Alipay (կոդը պատրաստ է ավելացնելու)")

# ---------- SEARCH PLACEHOLDER ----------
@bot.message_handler(func=lambda m: m.text == BTN_SEARCH)
def search(m: types.Message):
    bot.send_message(m.chat.id, "🔍 Գրեք ապրանքի անունը/կոդը՝ (շուտով smart որոնում)")

# ---------- MAIN MENU BTN ----------
@bot.message_handler(func=lambda m: m.text == BTN_MAIN)
def go_main(m: types.Message):
    bot.send_message(m.chat.id, "Գլխավոր մենյու ✨", reply_markup=build_main_menu())

# ---------- ADMIN PANEL (թեթև) ----------
def is_admin(uid:int)->bool: return int(uid)==int(ADMIN_ID)

@bot.message_handler(commands=["admin"])
def open_admin(m: types.Message):
    if not is_admin(m.from_user.id):
        return bot.reply_to(m,"❌ Դուք ադմին չեք")
    kb=types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📊 Ping", callback_data="adm:ping"))
    kb.add(types.InlineKeyboardButton("👥 Users", callback_data="adm:users"))
    kb.add(types.InlineKeyboardButton("🧾 Orders", callback_data="adm:orders"))
    bot.send_message(m.chat.id,"🛠 Ադմին պանել", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm:"))
def admin_cb(c: types.CallbackQuery):
    if not is_admin(c.from_user.id):
        return bot.answer_callback_query(c.id,"Ոչ ադմին")
    act=c.data.split(":")[1]
    if act=="ping":
        bot.answer_callback_query(c.id,"OK")
        bot.edit_message_text(f"🟢 Pong\nUTC: {datetime.utcnow().isoformat()}Z", c.message.chat.id, c.message.message_id)
    elif act=="users":
        lst=list(USERS.keys())[:20]
        bot.answer_callback_query(c.id)
        bot.edit_message_text("👥 Վերջին users (ID-ներ)\n"+"\n".join(lst or ["—"]),
                              c.message.chat.id, c.message.message_id)
    elif act=="orders":
        bot.answer_callback_query(c.id)
        bot.edit_message_text(f"🧾 Պատվերների քանակ՝ {len(ORDERS)}", c.message.chat.id, c.message.message_id)

# ---------- RUN ----------
if __name__ == "__main__":
    print("dotenv path:", find_dotenv())
    print("BOT_TOKEN len:", len(BOT_TOKEN))
    print("Bot is running...")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
