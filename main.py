import os
from dotenv import load_dotenv
import telebot
from telebot import types

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# Քո ուղարկած ողջույնի խոսքը
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

# Մենյու (քո ուղարկած)
MENU_ROWS = [
    ["🛍 Խանութ", "🛒 Զամբյուղ"],
    ["💱 Փոխարկումներ", "👤 Իմ էջը"],
    ["📊 Օրվա կուրսեր", "🏆 Լավագույններ"],
    ["💬 Կապ մեզ հետ", "🤝 Բիզնես գործընկերներ"],
    ["🔍 Ապրանքի որոնում", "👥 Հրավիրել ընկերների"],
    ["🏠 Գլխավոր մենյու"]
]

# Հաճախորդի հաշվիչ
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
    with open(photo_path, "rb") as photo:
        bot.send_photo(
            message.chat.id,
            photo,
            caption=GREETING_TEXT.format(customer_no=customer_no)
        )

    # Մենյու
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in MENU_ROWS:
        markup.row(*row)

    bot.send_message(message.chat.id, "Մենյուից ընտրեք բաժին 👇", reply_markup=markup)

print("🤖 Bot is running…")
bot.infinity_polling()

