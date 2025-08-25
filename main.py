import os, json, time, traceback
from datetime import datetime
from telebot import TeleBot, types
from dotenv import load_dotenv
from telebot import apihelper
from telebot.types import InputMediaPhoto
# դեպի Telegram API ճիշտ URL
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"

# կարդում ենք .env-ը
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
from dotenv import find_dotenv
print("dotenv path:", find_dotenv())
print("BOT_TOKEN raw:", repr(BOT_TOKEN))   # կտեսնենք եթե կա \n, space, կամ չակերտ
print("BOT_TOKEN len:", len(BOT_TOKEN))

bot = TeleBot(BOT_TOKEN)

# debug
print("BOT_TOKEN read:", (BOT_TOKEN[:6] + "..." + BOT_TOKEN[-6:]) if BOT_TOKEN else "EMPTY")
me = bot.get_me()
print("Connected as:", me.username, me.id)


if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is empty. Put it in your .env file.")

bot = TeleBot(BOT_TOKEN)

# արագ ստուգում՝ token-ը աշխատո՞ւմ է
from telebot.apihelper import ApiTelegramException
try:
    me = bot.get_me()
    print("Connected as:", me.username, me.id)
except ApiTelegramException as e:
    print("TOKEN FAIL:", e)
    raise

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

# --- MENU LABELS ---
BTN_SHOP = "🛍 Խանութ"
BTN_CART = "🛒 Զամբյուղ"
BTN_ORDERS = "📦 Իմ պատվերները"
BTN_COUPONS = "🎁 Կուպոններ"
BTN_SEARCH = "🔍 Որոնել ապրանք"
BTN_GOOD_THOUGHTS = "🧠 Լավ մտքեր"
BTN_PROFILE = "🧍 Իմ էջը"
BTN_BEST = "🏆 Լավագույններ"
BTN_EXCHANGE = "💱 Փոխարկումներ"
BTN_FEEDBACK = "💬 Հետադարձ կապ"
BTN_BONUS = "🎡 Բոնուս անիվ"
BTN_ADS = "📣 Գովազդներ"
BTN_INVITE = "👥 Հրավիրել ընկերների"
BTN_BACK = "⬅️ Վերադառնալ"

# ------------------- RUNTIME (in-memory) -------------------
USER_STATE = {}          # user_id -> state
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
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(BTN_SHOP, BTN_CART)
    markup.add(BTN_ORDERS, BTN_COUPONS)
    markup.add(BTN_SEARCH, BTN_GOOD_THOUGHTS)
    markup.add(BTN_PROFILE, BTN_BEST)
    markup.add(BTN_EXCHANGE, BTN_FEEDBACK)
    markup.add(BTN_BONUS, BTN_ADS)
    markup.add(BTN_INVITE)
    return markup
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
bot = TeleBot(BOT_TOKEN, parse_mode=None)  # we'll set parse_mode per message

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

@bot.message_handler(func=lambda m: m.text == BTN_GOOD_THOUGHTS)
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

@bot.message_handler(func=lambda m: m.text == BTN_ADS)
def show_ads(m: types.Message):
    text, kb = render_ads_list(page=1)
    bot.send_message(m.chat.id, text, reply_markup=kb, parse_mode="HTML")

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
@bot.message_handler(func=lambda m: m.text == "⬅️ Վերադառնալ գլխավոր մենյու")
def go_home(m: types.Message):
    main = types.ReplyKeyboardMarkup(resize_keyboard=True)
    main.add("🛍 Խանութ")   # մնացած կոճակները հետո կավելացնես
    bot.send_message(m.chat.id, "🏠 Գլխավոր մենյու", reply_markup=main)


# 🔙 Back callback-ներ (միայն ՄԵԿ հատ թող)
@bot.callback_query_handler(func=lambda c: c.data in ("back:shop", "back:home", "back:home_list"))
def back_callbacks(c: types.CallbackQuery):
    if c.data == "back:shop":
        shop_menu(c.message)          # Խանութ
    elif c.data == "back:home":
        go_home(c.message)            # Գլխավոր մենյու
    elif c.data == "back:home_list":
        home_accessories(c.message)   # Կենցաղային ցուցակ
    bot.answer_callback_query(c.id)

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

# ---------------------------

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

# 🖼 Ապրանքի էջ — նկար + նկարագրություն
# ---------------------------
@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("p:"))
def show_product(c: types.CallbackQuery):
    code = c.data.split(":", 1)[1]
    p = PRODUCTS.get(code)
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
    imgs = p.get("images") or [p.get("img")]
    media = []
    for i, path in enumerate(imgs[:10]):
        try:
            f = open(path, "rb")
        except Exception:
            continue
        media.append(InputMediaPhoto(f, caption=caption, parse_mode="Markdown") if i == 0 else InputMediaPhoto(f))
    if media:
        bot.send_media_group(c.message.chat.id, media)
    else:
        bot.send_message(c.message.chat.id, caption, parse_mode="Markdown")

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("⬅️ Վերադառնալ ցուցակ", callback_data="back:home_list"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="back:home"),
    )
    bot.send_message(c.message.chat.id, "Ընտրեք գործողություն 👇", reply_markup=kb)
    bot.answer_callback_query(c.id)

# ---------------------------
# 🔙 Back callback-ները
# ---------------------------
@bot.callback_query_handler(func=lambda c: c.data in ("back:shop", "back:home", "back:home_list"))
def back_callbacks(c: types.CallbackQuery):
    if c.data == "back:shop":
        # վերադարձ խանութ
        shop_menu(c.message)
    elif c.data == "back:home":
        # վերադարձ գլխավոր մենյու (օգտագործիր քո go_home-ը)
        try:
            go_home(c.message)
        except Exception:
            # fallback՝ միայն Խանութ կոճակով
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🛍 Խանութ")
            bot.send_message(c.message.chat.id, "🏠 Գլխավոր մենյու", reply_markup=markup)
    elif c.data == "back:home_list":
        # վերադարձ Կենցաղային բաժնի ցուցակ
        home_accessories(c.message)
    bot.answer_callback_query(c.id)


# 🍳 Խոհանոցային տեխնիկա
@bot.message_handler(func=lambda m: m.text == "🍳 Խոհանոցային տեխնիկա")
def kitchen_tools(m: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⬅️ Վերադառնալ խանութ")
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

# ------------------- RUN -------------------
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)




