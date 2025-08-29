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
# ========== PART 2/8 — ԿԱՏԵԳՈՐԻԱՆԵՐ ==========

# Կատեգորիաների անունները
CAT_HOME       = "🏡 Կենցաղային ապրանքներ"
CAT_RUGS       = "🧼 Գորգեր"
CAT_AUTO       = "🚗 Ավտոմեքենայի պարագաներ"
CAT_SMART      = "⌚ Սմարթ ժամացույցներ"
CAT_PC         = "💻 Համակարգչային աքսեսուարներ"
CAT_CARE       = "🍼 Խնամքի պարագաներ"
CAT_ECIG       = "🌬 Էլեկտրոնային ծխախոտ"
CAT_WOMEN      = "👗 Կանացի (Շուտով)"
CAT_MEN        = "👔 Տղամարդու (Շուտով)"
CAT_KIDS       = "🧸 Մանկական (Շուտով)"

# ReplyKeyboard կատեգորիաների համար
def shop_categories_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(CAT_HOME, CAT_RUGS)
    kb.add(CAT_AUTO, CAT_SMART)
    kb.add(CAT_PC, CAT_CARE)
    kb.add(CAT_ECIG, CAT_WOMEN)
    kb.add(CAT_MEN, CAT_KIDS)
    kb.add(BTN_BACK_MAIN, BTN_MAIN)  # միշտ հետ գնալու հնարավորություն
    return kb

# 🛍 Խանութ → կատեգորիաներ
@bot.message_handler(func=lambda m: m.text == BTN_SHOP)
def on_shop(m: types.Message):
    bot.send_message(m.chat.id, "Ընտրեք կատեգորիան 👇", reply_markup=shop_categories_kb())

# Յուրաքանչյուր կատեգորիայի վրա սեղմելիս հիմա միայն placeholder
@bot.message_handler(func=lambda m: m.text in {
    CAT_HOME, CAT_RUGS, CAT_AUTO, CAT_SMART, CAT_PC,
    CAT_CARE, CAT_ECIG, CAT_WOMEN, CAT_MEN, CAT_KIDS
})
def on_category_selected(m: types.Message):
    bot.send_message(
        m.chat.id,
        f"«{m.text}» բաժնի ապրանքները կավելացվեն Part 3-ում։",
        reply_markup=shop_categories_kb()
    )

# ========== END PART 2 ==========
PRODUCTS = {
    "BA100810": {
        "title": "Գորգ — BA100810",
        "category": "rugs",
        "price": 1690,
        "media": ["media/products/BA100810.jpg"],
        "desc": (
            "🌸 Եզակի ծաղկային ռելիեֆ՝ ջերմ տեսք ցանկացած սենյակում։\n"
            "Չսահող խիտ հիմք՝ անվտանգ քայլելու համար թաց մակերեսին։\n"
            "3D փափուկ տեքստուրա՝ հաճելի հպում։\n"
            "Միկրոֆիբրա՝ արագ կլանում և չորացում։\n"
            "Չի թափվում, չի գունաթափվում։\n"
            "Չափ՝ 40×60 սմ (կենցաղային ստանդարտ)։\n"
            "Հարմար՝ լոգասենյակ, միջանցք, խոհանոց, պատշգամբ։\n"
            "Լվացք՝ 30°C, առանց խլորի։\n"
            "Շնչող շերտ՝ չի պահում հոտեր։\n"
            "Ժամանակակից դիզայն՝ համադրվում է տարբեր ինտերիերի հետ։"
        ),
    },
    "BA100811": {
        "title": "Գորգ — BA100811",
        "category": "rugs",
        "price": 1690,
        "media": ["media/products/BA100811.jpg"],
        "desc": (
            "🍃 Մினிமալիստական գույներ՝ հանգիստ ինտերիերի համար։\n"
            "Բարձր կլանում՝ հատակը պահում է չոր։\n"
            "Anti-slip հիմք՝ վստահություն յուրաքանչյուր քայլի։\n"
            "Թեթև, բայց խիտ կառուցվածք՝ եզրերը չեն ծալվում։\n"
            "Կրկնակի կար՝ դիմացկունություն լվացքի ժամանակ։\n"
            "Չափ՝ 40×60 սմ, բարակ պրոֆիլ՝ դռանը չի խանգարում։\n"
            "Օդաթափանց հյուսք՝ արագ չորանում է։\n"
            "Հարմար՝ լոգարան/զուգարան, մանկական, հյուրասենյակ։\n"
            "Մաշվածակայուն՝ կենդանիներ ունեցողների համար։\n"
            "Խնամք՝ նուրբ ռեժիմ, հարթ չորացում։"
        ),
    },
    "BA100812": {
        "title": "Գորգ — BA100812",
        "category": "rugs",
        "price": 1690,
        "media": ["media/products/BA100812.jpg"],
        "desc": (
            "🦋 Թիթեռ-ծաղիկ կոմպոզիցիա՝ աչք գրավող տեսք։\n"
            "Memory foam միջուկ՝ քայլելիս մեղմ «ամպյա» զգացողություն։\n"
            "Կրկնակի շերտ՝ ջրի/փոշու կլանում + սահումից պաշտպանություն։\n"
            "Հպմանն հաճելի տեքստուրա՝ ոտքը չի սառչում։\n"
            "Չափ՝ 45×65 սմ՝ կլորացված անվտանգ եզրերով։\n"
            "Ապահով ներկեր՝ մաշկի համար անվտանգ։\n"
            "Համադրվում է բաց/նեյտրալ ինտերիերի հետ։\n"
            "Հարմար՝ լոգարան, ննջասենյակ, հայելիի մոտ։\n"
            "Լվացք՝ մեքենայով, ցածր պտույտներ։\n"
            "Չի կորցնում ձևն ու փափկությունը։"
        ),
    },
    "BA100813": {
        "title": "Գորգ — BA100813",
        "category": "rugs",
        "price": 1690,
        "media": ["media/products/BA100813.jpg"],
        "desc": (
            "🌼 Հիանալի պաշտպան սալիկի/լամինատի/քարե հատակի համար։\n"
            "Խիտ միջուկ՝ չի «տաշտա» ոտնահետքերից։\n"
            "Կլորացված եզրեր՝ էլեգանտ ու անվտանգ։\n"
            "Սիլիկոնե կետային հիմք՝ սահք ու ճռճռոց չկա։\n"
            "Չափ՝ 45×65 սմ, ունիվերսալ կիրառություն։\n"
            "Հարմար նաև կենդանու ափսեների տակ։\n"
            "Թեթև լվացք՝ 30°C, արագ չորանում։\n"
            "UV Safe՝ արևից չի գունաթափվում։\n"
            "Լուսավոր դիզայն՝ դարձնում է տարածքը կենսուրախ։\n"
            "Գեղեցիկ նվերի տարբերակ տան համար։"
        ),
    },
    "BA100814": {
        "title": "Գորգ — BA100814",
        "category": "rugs",
        "price": 1690,
        "media": ["media/products/BA100814.jpg"],
        "desc": (
            "🌿 Տերևային նրբագեղ պատկեր՝ հանգստացնող էֆեկտ։\n"
            "Թավշյա վերին շերտ՝ հարմար ու հաճելի հպում։\n"
            "Ultra-absorb tech՝ կաթիլներն անմիջապես ներծծվում են։\n"
            "Հակաբակտերիալ մշակված հիմք։\n"
            "Չափ՝ 40×60 սմ։\n"
            "Հարմար՝ լոգարան, լվացարան, խոհանոց։\n"
            "Սահակապ հիմք՝ չի շարժվում դռան բացելիս։\n"
            "Պահպանում՝ առանց հատուկ խնամքի։\n"
            "Բարձր խտություն՝ աղմուկը «ուտում» է։\n"
            "Չի փոքրանում կանոնավոր լվացքից։"
        ),
    },
    "BA100815": {
        "title": "Գորգ — BA100815",
        "category": "rugs",
        "price": 1690,
        "media": ["media/products/BA100815.jpg"],
        "desc": (
            "☁️ Սուպեր փափուկ, խիտ՝ առավոտյան առաջին քայլի համար։\n"
            "Տաքացնող շերտ՝ սառը հատակին էլ հարմար է։\n"
            "Չափ՝ 45×65 սմ, premium եզրազարդում։\n"
            "Շնչող կառուցվածք՝ հոտեր չի պահում։\n"
            "Կրկնակի կար՝ երկար կյանք։\n"
            "Մաքրում՝ փոշեկուլ/լվացք մեքենա։\n"
            "Հարմար բոլոր սենյակների համար։\n"
            "Չի քաշում կոշիկների կոշտ աղտը։\n"
            "Երկար ժամանակ պահպանում է տեսքը։\n"
            "Նրբագեղ գույներ՝ լուսավորում են միջավայրը։"
        ),
    },
    "BA100816": {
        "title": "Գորգ — BA100816",
        "category": "rugs",
        "price": 1690,
        "media": ["media/products/BA100816.jpg"],
        "desc": (
            "💧 Բարձր կլանում + արագ չորացում՝ րոպեների ընթացքում։\n"
            "Anti-slip բազա՝ խիտ կետային սիլիկոն։\n"
            "Չափ՝ 40×60 սմ։\n"
            "Տպագրությունը չի խամրում լվացքից։\n"
            "Իրական 3D լույս-ստվեր էֆեկտ՝ premium տեսք։\n"
            "Հարմար՝ բաղնիք, լվացքատարածք, պատշգամբ։\n"
            "Թեթև, հեշտ տեղափոխվող/պահվող։\n"
            "Միկրոֆիբրա՝ մաշկասիրող շերտ։\n"
            "Հարմար երեխաների համար որպես ոտնակ։\n"
            "Էրգոնոմիկ, գրավիչ լուծում։"
        ),
    },
    "BA100817": {
        "title": "Գորգ — BA100817",
        "category": "rugs",
        "price": 1690,
        "media": ["media/products/BA100817.jpg"],
        "desc": (
            "🌼 Ռոմանտիկ դիզայն՝ cozy ինտերիերի համար։\n"
            "Memory foam՝ ճնշմանը հարմարվող միջուկ։\n"
            "Չափ՝ 45×65 սմ։\n"
            "Սահամեկուսիչ սիլիկոնե հիմք։\n"
            "Քայլելիս ձայնը նվազեցնում է։\n"
            "Մաքրում՝ թափ տալ/նուրբ լվացք/քիմ. մաքրում։\n"
            "Չի գունաթափվում, եզրերը չեն քանդվում։\n"
            "Կանգնած աշխատանքի համար հարմար՝ ոտքը չի հոգնում։\n"
            "Համադրվում է նույն սերիայի այլ մոդելների հետ։\n"
            "Ընտանիքի համար գործնական ընտրություն։"
        ),
    },
    "BA100818": {
        "title": "Գորգ — BA100818",
        "category": "rugs",
        "price": 1690,
        "media": ["media/products/BA100818.jpg"],
        "desc": (
            "🛁 Հատուկ բաղնիքի համար՝ հակասնկային մշակմամբ։\n"
            "Thick absorb tech՝ պահում է հատակը չոր։\n"
            "Չափ՝ 40×60 սմ, slim profile։\n"
            "Խիտ սահակապ հիմք՝ անվտանգություն բոլորին։\n"
            "Օդանցիկ շերտ՝ արագ չորացում։\n"
            "Լվացք՝ 30°C, հարթ չորացում՝ առանց ծալքերի։\n"
            "Թեթև նեյտրալ գույներ՝ համընդհանուր։\n"
            "Երեխաների/տարեցների համար ապահով։\n"
            "Մաշվածակայուն, երկար կյանք։\n"
            "Հրաշալի արժեք/գին հարաբերակցություն։"
        ),
    },
    "BA100819": {
        "title": "Գորգ — BA100819",
        "category": "rugs",
        "price": 1690,
        "media": ["media/products/BA100819.jpg"],
        "desc": (
            "🌺 Դեկորատիվ ռելիեֆ՝ premium շունչ հյուրասենյակում։\n"
            "Ultra-soft մակերես՝ հաճելի հպում։\n"
            "Anti-slip հիմք՝ չի սահում նույնիսկ քարե հատակին։\n"
            "Չափ՝ 45×65 սմ։\n"
            "Բարձր խտություն՝ չի «թուլանում» երկար օգտագործումից։\n"
            "Արևասեր գույներ՝ լուսավոր միջավայրերի համար։\n"
            "Մաքրում՝ արագ, չորանում՝ շուտ։\n"
            "Չի թողնում մազիկներ/փշրանքներ։\n"
            "Հարմար որպես «welcome mat» դռան մոտ։\n"
            "Դիմանում է ամենօրյա ծանրաբեռնվածությանը։"
        ),
    },
    "BA100820": {
        "title": "Գորգ — BA100820",
        "category": "rugs",
        "price": 1690,
        "media": ["media/products/BA100820.jpg"],
        "desc": (
            "🌿 Eco-friendly նյութեր՝ անվտանգ երեխաների/կենդանիների համար։\n"
            "3D pattern՝ «կենդանի» լուսանկարներում ու իրականում։\n"
            "Չափ՝ 45×65 սմ։\n"
            "Շնչող հիմք՝ չի պահում խոնավություն ու հոտ։\n"
            "Extra-grip սահակապ շերտ՝ վստահ քայլք։\n"
            "Բազմաշերտ կար՝ եզրերը չեն քանդվում։\n"
            "Հարմար՝ միջանցք, լոգասենյակ, խոհանոց։\n"
            "Թեթև, կոմպակտ պահեստավորում։\n"
            "Դիմացկուն household heavy-use-ում։\n"
            "Համադրել մյուս մոդելների հետ՝ համաչափ տեսք։"
        ),
    },
    "BA100821": {
        "title": "Գորգ — BA100821",
        "category": "rugs",
        "price": 1690,
        "media": ["media/products/BA100821.jpg"],
        "desc": (
            "🌸 Կազմաձևված ծաղկային պատկեր՝ «կողմնակի» շքեղություն։\n"
            "Plush մակերես՝ սուպեր փափուկ քայլք։\n"
            "Չափ՝ 45×65 սմ։\n"
            "Anti-slip սիլիկոնե հիմք՝ անվտանգ թաց տարածքում։\n"
            "Հարթ եզրեր՝ դուռը չի «քաշում», չի ծալվում։\n"
            "Օդանցիկ հիմք՝ արագ չորացում։\n"
            "Լվացք՝ մեքենայով, գույնը չի խամրում։\n"
            "Հարմար բոլոր սենյակներում։\n"
            "Սեզոնից անկախ կիրառելիություն։\n"
            "Լավ արժեք/որակ հարաբերակցություն։"
        ),
    },
    "CAR001": {
        "title": "Ավտոմաքրող սարք — CAR001",
        "category": "auto",
        "price": 3580,
        "media": [
            "media/products/CAR001_1.jpg",
            "media/products/CAR001_2.jpg",
            "media/products/CAR001.mp4"
        ],
        "desc": (
            "🚗 Բազմաֆունկցիոնալ մաքրիչ՝ ապակի/սրահ/դետալների համար։\n"
            "Սիլիկոնե շեղբեր՝ շերտեր ու կաթիլներ չեն մնում։\n"
            "Փոխարինվող ներծծող բարձիկ՝ արագ չորացում։\n"
            "Մանր դետալների խոզանակ՝ օդափոխիչ/ճեղքեր։\n"
            "Էրգոնոմիկ բռնակ՝ ձեռք չի հոգնում։\n"
            "Կոմպակտ չափ՝ տեղ չի զբաղեցնում բեռնախցիկում։\n"
            "Հեշտ լվացվում է՝ պարզ ջրով։\n"
            "Դիմացկուն նյութեր՝ ջերմաստիճանների տատանումները չեն վախենում։\n"
            "Կիրառելի նաև տան ապակիների/հայելիների վրա։\n"
            "Արագ և մաքուր խնամք՝ ամեն օր։"
        ),
    },
}

# --- Run ---
if __name__ == "__main__":
    print("Bot is running…")
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)

# ========== END PART 1 ==========
