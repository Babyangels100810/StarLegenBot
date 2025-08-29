# Part 1 — clean start (welcome.txt-ից welcome)
import os, json
from telebot import TeleBot, types
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN") or ""
bot = TeleBot(TOKEN, parse_mode="HTML")

STATE_FILE = "state.json"

def _load_customer_no() -> int:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("customer_no", 1000)
    except Exception:
        return 1000

def _save_customer_no(n: int) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"customer_no": n}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_welcome_text(customer_no: int) -> str:
    try:
        with open("welcome.txt", "r", encoding="utf-8") as f:
            txt = f.read()
        return txt.format(customer_no=customer_no)
    except Exception:
        # fallback՝ եթե welcome.txt չկա կամ չի ընթերցվել
        return f"Բարի գալուստ ❤️ Դուք արդեն մեր սիրելի հաճախորդն եք №{customer_no}։"

customer_no = _load_customer_no()

# --- Գլխավոր մենյուի կոճակներ (միայն ցուցադրելու համար) ---
BTN_SHOP      = "🛍 Խանութ"
BTN_CART      = "🛒 Զամբյուղ"
BTN_EXCHANGE  = "💱 Փոխանակումներ"
BTN_PROFILE   = "👤 Իմ էջը"
BTN_MAIN      = "🏠 Գլխավոր մենյու"

def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_SHOP, BTN_CART)
    kb.add(BTN_EXCHANGE, BTN_PROFILE)
    kb.add(BTN_MAIN)
    return kb

@bot.message_handler(commands=["start"])
def on_start(m: types.Message):
    global customer_no
    customer_no += 1
    _save_customer_no(customer_no)

    bunny = os.path.join("media", "bunny.jpg")
    if os.path.exists(bunny):
        with open(bunny, "rb") as ph:
            bot.send_photo(m.chat.id, ph)

    bot.send_message(m.chat.id, get_welcome_text(customer_no), reply_markup=main_menu_kb())

@bot.message_handler(func=lambda msg: msg.text == BTN_MAIN)
def back_main(m: types.Message):
    bot.send_message(m.chat.id, "🏠 Գլխավոր մենյու", reply_markup=main_menu_kb())

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN բացակայում է .env ֆայլից")
    bot.infinity_polling(skip_pending=True)
