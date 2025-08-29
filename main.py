import os
from dotenv import load_dotenv
import telebot
from telebot import types

# --- .env only ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN չի գտնվել (.env ֆայլը չկա/սխալ է).")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# Քո վերջնական ողջույնի խոսքը (ինչը գրել էիր)
GREETING_TEXT = (
    "🐰🌸 Բարի գալուստ BabyAngels 🛍️\n\n"
    "💖 Շնորհակալ ենք, որ ընտրել եք մեզ ❤️ Դուք արդեն մեր սիրելի հաճախորդն եք №{customer_no}։\n\n"
    "🎁 Լավ լուր․ առաջին պատվերի համար ունեք 5% զեղչ — կգտնեք վարկածի ավարտին վճարման պահին։\n\n"
    "📦 Ի՞նչ կգտնեք մեզ մոտ․\n"
    "• Ժամանակակից ու օգտակար ապրանքներ ամեն օր թարմացվող տեսականու մեջ\n"
    "• Գեղեցիկ դիզայն և անմիջական օգտագործում\n"
    "• Անվճար առաքում ամբողջ Հայաստանով\n\n"
    "💱 Բացի խանութից՝ տրամադրում ենք նաև հուսալի և արագ փոխանակման ծառայություններ․  \n"
    "PI ➝ USDT | FTN ➝ AMD | Alipay ➝ CNY\n\n"
    "👇 Ընտրեք բաժին և սկսեք գնումները հիմա"
)

# Քո մենյուն (ինչը նկարում էր)
MENU_ROWS = [
    ["🛍 Խանութ", "🛒 Զամբյուղ"],
    ["💱 Փոխարկումներ", "👤 Իմ էջը"],
    ["📊 Օրվա կուրսեր", "🏆 Լավագույններ"],
    ["💬 Կապ մեզ հետ", "🤝 Բիզնես գործընկերներ"],
    ["🔍 Ապրանքի որոնում", "👥 Հրավիրել ընկերների"],
    ["🏠 Գլխավոր մենյու"]
]

# Պարզ հաճախորդի հաշվիչ (մինչև տվյալների բազա կապենք)
customer_counter = 1007
def next_customer_id():
    global customer_counter
    customer_counter += 1
    return customer_counter

@bot.message_handler(commands=['start'])
def start(message):
    cid = next_customer_id()

    # լուսանկարը
    photo_path = os.path.join("media", "bunny.jpg")
    if os.path.exists(photo_path):
        with open(photo_path, "rb") as p:
            bot.send_photo(message.chat.id, p, caption=GREETING_TEXT.format(customer_no=cid))
    else:
        bot.send_message(message.chat.id, GREETING_TEXT.format(customer_no=cid))

    # մենյու
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MENU_ROWS:
        kb.row(*row)
    bot.send_message(message.chat.id, "Մենյուից ընտրեք բաժին 👇", reply_markup=kb)

print("🤖 Running…  /start")
bot.infinity_polling()

