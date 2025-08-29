# ========== PART 1/8 (INIT + /start + MAIN MENU) ==========

import os, json
from telebot import TeleBot, types, apihelper
from dotenv import load_dotenv, find_dotenv

# --- Load env token ---
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
print("dotenv path:", find_dotenv())
print("BOT_TOKEN len:", len(BOT_TOKEN))
if not BOT_TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN is empty in .env")

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# --- Counter for customers ---
COUNTER_FILE = "data/counter.json"
os.makedirs("data", exist_ok=True)

def _load_counter():
    if os.path.exists(COUNTER_FILE):
        return json.load(open(COUNTER_FILE,"r",encoding="utf-8")).get("customer_counter", 1008)
    return 1008

def _save_counter(v:int):
    json.dump({"customer_counter": v}, open(COUNTER_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

customer_counter = _load_counter()

# --- Menu buttons ---
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

# --- Welcome text ---
def welcome_text(customer_no: int) -> str:
    return (
        "🐰🌸 Բարի գալուստ BabyAngels 🛍️\n\n"
        f"💖 Շնորհակալ ենք, որ ընտրել եք մեզ ❤️ Դուք արդեն մեր սիրելի հաճախորդն եք №{customer_no}։\n\n"
        "🎁 Առաջին պատվերի համար ունեք 5% զեղչ — կգտնեք վճարման պահին։\n\n"
        "📦 Մեզ մոտ կգտնեք․\n"
        "• Ժամանակակից ու օգտակար ապրանքներ ամեն օր թարմացվող տեսականու մեջ\n"
        "• Գեղեցիկ դիզայն և անմիջական օգտագործում\n"
        "• Անվճար առաքում ամբողջ Հայաստանով\n\n"
        "💱 Բացի խանութից՝ տրամադրում ենք նաև փոխանակման ծառայություններ․\n"
        "PI ➝ USDT | FTN ➝ AMD | Alipay ➝ CNY\n\n"
        "👇 Ընտրեք բաժին և սկսեք գնումները հիմա"
    )

# --- /start ---
@bot.message_handler(commands=['start'])
def on_start(m: types.Message):
    global customer_counter
    customer_counter += 1
    _save_counter(customer_counter)

    # bunny photo
    bunny = "media/bunny.jpg"
    if os.path.exists(bunny):
        with open(bunny, "rb") as ph:
            bot.send_photo(m.chat.id, ph)

    bot.send_message(m.chat.id, welcome_text(customer_counter), reply_markup=main_menu_kb())

@bot.message_handler(commands=['menu'])
def on_menu(m: types.Message):
    bot.send_message(m.chat.id, "Գլխավոր մենյու ✨", reply_markup=main_menu_kb())

# --- Run ---
if __name__ == "__main__":
    print("Bot is running…")
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)

# ========== END PART 1 ==========
