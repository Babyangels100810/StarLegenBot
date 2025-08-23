# =========================
# StarLegen — clean minimal main.py
# Flask healthcheck + TeleBot polling (Render Web Service)
# ~210 lines
# =========================
import os, json, time, threading, traceback
from datetime import datetime
import telebot
from telebot import types
from flask import Flask
from dotenv import load_dotenv

# Load .env file variables
load_dotenv()

# ---------- ENV ----------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or ""
ADMIN_ID = os.getenv("ADMIN_ID", "")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in environment variables.")

# ---------- PATHS / DATA ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
COUNTER_FILE = os.path.join(DATA_DIR, "customer_counter.json")

# Banner image (put your file here: media/banners/bunny.jpg)
BANNER_PATH = os.path.join(BASE_DIR, "bunny.jpg")
def _load_counter() -> int:
    try:
        with open(COUNTER_FILE, "r", encoding="utf-8") as f:
            obj = json.load(f)
            return int(obj.get("counter", 1007))
    except Exception:
        return 1007

def _save_counter(v: int):
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            json.dump({"counter": v}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("save counter error:", e)

def get_and_increment_customer_no() -> int:
    c = _load_counter() + 1
    _save_counter(c)
    return c

# ---------- BOT ----------
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
try:
    # polling-ի համար՝ անջատել webhook-ը, եթե նախկինում եղել է
    bot.remove_webhook()
except Exception as e:
    print("remove_webhook error:", e)

# ---------- MENU (11 tools) ----------
def build_main_menu() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🛍 Խանութ", "🛒 Զամբյուղ")
    kb.add("📦 Իմ պատվերները", "🎁 Կուպոններ")
    kb.add("🔍 Որոնել ապրանք", "🎡 Բոնուս անիվ")
    kb.add("🧍 Իմ էջը", "🏆 Լավագույններ")
    kb.add("💱 Փոխարկումներ", "💬 Հետադարձ կապ")
    kb.add("Հրավիրել ընկերների")
    return kb

def safe_reply(chat_id: int, text: str):
    try:
        bot.send_message(chat_id, text, reply_markup=build_main_menu())
    except Exception as e:
        print("safe_reply error:", e)

# --- Welcome template (ONE place only) ---
WELCOME_TEMPLATE = (
    "🐰🌸 Բարի գալուստ StarLegen 🛍️✨\n\n"
    "💖 Շնորհակալ ենք, որ միացել եք մեր սիրելի ընտանիքին ❤️\n"
    "Դուք այժմ մեր սիրելի հաճախորդն եք №{customer_no} ✨\n"
    "Մեր խանութում կարող եք գտնել ամեն օր օգտակար ապրանքների գծով լավագույն գները։\n\n"
    "🎁 Ակտիվ շանս՝ առաջին գնմանց հետո կստանաք 10% զեղչ հաջորդ պատվերի համար։\n\n"
    "📦 Ի՞նչ կգտնեք այստեղ\n"
    "• Ժամանակին և օգտակար ապրանքներ՝ ամեն օր թարմացվող տեսականիով\n"
    "• Լոյալ ակցիաներ և արագ արձագանք Telegram աջակցությամբ\n"
    "• Հարմարեցված և արագ առաքում 🚚\n\n"
    "💳 Փոխարկման ծառայություններ\n"
    "• PI ➜ USDT (շուկայական կուրս, +20% սպասարկում)\n"
    "• FTN ➜ AMD (միայն 10% սպասարկում)\n"
    "• Alipay լիցքավորում (1 CNY = 58֏)\n\n"
    "✨ Ավելի արագ՝ պարզապես ուղարկեք հարցը ներքևում 👇"
)

def send_welcome(chat_id: int, customer_no: int):
    text = WELCOME_TEMPLATE.format(customer_no=customer_no)
    try:
        with open(BANNER_PATH, "rb") as ph:
            bot.send_photo(chat_id, ph, caption=text, reply_markup=build_main_menu())
            return
    except Exception as e:
        print("BANNER ERROR:", e)
    bot.send_message(chat_id, text, reply_markup=build_main_menu())
@bot.message_handler(commands=["test_banner"])
def test_banner(m: types.Message):
    try:
        with open(BANNER_PATH, "rb") as ph:
            bot.send_photo(m.chat.id, ph, caption="OK banner")
    except Exception as e:
        bot.send_message(m.chat.id, f"Banner fail: {e}")


# ---------- /start ----------
@bot.message_handler(commands=["start"])
def cmd_start(m: types.Message):
    customer_no = get_and_increment_customer_no()
    send_welcome(m.chat.id, customer_no)

# ---------- SAFE STUB HANDLERS (all buttons reply safely) ----------
@bot.message_handler(func=lambda m: m.text == "🛍 Խանութ")
def h_shop(m: types.Message):
    safe_reply(m.chat.id, "🛍 Խանութ — շուտով կակտիվացնենք լիարժեք բաժինը։")

@bot.message_handler(func=lambda m: m.text == "🛒 Զամբյուղ")
def h_cart(m: types.Message):
    safe_reply(m.chat.id, "🛒 Ձեր զամբյուղը դեռ դատարկ է (demo).")

@bot.message_handler(func=lambda m: m.text == "📦 Իմ պատվերները")
def h_orders(m: types.Message):
    safe_reply(m.chat.id, "📦 Դեռ պատվերներ չկան (demo).")

@bot.message_handler(func=lambda m: m.text == "🎁 Կուպոններ")
def h_coupons(m: types.Message):
    safe_reply(m.chat.id, "🎁 Կուպոնների համակարգը շուտով կակտիվացնենք։")

@bot.message_handler(func=lambda m: m.text == "🔍 Որոնել ապրանք")
def h_search(m: types.Message):
    safe_reply(m.chat.id, "🔍 Որոնումը հասանելի կլինի շուտով։")

@bot.message_handler(func=lambda m: m.text == "🎡 Բոնուս անիվ")
def h_bonus(m: types.Message):
    safe_reply(m.chat.id, "🎡 Բոնուս անիվը շուտով կլինի։")

@bot.message_handler(func=lambda m: m.text == "🧍 Իմ էջը")
def h_profile(m: types.Message):
    safe_reply(m.chat.id, "🧍 Ձեր անձնական էջը (demo).")

@bot.message_handler(func=lambda m: m.text == "🏆 Լավագույններ")
def h_best(m: types.Message):
    safe_reply(m.chat.id, "🏆 Լավագույն ապրանքները շուտով։")

@bot.message_handler(func=lambda m: m.text == "💱 Փոխարկումներ")
def h_exchange(m: types.Message):
    safe_reply(m.chat.id, "💱 Փոխարկումներ (PI / FTN / Alipay) — շուտով։")

@bot.message_handler(func=lambda m: m.text == "💬 Հետադարձ կապ")
def h_feedback(m: types.Message):
    safe_reply(m.chat.id, "💬 Գրի՛ր քո կարծիքը — շուտով կտանք լիարժեք ձևը։")

@bot.message_handler(func=lambda m: m.text == "Հրավիրել ընկերների")
def h_invite(m: types.Message):
    try:
        username = bot.get_me().username
    except Exception:
        username = "your_bot"
    link = f"https://t.me/{username}?start={m.from_user.id}"
    safe_reply(m.chat.id, f"👥 Կիսվիր քո հրավիրումի հղումով:\n{link}")

# ---------- FLASK (Render health) ----------
app = Flask(__name__)

@app.get("/")
def index():
    return "OK"

@app.get("/healthz")
def healthz():
    return "ok"

# ---------- POLLING THREAD ----------
def run_bot():
    print(">> Starting polling thread…")
    while True:
        try:
            print(">> Bot polling ON", datetime.now().strftime("%H:%M:%S"))
            bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            print("Polling crashed:", e)
            print(traceback.format_exc())
            time.sleep(3)  # փոքր դադար, նոր փորձ

def start_render_mode():
    # Բոտը՝ առանձին թելով
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    # Flask՝ Render-ի PORT-ին
    port = int(os.environ.get("PORT", 5000))
    print(f">> Flask running on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    start_render_mode()
