import os
from dotenv import load_dotenv
import telebot
from telebot import types

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN չի գտնվել. .env-ը ճիշտ տեղում/անունո՞վ է։")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# Քո ուղարկած ողջույնի խոսքը 1:1
GREETING_TEXT = (
    "🐰🌸 Բարի գալուստ BabyAngels 🛍️\n\n"
    "💖 Շնորհակալ ենք, որ ընտրել եք մեզ ❤️ Դուք արդեն մեր սիրելի հաճախորդն եք №{customer_no}։\n\n"
    "🎁 Լավ լուր․ առաջին պատվերի համար ունեք 5% զեղ్చ — կգտնեք վարկածի ավարտին վճարման պահին։\n\n"
    "📦 Ի՞նչ կգտնեք մեզ մոտ․\n"
    "• Ժամանակակից ու օգտակար ապրանքներ ամեն օր թարմացվող տեսականու մեջ\n"
    "• Գեղեցիկ դիզայն և անմիջական օգտագործում\n"
    "• Անվճար առաքում ամբողջ Հայաստանով\n\n"
    "💱 Բացի խանութից՝ տրամադրում ենք նաև հուսալի և արագ փոխանակման ծառայություններ․  \n"
    "PI ➝ USDT | FTN ➝ AMD | Alipay ➝ CNY\n\n"
    "👇 Ընտրեք բաժին և սկսեք գնումները հիմա"
)

# Քո մենյուն՝ ըստ նկարի
MENU_ROWS = [
    ["🛍 Խանութ", "🛒 Զամբյուղ"],
    ["💱 Փոխարկումներ", "👤 Իմ էջը"],
    ["📊 Օրվա կուրսեր", "🏆 Լավագույններ"],
    ["💬 Կապ մեզ հետ", "🤝 Բիզնես գործընկերներ"],
    ["🔍 Ապրանքի որոնում", "👥 Հրավիրել ընկերների"],
    ["🏠 Գլխավոր մենյու"]
]

# Հաճախորդների հաշվիչ (պարզ՝ հիշողության մեջ)
customer_counter = 1007
def get_new_customer_id():
    global customer_counter
    customer_counter += 1
    return customer_counter

@bot.message_handler(commands=['start'])
def send_welcome(message):
    customer_no = get_new_customer_id()

    # bunny.jpg ուղարկում
    photo_path = os.path.join("media", "bunny.jpg")
    if not os.path.exists(photo_path):
        bot.send_message(message.chat.id, "⚠️ Չգտա media/bunny.jpg լուսանկարը։")
    else:
        with open(photo_path, "rb") as photo:
            bot.send_photo(
                message.chat.id,
                photo,
                caption=GREETING_TEXT.format(customer_no=customer_no)
            )

    # Մենյու կառուցում
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MENU_ROWS:
        kb.row(*row)
    bot.send_message(message.chat.id, "Մենյուից ընտրեք բաժին 👇", reply_markup=kb)

print("🤖 Bot is running…  /start")
bot.infinity_polling()

