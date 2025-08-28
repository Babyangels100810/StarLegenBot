import os, json, time, traceback
from datetime import datetime
from telebot import TeleBot, types
from dotenv import load_dotenv, find_dotenv
from telebot import apihelper
from telebot.types import InputMediaPhoto
from collections import defaultdict
import os, json, time, threading, traceback, datetime
import re
import requests
from datetime import datetime
from collections import defaultdict
import re

# ===== STORAGE =====
CART = defaultdict(dict)         # {user_id: {code: qty}}
CHECKOUT_STATE = {}              # per-user checkout wizard state
ORDERS = []                      # demo storage

# ===== BUTTONS =====
BTN_BACK_MAIN = "⬅ Վերադառնալ գլխավոր մենյու"
# ===== CHECKOUT LISTS =====
COUNTRIES = ["Հայաստան"]
CITIES = ["Երևան","Գյումրի","Վանաձոր","Աբովյան","Արտաշատ","Արմավիր","Հրազդան","Մասիս","Աշտարակ","Եղվարդ","Չարենցավան"]
def _set_step(uid: int, step: str):
    if uid in CHECKOUT_STATE:
        CHECKOUT_STATE[uid]["step"] = step

def _ask_name(chat_id: int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_BACK_MAIN)
    bot.send_message(chat_id, "✍️ Գրեք ձեր **Անուն Ազգանուն** (առնվազն 3 նիշ):", reply_markup=kb, parse_mode="Markdown")

def _ask_phone(chat_id: int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_BACK_MAIN)
    bot.send_message(chat_id, "📞 Մուտքագրեք ձեր հեռախոսահամարը՝ **+374xxxxxxxx** կամ **0xxxxxxxx**:", reply_markup=kb, parse_mode="Markdown")

def _ask_country(chat_id: int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for c in COUNTRIES:
        kb.add(c)
    kb.add(BTN_BACK_MAIN)
    bot.send_message(chat_id, "🌍 Ընտրեք երկիրը՝", reply_markup=kb)

def _ask_city(chat_id: int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    for name in CITIES:
        kb.add(name)
    kb.add(BTN_BACK_MAIN)
    bot.send_message(chat_id, "🏙 Ընտրեք քաղաքը՝", reply_markup=kb)

def _ask_address(chat_id: int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_BACK_MAIN)
    bot.send_message(chat_id, "🏠 Գրեք հասցեն (փողոց, շենք, բնակարան, նշումներ):", reply_markup=kb)

def _finalize_order(uid: int, chat_id: int):
    order = CHECKOUT_STATE[uid]["order"]
    order["status"] = "Pending"
    ORDERS.append(order)

    # քլին ենք անում զամբյուղն ու checkout state-ը
    CART[uid].clear()
    CHECKOUT_STATE.pop(uid, None)

    # ✅ Վերջնական հաղորդագրություն + ավտոմատ վերադարձ գլխավոր մենյու
    bot.send_message(
        chat_id,
        "✅ Պատվերը գրանցվեց։ Մեր օպերատորը շուտով կապ կհաստատի։ Շնորհակալություն 🌸"
    )
    show_main_menu(chat_id, "Գլխավոր մենյու ✨")

# ===== MAIN MENU =====
def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🛍 Խանութ", "🛒 Զամբյուղ")
    kb.add("💱 Փոխարկումներ", "💬 Կապ մեզ հետ")
    kb.add("🔍 Որոնել ապրանք", "🧍 Իմ էջը")
    return kb

def show_main_menu(chat_id, text="Գլխավոր մենյու ✨"):
    bot.send_message(chat_id, text, reply_markup=main_menu_kb())
    # 🔙 Վերադառնալ գլխավոր մենյու
@bot.message_handler(func=lambda m: m.text in ("⬅️ Վերադառնալ գլխավոր մենյու", "🏠 Գլխավոր մենյու"))
def back_main_msg(m: types.Message):
    try:
        CHECKOUT_STATE.pop(m.from_user.id, None)
    except Exception:
        pass
    show_main_menu(m.chat.id, "Վերադարձաք գլխավոր մենյու։ ✨")

# ===== VALIDATION REGEX =====
NAME_RE  = re.compile(r"^[A-Za-z\u0531-\u0556\u0561-\u0587ЁёЪъЫыЭэЙй\s'\-\.]{3,60}$")
PHONE_RE = re.compile(r"^(\+374|0)\d{8}$")


# դեպի Telegram API ճիշտ URL
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"

# .env
load_dotenv()
ENV_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
print("dotenv path:", find_dotenv())
print("BOT_TOKEN raw:", repr(ENV_TOKEN))
print("BOT_TOKEN len:", len(ENV_TOKEN))

# ------------------- CONFIG / CONSTANTS -------------------
DATA_DIR = "data"
MEDIA_DIR = "media"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
THOUGHTS_FILE = os.path.join(DATA_DIR, "thoughts.json")
PENDING_THOUGHTS_FILE = os.path.join(DATA_DIR, "pending_thoughts.json")
ADS_FILE = os.path.join(DATA_DIR, "ads.json")
PENDING_ADS_FILE = os.path.join(DATA_DIR, "pending_ads.json")

ADMIN_ID = 6822052289
RL_THOUGHT_SUBMIT_SEC = 180
RL_AD_SUBMIT_SEC = 300

# ------------------- HELPERS: FILE IO -------------------
def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(os.path.join(MEDIA_DIR, "exchange"), exist_ok=True)
    os.makedirs(os.path.join(MEDIA_DIR, "products"), exist_ok=True)

# ------------------- BOT INIT -------------------
ensure_dirs()

# token՝ ENV > SETTINGS
BOT_TOKEN = ENV_TOKEN or (SETTINGS.get("bot_token") or "")
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is empty. Put it in your .env or settings.json")


bot = TeleBot(BOT_TOKEN, parse_mode="Markdown")
# === ADMIN PANEL + HEALTH-CHECK (drop-in block) ==============================
# ՊԱՏՍՏԱՑՐԵԼ՝ տեղադրել bot = telebot.TeleBot(TOKEN) տողի ՀԵՏՈ մեկ անգամ
# ՏԵՂԱՓՈԽԵԼ՝ ADMIN_ID-ն քո իրական Telegram ID-ով
# ============================================================================
# --- ԿԱՐԵՎՈՐ ԿԱՐԳԱՎՈՐՄԱՆԸ ---
ADMIN_ID = int(os.getenv("ADMIN_ID", "6822052289"))  # ← փոխիր, եթե պետք է

# --- Ֆայլային պահեստ ---
DATA_DIR = "admin_data"
os.makedirs(DATA_DIR, exist_ok=True)
USERS_FILE = os.path.join(DATA_DIR, "users.json")
MSG_LOG   = os.path.join(DATA_DIR, "messages.log")
ERR_LOG   = os.path.join(DATA_DIR, "errors.log")

def _load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_users(data):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        _log_error(e)

def _log_message(line: str):
    try:
        with open(MSG_LOG, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")
    except Exception as e:
        _log_error(e)

def _log_error(e):
    try:
        with open(ERR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.utcnow().isoformat()}Z] {repr(e)}\n")
            f.write(traceback.format_exc() + "\n")
    except:
        pass

# --- UPTIME / HEALTH ---
START_TS = time.time()
LAST_ERROR_TEXT = "չկա"

def _set_last_error_text(text: str):
    global LAST_ERROR_TEXT
    LAST_ERROR_TEXT = text

# --- Թեթև keep-alive թել (ոչինչ չի անում, պարզապես պահում ենք կենդանի վիճակը) ---
def _keepalive_thread():
    while True:
        time.sleep(60)  # ամեն 60վ մի փոքր շնչում է
t = threading.Thread(target=_keepalive_thread, daemon=True)
t.start()

# --- Քո բոտի բոլոր update-ները "լսելու" hook (չի խանգարում հենդլերներին) ---
def _update_listener(updates):
    # updates-ը list է՝ message/update օբյեկտներով
    for u in updates:
        try:
            if getattr(u, "content_type", None):  # message
                _capture_user_and_log(u)
        except Exception as e:
            _set_last_error_text(str(e))
            _log_error(e)

# Կցում ենք listener-ը (ՉԻ ՓՈԽՈՒՄ քո գործող հենդլերները)
try:
    bot.set_update_listener(_update_listener)
except Exception as e:
    _set_last_error_text("set_update_listener failed")
    _log_error(e)

# --- Օգտատերերի և հաղորդագրությունների ավտոմատ գրանցում ---
def _capture_user_and_log(m):
    # user bookkeeping
    users = _load_users()
    u = m.from_user
    uid = str(u.id)
    users.setdefault(uid, {
        "id": u.id,
        "first_name": u.first_name or "",
        "last_name": u.last_name or "",
        "username": u.username or "",
        "lang": u.language_code or "",
        "joined_at": datetime.datetime.utcnow().isoformat() + "Z",
        "messages": 0,
        "last_seen": "",
        "blocked": False
    })
    users[uid]["messages"] += 1
    users[uid]["last_seen"] = datetime.datetime.utcnow().isoformat() + "Z"
    # keep latest username/name
    users[uid]["first_name"] = u.first_name or users[uid]["first_name"]
    users[uid]["last_name"]  = u.last_name or users[uid]["last_name"]
    users[uid]["username"]   = u.username or users[uid]["username"]
    _save_users(users)

    # message log
    try:
        chat_type = getattr(m.chat, "type", "")
        text = getattr(m, "text", None)
        caption = getattr(m, "caption", None)
        content = text if text is not None else (caption if caption is not None else m.content_type)
        _log_message(f"[{datetime.datetime.utcnow().isoformat()}Z] "
                     f"uid={u.id} (@{u.username}) chat={chat_type} -> {content}")
    except Exception as e:
        _set_last_error_text(str(e))
        _log_error(e)

# --- ՕԳՏԱԿԱՐ ՖՈՐՄԱՏՆԵՐ ---
def fmt_user(u):
    tag = f"@{u.get('username')}" if u.get("username") else f"id={u.get('id')}"
    name = (u.get("first_name") or "") + (" " + u.get("last_name") if u.get("last_name") else "")
    return f"{tag} — {name.strip()}"

def _human_uptime():
    sec = int(time.time() - START_TS)
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    m, s  = divmod(sec, 60)
    parts = []
    if d: parts.append(f"{d} օր")
    if h: parts.append(f"{h} ժ")
    if m: parts.append(f"{m} ր")
    parts.append(f"{s} վ")
    return " ".join(parts)

# --- Ադմին ստուգում ---
def _is_admin(uid: int) -> bool:
    return int(uid) == int(ADMIN_ID)

# --- ԱԴՄԻՆ ՄԵՆՅՈՒ / ԿՈՃԱԿՆԵՐ ---
def admin_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🧾 Վերջին հաղորդագրություններ", callback_data="adm_last_msgs"),
        types.InlineKeyboardButton("👥 Վերջին օգտատերեր", callback_data="adm_last_users"),
    )
    kb.add(
        types.InlineKeyboardButton("📣 Broadcast (բոլորին)", callback_data="adm_broadcast"),
        types.InlineKeyboardButton("🔎 Փնտրել օգտատիրոջը", callback_data="adm_search"),
    )
    kb.add(
        types.InlineKeyboardButton("⬇️ Ներբեռնել logs", callback_data="adm_download_logs"),
        types.InlineKeyboardButton("📊 Վիճակագրություն / Ping", callback_data="adm_stats"),
    )
    kb.add(
        types.InlineKeyboardButton("↩️ Փակել", callback_data="adm_close"),
    )
    return kb

# --- /admin հրաման ---
@bot.message_handler(commands=["admin"])
def open_admin(message):
    if not _is_admin(message.from_user.id):
        return bot.reply_to(message, "❌ Դուք ադմին չեք։")
    text = (
        "🛠 **Ադմին պանել**\n"
        "Այստեղից կարող ես տեսնել վիճակագրություն, վերջին հաղորդագրությունները, օգտատերերին, "
        "ուղարկել broadcast, փնտրել օգտատիրոջը, ներբեռնել լոգերը և ստուգել uptime-ը։"
    )
    bot.send_message(message.chat.id, text, reply_markup=admin_keyboard(), parse_mode="Markdown")

# --- Վիճակագրություն / Ping ---
@bot.callback_query_handler(func=lambda c: c.data == "adm_stats")
def adm_stats(c):
    if not _is_admin(c.from_user.id):
        return bot.answer_callback_query(c.id, "Ադմին չէս")
    users = _load_users()
    total_users = len(users)
    now = datetime.datetime.utcnow().isoformat() + "Z"
    txt = (
        f"📊 **Վիճակագրություն**\n"
        f"- Օգտատերեր՝ {total_users}\n"
        f"- Uptime՝ { _human_uptime() }\n"
        f"- Վերջին սխալ՝ {LAST_ERROR_TEXT}\n"
        f"- Ժամը (UTC)՝ {now}\n"
        f"\n✅ Եթե uptime-ը աճում է, բոտը աշխատում է 24/7։"
    )
    bot.edit_message_text(txt, c.message.chat.id, c.message.message_id, parse_mode="Markdown",
                          reply_markup=admin_keyboard())

# --- Վերջին օգտատերեր ---
@bot.callback_query_handler(func=lambda c: c.data == "adm_last_users")
def adm_last_users(c):
    if not _is_admin(c.from_user.id):
        return bot.answer_callback_query(c.id, "Ադմին չէս")
    users = list(_load_users().values())
    users.sort(key=lambda x: x.get("last_seen",""), reverse=True)
    chunk = users[:20]
    if not chunk:
        text = "Օգտատերեր դեռ չկան։"
    else:
        lines = [f"👥 **Վերջին 20 օգտատերեր**"]
        for u in chunk:
            lines.append("• " + fmt_user(u) + f" | last_seen: {u.get('last_seen','')}")
        text = "\n".join(lines)
    bot.edit_message_text(text, c.message.chat.id, c.message.message_id, parse_mode="Markdown",
                          reply_markup=admin_keyboard())

# --- Վերջին հաղորդագրություններ (քաշում ենք log-ից) ---
@bot.callback_query_handler(func=lambda c: c.data == "adm_last_msgs")
def adm_last_msgs(c):
    if not _is_admin(c.from_user.id):
        return bot.answer_callback_query(c.id, "Ադմին չէս")
    try:
        if not os.path.exists(MSG_LOG):
            text = "Լոգ ֆայլը դեռ չկա։"
        else:
            with open(MSG_LOG, "r", encoding="utf-8") as f:
                lines = f.readlines()[-50:]  # վերջին 50 տողը
            text = "🧾 **Վերջին հաղորդագրություններ (50 տող)**\n" + "".join(["• " + l for l in lines])
            # երկար կարող է լինել, Telegram-ի սահմանները հաշվել
            if len(text) > 3800:
                text = text[-3800:]
        bot.edit_message_text(text, c.message.chat.id, c.message.message_id,
                              reply_markup=admin_keyboard(), parse_mode=None)
    except Exception as e:
        _set_last_error_text(str(e))
        _log_error(e)
        bot.answer_callback_query(c.id, "Չստացվեց կարդալ լոգը")

# --- Logs download (որպես ֆայլ) ---
@bot.callback_query_handler(func=lambda c: c.data == "adm_download_logs")
def adm_download_logs(c):
    if not _is_admin(c.from_user.id):
        return bot.answer_callback_query(c.id, "Ադմին չէս")
    sent_something = False
    try:
        if os.path.exists(MSG_LOG):
            with open(MSG_LOG, "rb") as f:
                bot.send_document(c.message.chat.id, f, caption="messages.log")
                sent_something = True
        if os.path.exists(ERR_LOG):
            with open(ERR_LOG, "rb") as f:
                bot.send_document(c.message.chat.id, f, caption="errors.log")
                sent_something = True
        if not sent_something:
            bot.answer_callback_query(c.id, "Լոգեր չկան դեռ")
    except Exception as e:
        _set_last_error_text(str(e))
        _log_error(e)
        bot.answer_callback_query(c.id, "Սխալ՝ logs ուղարկելիս")

# --- Broadcast բոլոր օգտատերերին ---
BROADCAST_STATE = {}  # {admin_id: True/False}
@bot.callback_query_handler(func=lambda c: c.data == "adm_broadcast")
def adm_broadcast(c):
    if not _is_admin(c.from_user.id):
        return bot.answer_callback_query(c.id, "Ադմին չէս")
    BROADCAST_STATE[c.from_user.id] = True
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id,
                     "✍️ Ուղարկիր հաղորդագրություն՝ broadcast անել բոլոր օգտատերերին։\n"
                     "Չեղարկելու համար գրիր `/cancel`.")

@bot.message_handler(commands=["cancel"])
def adm_broadcast_cancel(m):
    if not _is_admin(m.from_user.id):
        return
    if BROADCAST_STATE.get(m.from_user.id):
        BROADCAST_STATE[m.from_user.id] = False
        bot.reply_to(m, "❌ Չեղարկվեց broadcast-ը։")

@bot.message_handler(func=lambda m: BROADCAST_STATE.get(m.from_user.id, False))
def adm_broadcast_do(m):
    if not _is_admin(m.from_user.id):
        return
    text_or_caption = m.text or m.caption or ""
    users = list(_load_users().values())
    ok = fail = 0
    for u in users:
        try:
            bot.copy_message(u["id"], m.chat.id, m.message_id)
            ok += 1
            time.sleep(0.03)  # մի փոքր սահունություն
        except Exception as e:
            fail += 1
    BROADCAST_STATE[m.from_user.id] = False
    bot.reply_to(m, f"📣 Ավարտված է. ✅ {ok} | ❌ {fail}")

# --- Ուզեր որոնում ---
SEARCH_STATE = {}
@bot.callback_query_handler(func=lambda c: c.data == "adm_search")
def adm_search(c):
    if not _is_admin(c.from_user.id):
        return bot.answer_callback_query(c.id, "Ադմին չէս")
    SEARCH_STATE[c.from_user.id] = True
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id,
                     "Ներմուծիր user ID կամ @username՝ տվյալ օգտատիրոջ քարտը տեսնելու համար.\n"
                     "Օր.` 123456789 կամ @nickname")

@bot.message_handler(func=lambda m: SEARCH_STATE.get(m.from_user.id, False))
def do_search_user(m):
    if not _is_admin(m.from_user.id):
        return
    query = (m.text or "").strip()
    SEARCH_STATE[m.from_user.id] = False
    users = _load_users()
    found = None
    if query.startswith("@"):
        uname = query[1:].lower()
        for u in users.values():
            if (u.get("username") or "").lower() == uname:
                found = u; break
    else:
        if query.isdigit() and query in users:
            found = users[query]
    if not found:
        return bot.reply_to(m, "Չգտա այդ օգտատիրոջը։")
    text = (
        "🪪 **Օգտատիրոջ քարտ**\n" +
        fmt_user(found) + "\n" +
        f"ID: `{found.get('id')}`\n"
        f"Լեզու: {found.get('lang')}\n"
        f"Գրանցված: {found.get('joined_at')}\n"
        f"Վերջ. ակտիվություն: {found.get('last_seen')}\n"
        f"Հաղորդագրություններ: {found.get('messages')}\n"
    )
    bot.reply_to(m, text, parse_mode="Markdown")

# --- Փակել ադմին մենյուն ---
@bot.callback_query_handler(func=lambda c: c.data == "adm_close")
def adm_close(c):
    if not _is_admin(c.from_user.id):
        return bot.answer_callback_query(c.id, "Ադմին չէս")
    try:
        bot.delete_message(c.message.chat.id, c.message.message_id)
    except Exception:
        pass

# --- Ընդհանուր error-wrapper օրինակ՝ եթե ուզում ես օգտագործել քո կոդում ---
def safe_send(chat_id, *args, **kwargs):
    try:
        return bot.send_message(chat_id, *args, **kwargs)
    except Exception as e:
        _set_last_error_text(str(e))
        _log_error(e)

# --- /ping արագ health-check (կարող ես գործարկել ցանկացած պահին) ---
@bot.message_handler(commands=["ping"])
def cmd_ping(m):
    if not _is_admin(m.from_user.id):
        return bot.reply_to(m, "Pong 🟢")
    bot.reply_to(m, f"🟢 Pong\nUptime: {_human_uptime()}\nLast error: {LAST_ERROR_TEXT}")
# =============================================================================


# ------------------- CONFIG / CONSTANTS -------------------
DATA_DIR = "data"
MEDIA_DIR = "media"

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

THOUGHTS_FILE = os.path.join(DATA_DIR, "thoughts.json")
PENDING_THOUGHTS_FILE = os.path.join(DATA_DIR, "pending_thoughts.json")

ADS_FILE = os.path.join(DATA_DIR, "ads.json")
PENDING_ADS_FILE = os.path.join(DATA_DIR, "pending_ads.json")

# --- Admin ---
ADMIN_ID = 6822052289  # քո ադմին ID

# --- Rate limits (anti-spam) ---
RL_THOUGHT_SUBMIT_SEC = 180   # 1 հայտ / 3 րոպե
RL_AD_SUBMIT_SEC = 300        # 1 հայտ / 5 րոպե

# --- States (պարզ FSM) ---
STATE_NONE = "NONE"
STATE_GT_TEXT = "GT_TEXT"
STATE_GT_AUTHOR = "GT_AUTHOR"

STATE_AD_BNAME = "AD_BNAME"
STATE_AD_DESC = "AD_DESC"
STATE_AD_WEBSITE = "AD_WEBSITE"
STATE_AD_TG = "AD_TG"
STATE_AD_VIBER = "AD_VIBER"
STATE_AD_WHATSAPP = "AD_WHATSAPP"
STATE_AD_PHONE = "AD_PHONE"
STATE_AD_ADDRESS = "AD_ADDRESS"
STATE_AD_HOURS = "AD_HOURS"
STATE_AD_CTA_TEXT = "AD_CTA_TEXT"
STATE_AD_CTA_URL = "AD_CTA_URL"
STATE_AD_CONFIRM = "AD_CONFIRM"

# --- MENU LABELS (FINAL, as requested) ---
BTN_SHOP      = "🛍 Խանութ"
BTN_CART      = "🛒 Զամբյուղ"
BTN_EXCHANGE  = "💱 Փոխարկումներ"
BTN_THOUGHTS  = "💡 Խոհուն մտքեր"
BTN_RATES     = "📈 Օրվա կուրսեր"
BTN_PROFILE   = "🧍 Իմ էջը"
BTN_FEEDBACK  = "💬 Կապ մեզ հետ"
BTN_PARTNERS  = "📢 Բիզնես գործընկերներ"
BTN_SEARCH    = "🔍 Ապրանքի որոնում"
BTN_INVITE    = "👥 Հրավիրել ընկերների"
BTN_HOME      = "🏠 Գլխավոր մենյու"

# ------------------- RUNTIME (in-memory) -------------------
USER_STATE = {}   
def set_state(cid, s): USER_STATE[cid] = s
def get_state(cid): return USER_STATE.get(cid)
def clear_state(cid): USER_STATE.pop(cid, None)


NUMBER_RE = re.compile(r"^\d+([.,]\d{1,2})?$")
def is_amount(text: str) -> bool:
    return bool(NUMBER_RE.match(text.strip()))
USER_FORM = {}           # user_id -> dict (session)
USER_LAST_ACTION = {}    # user_id -> {key: timestamp}  (rate-limit)

# cache
SETTINGS = {}
USERS = {}
GOOD_THOUGHTS = []       # approved
PENDING_THOUGHTS = {}    # id -> dict
ADS_STORE = []           # approved
PENDING_ADS = {}         # id -> dict

NEXT_THOUGHT_ID = 1001
NEXT_AD_ID = 5001

# ------------------- HELPERS: FILE IO -------------------
def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(os.path.join(MEDIA_DIR, "exchange"), exist_ok=True)
    os.makedirs(os.path.join(MEDIA_DIR, "products"), exist_ok=True)

def load_json(path, default):
    try:
        if not os.path.exists(path):
            save_json(path, default)
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        print("load_json ERROR:", path)
        print(traceback.format_exc())
        return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        print("save_json ERROR:", path)
        print(traceback.format_exc())
        return False

def reload_all():
    # ← ADD ADMIN_ID here with the other globals
    global SETTINGS, USERS, GOOD_THOUGHTS, PENDING_THOUGHTS, ADS_STORE, PENDING_ADS
    global NEXT_THOUGHT_ID, NEXT_AD_ID, ADMIN_ID

    SETTINGS = load_json(SETTINGS_FILE, {
        "bot_token": "PASTE_YOUR_BOT_TOKEN_HERE",
        "admin_id": ADMIN_ID,
        "customer_counter": 1007,  # so the next will be 1008
        "alipay_rate_amd": 58,
        "bot_username": "YourBotUsernameHere"
    })

    # allow changing admin id from settings if needed (NO 'global' inside)
    if isinstance(SETTINGS.get("admin_id"), int):
        ADMIN_ID = SETTINGS["admin_id"]

    USERS = load_json(USERS_FILE, {})  # user_id -> {"referrer_id": int, "shares": int}
    GOOD_THOUGHTS = load_json(THOUGHTS_FILE, [])
    PENDING_THOUGHTS = load_json(PENDING_THOUGHTS_FILE, {})
    ADS_STORE = load_json(ADS_FILE, [])
    PENDING_ADS = load_json(PENDING_ADS_FILE, {})

    # compute next ids
    if GOOD_THOUGHTS:
        # use get with default to be safe
        ids = [x.get("id", 0) for x in GOOD_THOUGHTS]
        NEXT_THOUGHT_ID = max(ids + [1000]) + 1
    if PENDING_THOUGHTS:
        NEXT_THOUGHT_ID = max(NEXT_THOUGHT_ID, max([int(k) for k in PENDING_THOUGHTS.keys()]) + 1)

    if ADS_STORE:
        ids = [x.get("id", 0) for x in ADS_STORE]
        NEXT_AD_ID = max(ids + [5000]) + 1
    if PENDING_ADS:
        NEXT_AD_ID = max(NEXT_AD_ID, max([int(k) for k in PENDING_ADS.keys()]) + 1)


def persist_all():
    save_json(SETTINGS_FILE, SETTINGS)
    save_json(USERS_FILE, USERS)
    save_json(THOUGHTS_FILE, GOOD_THOUGHTS)
    save_json(PENDING_THOUGHTS_FILE, PENDING_THOUGHTS)
    save_json(ADS_FILE, ADS_STORE)
    save_json(PENDING_ADS_FILE, PENDING_ADS)

# ------------------- HELPERS: UTILS -------------------
def ts() -> int:
    return int(time.time())

def rate_limited(user_id: int, key: str, window_sec: int) -> bool:
    rec = USER_LAST_ACTION.setdefault(user_id, {})
    last = rec.get(key, 0)
    now = ts()
    if now - last < window_sec:
        return True
    rec[key] = now
    return False

def build_main_menu() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(BTN_SHOP, BTN_CART)
    kb.add(BTN_EXCHANGE, BTN_THOUGHTS)
    kb.add(BTN_RATES, BTN_PROFILE)
    kb.add(BTN_FEEDBACK, BTN_PARTNERS)
    kb.add(BTN_SEARCH, BTN_INVITE)
    return kb

@bot.message_handler(func=lambda m: m.text == BTN_HOME)
def back_home(m: types.Message):
    bot.send_message(m.chat.id, "Գլխավոր մենյու ✨", reply_markup=build_main_menu())
def send_welcome(message: types.Message):
    user_id = message.from_user.id
    global customer_counter
    customer_counter += 1
    save_counter(customer_counter)
    customer_no = customer_counter

    markup = build_main_menu()
    text = welcome_text(customer_no)

    # Սկզբում նապաստակի նկարը
    try:
        with open("media/bunny.jpg", "rb") as photo:
            bot.send_photo(message.chat.id, photo)

    except Exception as e:
        print("Bunny image not found:", e)

    # Հետո արդեն տեքստը
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=markup,
        parse_mode="HTML"
    )

def get_username_or_id(u) -> str:
    uname = getattr(u, "username", None)
    return f"@{uname}" if uname else f"id{u.id}"

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


def share_button(cb_prefix: str, payload: str) -> types.InlineKeyboardButton:
    # We use callback to show a copyable share text
    return types.InlineKeyboardButton("🔗 Կիսվել", callback_data=f"{cb_prefix}:share:{payload}")

def do_share_message(chat_id: int, text: str):
    # send a message with the share text so user can forward/copy
    msg = "🔗 <b>Կիսվելու տեքստ</b>\n\n" + text + "\n\nՊարզապես փոխանցեք սա ձեր ընկերներին 😉"
    bot.send_message(chat_id, msg, parse_mode="HTML")

def bot_link_with_ref(user_id: int) -> str:
    # referral-friendly, replace with your actual bot username if known
    # If you have actual bot username, put it to SETTINGS["bot_username"]
    bot_username = SETTINGS.get("bot_username", "YourBotUsernameHere")
    return f"https://t.me/{bot_username}?start={user_id}"

# ------------------- BOT INIT -------------------
ensure_dirs()
reload_all()

BOT_TOKEN = SETTINGS.get("bot_token") or "PASTE_YOUR_BOT_TOKEN_HERE"

# ------------------- /start & welcome -------------------
@bot.message_handler(commands=['start'])
def start_handler(m: types.Message):
    # only private chats
    if getattr(m.chat, "type", "") != "private":
        return

    user_id = m.from_user.id

    # referral capture: /start <ref_id>
    try:
        parts = (m.text or "").split(maxsplit=1)
        if len(parts) == 2:
            ref = parts[1].strip()
            if ref.isdigit():
                ref_id = int(ref)
                if user_id != ref_id:
                    u = USERS.setdefault(str(user_id), {})
                    if "referrer_id" not in u:
                        u["referrer_id"] = ref_id
                        save_json(USERS_FILE, USERS)
    except Exception:
        pass

    # increment customer counter
    try:
        SETTINGS["customer_counter"] = int(SETTINGS.get("customer_counter", 1007)) + 1
    except Exception:
        SETTINGS["customer_counter"] = 1008
    persist_all()

    customer_no = SETTINGS["customer_counter"]

    # send bunny (if exists), then welcome with menu
    markup = build_main_menu()
    bunny_path = os.path.join(MEDIA_DIR, "bunny.jpg")
    try:
        if os.path.exists(bunny_path):
            with open(bunny_path, "rb") as ph:
                bot.send_photo(m.chat.id, ph)
    except Exception:
        print("BUNNY SEND ERROR")
        print(traceback.format_exc())

    try:
        bot.send_message(m.chat.id, welcome_text(customer_no), reply_markup=markup, parse_mode="HTML")
    except Exception:
        bot.send_message(m.chat.id, "Բարի գալուստ!", reply_markup=markup)
@bot.message_handler(commands=['menu'])
def menu_cmd(m: types.Message):
    return go_home(m)

# ------------------- Invite / share bot -------------------
@bot.message_handler(func=lambda msg: msg.text == BTN_INVITE)
def invite_handler(m: types.Message):
    user_id = m.from_user.id
    link = bot_link_with_ref(user_id)
    text = (
        "👥 <b>Կիսվեք բոտով և ստացեք բոնուսներ</b>\n\n"
        f"Ձեր հրավերի հղումը՝\n{link}\n\n"
        "Ուղարկեք սա ընկերներին, որ միանան բոտին 🌸"
    )
    bot.send_message(m.chat.id, text, parse_mode="HTML")

# =========================
# 🧠 ԼԱՎ ՄՏՔԵՐ (ԱՍԱՑՎԱԾՔՆԵՐ)
# =========================
def render_good_thoughts(page: int = 1, per_page: int = 1):
    total = len(GOOD_THOUGHTS)
    page = max(1, min(page, max(1, total if total else 1)))
    idx = page - 1
    item = GOOD_THOUGHTS[idx] if total else None

    if not item:
        text = "Այս պահին ասույթներ չկան։"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("➕ Ավելացնել մտք", callback_data="gt:new"))
        kb.add(types.InlineKeyboardButton("🏠 Գլխավոր", callback_data="gt:home"))
        return text, kb

    posted_by = item.get("posted_by")
    by_line = f"\n\n📎 Տեղադրող՝ {posted_by}" if posted_by else ""
    text = f"🧠 <b>Լավ մտքեր</b>\n\n{item['text']}{by_line}\n\n— Էջ {page}/{total}"

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("❤️ Հավանել", callback_data=f"gt:like:{item['id']}"),
        types.InlineKeyboardButton("🔖 Պահել", callback_data=f"gt:save:{item['id']}")
    )
    kb.add(share_button("gt", str(item['id'])))
    kb.add(types.InlineKeyboardButton("➕ Ավելացնել մտք", callback_data="gt:new"))

    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("⬅️ Նախորդ", callback_data=f"gt:page:{page-1}"))
    if total and page < total:
        nav.append(types.InlineKeyboardButton("Այժմոք ➡️", callback_data=f"gt:page:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="gt:home"))
    return text, kb

@bot.message_handler(func=lambda m: m.text == BTN_THOUGHTS)
def show_good_thoughts(m: types.Message):
    text, kb = render_good_thoughts(page=1)
    bot.send_message(m.chat.id, text, reply_markup=kb, parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data.startswith("gt:"))
def on_good_thoughts_cb(c: types.CallbackQuery):
    try:
        parts = c.data.split(":")
        action = parts[1]

        if action == "page" and len(parts) == 3:
            page = max(1, int(parts[2]))
            text, kb = render_good_thoughts(page=page)
            bot.edit_message_text(
                chat_id=c.message.chat.id,
                message_id=c.message.message_id,
                text=text,
                reply_markup=kb,
                parse_mode="HTML"
            )

        elif action in ("like", "save") and len(parts) == 3:
            bot.answer_callback_query(c.id, "Գրանցվեց ✅")

        elif action == "new":
            user_id = c.from_user.id
            # rate-limit
            if rate_limited(user_id, "gt_submit", RL_THOUGHT_SUBMIT_SEC):
                bot.answer_callback_query(c.id, "Խնդրում ենք փորձել ավելի ուշ։")
                return

            USER_STATE[user_id] = STATE_GT_TEXT
            USER_FORM[user_id] = {}
            bot.answer_callback_query(c.id)
            bot.send_message(
                c.message.chat.id,
                "✍️ Գրեք ձեր մտածումը/ասույթը ամբողջությամբ (մինչև 400 նիշ):"
            )

        elif action == "share" and len(parts) == 3:
            tid = parts[2]
            item = None
            for t in GOOD_THOUGHTS:
                if str(t.get("id")) == tid:
                    item = t
                    break
            if not item:
                bot.answer_callback_query(c.id, "Չի գտնվել։")
                return
            # compose share text
            share_txt = (
                f"🧠 Լավ միտք՝\n\n{item['text']}\n\n"
                f"Միացիր մեր բոտին 👉 {bot_link_with_ref(c.from_user.id)}"
            )
            bot.answer_callback_query(c.id)
            do_share_message(c.message.chat.id, share_txt)

        elif action == "home":
            bot.edit_message_text(
                chat_id=c.message.chat.id,
                message_id=c.message.message_id,
                text="Վերադարձ գլխավոր մենյու 👇",
                parse_mode="HTML"
            )
            bot.send_message(c.message.chat.id, "Ընտրեք բաժին 👇", reply_markup=build_main_menu())

    except Exception as e:
        print("GOOD THOUGHTS NAV ERROR:", e)
        bot.answer_callback_query(c.id, "Սխալ տեղի ունեցավ")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_GT_TEXT)
def on_gt_text(m: types.Message):
    txt = (m.text or "").strip()
    if not txt:
        bot.send_message(m.chat.id, "Խնդրում եմ ուղարկել տեքստ։")
        return
    if len(txt) > 400:
        bot.send_message(m.chat.id, "Խոսքը շատ երկար է, կրճատեք մինչև 400 նիշ։")
        return

    USER_FORM[m.from_user.id]["text"] = txt
    USER_STATE[m.from_user.id] = STATE_GT_AUTHOR
    bot.send_message(m.chat.id, "✍️ Նշեք հեղինակին (կամ գրեք «—» եթե չգիտեք):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_GT_AUTHOR)
def on_gt_author(m: types.Message):
    global NEXT_THOUGHT_ID
    user_id = m.from_user.id
    author = (m.text or "").strip() or "—"

    data = USER_FORM.get(user_id, {})
    text = data.get("text", "")

    th_id = NEXT_THOUGHT_ID
    NEXT_THOUGHT_ID += 1

    submitter = m.from_user.username or f"id{user_id}"
    PENDING_THOUGHTS[str(th_id)] = {
        "id": th_id,
        "text": f"{text}\n\n— {author}",
        "submitter_id": user_id,
        "submitter_name": submitter,
        "created_at": datetime.utcnow().isoformat()
    }
    save_json(PENDING_THOUGHTS_FILE, PENDING_THOUGHTS)

    USER_STATE[user_id] = STATE_NONE
    USER_FORM.pop(user_id, None)

    bot.send_message(m.chat.id, "✅ Ուղարկված է ադմինին հաստատման համար։ Շնորհակալություն!")

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Հաստատել", callback_data=f"gtadm:approve:{th_id}"),
        types.InlineKeyboardButton("❌ Մերժել", callback_data=f"gtadm:reject:{th_id}")
    )
    admin_text = (
        f"🧠 <b>Նոր մտքի հայտ</b>\n"
        f"ID: {th_id}\n"
        f"Ուղարկող՝ @{submitter}\n\n"
        f"{PENDING_THOUGHTS[str(th_id)]['text']}"
    )
    bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data.startswith("gtadm:"))
def on_gt_admin(c: types.CallbackQuery):
    parts = c.data.split(":")
    if len(parts) != 3:
        return
    action, th_id_str = parts[1], parts[2]

    if c.from_user.id != ADMIN_ID:
        bot.answer_callback_query(c.id, "Միայն ադմինը կարող է հաստատել։")
        return

    item = PENDING_THOUGHTS.get(th_id_str)
    if not item:
        bot.answer_callback_query(c.id, "Դատարկ է կամ արդեն մշակված է։")
        return

    if action == "approve":
        GOOD_THOUGHTS.append({
            "id": item["id"],
            "text": item["text"],
            "posted_by": f"@{item['submitter_name']}"
        })
        save_json(THOUGHTS_FILE, GOOD_THOUGHTS)
        PENDING_THOUGHTS.pop(th_id_str, None)
        save_json(PENDING_THOUGHTS_FILE, PENDING_THOUGHTS)

        bot.edit_message_text("✅ Հաստատվեց և ավելացավ «Լավ մտքեր»-ում։",
                              c.message.chat.id, c.message.message_id)
        bot.answer_callback_query(c.id, "Հաստատվեց")
        try:
            bot.send_message(item["submitter_id"], "✅ Ձեր միտքը հաստատվեց և հրապարակվեց։ Շնորհակալություն!")
        except:
            pass

    elif action == "reject":
        PENDING_THOUGHTS.pop(th_id_str, None)
        save_json(PENDING_THOUGHTS_FILE, PENDING_THOUGHTS)
        bot.edit_message_text("❌ Մերժվեց։", c.message.chat.id, c.message.message_id)
        bot.answer_callback_query(c.id, "Մերժվեց")
        try:
            bot.send_message(item["submitter_id"], "❌ Ձեր միտքը մերժվեց (կարող եք փորձել նորից):")
        except:
            pass

# =========================
# 📣 ԳՈՎԱԶԴՆԵՐ (ADS)
# =========================
def render_ads_list(page: int = 1, per_page: int = 5):
    active = [a for a in ADS_STORE if a.get("active")]
    total = len(active)
    page = max(1, min(page, max(1, (total + per_page - 1) // per_page if total else 1)))
    start = (page - 1) * per_page
    end = start + per_page
    chunk = active[start:end]

    lines = ["📣 <b>Գովազդային առաջարկներ</b>\n"]
    if not chunk:
        lines.append("Այս պահին առաջարկներ չկան։")
    else:
        for ad in chunk:
            by = ad.get("posted_by")
            lines.append(
                f"🏪 <b>{ad.get('title')}</b>{' — ' + by if by else ''}\n"
                f"📝 {ad.get('desc','')}\n"
                f"🌐 {ad.get('website','—')}\n"
                f"Telegram: {ad.get('telegram','—')}\n"
                f"Viber: {ad.get('viber','—')} | WhatsApp: {ad.get('whatsapp','—')}\n"
                f"☎️ {ad.get('phone','—')}\n"
                f"📍 {ad.get('address','—')} | 🕒 {ad.get('hours','—')}\n"
                f"{'🔘 ' + ad.get('cta','Դիտել') if ad.get('cta') else ''}"
            )
            lines.append("— — —")

    text = "\n".join(lines)

    kb = types.InlineKeyboardMarkup()
    for ad in chunk:
        if ad.get("url"):
            kb.add(types.InlineKeyboardButton(ad.get("cta") or "Դիտել", url=ad["url"]))

    nav = []
    if start > 0:
        nav.append(types.InlineKeyboardButton("⬅️ Նախորդ", callback_data=f"ads:page:{page-1}"))
    if end < total:
        nav.append(types.InlineKeyboardButton("Այժմոք ➡️", callback_data=f"ads:page:{page+1}"))
    if nav:
        kb.row(*nav)

    kb.add(types.InlineKeyboardButton("➕ Դառնալ գովազդատու", callback_data="ads:new"))
    kb.add(types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="ads:home"))
    return text, kb


@bot.callback_query_handler(func=lambda c: c.data.startswith("ads:"))
def on_ads_nav(c: types.CallbackQuery):
    try:
        parts = c.data.split(":")
        action = parts[1]

        if action == "page" and len(parts) == 3:
            page = max(1, int(parts[2]))
            text, kb = render_ads_list(page=page)
            bot.edit_message_text(
                chat_id=c.message.chat.id,
                message_id=c.message.message_id,
                text=text,
                reply_markup=kb,
                parse_mode="HTML"
            )
        elif action == "new":
            user_id = c.from_user.id
            if rate_limited(user_id, "ad_submit", RL_AD_SUBMIT_SEC):
                bot.answer_callback_query(c.id, "Խնդրում ենք փորձել ավելի ուշ։")
                return
            USER_STATE[user_id] = STATE_AD_BNAME
            USER_FORM[user_id] = {}
            bot.answer_callback_query(c.id)
            bot.send_message(c.message.chat.id, "🏪 Գրեք ձեր խանութի/ծառայության անունը (օր․ «Starlegen Store»):")
        elif action == "home":
            bot.edit_message_text(
                chat_id=c.message.chat.id,
                message_id=c.message.message_id,
                text="Վերադարձ գլխավոր մենյու 👇",
                parse_mode="HTML"
            )
            bot.send_message(c.message.chat.id, "Ընտրեք բաժին 👇", reply_markup=build_main_menu())
    except Exception as e:
        print("ADS NAV ERROR:", e)
        bot.answer_callback_query(c.id, "Սխալ տեղի ունեցավ")

# ---- Ads form steps ----
def _ad_next(user_id, next_state, chat_id, prompt):
    USER_STATE[user_id] = next_state
    bot.send_message(chat_id, prompt)

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_AD_BNAME)
def ad_bname(m: types.Message):
    nm = (m.text or "").strip()
    if not nm:
        bot.send_message(m.chat.id, "Խնդրում եմ գրել անվանումը։")
        return
    USER_FORM[m.from_user.id]["business_name"] = nm
    _ad_next(m.from_user.id, STATE_AD_DESC, m.chat.id, "📝 Գրեք մարկետինգային նկարագրությունը (կարճ, 1–3 նախադասություն):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_AD_DESC)
def ad_desc(m: types.Message):
    USER_FORM[m.from_user.id]["desc"] = (m.text or "").strip()
    _ad_next(m.from_user.id, STATE_AD_WEBSITE, m.chat.id, "🌐 Վեբսայթ (եթե չկա՝ գրեք «—»):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_AD_WEBSITE)
def ad_website(m: types.Message):
    USER_FORM[m.from_user.id]["website"] = (m.text or "").strip()
    _ad_next(m.from_user.id, STATE_AD_TG, m.chat.id, "📲 Telegram հղում/username (եթե չկա՝ «—»):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_AD_TG)
def ad_tg(m: types.Message):
    USER_FORM[m.from_user.id]["telegram"] = (m.text or "").strip()
    _ad_next(m.from_user.id, STATE_AD_VIBER, m.chat.id, "📞 Viber համար/հղում (եթե չկա՝ «—»):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_AD_VIBER)
def ad_viber(m: types.Message):
    USER_FORM[m.from_user.id]["viber"] = (m.text or "").strip()
    _ad_next(m.from_user.id, STATE_AD_WHATSAPP, m.chat.id, "📞 WhatsApp համար/հղում (եթե չկա՝ «—»):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_AD_WHATSAPP)
def ad_wa(m: types.Message):
    USER_FORM[m.from_user.id]["whatsapp"] = (m.text or "").strip()
    _ad_next(m.from_user.id, STATE_AD_PHONE, m.chat.id, "☎️ Հեռախոսահամար (եթե չկա՝ «—»):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_AD_PHONE)
def ad_phone(m: types.Message):
    USER_FORM[m.from_user.id]["phone"] = (m.text or "").strip()
    _ad_next(m.from_user.id, STATE_AD_ADDRESS, m.chat.id, "📍 Հասցե (եթե չկա՝ «—»):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_AD_ADDRESS)
def ad_addr(m: types.Message):
    USER_FORM[m.from_user.id]["address"] = (m.text or "").strip()
    _ad_next(m.from_user.id, STATE_AD_HOURS, m.chat.id, "🕒 Աշխ. ժամեր (օր․ «Երկ–Կիր 10:00–20:00» կամ «—»):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_AD_HOURS)
def ad_hours(m: types.Message):
    USER_FORM[m.from_user.id]["hours"] = (m.text or "").strip()
    _ad_next(m.from_user.id, STATE_AD_CTA_TEXT, m.chat.id, "🔘 CTA կոճակի տեքստ (օր. «Պատվիրել», «Կապվել»):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_AD_CTA_TEXT)
def ad_cta_text(m: types.Message):
    USER_FORM[m.from_user.id]["cta_text"] = (m.text or "Դիտել").strip() or "Դիտել"
    _ad_next(m.from_user.id, STATE_AD_CTA_URL, m.chat.id, "🔗 CTA հղում (URL) (եթե չկա՝ «—»):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == STATE_AD_CTA_URL)
def ad_cta_url(m: types.Message):
    USER_FORM[m.from_user.id]["cta_url"] = (m.text or "").strip()
    USER_STATE[m.from_user.id] = STATE_AD_CONFIRM
    d = USER_FORM[m.from_user.id].copy()
    preview = (
        f"📣 <b>Գովազդի հայտ — նախադիտում</b>\n\n"
        f"🏪 Անուն՝ {d.get('business_name')}\n"
        f"📝 Նկարագրություն՝ {d.get('desc')}\n"
        f"🌐 Վեբսայթ՝ {d.get('website')}\n"
        f"Telegram՝ {d.get('telegram')}\n"
        f"Viber՝ {d.get('viber')} | WhatsApp՝ {d.get('whatsapp')}\n"
        f"☎️ Հեռ.՝ {d.get('phone')}\n"
        f"📍 Հասցե՝ {d.get('address')}\n"
        f"🕒 Ժամեր՝ {d.get('hours')}\n"
        f"🔘 CTA՝ {d.get('cta_text')} → {d.get('cta_url')}\n\n"
        f"✅ Հաստատե՞լ ուղարկումը ադմինին։"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Ուղարկել ադմինին", callback_data="adsub:send"),
        types.InlineKeyboardButton("❌ Չեղարկել", callback_data="adsub:cancel")
    )
    bot.send_message(m.chat.id, preview, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adsub:"))
def on_ad_submit(c: types.CallbackQuery):
    user_id = c.from_user.id
    action = c.data.split(":")[1]

    if USER_STATE.get(user_id) != STATE_AD_CONFIRM:
        bot.answer_callback_query(c.id, "Ժամկետն անցել է կամ ձևաթուղթը փակվեց։")
        return

    if action == "cancel":
        USER_STATE[user_id] = STATE_NONE
        USER_FORM.pop(user_id, None)
        bot.answer_callback_query(c.id, "Չեղարկվեց։")
        bot.edit_message_text("Չեղարկվեց։", c.message.chat.id, c.message.message_id)
        return

    if action == "send":
        data = USER_FORM.get(user_id, {}).copy()
        if not data:
            bot.answer_callback_query(c.id, "Տվյալները չեն գտնվել։")
            return

        global NEXT_AD_ID
        ad_id = NEXT_AD_ID
        NEXT_AD_ID += 1

        submitter = c.from_user.username or f"id{user_id}"
        PENDING_ADS[str(ad_id)] = {
            "id": ad_id,
            "submitter_id": user_id,
            "submitter_name": submitter,
            **data,
            "created_at": datetime.utcnow().isoformat()
        }
        save_json(PENDING_ADS_FILE, PENDING_ADS)

        USER_STATE[user_id] = STATE_NONE
        USER_FORM.pop(user_id, None)

        bot.answer_callback_query(c.id, "Ուղարկվեց ադմինին։")
        bot.edit_message_text("✅ Հայտը ուղարկվեց ադմինին հաստատման համար։", c.message.chat.id, c.message.message_id)

        # to admin
        d = PENDING_ADS[str(ad_id)]
        admin_text = (
            f"📣 <b>Նոր գովազդի հայտ</b>\n"
            f"ID: {ad_id}\nՈւղարկող՝ @{submitter}\n\n"
            f"🏪 {d.get('business_name')}\n"
            f"📝 {d.get('desc')}\n"
            f"🌐 {d.get('website')}\n"
            f"Telegram: {d.get('telegram')}\n"
            f"Viber: {d.get('viber')} | WhatsApp: {d.get('whatsapp')}\n"
            f"☎️ {d.get('phone')}\n"
            f"📍 {d.get('address')}\n"
            f"🕒 {d.get('hours')}\n"
            f"🔘 {d.get('cta_text')} → {d.get('cta_url')}"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ Հաստատել", callback_data=f"adadm:approve:{ad_id}"),
            types.InlineKeyboardButton("❌ Մերժել", callback_data=f"adadm:reject:{ad_id}")
        )
        bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adadm:"))
def on_ad_admin(c: types.CallbackQuery):
    parts = c.data.split(":")
    if len(parts) != 3:
        return
    action, ad_id_str = parts[1], parts[2]

    if c.from_user.id != ADMIN_ID:
        bot.answer_callback_query(c.id, "Միայն ադմինը կարող է հաստատել։")
        return

    item = PENDING_ADS.get(ad_id_str)
    if not item:
        bot.answer_callback_query(c.id, "Արդեն մշակված է կամ չկա։")
        return

    if action == "approve":
        ADS_STORE.append({
            "id": item["id"],
            "title": item["business_name"],
            "desc": item["desc"],
            "website": item["website"],
            "telegram": item["telegram"],
            "viber": item["viber"],
            "whatsapp": item["whatsapp"],
            "phone": item["phone"],
            "address": item["address"],
            "hours": item["hours"],
            "cta": item["cta_text"] or "Դիտել",
            "url": item["cta_url"] or "",
            "posted_by": f"@{item['submitter_name']}",
            "active": True,
        })
        save_json(ADS_FILE, ADS_STORE)
        PENDING_ADS.pop(ad_id_str, None)
        save_json(PENDING_ADS_FILE, PENDING_ADS)

        bot.edit_message_text("✅ Հաստատվեց և ավելացավ «Գովազդներ»-ում։",
                              c.message.chat.id, c.message.message_id)
        bot.answer_callback_query(c.id, "Հաստատվեց")
        try:
            bot.send_message(item["submitter_id"], "✅ Ձեր գովազդը հաստատվեց և հրապարակվեց։ Շնորհակալություն!")
        except:
            pass

    elif action == "reject":
        PENDING_ADS.pop(ad_id_str, None)
        save_json(PENDING_ADS_FILE, PENDING_ADS)
        bot.edit_message_text("❌ Մերժվեց։", c.message.chat.id, c.message.message_id)
        bot.answer_callback_query(c.id, "Մերժվեց")
        try:
            bot.send_message(item["submitter_id"], "❌ Ձեր գովազդը մերժվեց (կարող եք խմբագրել և կրկին ուղարկել):")
        except:
            pass

# ---- Share buttons for Ads (send share text) ----
def ad_share_text(ad: dict, ref_user_id: int) -> str:
    link = bot_link_with_ref(ref_user_id)
    body = (
        f"🏪 {ad.get('title')}\n"
        f"📝 {ad.get('desc','')}\n"
        f"🌐 {ad.get('website','—')}\n"
        f"Telegram: {ad.get('telegram','—')}\n"
        f"Viber: {ad.get('viber','—')} | WhatsApp: {ad.get('whatsapp','—')}\n"
        f"☎️ {ad.get('phone','—')} | 📍 {ad.get('address','—')}\n\n"
        f"Փորձիր Starlegen բոտը 👉 {link}"
    )
    return body

# We inject share buttons per-card by reusing render, so share is provided as separate callback
@bot.callback_query_handler(func=lambda c: c.data.startswith("adsShare:"))
def on_ad_share_cb(c: types.CallbackQuery):
    # not used in current list rendering—left for extension if per-card messages are used
    pass

# =========================
# Admin commands
# =========================
@bot.message_handler(commands=['pending'])
def cmd_pending(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    th = len(PENDING_THOUGHTS)
    ad = len(PENDING_ADS)
    bot.send_message(m.chat.id, f"🧠 Սպասող մտքեր՝ {th}\n📣 Սպասող գովազդներ՝ {ad}")

@bot.message_handler(commands=['reload'])
def cmd_reload(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return
    reload_all()
    bot.send_message(m.chat.id, "♻️ Settings/Data reloaded.")

# 🛍 Խանութ գլխավոր մենյու
@bot.message_handler(func=lambda m: m.text == "🛍 Խանութ")
def shop_menu(m: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⌚ Սմարթ ժամացույցներ", "💻 Համակարգչային աքսեսուարներ")
    markup.add("🚗 Ավտոմեքենայի պարագաներ", "🏠 Կենցաղային պարագաներ")
    markup.add("🍳 Խոհանոցային տեխնիկա", "💅 Խնամքի պարագաներ")
    markup.add("🚬 Էլեկտրոնային ծխախոտ", "👩 Կանացի (շուտով)")
    markup.add("👨 Տղամարդու (շուտով)", "🧒 Մանկական (շուտով)")
    markup.add("⬅️ Վերադառնալ գլխավոր մենյու")
    bot.send_message(m.chat.id, "🛍 Խանութ — ընտրեք կատեգորիա 👇", reply_markup=markup)

# 🏠 Գլխավոր մենյու (միայն ՄԵԿ հատ թող)
# 🏠 Գլխավոր մենյու (բոլոր 13 կոճակներով)
# 🏠 Գլխավոր մենյու (/menu հրամանով)
@bot.message_handler(commands=['menu'])
def menu_cmd(m: types.Message):
    bot.send_message(m.chat.id, "Գլխավոր մենյու ✨", reply_markup=build_main_menu())

    main = types.ReplyKeyboardMarkup(resize_keyboard=True)
    main.add(BTN_SHOP, BTN_CART)
    main.add(BTN_ORDERS, BTN_SEARCH)
    main.add(BTN_PROFILE, BTN_EXCHANGE)
    main.add(BTN_FEEDBACK, BTN_THOUGHTS)
    main.add(BTN_PARTNERS)
    main.add(BTN_RATES)
    main.add(BTN_INVITE)
    bot.send_message(m.chat.id, "Գլխավոր մենյու ✨", reply_markup=main)
# ========== DAILY RATES (auto-refresh) ==========

DATA_DIR = "admin_data"
os.makedirs(DATA_DIR, exist_ok=True)
RATES_FILE = os.path.join(DATA_DIR, "rates.json")

RATES_CACHE = {"rates": {}, "updated_at": None, "error": None}

def _rates_save():
    try:
        with open(RATES_FILE, "w", encoding="utf-8") as f:
            json.dump(RATES_CACHE, f, ensure_ascii=False, indent=2)
    except:
        pass

def _rates_load():
    global RATES_CACHE
    try:
        with open(RATES_FILE, "r", encoding="utf-8") as f:
            RATES_CACHE = json.load(f)
    except:
        pass

def fetch_rates():
    try:
        url = "https://api.exchangerate.host/latest"
        symbols = ["USD", "EUR", "RUB", "GBP", "CNY"]
        r = requests.get(url, params={"base": "AMD", "symbols": ",".join(symbols)}, timeout=10)
        data = r.json()
        raw = data.get("rates", {}) if data else {}
        converted = {}
        for k, v in raw.items():
            if v:
                converted[k] = round(1.0 / v, 4)  # 1 <FX> = ? AMD
        RATES_CACHE["rates"] = converted
        RATES_CACHE["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        RATES_CACHE["error"] = None
        _rates_save()
    except Exception as e:
        RATES_CACHE["error"] = str(e)

def _rates_loop():
    while True:
        fetch_rates()
        time.sleep(600)  # 10 րոպե

threading.Thread(target=_rates_loop, daemon=True).start()
fetch_rates()

@bot.message_handler(func=lambda m: m.text == BTN_RATES)
def on_rates(m: types.Message):
    _rates_load()
    err = RATES_CACHE.get("error")
    rates = RATES_CACHE.get("rates", {})
    if err or not rates:
        bot.send_message(m.chat.id, "❗️Քաշումը ձախողվեց, փորձիր քիչ հետո։")
        return
    flags = {"USD":"🇺🇸","EUR":"🇪🇺","RUB":"🇷🇺","GBP":"🇬🇧","CNY":"🇨🇳"}
    order = ["USD","EUR","RUB","GBP","CNY"]
    lines = ["📈 **Օրվա կուրսեր** (AMD)", ""]
    for c in order:
        if c in rates:
            lines.append(f"{flags.get(c,'')} 1 {c} = **{rates[c]} AMD**")
    lines.append("")
    lines.append(f"🕒 Թարմացվել է (UTC): {RATES_CACHE.get('updated_at','-')}")
    bot.send_message(m.chat.id, "\n".join(lines), parse_mode="Markdown")
# ===============================================
THOUGHTS_FILE = os.path.join(DATA_DIR, "thoughts.json")

def _read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def _write_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

@bot.message_handler(func=lambda m: m.text == BTN_THOUGHTS)
def show_good_thoughts(m: types.Message):
    text, kb = render_good_thoughts(page=1)
    bot.send_message(m.chat.id, text, reply_markup=kb, parse_mode="HTML")

def on_thoughts_menu(m: types.Message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Ավելացնել միտք", callback_data="t_add"))
    kb.add(types.InlineKeyboardButton("📚 Դիտել վերջինները", callback_data="t_list"))
    bot.send_message(m.chat.id, "«Խոհուն մտքեր» բաժին ✨", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "t_list")
def t_list(c):
    arr = _read_json(THOUGHTS_FILE, []) or []
    if not arr:
        bot.answer_callback_query(c.id, "Դեռ չկա", show_alert=True)
        return
    text = "💡 Վերջին մտքեր\n\n" + "\n\n".join(arr[-5:])
    bot.send_message(c.message.chat.id, text)

PENDING_THOUGHT = {}

@bot.callback_query_handler(func=lambda c: c.data == "t_add")
def t_add(c):
    PENDING_THOUGHT[c.from_user.id] = True
    bot.send_message(c.message.chat.id, "Ուղարկիր քո միտքը (տեքստով)։ Ադմինը պետք է հաստատի։")

@bot.message_handler(func=lambda m: PENDING_THOUGHT.get(m.from_user.id, False))
def t_collect(m: types.Message):
    PENDING_THOUGHT[m.from_user.id] = False
    txt = (m.text or "").strip()
    if not txt:
        return bot.reply_to(m, "Դատարկ է 🤔")
    # ուղարկում ենք ադմինին approve-ի համար
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Հաստատել", callback_data=f"t_ok::{m.chat.id}"),
        types.InlineKeyboardButton("❌ Մերժել", callback_data=f"t_no::{m.chat.id}")
    )
    bot.send_message(ADMIN_ID, f"Նոր միտք՝\n\n{txt}", reply_markup=kb)
    bot.reply_to(m, "✅ Ուղարկվեց ադմինին հաստատման։")

THOUGHTS_FILE = os.path.join(DATA_DIR, "thoughts.json")

def _read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def _write_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass


# 💬 Կապ մեզ հետ
@bot.message_handler(func=lambda m: m.text == BTN_FEEDBACK)
def contact_us(m: types.Message):
    bot.send_message(
        m.chat.id,
        "📞 Կապ մեզ հետ\n"
        "Telegram support: @StarLegenSupport\n"
        "☎️ +374 XX XX XX\n"
        "✉️ Email: support@example.com"
    )

# 💱 Փոխարկումներ (stub մեթոդների ընտրություն)
@bot.message_handler(func=lambda m: m.text == BTN_EXCHANGE)
def exchange_menu(m: types.Message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("PI ➜ USDT", callback_data="ex:pi"))
    kb.add(types.InlineKeyboardButton("FTN ➜ AMD", callback_data="ex:ftn"))
    kb.add(types.InlineKeyboardButton("Alipay լիցքավորում", callback_data="ex:ali"))
    bot.send_message(m.chat.id, "💱 Ընտրեք փոխարկումը 👇", reply_markup=kb)

# 🔍 Ապրանքի որոնում (պարզ որոնում վերնագրով/կոդով)
SEARCH_STATE_K = "SEARCH_PRODUCTS"

@bot.message_handler(func=lambda m: m.text == BTN_SEARCH)
def search_prompt(m: types.Message):
    USER_STATE[m.from_user.id] = SEARCH_STATE_K
    bot.send_message(m.chat.id, "Գրեք ապրանքի կոդը կամ անվան մասը (օր. BA1008 կամ «գորգ»):")

@bot.message_handler(func=lambda m: USER_STATE.get(m.from_user.id) == SEARCH_STATE_K)
def do_search(m: types.Message):
    q = (m.text or "").strip().lower()
    USER_STATE.pop(m.from_user.id, None)
    if not q:
        return bot.reply_to(m, "Դատարկ հարցում 🤔")

    found = []
    for code, p in PRODUCTS.items():
        title = p.get("title","").lower()
        if q in code.lower() or q in title:
            found.append((code, p["title"], p["price"]))

    if not found:
        return bot.send_message(m.chat.id, "Չգտանք նման ապրանք 🙁")

    # ցույց ենք տալիս առաջին 8-ը
    for code, title, price in found[:8]:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("👀 Դիտել", callback_data=f"p:{code}"))
        bot.send_message(m.chat.id, f"• {title} — {price}֏ (կոդ՝ {code})", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == BTN_PARTNERS)
def on_partners(m: types.Message):
    arr = _read_json(PARTNERS_FILE, [])
    if not arr:
        bot.send_message(m.chat.id, "Այս պահին գործընկերների հայտարարություններ չկան։")
        return
    text = "📢 Բիզնես գործընկերներ\n\n" + "\n\n".join(arr[-5:])
    bot.send_message(m.chat.id, text)


# ⌚ Սմարթ ժամացույցներ
@bot.message_handler(func=lambda m: m.text == "⌚ Սմարթ ժամացույցներ")
def smart_watches(m: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Վերադառնալ խանութ")
    bot.send_message(m.chat.id, "⌚ Այստեղ կլինեն Սմարթ ժամացույցների ապրանքները։", reply_markup=markup)


# 💻 Համակարգչային աքսեսուարներ
@bot.message_handler(func=lambda m: m.text == "💻 Համակարգչային աքսեսուարներ")
def pc_accessories(m: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Վերադառնալ խանութ")
    bot.send_message(m.chat.id, "💻 Այստեղ կլինեն Համակարգչային աքսեսուարների ապրանքները։", reply_markup=markup)


# 🚗 Ավտոմեքենայի պարագաներ
@bot.message_handler(func=lambda m: m.text == "🚗 Ավտոմեքենայի պարագաներ")
def car_accessories(m: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Վերադառնալ խանութ")
    bot.send_message(m.chat.id, "🚗 Այստեղ կլինեն Ավտոմեքենայի պարագաները։", reply_markup=markup)


# 🏠 Կենցաղային պարագաներ
# ---------------------------
# 📦 ՏՎՅԱԼՆԵՐ — 11 գորգ (BA100810–BA100820)
# ---------------------------
PRODUCTS = {
    "BA100810": {
        "title": "Գորգ – BA100810",
        "category": "home",
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
        "bullets": [
            "Չսահող հիմք՝ անվտանգ քայլք սահուն մակերեսների վրա",
            "Թանձր, փափուկ շերտ՝ հարմարավետ քայլքի զգացողություն",
            "Հեշտ մաքրվում՝ ձեռքով կամ լվացքի մեքենայում մինչև 30°",
            "Գույնի կայունություն՝ չի խամրում և չի թափվում",
        ],
        "long_desc": "Թիթեռ–ծաղիկ 3D դիզայնը տունը դարձնում է ավելի ջերմ ու կոկիկ։ Համապատասխանում է մուտքին, խոհանոցին, լոգարանին ու նույնիսկ ննջարանին։ Հակասահող հիմքը պահում է գորգը տեղում, իսկ խիտ վերին շերտը արագ է չորանում ու չի ներծծում տհաճ հոտեր։"
    },
    "BA100811": {
        "title": "Գորգ – BA100811", "category": "home",
        "images": [
            "media/products/BA100811.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/absorb.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 295, "best": True,
        "bullets": [
            "Խիտ գործվածք՝ երկար ծառայության համար",
            "Անհոտ և անվտանգ նյութեր ողջ ընտանիքի համար",
            "Արագ չորացում՝ խոնավ տարածքներին հարմար",
        ],
        "long_desc": "Մինիմալիստական գույներ՝ գեղեցիկ համադրվում են ցանկացած ինտերիերի հետ։ Լավ լուծում է լոգարանի/խոհանոցի համար՝ արագ կլանելով խոնավությունը և չթողնելով հետքեր։"
    },
    "BA100812": {
        "title": "Գորգ – BA100812", "category": "home",
        "images": [
            "media/products/BA100812.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 241, "best": False,
        "bullets": [
            "Կոկիկ եզրեր՝ պրեմիում տեսք",
            "Ձևը չի փոխում՝ կանոնավոր լվացումից հետո էլ",
        ],
        "long_desc": "Էսթետիկ կոմպոզիցիա՝ նուրբ դետալներով։ Հարմար է միջանցքների, մուտքի և փոքր սենյակների համար։"
    },
    "BA100813": {
        "title": "Գորգ – BA100813", "category": "home",
        "images": [
            "media/products/BA100813.jpg",
            "media/products/shared/absorb.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/interior.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 198, "best": False,
        "bullets": [
            "Հարմար ծանրաբեռնված անցուղիների համար",
            "Չի ծալվում, չի սահում՝ շնորհիվ հիմքի կառուցվածքի",
        ],
        "long_desc": "Գործնական և դիմացկուն տարբերակ՝ ամենօրյա ակտիվ օգտագործման համար։"
    },
    "BA100814": {
        "title": "Գորգ – BA100814", "category": "home",
        "images": [
            "media/products/BA100814.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 175, "best": False,
        "bullets": [
            "Փափուկ մակերես՝ հաճելի հպում",
            "Գունային կայունություն՝ երկարատև օգտագործման ընթացքում",
        ],
        "long_desc": "Բնական երանգներ՝ հանգիստ և մաքուր միջավայրի համար։ Հեշտ է տեղափոխել ու տեղադրել՝ առանց հետքեր թողնելու։"
    },
    "BA100815": {
        "title": "Գորգ – BA100815", "category": "home",
        "images": [
            "media/products/BA100815.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 210, "best": False,
        "bullets": [
            "Խիտ շերտ՝ բարձր դիմացկունություն",
            "Եզրերը չեն փշրվում",
        ],
        "long_desc": "Հարմար է ինչպես բնակարանի, այնպես էլ օֆիսի համար․ տեսքը մնում է կոկիկ անգամ հաճախակի լվացումից հետո։"
    },
    "BA100816": {
        "title": "Գորգ – BA100816", "category": "home",
        "images": [
            "media/products/BA100816.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/absorb.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 233, "best": False,
        "bullets": [
            "Դեկորատիվ եզրագծեր",
            "Չսահող հիմք՝ առավել անվտանգություն",
        ],
        "long_desc": "Էլեգանտ շեշտադրում ցանկացած ինտերիերում։ Պահպանում է տեսքը երկարատև օգտագործման ընթացքում։"
    },
    "BA100817": {
        "title": "Գորգ – BA100817", "category": "home",
        "images": [
            "media/products/BA100817.jpg",
            "media/products/shared/care.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/interior.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 221, "best": False,
        "bullets": [
            "Իդեալ է խոհանոցի և մուտքի համար",
            "Արագ չորացում՝ առանց հետքերի",
        ],
        "long_desc": "Գործնական լուծում՝ գեղեցիկ դետալներով, որը պահպանում է մաքրությունն ու հիգիենան։"
    },
    "BA100818": {
        "title": "Գորգ – BA100818", "category": "home",
        "images": [
            "media/products/BA100818.jpg",
            "media/products/shared/layers.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 187, "best": False,
        "bullets": [
            "Կոմպակտ չափ՝ հեշտ տեղադրում",
            "Թեթև քաշ՝ հարմար տեղափոխել",
        ],
        "long_desc": "Կոկիկ տարբերակ փոքր տարածքների համար՝ պահելով հարմարավետությունն ու գեղեցկությունը։"
    },
    "BA100819": {
        "title": "Գորգ – BA100819", "category": "home",
        "images": [
            "media/products/BA100819.jpg",
            "media/products/shared/absorb.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 205, "best": False,
        "bullets": [
            "Կոկիկ տեսք՝ մաքուր եզրերով",
            "Հակասահող հիմք՝ կայուն դիրք",
        ],
        "long_desc": "Գեղեցիկ լուծում միջանցքի և լոգարանի համար․ արագ է կլանում խոնավությունը և չի թողնում լաքաներ։"
    },
    "BA100820": {
        "title": "Գորգ – BA100820", "category": "home",
        "images": [
            "media/products/BA100820.jpg",
            "media/products/shared/universal.jpg",
            "media/products/shared/interior.jpg",
            "media/products/shared/advantages.jpg",
        ],
        "old_price": 2560, "price": 1690, "size": "40×60 սմ",
        "sold": 199, "best": False,
        "bullets": [
            "Էսթետիկ կոմպոզիցիա՝ բնական երանգներ",
            "Դիմացկուն հիմք՝ երկար սպասարկում",
        ],
        "long_desc": "Թարմ դիզայն, որը հեշտ է համադրել ցանկացած ինտերիերի հետ։ Պահպանում է ձևը և հեշտությամբ մաքրվում է։"
    },
}

# Օգտակար՝ ըստ կատեգորիայի վերցնել կոդերը
def product_codes_by_category(cat_key):
    return [code for code, p in PRODUCTS.items() if p["category"] == cat_key]

# ─── 🏠 Կենցաղային պարագաներ — քարտիկներ նկարի՛նով ─────────────────────────────
@bot.message_handler(func=lambda m: m.text == "🏠 Կենցաղային պարագաներ")
def home_accessories(m: types.Message):
    codes = product_codes_by_category("home")
    for code in codes:
        p = PRODUCTS[code]
        main_img = (p.get("images") or [p.get("img")])[0]
        discount = int(round(100 - (p["price"] * 100 / p["old_price"])))
        best = "🔥 Լավագույն վաճառվող\n" if p.get("best") else ""
        caption = (
            f"{best}**{p['title']}**\n"
            f"Չափս՝ {p['size']}\n"
            f"Հին գին — {p['old_price']}֏ (−{discount}%)\n"
            f"Նոր գին — **{p['price']}֏**\n"
            f"Կոդ՝ `{code}`"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("👀 Դիտել ամբողջությամբ", callback_data=f"p:{code}"))
        try:
            with open(main_img, "rb") as ph:
                bot.send_photo(m.chat.id, ph, caption=caption, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            bot.send_message(m.chat.id, caption, reply_markup=kb, parse_mode="Markdown")
        time.sleep(0.2)

    back = types.ReplyKeyboardMarkup(resize_keyboard=True)
    back.add("⬅️ Վերադառնալ խանութ", "⬅️ Վերադառնալ գլխավոր մենյու")
    bot.send_message(m.chat.id, "📎 Վերևում տեսեք բոլոր քարտիկները։", reply_markup=back)

# ─── 🖼 Ապրանքի էջ — media group + երկար copy ──────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("p:"))
def show_product(c: types.CallbackQuery):
    code = c.data.split(":", 1)[1]
    p = PRODUCTS.get(code)
    if not p:
        bot.answer_callback_query(c.id, "Ապրանքը չի գտնվել")
        return

    # Caption
    discount = int(round(100 - (p["price"] * 100 / p["old_price"])))
    bullets = "\n".join([f"✅ {b}" for b in (p.get("bullets") or [])])
    caption = (
        f"🌸 **{p['title']}**\n"
        f"✔️ Չափս՝ {p['size']}\n"
        f"{bullets}\n\n"
        f"{p.get('long_desc','')}\n\n"
        f"Հին գին — {p['old_price']}֏ (−{discount}%)\n"
        f"Նոր գին — **{p['price']}֏**\n"
        f"Վաճառված — {p['sold']} հատ\n"
        f"Կոդ՝ `{code}`"
    )

    imgs = _product_images(code)
    if not imgs:
        bot.send_message(c.message.chat.id, caption, parse_mode="Markdown")
        kb = _slider_kb(code, 0, 1)
        bot.send_message(c.message.chat.id, "Ընտրեք գործողություն 👇", reply_markup=kb)
        bot.answer_callback_query(c.id)
        return

    # Սկսում ենք 0-րդ նկարից
    with open(imgs[0], "rb") as ph:
        bot.send_photo(
            c.message.chat.id, ph, caption=caption,
            parse_mode="Markdown", reply_markup=_slider_kb(code, 0, len(imgs))
        )
    bot.answer_callback_query(c.id)


# ---------------- SLIDER + BACK BUTTONS (robust) ----------------

def _product_images(code):
    p = PRODUCTS.get(code, {})
    raw = p.get("images") or [p.get("img")]
    return [x for x in raw if x and os.path.exists(x)]

def _slider_kb(code: str, idx: int, total: int):
    # arrows
    left  = types.InlineKeyboardButton("◀️", callback_data=f"slider:{code}:{(idx-1)%total}")
    right = types.InlineKeyboardButton("▶️", callback_data=f"slider:{code}:{(idx+1)%total}")
    # cart actions
    row_cart = [
        types.InlineKeyboardButton("➕ Ավելացնել զամբյուղ", callback_data=f"cart:add:{code}"),
        types.InlineKeyboardButton("🧺 Դիտել զամբյուղ", callback_data="cart:show"),
    ]
    # back/home
    row_back = [
        types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="go_home"),
    ]
    kb = types.InlineKeyboardMarkup()
    kb.row(left, right)
    kb.row(*row_cart)
    kb.row(*row_back)
    return kb

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("slider:"))
def product_slider(c: types.CallbackQuery):
    try:
        _, code, idx_str = c.data.split(":")
        idx = int(idx_str)
    except Exception:
        return bot.answer_callback_query(c.id, "Սխալ սլայդ")

    p = PRODUCTS.get(code, {})
    imgs = _product_images(code)
    total = len(imgs)
    if total == 0:
        return bot.answer_callback_query(c.id, "Նկար չկա")

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

    # Փորձում ենք edit_message_media, եթե չստացվի՝ ուղարկում ենք նոր
    try:
        with open(imgs[idx], "rb") as ph:
            media = InputMediaPhoto(ph, caption=caption, parse_mode="Markdown")
            bot.edit_message_media(
                media=media,
                chat_id=c.message.chat.id,
                message_id=c.message.message_id,
                reply_markup=_slider_kb(code, idx, total)
            )
    except Exception:
        try:
            with open(imgs[idx], "rb") as ph:
                bot.send_photo(
                    c.message.chat.id, ph, caption=caption, parse_mode="Markdown",
                    reply_markup=_slider_kb(code, idx, total)
                )
        except Exception:
            pass

    bot.answer_callback_query(c.id)

# Վերադարձները՝ առանձին հենդլերներով (ավելի կայուն)
@bot.callback_query_handler(func=lambda c: c.data == "go_home")
def cb_go_home(c: types.CallbackQuery):
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, "Գլխավոր մենյու ✨", reply_markup=build_main_menu())

@bot.callback_query_handler(func=lambda c: c.data == "back:home_list")
def cb_home_list(c: types.CallbackQuery):
    bot.answer_callback_query(c.id)
    home_accessories(c.message)

# ─── 🍳 Խոհանոցային տեխնիկա (skeleton՝ թող այսպես) ────────────────────────────
@bot.message_handler(func=lambda m: m.text == "🍳 Խոհանոցային տեխնիկա")
def kitchen_tools(m: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Վերադառնալ խանութ", "⬅️ Վերադառնալ գլխավոր մենյու")
    bot.send_message(m.chat.id, "🍳 Այստեղ կլինեն Խոհանոցային տեխնիկայի ապրանքները։", reply_markup=markup)


# 💅 Խնամքի պարագաներ
@bot.message_handler(func=lambda m: m.text == "💅 Խնամքի պարագաներ")
def care_products(m: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Վերադառնալ խանութ")
    bot.send_message(m.chat.id, "💅 Այստեղ կլինեն Խնամքի պարագաները։", reply_markup=markup)


# 🚬 Էլեկտրոնային ծխախոտ
@bot.message_handler(func=lambda m: m.text == "🚬 Էլեկտրոնային ծխախոտ")
def e_cigs(m: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Վերադառնալ խանութ")
    bot.send_message(m.chat.id, "🚬 Այստեղ կլինեն Էլեկտրոնային ծխախոտի ապրանքները։", reply_markup=markup)


# 👩 Կանացի (շուտով)
@bot.message_handler(func=lambda m: m.text == "👩 Կանացի (շուտով)")
def women_soon(m: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Վերադառնալ խանութ")
    bot.send_message(m.chat.id, "👩 Կանացի ապրանքները հասանելի կլինեն շուտով։", reply_markup=markup)


# 👨 Տղամարդու (շուտով)
@bot.message_handler(func=lambda m: m.text == "👨 Տղամարդու (շուտով)")
def men_soon(m: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Վերադառնալ խանութ")
    bot.send_message(m.chat.id, "👨 Տղամարդու ապրանքները հասանելի կլինեն շուտով։", reply_markup=markup)


# 🧒 Մանկական (շուտով)
@bot.message_handler(func=lambda m: m.text == "🧒 Մանկական (շուտով)")
def kids_soon(m: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Վերադառնալ խանութ")
    bot.send_message(m.chat.id, "🧒 Մանկական ապրանքները հասանելի կլինեն շուտով։", reply_markup=markup)


# 🔙 Վերադառնալ խանութ
@bot.message_handler(func=lambda m: m.text == "⬅️ Վերադառնալ խանութ")
def back_to_shop(m: types.Message):
    shop_menu(m)  # կանչում ենք վերևի ֆունկցիան
# ========== SALES (CART + CHECKOUT + ADMIN APPROVE + WALLET) ==========

# պահեստ՝ զամբյուղ/վալլետ/ջանք
CART = defaultdict(dict)      # user_id -> {code: qty}
WALLET = defaultdict(int)     # user_id -> approved overpay balance (֏)
PENDING_PAY = {}              # pay_id -> {user_id, order_id, method, amount, proof_msg_id, overpay}
PENDING_ORDERS = {}           # order_id -> order dict
CHECKOUT_STATE = {}           # user_id -> {"step": "...", "order": {...}}
ORDERS_JSON = os.path.join(DATA_DIR, "orders.json")

def _save_order(order):
    data = []
    if os.path.exists(ORDERS_JSON):
        try:
            data = json.load(open(ORDERS_JSON, "r", encoding="utf-8"))
        except Exception:
            data = []
    data.append(order)
    with open(ORDERS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _order_id():
    return "ORD-" + datetime.utcnow().strftime("%Y%m%d-%H%M%S")

def _cart_total(uid: int) -> int:
    return sum(int(PRODUCTS[c]["price"]) * q for c, q in CART[uid].items())

def _cart_text(uid: int) -> str:
    if not CART[uid]:
        return "🧺 Զամբյուղը դատարկ է"
    total = 0
    lines = []
    for code, qty in CART[uid].items():
        p = PRODUCTS[code]
        sub = int(p["price"]) * qty
        total += sub
        lines.append(f"• {p['title']} × {qty} — {sub}֏")
    lines.append(f"\nԸնդամենը՝ **{total}֏**")
    return "\n".join(lines)

def _check_stock(uid: int):
    for code, qty in CART[uid].items():
        st = PRODUCTS[code].get("stock")
        if isinstance(st, int) and qty > st:
            return False, code, st
    return True, None, None

def _apply_stock(order):
    # հանում ենք պահեստից հաստատման պահին
    for it in order.get("items", []):
        code, qty = it["code"], it["qty"]
        if code in PRODUCTS and "stock" in PRODUCTS[code]:
            PRODUCTS[code]["stock"] = max(0, PRODUCTS[code]["stock"] - qty)
        if code in PRODUCTS and "sold" in PRODUCTS[code]:
            PRODUCTS[code]["sold"] = PRODUCTS[code]["sold"] + qty
def _slider_kb(code: str, idx: int, total: int):
    left  = types.InlineKeyboardButton("◀️", callback_data=f"slider:{code}:{(idx-1)%total}")
    right = types.InlineKeyboardButton("▶️", callback_data=f"slider:{code}:{(idx+1)%total}")
    row1 = [left, right]

    # 🧺 Ավելացրենք զամբյուղի կոճակները
    row_cart = [
        types.InlineKeyboardButton("➕ Ավելացնել զամբյուղ", callback_data=f"cart:add:{code}"),
        types.InlineKeyboardButton("🧺 Դիտել զամբյուղ", callback_data="cart:show"),
    ]

    row2 = [
        types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="go_home"),
    ]
    kb = types.InlineKeyboardMarkup()
    kb.row(*row1)
    kb.row(*row_cart)   # ← ԱՅՍ ՏՈՂԸ ՆՈՐՆ Է
    kb.row(*row2)
    return kb
@bot.message_handler(func=lambda m: m.text == "🛒 Զամբյուղ")
def open_cart_from_menu(m: types.Message):
    uid = m.from_user.id
    kb = types.InlineKeyboardMarkup()

    # ցուցադրում ենք մինչև 6 ապրանք՝ քանակ/կառավարման կոճակներով
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
        types.InlineKeyboardButton("✅ Պատվիրել", callback_data="checkout:start"),
    )
    kb.row(
        types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="go_home"),
    )
    bot.send_message(m.chat.id, _cart_text(uid), reply_markup=kb, parse_mode="Markdown")


# ===== CART & CHECKOUT (FULL) =====
from collections import defaultdict
from datetime import datetime
import random

# Գլոբալ պահոցներ
CART = defaultdict(dict)           # {uid: {code: qty}}
CHECKOUT_STATE = {}                # {uid: {...}}
ORDERS = []                        # օպցիանալ՝ պահենք կազմված պատվերները
_order_seq = 10000                 # պատվերների աճող համարը

# ───────── ՕԳՆԱԿԱՆ ՖՈՒՆԿՑԻԱՆԵՐ ─────────
def _order_id() -> str:
    """Պարզ աճող order_id"""
    global _order_seq
    _order_seq += 1
    return f"BA-{_order_seq}"

def _cart_total(uid: int) -> int:
    """Հաշվում է զամբյուղի ընդհանուր գինը"""
    total = 0
    for code, qty in CART[uid].items():
        p = PRODUCTS.get(code) or {}
        price = int(p.get("price", 0))
        total += price * qty
    return total

def _cart_text(uid: int) -> str:
    """Զամբյուղի տեքստը Markdown-ով"""
    if not CART[uid]:
        return "🛒 **Զամբյուղը դատարկ է։**"

    lines = ["**Ձեր զամբյուղը**:\n"]
    for code, qty in CART[uid].items():
        p = PRODUCTS.get(code) or {}
        title = p.get("title", code)
        price = int(p.get("price", 0))
        lines.append(f"• {title} — {code} × {qty} — {price*qty}֏")
    lines.append(f"\n**Ընդամենը**՝ { _cart_total(uid) }֏")
    return "\n".join(lines)

def _check_stock(uid: int):
    """
    Ստուգում է պահեստը՝ եթե PRODUCTS[code]['stock'] կա ևս։
    Վերադարձնում է (ok, bad_code, available_qty)
    """
    for code, qty in CART[uid].items():
        st = PRODUCTS.get(code, {}).get("stock")
        if isinstance(st, int) and qty > st:
            return False, code, st
    return True, None, None

def _cart_keyboard(uid: int) -> types.InlineKeyboardMarkup:
    """Կառուցում է զամբյուղի ինլայն կառավարման ստեղնաշարը"""
    kb = types.InlineKeyboardMarkup()
    # մինչև 6 տող՝ յուրաքանչյուր ապրանքի համար inc/dec/rm
    for code, qty in list(CART[uid].items())[:6]:
        title = PRODUCTS.get(code, {}).get("title", code)
        kb.row(types.InlineKeyboardButton(f"🛒 {title} ({qty})", callback_data="noop"))
        kb.row(
            types.InlineKeyboardButton("➖", callback_data=f"cart:dec:{code}"),
            types.InlineKeyboardButton("➕", callback_data=f"cart:inc:{code}"),
            types.InlineKeyboardButton("🗑", callback_data=f"cart:rm:{code}"),
        )
    # ընդհանուր գործողություններ
    kb.row(
        types.InlineKeyboardButton("❌ Մաքրել", callback_data="cart:clear"),
        types.InlineKeyboardButton("✅ Պատվիրել", callback_data="checkout:start"),
    )
    return kb

def _product_exists(code: str) -> bool:
    return code in PRODUCTS

# ───────── CART ՀԵՆԴԼԵՐ ─────────
@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("cart:"))
def cart_callbacks(c: types.CallbackQuery):
    uid = c.from_user.id
    parts = c.data.split(":")
    action = parts[1]
    code = parts[2] if len(parts) > 2 else None

    if action == "add" and code:
        st = PRODUCTS[code].get("stock")
        new_q = CART[uid].get(code, 0) + 1
        if isinstance(st, int) and new_q > st:
            bot.answer_callback_query(c.id, "Պահեստում բավարար քանակ չկա")
            return
        CART[uid][code] = new_q
        bot.answer_callback_query(c.id, "Ավելացվեց զամբյուղում ✅")

    elif action == "inc" and code:
        st = PRODUCTS[code].get("stock")
        new_q = CART[uid].get(code, 0) + 1
        if isinstance(st, int) and new_q > st:
            bot.answer_callback_query(c.id, "Վերջասահմանը՝ ըստ պահեստի")
            return
        CART[uid][code] = new_q

    elif action == "dec" and code:
        q = CART[uid].get(code, 0)
        if q <= 1:
            CART[uid].pop(code, None)
        else:
            CART[uid][code] = q - 1

    elif action == "rm" and code:
        CART[uid].pop(code, None)

    elif action == "clear":
        CART[uid].clear()

    # show cart (այստեղ ենք նաև "cart:show"-ը մշակում)
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
            types.InlineKeyboardButton("✅ Պատվիրել", callback_data="checkout:start"),
        )
        kb.row(
            types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
            types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="go_home"),
        )
        bot.send_message(c.message.chat.id, _cart_text(uid), reply_markup=kb, parse_mode="Markdown")
        bot.answer_callback_query(c.id)
    else:
        bot.answer_callback_query(c.id)


# «🛒 Զամբյուղ» հիմնական մենյուի կոճակ
@bot.message_handler(func=lambda m: (m.text or "").strip() == "🛒 Զամբյուղ")
def show_cart_cmd(m: types.Message):
    uid = m.from_user.id
    _ = CART[uid]  # ապահովենք, որ կա
    bot.send_message(m.chat.id, _cart_text(uid), reply_markup=_cart_keyboard(uid), parse_mode="Markdown")

# ───────── CHECKOUT ─────────
@bot.message_handler(func=lambda m: m.from_user.id in CHECKOUT_STATE)
def checkout_flow(m: types.Message):
    uid = m.from_user.id
    st = CHECKOUT_STATE.get(uid)
    if not st: 
        return
    step = st["step"]
    order = st["order"]

    # Անուն Ազգանուն
    if step == "name":
        order["fullname"] = (m.text or "").strip()
        st["step"] = "phone"
        bot.send_message(m.chat.id, "📞 Գրեք ձեր **հեռախոսահամարը**:")
        return

    # Հեռախոս
    if step == "phone":
        order["phone"] = (m.text or "").strip()
        st["step"] = "country"
        # ընտրություն երկրից
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for c in COUNTRIES:
            kb.add(c)
        bot.send_message(m.chat.id, "🌍 Ընտրեք **երկիրը**:", reply_markup=kb)
        return

    # Երկիր
    if step == "country":
        order["country"] = (m.text or "").strip()
        st["step"] = "city"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for x in CITIES:
            kb.add(x)
        bot.send_message(m.chat.id, "🏙 Ընտրեք **քաղաքը**:", reply_markup=kb)
        return

    # Քաղաք
    if step == "city":
        order["city"] = (m.text or "").strip()
        st["step"] = "address"
        bot.send_message(m.chat.id, "🏡 Գրեք ձեր **հասցեն**:")
        return

    # Հասցե
    if step == "address":
        order["address"] = (m.text or "").strip()
        st["step"] = "comment"
        bot.send_message(m.chat.id, "✍️ Եթե ունեք մեկնաբանություն/ցուցում՝ գրեք, կամ գրեք «—»")
        return

    # Մեկնաբանություն
    if step == "comment":
        cm = (m.text or "").strip()
        if cm == "—":
            cm = ""
        order["comment"] = cm

        # Վերջնական ամրապնդում
        amount = order["total"]
        text = [
            f"✅ **Պատվերի ամփոփում** — {order['order_id']}",
            f"👤 {order['fullname']} | 📞 {order['phone']}",
            f"📍 {order['country']}, {order['city']}, {order['address']}",
            f"🧺 Ապրանքներ:"
        ]
        for it in order["items"]:
            p = PRODUCTS.get(it["code"], {})
            title = p.get("title", it["code"])
            price = int(p.get("price", 0))
            text.append(f"• {title} — {it['code']} × {it['qty']} — {price*it['qty']}֏")
        text.append(f"\n**Ընդամենը**՝ {amount}֏")
        if order["comment"]:
            text.append(f"💬 Մեկնաբանություն՝ {order['comment']}")
        # Սեղմելու ստեղն՝ ամրագրելու համար
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✅ Հաստատել պատվերը", callback_data=f"order:confirm:{order['order_id']}"))
        kb.add(types.InlineKeyboardButton("❌ Չեղարկել", callback_data=f"order:cancel:{order['order_id']}"))

        bot.send_message(m.chat.id, "\n".join(text), parse_mode="Markdown", reply_markup=kb)
        st["step"] = "done"
        return

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("order:"))
def order_finalize(c: types.CallbackQuery):
    uid = c.from_user.id
    st = CHECKOUT_STATE.get(uid)
    if not st:
        bot.answer_callback_query(c.id, "Պատվերի ընթացքը վերջացած է")
        return

    parts = c.data.split(":")
    action = parts[1]
    oid = parts[2] if len(parts) > 2 else ""

    if action == "confirm":
        # պահպանենք պատվերը
        st["order"]["status"] = "Pending"
        ORDERS.append(st["order"])
        # մաքրել զամբյուղ
        CART[uid].clear()
        bot.edit_message_text("✅ Պատվերը գրանցվեց։ Մեր օպերատորը շուտով կապ կհաստատի։",
                              chat_id=c.message.chat.id, message_id=c.message.message_id)
        bot.answer_callback_query(c.id, "Պատվերը հաստատված է")
        CHECKOUT_STATE.pop(uid, None)
    elif action == "cancel":
        bot.edit_message_text("❌ Պատվերը չեղարկված է։",
                              chat_id=c.message.chat.id, message_id=c.message.message_id)
        bot.answer_callback_query(c.id, "Չեղարկվեց")
        CHECKOUT_STATE.pop(uid, None)
    else:
        bot.answer_callback_query(c.id)
# ===== END CART & CHECKOUT =====


@bot.message_handler(func=lambda m: CHECKOUT_STATE.get(m.from_user.id, {}).get("step") == "name")
def chk_name(m: types.Message):
    s = CHECKOUT_STATE[m.from_user.id]
    s["order"]["fullname"] = m.text.strip()
    s["step"] = "phone"
    bot.send_message(m.chat.id, "📞 Գրեք ձեր **հեռախոսահամարը** (թվերով):")

@bot.message_handler(func=lambda m: CHECKOUT_STATE.get(m.from_user.id, {}).get("step") == "phone")
def chk_phone(m: types.Message):
    t = "".join(ch for ch in m.text if ch.isdigit())
    if len(t) < 8:
        bot.send_message(m.chat.id, "❗ Թվերի քանակը քիչ է, փորձեք կրկին:")
        return
    s = CHECKOUT_STATE[m.from_user.id]
    s["order"]["phone"] = t
    s["step"] = "country"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for c in COUNTRIES: kb.add(c)
    bot.send_message(m.chat.id, "🌍 Ընտրեք **երկիր**:", reply_markup=kb)

@bot.message_handler(func=lambda m: CHECKOUT_STATE.get(m.from_user.id, {}).get("step") == "country")
def chk_country(m: types.Message):
    s = CHECKOUT_STATE[m.from_user.id]
    s["order"]["country"] = m.text.strip()
    s["step"] = "city"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for c in CITIES: kb.add(c)
    bot.send_message(m.chat.id, "🏙 Ընտրեք **քաղաք**:", reply_markup=kb)

@bot.message_handler(func=lambda m: CHECKOUT_STATE.get(m.from_user.id, {}).get("step") == "city")
def chk_city(m: types.Message):
    s = CHECKOUT_STATE[m.from_user.id]
    s["order"]["city"] = m.text.strip()
    s["step"] = "address"
    bot.send_message(m.chat.id, "📦 Գրեք **հասցե/մասնաճյուղը**:")

@bot.message_handler(func=lambda m: CHECKOUT_STATE.get(m.from_user.id, {}).get("step") == "address")
def chk_address(m: types.Message):
    s = CHECKOUT_STATE[m.from_user.id]
    s["order"]["address"] = m.text.strip()
    s["step"] = "comment"
    bot.send_message(m.chat.id, "✍️ Մեկնաբանություն (ըստ ցանկության)՝ գրեք կամ ուղարկեք «—»։")

@bot.message_handler(func=lambda m: CHECKOUT_STATE.get(m.from_user.id, {}).get("step") == "comment")
def chk_comment(m: types.Message):
    s = CHECKOUT_STATE[m.from_user.id]
    s["order"]["comment"] = (m.text.strip() if m.text.strip() != "—" else "")
    s["step"] = "paymethod"
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("Իմ քարտը", callback_data="paym:CARD"),
        types.InlineKeyboardButton("TelCell", callback_data="paym:TELCELL"),
    )
    kb.add(
        types.InlineKeyboardButton("Idram", callback_data="paym:IDRAM"),
        types.InlineKeyboardButton("Fastshift", callback_data="paym:FASTSHIFT"),
    )
    bot.send_message(m.chat.id, "💳 Ընտրեք **վճարման եղանակը**:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("paym:"))
def choose_paymethod(c: types.CallbackQuery):
    method = c.data.split(":")[1]
    uid = c.from_user.id
    s = CHECKOUT_STATE.get(uid)
    if not s:
        bot.answer_callback_query(c.id, "Ժամկետը անցել է, սկսեք նորից")
        return

    s["order"]["payment"]["method"] = method
    s["step"] = "payamount"

    # ՊՐՈՎԱՅԴԵՐՆԵՐԻ ՄԱՆՐԱՄԱՍՆԵՐԸ — ՓՈԽԻՐ ՔՈ ՌԵՔՎԻԶԻՏՆԵՐՈՎ
    details = {
        "CARD":      "💳 Քարտ՝ 5355 **** **** 1234\nՍտացող՝ Your Name",
        "TELCELL":   "🏧 TelCell՝ Account: 123456",
        "IDRAM":     "📱 Idram ID: 123456789",
        "FASTSHIFT": "💠 Fastshift Wallet: fast_shift_acc",
    }.get(method, "Մանրամասները ճշտեք ադմինից")

    total = s["order"]["total"]

    bot.answer_callback_query(c.id)
    bot.send_message(
        c.message.chat.id,
        f"{details}\n\nՍտանդարտ գումարը՝ **{total}֏**\n"
        f"✅ Կարող եք ուղարկել ավելին (օր. 1300֏): տարբերությունը կդառնա Wallet՝ ադմինի հաստատումից հետո։\n\n"
        f"Գրեք ուղարկած **գումարը**՝ թվերով (֏):",
        parse_mode="Markdown"
    )

    # ⬇️ ԱՅՍՏԵՂ ԷՐ ԲԱՑ ԹՈՂՆՎԵԼ
    set_state(c.message.chat.id, "WAIT_AMOUNT")

@bot.message_handler(func=lambda m: get_state(m.chat.id) == "WAIT_AMOUNT")
def pay_amount(m: types.Message):
    txt = (m.text or "").strip()
    try:
        amount = int(txt)
    except ValueError:
        return bot.reply_to(m, "Մուտքագրիր գումարը թվերով, օրինակ՝ 1200")

    uid = m.from_user.id
    s = CHECKOUT_STATE.get(uid)
    if not s:
        clear_state(m.chat.id)
        return bot.reply_to(m, "Սեսիան ավարտված է, սկսիր նորից։")

    s["order"]["payment"]["amount"] = amount
    set_state(m.chat.id, "WAIT_PROOF")

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📎 Կցել փոխանցման чек-ը", callback_data="pay_attach"))
    bot.send_message(m.chat.id, "Շնորհակալություն ✅ Այժմ կցիր փոխանցման чек-ը (նկար):", reply_markup=kb)



@bot.message_handler(
    func=lambda m: get_state(m.chat.id) == "WAIT_CHECK",
    content_types=["photo", "document"]
)
def _pay_receipt(m: types.Message):
    uid = m.from_user.id
    order = CHECKOUT_STATE.get(uid, {})

    amount = order.get("amount")
    address = order.get("address")  # եթե հասցեն պահում ես նախորդ քայլում

    # մաքրում ենք state-ը
    set_state(m.chat.id, None)

    # տեղեկացնում ենք օգտվողին
    if amount and address:
        bot.send_message(
            m.chat.id,
            f"📩 Շնորհակալություն!\n"
            f"🏠 Հասցե՝ {address}\n"
            f"💵 Գումար՝ {amount}֏\n\n"
            "Պատվերը փոխանցվեց ադմինին հաստատման ✅"
        )
    else:
        bot.send_message(
            m.chat.id,
            "📩 Շնորհակալություն։ Ձեր чек-ը փոխանցվեց ադմինին հաստատման ✅"
        )

    # ԱԴՄԻՆԻՆ՝ ֆորվարդ
    ADMIN_ID = 6822052289  # ← փոխիր քո admin ID-ով, եթե պետք է
    try:
        bot.forward_message(ADMIN_ID, m.chat.id, m.message_id)
    except Exception:
        pass

@bot.message_handler(func=lambda m: CHECKOUT_STATE.get(m.from_user.id, {}).get("step") == "payamount")
def pay_amount(m: types.Message):
    uid = m.from_user.id
    s = CHECKOUT_STATE.get(uid)
    try:
        amount = int("".join(ch for ch in m.text if ch.isdigit()))
    except Exception:
        bot.send_message(m.chat.id, "Մուտքագրեք գումարը՝ օրինակ 1300")
        return
    s["order"]["payment"]["amount"] = amount
    s["step"] = "paytx"
    bot.send_message(m.chat.id, "✉️ Եթե ունեք փոխանցման սքրին/ID՝ ուղարկեք հիմա (կամ գրեք «—»):")

@bot.message_handler(content_types=["text","photo"])
def finalize_payment(m: types.Message):
    uid = m.from_user.id
    if CHECKOUT_STATE.get(uid, {}).get("step") != "paytx":
        return
    s = CHECKOUT_STATE[uid]
    order = s["order"]
    order_id = order["order_id"]
    amount = order["payment"]["amount"]
    total = order["total"]
    overpay = max(0, amount - total)

    proof_msg_id = None
    if m.content_type == "photo" or (m.text and m.text.strip() != "—"):
        proof_msg_id = m.message_id

    pay_id = f"PAY-{int(time.time())}-{uid}"
    PENDING_PAY[pay_id] = {
        "user_id": uid,
        "order_id": order_id,
        "method": order["payment"]["method"],
        "amount": amount,
        "proof_msg_id": proof_msg_id,
        "overpay": overpay,
    }

    order["status"] = "Awaiting Admin Confirm"
    PENDING_ORDERS[order_id] = order
    _save_order(order)

    # Ադմինին նամակ
    items_txt = "\n".join([f"• {PRODUCTS[i['code']]['title']} × {i['qty']}" for i in order["items"]])
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Հաստատել", callback_data=f"admin:approve:{pay_id}"),
        types.InlineKeyboardButton("❌ Մերժել", callback_data=f"admin:reject:{pay_id}"),
    )
    admin_text = (
        f"🆕 Նոր պատվեր {order_id}\n"
        f"👤 {order['fullname']} | 📞 {order['phone']}\n"
        f"📍 {order['country']}, {order['city']} | {order['address']}\n"
        f"🛒 Ապրանքներ:\n{items_txt}\n"
        f"💰 Ընդամենը՝ {total}֏ | Վճարել է՝ {amount}֏\n"
        f"💼 Overpay՝ {overpay}֏ (Wallet հաստատումից հետո)\n"
        f"💳 Մեթոդ՝ {order['payment']['method']}\n"
        f"📝 Մեկնաբանություն՝ {order['comment'] or '—'}\n"
        f"👤 User: @{order['username'] or '—'} (id {uid})\n"
        f"pay_id: {pay_id}"
    )
    try:
        bot.send_message(ADMIN_ID, admin_text, reply_markup=kb)
        if proof_msg_id and m.content_type == "photo":
            bot.forward_message(ADMIN_ID, m.chat.id, proof_msg_id)
    except Exception:
        pass

    bot.send_message(m.chat.id, f"✅ Վճարումը գրանցվեց։ Օրդեր՝ {order_id}\nՍպասեք ադմինի հաստատմանը։")
    CHECKOUT_STATE.pop(uid, None)  # state close, cart կմաքրվի approve-ի պահին

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("admin:"))
def admin_actions(c: types.CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        bot.answer_callback_query(c.id, "Ոչ ադմին")
        return
    _, action, pay_id = c.data.split(":")
    pay = PENDING_PAY.get(pay_id)
    if not pay:
        bot.answer_callback_query(c.id, "Չկա այս payment")
        return
    uid = pay["user_id"]
    order = PENDING_ORDERS.get(pay["order_id"])

    if action == "approve":
        if order:
            _apply_stock(order)
            if pay["overpay"] > 0:
                WALLET[uid] += pay["overpay"]
            order["status"] = "Confirmed/Paid"
            _save_order(order)
        CART[uid].clear()
        PENDING_PAY.pop(pay_id, None)
        bot.answer_callback_query(c.id, "Հաստատվեց ✅")
        bot.send_message(uid, f"✅ Ձեր պատվերը հաստատվեց։ {order['order_id']}\nՇնորհակալություն գնումի համար!")
        bot.send_message(uid, f"💼 Wallet մնացորդ՝ {WALLET[uid]}֏")

    elif action == "reject":
        if order:
            order["status"] = "Rejected"
            _save_order(order)
        PENDING_PAY.pop(pay_id, None)
        bot.answer_callback_query(c.id, "Մերժվեց ❌")
        bot.send_message(uid, "❌ Վճարումը/պատվերը մերժվել է։ Խնդրում ենք կապ հաստատել աջակցման հետ։")

# Իմ էջը (Wallet balance)
@bot.message_handler(func=lambda m: m.text in ("🧍 Իմ էջը", "🧍 Իմ էջը 👤"))
def my_page(m: types.Message):
    uid = m.from_user.id
    bal = WALLET[uid]
    bot.send_message(m.chat.id, f"👤 Իմ էջը\n💼 Wallet մնացորդ՝ **{bal}֏**")
# ========== END SALES ==========

# ------------------- RUN -------------------
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)




