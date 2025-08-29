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
BTN_HOME = "🏡 Կենցաղային պարագաներ"
BTN_CAR = "🚗 Ավտոմեքենայի պարագաներ"
BTN_KITCHEN = "🍳 Խոհանոցային տեխնիկա"
BTN_WATCH = "⌚️ Սմարթ ժամացույցներ"
BTN_PC = "💻 Համակարգչային աքսեսուարներ"
BTN_CARE = "🧴 Խնամքի պարագաներ"
BTN_SMOKE = "💨 Էլեկտրոնային ծխախոտ"
BTN_WOMEN = "👗 Կանացի (Շուտով)"
BTN_MEN = "🧑 Տղամարդու (Շուտով)"
BTN_KIDS = "🧸 Մանկական (Շուտով)"

def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_SHOP, BTN_CART)
    kb.add(BTN_EXCHANGE, BTN_THOUGHTS)
    kb.add(BTN_RATES, BTN_PROFILE)
    kb.add(BTN_FEEDBACK, BTN_PARTNERS)
    kb.add(BTN_SEARCH, BTN_INVITE)
    kb.add(BTN_MAIN)
    kb.add(BTN_HOME, BTN_CAR)
    kb.add(BTN_KITCHEN, BTN_WATCH)
    kb.add(BTN_PC, BTN_CARE)
    kb.add(BTN_SMOKE)
    kb.add(BTN_WOMEN, BTN_MEN, BTN_KIDS)

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

    bunny = "media/bunny.jpg"  # փոխի, եթե ֆայլդ ուրիշ տեղ ա

    if os.path.exists(bunny):
        with open(bunny, "rb") as ph:
            bot.send_photo(
                m.chat.id,
                ph,
                caption=welcome_text(customer_counter),
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
    else:
        bot.send_message(
            m.chat.id,
            welcome_text(customer_counter),
            reply_markup=main_menu_kb(),
        )


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
# Կատեգորիաների ընդհանուր հենդլեր
CAT_BTNS = {
    BTN_HOME, BTN_CAR, BTN_KITCHEN, BTN_WATCH,
    BTN_PC, BTN_CARE, BTN_SMOKE, BTN_WOMEN,
    BTN_MEN, BTN_KIDS
}

@bot.message_handler(func=lambda m: m.text in CAT_BTNS)
def on_category(m: types.Message):
    mapping = {
        BTN_HOME:  "home",
        BTN_CAR:   "car",
        BTN_KITCHEN: "kitchen",
        BTN_WATCH: "watch",
        BTN_PC:    "pc",
        BTN_CARE:  "care",
        BTN_SMOKE: "smoke",
        BTN_WOMEN: "women",
        BTN_MEN:   "men",
        BTN_KIDS:  "kids",
    }
    show_category(m.chat.id, mapping[m.text])


# --- CATEGORIES ---
CATEGORIES = {
    "home": {
        "title": "🏡 Կենցաղային պարագաներ",
        "items": ["BA100810", "BA100811", "BA100812", "BA100813", "BA100814", 
                  "BA100815", "BA100816", "BA100817", "BA100818", "BA100819", 
                  "BA100820", "BA100821"]
    },
    "car": {
        "title": "🚗 Ավտոմեքենայի պարագաներ",
        "items": ["CAR001"]
    },
    "kitchen": {
        "title": "🍳 Խոհանոցային տեխնիկա",
        "items": []
    },
    "watch": {
        "title": "⌚️ Սմարթ ժամացույցներ",
        "items": []
    },
    "pc": {
        "title": "💻 Համակարգչային աքսեսուարներ",
        "items": []
    },
    "care": {
        "title": "🧴 Խնամքի պարագաներ",
        "items": []
    },
    "smoke": {
        "title": "💨 Էլեկտրոնային ծխախոտ",
        "items": []
    },
    "women": {
        "title": "👗 Կանացի (Շուտով)",
        "items": []
    },
    "men": {
        "title": "🧑 Տղամարդու (Շուտով)",
        "items": []
    },
    "kids": {
        "title": "🧸 Մանկական (Շուտով)",
        "items": []
    }
}

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
PRODUCT_IMAGES = {
    "BA100810": [
        "media/products/BA100810.jpg",
        "media/products/shared/advantages.jpg",
        "media/products/shared/interior.jpg",
        "media/products/shared/layers.jpg",
        "media/products/shared/care.jpg",
        "media/products/shared/universal.jpg",
        "media/products/shared/absorb.jpg",
    ],
    "BA100811": [
        "media/products/BA100811.jpg",
        "media/products/shared/advantages.jpg",
        "media/products/shared/interior.jpg",
        "media/products/shared/layers.jpg",
        "media/products/shared/care.jpg",
        "media/products/shared/universal.jpg",
        "media/products/shared/absorb.jpg",
    ],
    "BA100812": [
        "media/products/BA100812.jpg",
        "media/products/shared/advantages.jpg",
        "media/products/shared/interior.jpg",
        "media/products/shared/layers.jpg",
        "media/products/shared/care.jpg",
        "media/products/shared/universal.jpg",
        "media/products/shared/absorb.jpg",
    ],
    "BA100813": [
        "media/products/BA100813.jpg",
        "media/products/shared/advantages.jpg",
        "media/products/shared/interior.jpg",
        "media/products/shared/layers.jpg",
        "media/products/shared/care.jpg",
        "media/products/shared/universal.jpg",
        "media/products/shared/absorb.jpg",
    ],
    "BA100814": [
        "media/products/BA100814.jpg",
        "media/products/shared/advantages.jpg",
        "media/products/shared/interior.jpg",
        "media/products/shared/layers.jpg",
        "media/products/shared/care.jpg",
        "media/products/shared/universal.jpg",
        "media/products/shared/absorb.jpg",
    ],
    "BA100815": [
        "media/products/BA100815.jpg",
        "media/products/shared/advantages.jpg",
        "media/products/shared/interior.jpg",
        "media/products/shared/layers.jpg",
        "media/products/shared/care.jpg",
        "media/products/shared/universal.jpg",
        "media/products/shared/absorb.jpg",
    ],
    "BA100816": [
        "media/products/BA100816.jpg",
        "media/products/shared/advantages.jpg",
        "media/products/shared/interior.jpg",
        "media/products/shared/layers.jpg",
        "media/products/shared/care.jpg",
        "media/products/shared/universal.jpg",
        "media/products/shared/absorb.jpg",
    ],
    "BA100817": [
        "media/products/BA100817.jpg",
        "media/products/shared/advantages.jpg",
        "media/products/shared/interior.jpg",
        "media/products/shared/layers.jpg",
        "media/products/shared/care.jpg",
        "media/products/shared/universal.jpg",
        "media/products/shared/absorb.jpg",
    ],
    "BA100818": [
        "media/products/BA100818.jpg",
        "media/products/shared/advantages.jpg",
        "media/products/shared/interior.jpg",
        "media/products/shared/layers.jpg",
        "media/products/shared/care.jpg",
        "media/products/shared/universal.jpg",
        "media/products/shared/absorb.jpg",
    ],
    "BA100819": [
        "media/products/BA100819.jpg",
        "media/products/shared/advantages.jpg",
        "media/products/shared/interior.jpg",
        "media/products/shared/layers.jpg",
        "media/products/shared/care.jpg",
        "media/products/shared/universal.jpg",
        "media/products/shared/absorb.jpg",
    ],
    "BA100820": [
        "media/products/BA100820.jpg",
        "media/products/shared/advantages.jpg",
        "media/products/shared/interior.jpg",
        "media/products/shared/layers.jpg",
        "media/products/shared/care.jpg",
        "media/products/shared/universal.jpg",
        "media/products/shared/absorb.jpg",
    ],
    # 11-րդի հետ “+1” (եթե ունես հավելյալ գորգ, օրինակ BA100821)
    "BA100821": [
        "media/products/BA100821.jpg",
        "media/products/shared/advantages.jpg",
        "media/products/shared/interior.jpg",
        "media/products/shared/layers.jpg",
        "media/products/shared/care.jpg",
        "media/products/shared/universal.jpg",
        "media/products/shared/absorb.jpg",
    ],

    # 🚗 Մեքենայի մաքրիչ (Car Cleaner)
    "CAR001": [
        "media/products/car_cleaner/CAR001_1.jpg",
        "media/products/car_cleaner/CAR001_2.jpg",
        "media/products/car_cleaner/CAR001_3.jpg",
        "media/products/car_cleaner/CAR001_4.jpg",
        "media/products/car_cleaner/CAR001_5.jpg",
        "media/products/car_cleaner/video_cover.jpg",
    ],
}

# ---------------- CATEGORIES ----------------
# Քեզ մոտ PRODUCTS արդեն կա (BA10..., CAR001 և այլն) — այստեղ կապում ենք կատեգորիաների հետ
CATEGORIES = {
    "home": {
        "title": "🏡 Կենցաղային պարագաներ",
        # քո գորգերի կոդերը տեղավորի այստեղ
        "items": ["BA100810","BA100811","BA100812","BA100813","BA100814","BA100815","BA100816","BA100817","BA100818","BA100819","BA100820"]
    },
    "car": {
        "title": "🚗 Ավտոմեքենայի պարագաներ",
        # օրինակ՝ ապակու մաքրող սարք
        "items": ["CAR001"]
    },
    # Կարաս հետո ավելացնես մյուսները՝ նույն ձևով
    "beauty":  {"title": "💄 Գեղեցկության/խնամք", "items": []},
    "kids":    {"title": "👶 Մանկական (ընտրվող)", "items": []},
    "men":     {"title": "🧍‍♂️ Տղամարդկանց (ընտրվող)", "items": []},
    "women":   {"title": "👩 Կանանց (ընտրվող)", "items": []},
    "gadgets": {"title": "💻 Համանվագչային (ընտրվող)", "items": []},
    "clean":   {"title": "🧼 Քիմմաքի ապրանքներ", "items": []},
    "measure": {"title": "🔎 Խոհանոց/կենցաղ", "items": []},
    "season":  {"title": "🌬️ Սեզոնային", "items": []},
    "travel":  {"title": "🧳 Փոքրաքանակ ուղեփ", "items": []},
}
@bot.message_handler(func=lambda m: m.text == BTN_HOME)
def on_home(m):
    _send_category(m.chat.id, "home")

@bot.message_handler(func=lambda m: m.text == BTN_CAR)
def on_car(m):
    _send_category(m.chat.id, "car")

@bot.message_handler(func=lambda m: m.text == BTN_KITCHEN)
def on_kitchen(m):
    _send_category(m.chat.id, "kitchen")

@bot.message_handler(func=lambda m: m.text == BTN_WATCH)
def on_watch(m):
    _send_category(m.chat.id, "watch")

@bot.message_handler(func=lambda m: m.text == BTN_PC)
def on_pc(m):
    _send_category(m.chat.id, "pc")

@bot.message_handler(func=lambda m: m.text == BTN_CARE)
def on_care(m):
    _send_category(m.chat.id, "care")

@bot.message_handler(func=lambda m: m.text == BTN_SMOKE)
def on_smoke(m):
    _send_category(m.chat.id, "smoke")

@bot.message_handler(func=lambda m: m.text == BTN_WOMEN)
def on_women(m):
    _send_category(m.chat.id, "women")

@bot.message_handler(func=lambda m: m.text == BTN_MEN)
def on_men(m):
    _send_category(m.chat.id, "men")

@bot.message_handler(func=lambda m: m.text == BTN_KIDS)
def on_kids(m):
    _send_category(m.chat.id, "kids")

# ---------------- PRICE HELPERS ----------------
def price_int(code: str) -> int:
    d = PRODUCTS.get(code, {})
    p = str(d.get("price", "0"))
    digits = "".join(ch for ch in p if ch.isdigit())
    return int(digits or "0")

def price_old_int(code: str) -> int:
    d = PRODUCTS.get(code, {})
    p = str(d.get("price_old", d.get("price", "0")))
    digits = "".join(ch for ch in p if ch.isdigit())
    return int(digits or "0")

def _fmt_cur(v: int) -> str:
    # 1690֏ → '1 690֏'
    s = f"{v:,}".replace(",", " ")
    return f"{s}֏"

# ---------------- KEYBOARDS ----------------
def categories_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🏡 Կենցաղային պարագաներ"),
           types.KeyboardButton("🚗 Ավտոմեքենայի պարագաներ"))
    kb.add(types.KeyboardButton(BTN_BACK_MAIN), types.KeyboardButton(BTN_MAIN))
    return kb

def _category_inline_kb(cat_key: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Կատեգորիաներ", callback_data="shop:backcats"),
           types.InlineKeyboardButton("🏠 Գլխավոր", callback_data="shop:main"))
    return kb

def _products_page_kb(cat_key: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅️ Կատեգորիաներ", callback_data="shop:backcats"))
    return kb

def _item_kb(code: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🛒 Ավելացնել զամբյուղ", callback_data=f"cart:add:{code}"))
    kb.add(types.InlineKeyboardButton("⬅️ Վերադառնալ", callback_data=f"shop:catof:{code}"),
           types.InlineKeyboardButton("🏠 Գլխավոր", callback_data="shop:main"))
    return kb

# ---------------- OPENERS ----------------
def _product_main_image(code: str) -> str | None:
    # եթե ապրանքի dict-ում կա 'img_main' օգտագործում ենք, թե չէ media/products/<code>*.jpg
    d = PRODUCTS.get(code, {})
    if "img_main" in d and os.path.exists(d["img_main"]):
        return d["img_main"]
    # փնտրում ենք media/products/shared կամ media/products/<աղբյուր պապկա> ...
    # ամենապարզը՝ փորձել մի քանի տարբերակ
    guess_list = [
        os.path.join(MEDIA_DIR, "products", f"{code}.jpg"),
        os.path.join(MEDIA_DIR, "products", f"{code}.png"),
        os.path.join(MEDIA_DIR, "products", "shared", f"{code}.jpg"),
        os.path.join(MEDIA_DIR, "products", "shared", f"{code}.png"),
    ]
    for p in guess_list:
        if os.path.exists(p):
            return p
    return d.get("img") if os.path.exists(d.get("img","")) else None

def _item_caption(code: str) -> str:
    d = PRODUCTS.get(code, {})
    title = d.get("title", code)
    p_new = _fmt_cur(price_int(code))
    p_old = price_old_int(code)
    price_line = f"<b>{p_new}</b>"
    if p_old and p_old > price_int(code):
        price_line = f"<s>{_fmt_cur(p_old)}</s>  <b>{p_new}</b>"
    return f"<b>{title}</b> – <code>{code}</code>\n{price_line}\n👉 Սեղմեք «Ավելացնել զամբյուղ»"

    # յուրաքանչյուր ապրանքի համար՝ preview (ֆոտո + գներ) մեսիջ
    for code in items:
        img = _product_main_image(code)
        cap = _item_caption(code)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔍 Դիտել մանրամասն", callback_data=f"shop:item:{code}"))
        kb.add(types.InlineKeyboardButton("⬅️ Կատեգորիաներ", callback_data="shop:backcats"))
        if img:
            try:
                with open(img, "rb") as ph:
                    bot.send_photo(chat_id, ph, caption=cap, reply_markup=kb, parse_mode="HTML")
            except:
                bot.send_message(chat_id, cap, reply_markup=kb, parse_mode="HTML")
        else:
            bot.send_message(chat_id, cap, reply_markup=kb, parse_mode="HTML")

def open_item(chat_id: int, code: str):
    img = _product_main_image(code)
    cap = _item_caption(code)
    kb  = _item_kb(code)
    if img:
        try:
            with open(img, "rb") as ph:
                bot.send_photo(chat_id, ph, caption=cap, reply_markup=kb, parse_mode="HTML")
        except:
            bot.send_message(chat_id, cap, reply_markup=kb, parse_mode="HTML")
    else:
        bot.send_message(chat_id, cap, reply_markup=kb, parse_mode="HTML")

# ---------------- HANDLERS ----------------
@bot.message_handler(func=lambda m: m.text == BTN_SHOP)
def shop_entry(m: types.Message):
    show_categories(m.chat.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("shop:"))
def shop_callbacks(c: types.CallbackQuery):
    data = c.data.split(":", 2)  # shop:action[:arg]
    action = data[1] if len(data) > 1 else ""
    arg = data[2] if len(data) > 2 else ""

    if action == "backcats" or action == "main":
        bot.answer_callback_query(c.id)
        show_categories(c.message.chat.id)
        return

    if action == "cat":
        # օրինակ՝ shop:cat:home
        bot.answer_callback_query(c.id)
        show_category(c.message.chat.id, arg)
        return

    if action == "item":
        bot.answer_callback_query(c.id)
        open_item(c.message.chat.id, arg)
        return

    if action == "catof":
        # shop:catof:CODE → վերադառնալ հենց այդ ապրանքի կատեգորիա
        code = arg
        # փնտրում ենք որ կատեգորիայի մեջ է այդ code-ը
        for k, v in CATEGORIES.items():
            if code in v.get("items", []):
                show_category(c.message.chat.id, k)
                break
        bot.answer_callback_query(c.id)
        return

# ---------------- MESSAGE SHORTCUTS ----------------
@bot.message_handler(func=lambda m: m.text == "🏡 Կենցաղային պարագաներ")
def open_home(m: types.Message):
    show_category(m.chat.id, "home")

@bot.message_handler(func=lambda m: m.text == "🚗 Ավտոմեքենայի պարագաներ")
def open_car(m: types.Message):
    show_category(m.chat.id, "car")
# =================== PART 4.1 — CART SUMMARY ===================

# Cart տվյալների պահեստ
CART = {}

# Ստեղծում ենք զամբյուղի ամփոփման տեքստը
def _cart_summary_text(uid: int) -> str:
    items = CART.get(uid, {})
    if not items:
        return "🛒 Ձեր զամբյուղը դատարկ է։"
    lines = []
    total = 0
    for code, qty in items.items():
        product = PRODUCTS.get(code, {})
        title = product.get("title", "Անհայտ")
        price = int(product.get("price_new", "0"))
        subtotal = price * qty
        total += subtotal
        lines.append(f"• {title} — {qty} հատ × {price}֏ = {subtotal}֏")
    lines.append(f"\n**Ընդհանուր գումար՝ {total}֏**")
    return "\n".join(lines)

# Զամբյուղի կոճակներ
def _cart_summary_kb() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("🧹 Մաքրել զամբյուղը", callback_data="cart:clear"),
        types.InlineKeyboardButton("⬅️ Վերադառնալ կատեգորիաներ", callback_data="back:categories"),
    )
    kb.row(
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="mainmenu"),
        types.InlineKeyboardButton("✅ Շարունակել պատվերով", callback_data="checkout:start"),
    )
    return kb

# Զամբյուղի ցույց տալու ֆունկցիա
@bot.message_handler(func=lambda m: m.text == "🛒 Զամբյուղ")
def show_cart(message):
    uid = message.from_user.id
    text = _cart_summary_text(uid)
    kb = _cart_summary_kb()
    bot.send_message(message.chat.id, text, reply_markup=kb, parse_mode="Markdown")
# =================== PART 4.2 — CART ACTIONS ===================

# Ապրանք ավելացնել զամբյուղ
@bot.callback_query_handler(func=lambda c: c.data.startswith("cart:add:"))
def cart_add(c: types.CallbackQuery):
    uid = c.from_user.id
    code = c.data.split(":")[2]
    CART.setdefault(uid, {})
    CART[uid][code] = CART[uid].get(code, 0) + 1
    bot.answer_callback_query(c.id, "Ավելացվեց զամբյուղում 🛒")
    # թարմացնենք զամբյուղի ամփոփումը
    bot.edit_message_text(
        _cart_summary_text(uid),
        c.message.chat.id,
        c.message.message_id,
        reply_markup=_cart_summary_kb(),
        parse_mode="Markdown"
    )

# Քանակ պակասեցնել
@bot.callback_query_handler(func=lambda c: c.data.startswith("cart:dec:"))
def cart_dec(c: types.CallbackQuery):
    uid = c.from_user.id
    code = c.data.split(":")[2]
    if uid in CART and code in CART[uid]:
        CART[uid][code] -= 1
        if CART[uid][code] <= 0:
            del CART[uid][code]
    bot.answer_callback_query(c.id, "Քանակը թարմացվեց")
    bot.edit_message_text(
        _cart_summary_text(uid),
        c.message.chat.id,
        c.message.message_id,
        reply_markup=_cart_summary_kb(),
        parse_mode="Markdown"
    )

# Ապրանք հեռացնել
@bot.callback_query_handler(func=lambda c: c.data.startswith("cart:remove:"))
def cart_remove(c: types.CallbackQuery):
    uid = c.from_user.id
    code = c.data.split(":")[2]
    if uid in CART and code in CART[uid]:
        del CART[uid][code]
    bot.answer_callback_query(c.id, "Ապրանքը հեռացվեց")
    bot.edit_message_text(
        _cart_summary_text(uid),
        c.message.chat.id,
        c.message.message_id,
        reply_markup=_cart_summary_kb(),
        parse_mode="Markdown"
    )

# Մաքրել ամբողջ զամբյուղը
@bot.callback_query_handler(func=lambda c: c.data == "cart:clear")
def cart_clear(c: types.CallbackQuery):
    uid = c.from_user.id
    CART[uid] = {}
    bot.answer_callback_query(c.id, "Զամբյուղը մաքրվեց 🧹")
    bot.edit_message_text(
        _cart_summary_text(uid),
        c.message.chat.id,
        c.message.message_id,
        reply_markup=_cart_summary_kb(),
        parse_mode="Markdown"
    )
# =================== PART 5.1 — CHECKOUT CORE FLOW ===================

import re
from collections import defaultdict

# --- կարգավորումներ/տվյալներ ---
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))  # ցանկալի է դնել .env-ում
PAYMENT_DETAILS = {
    # Սրանց արժեքները դնի .env-ում, իսկ այստեղ կարդա os.getenv-ով, օրինակ:
    "idram": os.getenv("PAY_IDRAM", "IDram: 123456 (BabyAngels)"),
    "telcell": os.getenv("PAY_TELCELL", "TelCell Wallet: +37400000000"),
    "bank": os.getenv("PAY_BANK", "Bank transfer: AM00 0000 0000 0000"),
    "cash": "Կանխիկ առաքման պահին",
}

# --- օգտատերերի "կուպոնների" մնացորդ ---
USER_WALLET = defaultdict(int)  # {uid: balance_amd}

# --- checkout state ---
CHECKOUT_STATE = {}  # {uid: {"step":..., "data": {...}, "msg_id": int}}

# --- երկրներ/քաղաքներ ---
COUNTRIES = {
    "AM": {"label": "🇦🇲 Հայաստան", "cities": ["Երևան", "Գյումրի", "Վանաձոր", "Աբովյան", "Աշտարակ", "Արտաշատ", "Կապան", "Գորիս"]},
    "RU": {"label": "🇷🇺 Ռուսաստան", "cities": ["Մոսկվա", "Սանկտ Պետերբուրգ", "Կրասնոդար", "Սոչի"]},
    "GE": {"label": "🇬🇪 Վրաստան", "cities": ["Թբիլիսի", "Բաթումի", "Քութայիսի"]},
}

PAY_METHODS = [
    ("idram", "💳 IDram"),
    ("telcell", "💳 TelCell"),
    ("bank", "🏦 Բանկային փոխանցում"),
    ("cash", "💵 Կանխիկ առաքման պահին"),
]

# --- վավերացումներ ---
NAME_RE   = re.compile(r"^[A-Za-zԱ-Ֆա-ֆԵեԸըԹթԺժԻիԼլԽխԾծԿկՀհՁձՂղՃճՄմՅյՆնՇշՈոՉչՊպՋջՌռՍսՎվՏտՐրՑցՓփՔքև\s'\-\.]{3,60}$")
INDEX_RE  = re.compile(r"^\d{4,6}$")

def _fmt_amd(n: int) -> str:
    return f"{n:,}".replace(",", " ") + "֏"

def _cart_total(uid: int) -> int:
    total = 0
    for code, qty in CART.get(uid, {}).items():
        d = PRODUCTS.get(code, {})
        price = int(d.get("price", 0))
        total += price * int(qty)
    return total

def _checkout_kb_country():
    kb = types.InlineKeyboardMarkup()
    for k, v in COUNTRIES.items():
        kb.add(types.InlineKeyboardButton(v["label"], callback_data=f"co:country:{k}"))
    kb.add(types.InlineKeyboardButton("🏠 Գլխավոր", callback_data="mainmenu"))
    return kb

def _checkout_kb_cities(country_code: str):
    kb = types.InlineKeyboardMarkup()
    for city in COUNTRIES[country_code]["cities"]:
        kb.add(types.InlineKeyboardButton(city, callback_data=f"co:city:{city}"))
    kb.add(types.InlineKeyboardButton("⬅️ Երկիր", callback_data="co:back:countries"))
    kb.add(types.InlineKeyboardButton("🏠 Գլխավոր", callback_data="mainmenu"))
    return kb

def _checkout_kb_pay():
    kb = types.InlineKeyboardMarkup()
    for key, label in PAY_METHODS:
        kb.add(types.InlineKeyboardButton(label, callback_data=f"co:pay:{key}"))
    kb.add(types.InlineKeyboardButton("⬅️ Քաղաք", callback_data="co:back:cities"))
    kb.add(types.InlineKeyboardButton("🏠 Գլխավոր", callback_data="mainmenu"))
    return kb

def _checkout_kb_confirm():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Հաստատել պատվերը", callback_data="co:confirm"))
    kb.add(types.InlineKeyboardButton("⬅️ Վճարման մեթոդ", callback_data="co:back:pay"))
    kb.add(types.InlineKeyboardButton("🏠 Գլխավոր", callback_data="mainmenu"))
    return kb

def _checkout_text(uid: int) -> str:
    st = CHECKOUT_STATE.get(uid, {})
    d  = st.get("data", {})
    lines = [
        "<b>🧾 Պատվերի ձևավորում</b>",
        "",
        f"Երկիր: {d.get('country_label','-')}",
        f"Քաղաք: {d.get('city','-')}",
        f"Անուն Ազգանուն: {d.get('full_name','-')}",
        f"Հասցե: {d.get('address','-')}",
        f"Փոստային ինդեքս: {d.get('index','-')}",
        f"Վճարման մեթոդ: {d.get('pay_label','-')}",
        "",
        "<b>Զամբյուղ</b>:"
    ]
    total = 0
    for code, qty in CART.get(uid, {}).items():
        pd = PRODUCTS.get(code, {})
        price = int(pd.get("price", 0))
        sub = price * int(qty)
        total += sub
        lines.append(f"• {pd.get('title', code)} — {qty} × {price}֏ = <b>{sub}֏</b>")
    lines.append("")
    lines.append(f"<b>Ընդհանուր` {total}֏</b>")
    wallet = USER_WALLET.get(uid, 0)
    lines.append(f"Քո կուպոնների մնացորդը՝ {_fmt_amd(wallet)}")
    return "\n".join(lines)

def _checkout_edit(chat_id: int, uid: int, text: str, kb: types.InlineKeyboardMarkup):
    # edit if we have a message, else send new one and remember id
    st = CHECKOUT_STATE.get(uid, {})
    msg_id = st.get("msg_id")
    try:
        if msg_id:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb, parse_mode="HTML")
        else:
            msg = bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
            CHECKOUT_STATE.setdefault(uid, {})["msg_id"] = msg.message_id
    except:
        msg = bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
        CHECKOUT_STATE.setdefault(uid, {})["msg_id"] = msg.message_id

# --- start checkout (comes from Part 4's button: "checkout:start") ---
@bot.callback_query_handler(func=lambda c: c.data == "checkout:start")
def cb_checkout_start(c: types.CallbackQuery):
    uid = c.from_user.id
    if not CART.get(uid):
        bot.answer_callback_query(c.id, "Զամբյուղը դատարկ է")
        return
    CHECKOUT_STATE[uid] = {"step": "country", "data": {}}
    bot.answer_callback_query(c.id)
    _checkout_edit(c.message.chat.id, uid, "Ընտրեք երկիրը 👇", _checkout_kb_country())

# --- pick country ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("co:country:"))
def cb_country(c: types.CallbackQuery):
    uid = c.from_user.id
    code = c.data.split(":")[2]
    if code not in COUNTRIES:
        bot.answer_callback_query(c.id, "Սխալ երկիր")
        return
    CHECKOUT_STATE.setdefault(uid, {"data": {}})
    CHECKOUT_STATE[uid]["data"]["country_code"]  = code
    CHECKOUT_STATE[uid]["data"]["country_label"] = COUNTRIES[code]["label"]
    CHECKOUT_STATE[uid]["step"] = "city"
    bot.answer_callback_query(c.id)
    _checkout_edit(c.message.chat.id, uid, f"Երկիր՝ {COUNTRIES[code]['label']}\nԸնտրեք քաղաք 👇", _checkout_kb_cities(code))

@bot.callback_query_handler(func=lambda c: c.data == "co:back:countries")
def cb_back_countries(c: types.CallbackQuery):
    uid = c.from_user.id
    CHECKOUT_STATE.setdefault(uid, {"data": {}})["step"] = "country"
    bot.answer_callback_query(c.id)
    _checkout_edit(c.message.chat.id, uid, "Ընտրեք երկիրը 👇", _checkout_kb_country())

# --- pick city ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("co:city:"))
def cb_city(c: types.CallbackQuery):
    uid = c.from_user.id
    city = c.data.split(":")[2]
    CHECKOUT_STATE.setdefault(uid, {"data": {}})
    CHECKOUT_STATE[uid]["data"]["city"] = city
    CHECKOUT_STATE[uid]["step"] = "name"
    bot.answer_callback_query(c.id)
    # name input via ForceReply
    msg = bot.send_message(c.message.chat.id, "✍️ Մուտքագրեք ձեր Անուն Ազգանունը (3–60 նիշ):", reply_markup=types.ForceReply())
    CHECKOUT_STATE[uid]["ask"] = {"field": "full_name", "msg_id": msg.message_id}

@bot.callback_query_handler(func=lambda c: c.data == "co:back:cities")
def cb_back_cities(c: types.CallbackQuery):
    uid = c.from_user.id
    code = CHECKOUT_STATE.get(uid, {}).get("data", {}).get("country_code")
    if not code:
        bot.answer_callback_query(c.id); return
    CHECKOUT_STATE[uid]["step"] = "city"
    bot.answer_callback_query(c.id)
    _checkout_edit(c.message.chat.id, uid, f"Երկիր՝ {COUNTRIES[code]['label']}\nԸնտրեք քաղաք 👇", _checkout_kb_cities(code))

# --- capture typed answers (name, address, index) ---
@bot.message_handler(func=lambda m: CHECKOUT_STATE.get(m.from_user.id, {}).get("ask"))
def checkout_text_answers(m: types.Message):
    uid = m.from_user.id
    st  = CHECKOUT_STATE.get(uid, {})
    ask = st.get("ask", {})
    field = ask.get("field")
    if not field:
        return
    text = (m.text or "").strip()

    if field == "full_name":
        if not NAME_RE.match(text):
            msg = bot.send_message(m.chat.id, "❌ Անուն/Ազգանունը սխալ է։ Փորձեք նորից (միայն տառեր, 3–60 նիշ):", reply_markup=types.ForceReply())
            CHECKOUT_STATE[uid]["ask"] = {"field": "full_name", "msg_id": msg.message_id}
            return
        CHECKOUT_STATE[uid]["data"]["full_name"] = text
        CHECKOUT_STATE[uid]["step"] = "address"
        # ask address
        msg = bot.send_message(m.chat.id, "🏠 Մուտքագրեք հասցեն (փողոց, շենք, բակ, բնակարան):", reply_markup=types.ForceReply())
        CHECKOUT_STATE[uid]["ask"] = {"field": "address", "msg_id": msg.message_id}
        return

    if field == "address":
        if len(text) < 5:
            msg = bot.send_message(m.chat.id, "❌ Խնդրում ենք մուտքագրել ավելի մանրամասն հասցե (նվազագույնը 5 նիշ):", reply_markup=types.ForceReply())
            CHECKOUT_STATE[uid]["ask"] = {"field": "address", "msg_id": msg.message_id}
            return
        CHECKOUT_STATE[uid]["data"]["address"] = text
        CHECKOUT_STATE[uid]["step"] = "index"
        # ask index
        msg = bot.send_message(m.chat.id, "🏷 Մուտքագրեք փոստային ինդեքսը (4–6 թվանշան):", reply_markup=types.ForceReply())
        CHECKOUT_STATE[uid]["ask"] = {"field": "index", "msg_id": msg.message_id}
        return

    if field == "index":
        if not INDEX_RE.match(text):
            msg = bot.send_message(m.chat.id, "❌ Ինդեքսը պետք է լինի 4–6 թվանշան:", reply_markup=types.ForceReply())
            CHECKOUT_STATE[uid]["ask"] = {"field": "index", "msg_id": msg.message_id}
            return
        CHECKOUT_STATE[uid]["data"]["index"] = text
        CHECKOUT_STATE[uid]["step"] = "pay"
        # show pay methods
        _checkout_edit(m.chat.id, uid, "Ընտրեք վճարման մեթոդը 👇", _checkout_kb_pay())
        CHECKOUT_STATE[uid].pop("ask", None)
        return

# --- choose pay method ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("co:pay:"))
def cb_pay(c: types.CallbackQuery):
    uid = c.from_user.id
    key = c.data.split(":")[2]
    label = dict(PAY_METHODS).get(key, key)
    CHECKOUT_STATE.setdefault(uid, {"data": {}})
    CHECKOUT_STATE[uid]["data"]["pay_key"]   = key
    CHECKOUT_STATE[uid]["data"]["pay_label"] = label
    CHECKOUT_STATE[uid]["step"] = "confirm"
    bot.answer_callback_query(c.id)
    _checkout_edit(c.message.chat.id, uid, _checkout_text(uid), _checkout_kb_confirm())

@bot.callback_query_handler(func=lambda c: c.data == "co:back:pay")
def cb_back_pay(c: types.CallbackQuery):
    uid = c.from_user.id
    CHECKOUT_STATE[uid]["step"] = "pay"
    bot.answer_callback_query(c.id)
    _checkout_edit(c.message.chat.id, uid, "Ընտրեք վճարման մեթոդը 👇", _checkout_kb_pay())

# --- confirm order (goes to pending_payment) ---
ORDERS = []  # demo storage

def _new_order_id():
    return f"BA{int(time.time())%1000000}"

@bot.callback_query_handler(func=lambda c: c.data == "co:confirm")
def cb_confirm_order(c: types.CallbackQuery):
    uid = c.from_user.id
    st = CHECKOUT_STATE.get(uid, {})
    data = st.get("data", {})
    total = _cart_total(uid)
    if total <= 0:
        bot.answer_callback_query(c.id, "Զամբյուղը դատարկ է")
        return

    order = {
        "id": _new_order_id(),
        "uid": uid,
        "total": total,
        "items": dict(CART.get(uid, {})),
        "delivery": {
            "country": data.get("country_label"),
            "city": data.get("city"),
            "name": data.get("full_name"),
            "address": data.get("address"),
            "index": data.get("index"),
        },
        "payment": {
            "method": data.get("pay_key"),
            "method_label": data.get("pay_label"),
            "status": "pending",
            "paid_amount": 0,
            "proof_msg_id": None
        },
        "status": "pending_payment"
    }
    ORDERS.append(order)

    # instruct payment
    pay_key = order["payment"]["method"]
    details = PAYMENT_DETAILS.get(pay_key, "Կապ՝ ադմինին։")
    text = (
        f"✅ Պատվերը ստեղծվեց։ Պատվեր №<b>{order['id']}</b>\n\n"
        f"{_checkout_text(uid)}\n\n"
        f"💳 <b>Վճարման տվյալներ</b> — {details}\n"
        "✉️ Խնդրում ենք ուղարկել վճարման ապացույց (նկար/վիդեո/փաստաթուղթ) և մուտքագրել փոխանցած գումարը AMD-ով։"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📎 Ուղարկել ապացույց", callback_data=f"pay:proof:{order['id']}"))
    kb.add(types.InlineKeyboardButton("🏠 Գլխավոր", callback_data="mainmenu"))
    bot.answer_callback_query(c.id)
    _checkout_edit(c.message.chat.id, uid, text, kb)

    # optionally՝ ադմինին order summary
    if ADMIN_CHAT_ID:
        bot.send_message(
            ADMIN_CHAT_ID,
            f"🆕 Նոր պատվեր №{order['id']} ({uid}) — {_fmt_amd(total)}\nՍտատուս՝ pending_payment",
            parse_mode="HTML"
        )
# =================== PART 5.2 — PAYMENT PROOF & ADMIN APPROVAL ===================

def _find_order(uid: int, order_id: str):
    for o in ORDERS:
        if o["uid"] == uid and o["id"] == order_id:
            return o
    return None

# user taps: "📎 Ուղարկել ապացույց"
@bot.callback_query_handler(func=lambda c: c.data.startswith("pay:proof:"))
def cb_pay_proof(c: types.CallbackQuery):
    uid = c.from_user.id
    order_id = c.data.split(":")[2]
    order = _find_order(uid, order_id)
    if not order:
        bot.answer_callback_query(c.id, "Պատվերը չի գտնվել"); return
    bot.answer_callback_query(c.id)
    # ask for file and amount
    msg1 = bot.send_message(c.message.chat.id, "📷 Ներբեռնեք վճարման ապացույցը (նկար/ֆայլ):")
    CHECKOUT_STATE.setdefault(uid, {})["await_proof_for"] = order_id
    msg2 = bot.send_message(c.message.chat.id, "💵 Մուտքագրեք փոխանցած գումարը AMD-ով (միայն թվեր):", reply_markup=types.ForceReply())
    CHECKOUT_STATE[uid]["await_amount_for"] = order_id
    CHECKOUT_STATE[uid]["amount_msg_id"] = msg2.message_id

# capture media as proof
@bot.message_handler(content_types=['photo', 'document', 'video'])
def on_payment_media(m: types.Message):
    uid = m.from_user.id
    order_id = CHECKOUT_STATE.get(uid, {}).get("await_proof_for")
    if not order_id:
        return
    order = _find_order(uid, order_id)
    if not order:
        return
    order["payment"]["proof_msg_id"] = m.message_id
    bot.reply_to(m, "✅ Ապացույցը պահպանվեց։")
    # notify admin with approve/reject
    if ADMIN_CHAT_ID:
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ Հաստատել վճարումը", callback_data=f"admin:payok:{order['id']}"),
            types.InlineKeyboardButton("❌ Մերժել", callback_data=f"admin:payno:{order['id']}")
        )
        bot.copy_message(ADMIN_CHAT_ID, m.chat.id, m.message_id)
        bot.send_message(ADMIN_CHAT_ID, f"Պատվեր №{order['id']} — սպասում է վճարման հաստատման։", reply_markup=kb)

# capture amount
@bot.message_handler(func=lambda m: CHECKOUT_STATE.get(m.from_user.id, {}).get("await_amount_for"))
def on_payment_amount(m: types.Message):
    uid = m.from_user.id
    order_id = CHECKOUT_STATE[uid].get("await_amount_for")
    txt = (m.text or "").strip()
    if not txt.isdigit():
        msg = bot.send_message(m.chat.id, "❌ Կարող եք գրել միայն թվեր (AMD):", reply_markup=types.ForceReply())
        CHECKOUT_STATE[uid]["await_amount_for"] = order_id
        CHECKOUT_STATE[uid]["amount_msg_id"] = msg.message_id
        return
    amt = int(txt)
    order = _find_order(uid, order_id)
    if not order:
        bot.send_message(m.chat.id, "Պատվերը չի գտնվել"); return
    order["payment"]["paid_amount"] = amt
    # add to coupons wallet
    USER_WALLET[uid] += amt
    bot.send_message(m.chat.id, f"✅ Փոխանցած գումարը՝ {_fmt_amd(amt)}. Ձեր կուպոնների մնացորդը այժմ՝ {_fmt_amd(USER_WALLET[uid])}։")
    # cleanup awaits
    CHECKOUT_STATE[uid].pop("await_amount_for", None)

# ADMIN approves/rejects payment
@bot.callback_query_handler(func=lambda c: c.data.startswith("admin:"))
def admin_payment_actions(c: types.CallbackQuery):
    if c.message.chat.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(c.id, "Միայն ադմինի համար"); return
    parts = c.data.split(":")  # admin:payok:ORDERID or admin:payno:ORDERID
    action, order_id = parts[1], parts[2]
    # find order by id (admin sees all)
    order = None
    for o in ORDERS:
        if o["id"] == order_id:
            order = o; break
    if not order:
        bot.answer_callback_query(c.id, "Պատվերը չի գտնվել"); return

    uid = order["uid"]
    if action == "payok":
        order["payment"]["status"] = "paid"
        order["status"] = "processing"
        bot.answer_callback_query(c.id, "Հաստատվեց ✅")
        bot.edit_message_text(f"Պատվեր №{order_id} — վճարումը ՀԱՍՏԱՏՎԵՑ ✅", c.message.chat.id, c.message.message_id)
        bot.send_message(uid, f"💳 Ձեր վճարումը հաստատվեց ✅\nՊատվեր №{order_id} անցավ «Մշակման» վիճակ։")
    elif action == "payno":
        order["payment"]["status"] = "rejected"
        order["status"] = "payment_rejected"
        bot.answer_callback_query(c.id, "Մերժվեց ❌")
        bot.edit_message_text(f"Պատվեր №{order_id} — վճարումը ՄԵՐԺՎԵՑ ❌", c.message.chat.id, c.message.message_id)
        bot.send_message(uid, f"⚠️ Ձեր վճարումը մերժվել է։ Պատվեր №{order_id}\nԿապնվեք օպերատորի հետ։")

# Mark delivered by customer
def _delivery_done_kb(order_id: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📦 Ստացա պատվերը", callback_data=f"co:delivered:{order_id}"))
    return kb

def notify_out_for_delivery(order):
    uid = order["uid"]
    bot.send_message(uid, f"🚚 Պատվեր №{order['id']} ճանապարհին է։", reply_markup=_delivery_done_kb(order["id"]))

@bot.callback_query_handler(func=lambda c: c.data.startswith("co:delivered:"))
def cb_delivered(c: types.CallbackQuery):
    uid = c.from_user.id
    order_id = c.data.split(":")[2]
    order = _find_order(uid, order_id)
    if not order:
        bot.answer_callback_query(c.id, "Պատվերը չի գտնվել"); return
    order["status"] = "delivered"
    bot.answer_callback_query(c.id, "Շնորհակալություն 🫶")
    bot.edit_message_text(f"📦 Պատվեր №{order_id} — ստացված է ✅", c.message.chat.id, c.message.message_id)
    if ADMIN_CHAT_ID:
        bot.send_message(ADMIN_CHAT_ID, f"📦 Հաճախորդը հաստատեց՝ պատվեր №{order_id} ստացված է ✅")

# --- Run ---
if __name__ == "__main__":
    print("Bot is running…")
    bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)

# ========== END PART 1 ==========
