### START PART 1/8

import os, json, time, traceback
from datetime import datetime
from telebot import TeleBot, types
from dotenv import load_dotenv, find_dotenv
from telebot.types import InputMediaPhoto
from collections import defaultdict
import re
import requests

# ===== STORAGE =====
CART = defaultdict(dict)         # {user_id: {code: qty}}
CHECKOUT_STATE = {}              # per-user checkout wizard state
ORDERS = []                      # demo storage

# ===== BUTTONS =====
BTN_BACK_MAIN = "⬅ Վերադառնալ գլխավոր մենյու"

# ===== MAIN MENU =====
def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🛍 Խանութ", "🛒 Զամբյուղ")
    kb.add("💱 Փոխարկումներ", "💬 Կապ մեզ հետ")
    kb.add("🔍 Որոնել ապրանք", "🧍 Իմ էջը")
    return kb

def show_main_menu(chat_id, text="Գլխավոր մենյու ✨"):
    bot.send_message(chat_id, text, reply_markup=main_menu_kb())

# ===== VALIDATION REGEX =====
NAME_RE  = re.compile(r"^[A-Za-z\u0531-\u0556\u0561-\u0587ЁёЪъЫыЭэЙй\s'\-\.]{3,60}$")
PHONE_RE = re.compile(r"^(\+374|0)\d{8}$")

def _order_id():
    import time
    return f"BA{int(time.time()) % 1000000}"

def _cart_total(uid: int) -> int:
    return sum(PRODUCTS[c]["price"] * q for c, q in CART[uid].items())

def _check_stock(uid: int):
    for code, qty in CART[uid].items():
        st = PRODUCTS[code].get("stock")
        if isinstance(st, int) and qty > st:
            return False, code, st
    return True, None, None

COUNTRIES = ["Հայաստան", "Ռուսաստան"]
CITIES = ["Երևան", "Գյումրի", "Վանաձոր", "Աբովյան", "Արտաշատ",
          "Արմավիր", "Հրազդան", "Մասիս", "Աշտարակ", "Եղվարդ", "Չարենցավան"]

@bot.message_handler(content_types=['text', 'contact'], func=lambda m: m.from_user.id in CHECKOUT_STATE)
def checkout_flow(m: types.Message):
    uid = m.from_user.id
    st = CHECKOUT_STATE.get(uid)
    if not st:
        return
    step  = st["step"]
    order = st["order"]

    # universal back
    if m.text == BTN_BACK_MAIN:
        CHECKOUT_STATE.pop(uid, None)
        show_main_menu(m.chat.id, "Վերադարձաք գլխավոր մենյու։")
        return

    # STEP: name
    if step == "name":
        txt = (m.text or "").strip()
        if not NAME_RE.match(txt):
            bot.send_message(m.chat.id, "❗ Անուն/Ազգանուն՝ միայն տառերով (3–60 նշան). Կրկին փորձեք։")
            return
        order["fullname"] = txt
        st["step"] = "phone"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(types.KeyboardButton("📱 Ուղարկել կոնտակտ", request_contact=True))
        kb.add(BTN_BACK_MAIN)
        bot.send_message(m.chat.id, "📞 Գրեք հեռախոսահամարը (+374xxxxxxxx կամ 0xxxxxxxx) կամ սեղմեք «📱 Ուղարկել կոնտակտ».", reply_markup=kb)
        return

    # STEP: phone
    if step == "phone":
        phone = None
        if m.contact and m.contact.phone_number:
            phone = m.contact.phone_number.replace(" ", "")
            if not phone.startswith("+"):
                phone = "+" + phone
        else:
            phone = (m.text or "").replace(" ", "")
        if not PHONE_RE.match(phone):
            bot.send_message(m.chat.id, "❗ Սխալ հեռախոսահամար. օրինակ՝ +374441112233 կամ 0441112233։ Կրկին գրեք։")
            return
        order["phone"] = phone
        st["step"] = "country"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for c in COUNTRIES:
            kb.add(c)
        kb.add(BTN_BACK_MAIN)
        bot.send_message(m.chat.id, "🌍 Ընտրեք երկիրը՝", reply_markup=kb)
        return

    # ... շարունակվում է հաջորդ մասում ...

### END PART 1/8
### PART 2/8 START

    # STEP: country
    if step == "country":
        if m.text not in COUNTRIES:
            bot.send_message(m.chat.id, "Խնդրում ենք ընտրել առաջարկվող կոճակներից։")
            return
        order["country"] = m.text
        st["step"] = "city"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for i in range(0, len(CITIES), 2):
            row = [types.KeyboardButton(x) for x in CITIES[i:i+2]]
            kb.row(*row)
        kb.add(BTN_BACK_MAIN)
        bot.send_message(m.chat.id, "🏙️ Ընտրեք քաղաքը՝", reply_markup=kb)
        return

    # STEP: city
    if step == "city":
        if m.text not in CITIES:
            bot.send_message(m.chat.id, "Խնդրում ենք ընտրել առաջարկվող քաղաքներից։")
            return
        order["city"] = m.text
        st["step"] = "address"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(BTN_BACK_MAIN)
        bot.send_message(m.chat.id, "🏡 Գրեք հասցեն (փողոց, տուն, մուտք, բնակարան)․", reply_markup=kb)
        return

    # STEP: address
    if step == "address":
        txt = (m.text or "").strip()
        if len(txt) < 5:
            bot.send_message(m.chat.id, "❗ Գրեք ավելի մանր հասցե (առնվազն 5 նշան)։")
            return
        order["address"] = txt
        st["step"] = "comment"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add("—")
        kb.add(BTN_BACK_MAIN)
        bot.send_message(m.chat.id, "📝 Լրացուցիչ մեկնաբանություն (կամ գրեք «—», եթե չկա)։", reply_markup=kb)
        return

    # STEP: comment (final)
    if step == "comment":
        order["comment"] = "" if (m.text or "").strip() in {"", "—", "-"} else (m.text or "").strip()
        order["status"] = "Pending"
        order["created_at"] = datetime.utcnow().isoformat()

        # պահպանում ենք պատվերը (demo)
        ORDERS.append(order)

        # մաքրում ենք state-ը և զամբյուղը
        CART[uid].clear()
        CHECKOUT_STATE.pop(uid, None)

        bot.send_message(
            m.chat.id,
            f"✅ Պատվերը գրանցվեց։ Մեր օպերատորը շուտով կկապվի։\nՊատվերի ID: {order['order_id']}",
            reply_markup=types.ReplyKeyboardRemove()
        )
        # ⬇️ Ավտոմատ բացում ենք ԳԼԽԱՎՈՐ ՄԵՆՅՈւ
        show_main_menu(m.chat.id)
        return


@bot.message_handler(func=lambda m: m.text == BTN_BACK_MAIN)
def back_to_main(m: types.Message):
    CHECKOUT_STATE.pop(m.from_user.id, None)
    show_main_menu(m.chat.id, "Վերադարձաք գլխավոր մենյու։")


# ===== CART HANDLER =====
def _cart_text(uid: int) -> str:
    if not CART[uid]:
        return "🛒 Զամբյուղը դատարկ է։"
    out = ["Ձեր զամբյուղը:"]
    total = 0
    for code, qty in CART[uid].items():
        p = PRODUCTS[code]
        line = f"• {p['title']} ({code}) × {qty} – {p['price']*qty}֏"
        out.append(line)
        total += p['price'] * qty
    out.append(f"\nԸնդամենը՝ {total}֏")
    return "\n".join(out)


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("cart:"))
def cart_callbacks(c: types.CallbackQuery):
    uid = c.from_user.id
    parts = c.data.split(":")
    action = parts[1]
    code = parts[2] if len(parts) > 2 else None

    if action == "add" and code:
        CART[uid][code] = CART[uid].get(code, 0) + 1
        bot.answer_callback_query(c.id, "Ավելացվեց զամբյուղում ✅")

    elif action == "inc" and code:
        st = PRODUCTS[code].get("stock")
        new_q = CART[uid].get(code, 0) + 1
        if isinstance(st, int) and new_q > st:
            bot.answer_callback_query(c.id, "Վերջասահմանը՝ ըստ պահեստի")
            return
        CART[uid][code] = new_q
        bot.answer_callback_query(c.id)

    elif action == "dec" and code:
        q = CART[uid].get(code, 0)
        if q <= 1:
            CART[uid].pop(code, None)
        else:
            CART[uid][code] = q - 1
        bot.answer_callback_query(c.id)

    elif action == "rm" and code:
        CART[uid].pop(code, None)
        bot.answer_callback_query(c.id)

    elif action == "clear":
        CART[uid].clear()
        bot.answer_callback_query(c.id)

    # show cart again
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
        bot.send_message(c.message.chat.id, _cart_text(uid), reply_markup=kb, parse_mode="Markdown")

### END PART 2/8
### PART 3/8 START

@bot.callback_query_handler(func=lambda c: c.data == "checkout:start")
def checkout_start(c: types.CallbackQuery):
    uid = c.from_user.id
    if not CART[uid]:
        bot.answer_callback_query(c.id, "Զամբյուղը դատարկ է")
        return

    ok, code, st = _check_stock(uid)
    if not ok:
        bot.answer_callback_query(c.id, "Պահեստում բավարար քանակ չկա")
        bot.send_message(c.message.chat.id, f"⚠️ {PRODUCTS[code]['title']} — հասանելի՝ {st} հատ")
        return

    order_id = _order_id()
    CHECKOUT_STATE[uid] = {
        "step": "name",
        "order": {
            "order_id": order_id,
            "user_id": uid,
            "username": c.from_user.username,
            "fullname": "",
            "phone": "",
            "country": "",
            "city": "",
            "address": "",
            "comment": "",
            "items": [{"code": code, "qty": qty} for code, qty in CART[uid].items()],
            "total": _cart_total(uid),
            "status": "Draft",
            "payment": {"method": "", "amount": 0, "tx": "", "state": "Pending"},
            "created_at": datetime.utcnow().isoformat()
        }
    }
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, f"🧾 Պատվեր {order_id}\nԳրեք ձեր **Անուն Ազգանուն**:")


# ===== PRODUCT SHOW =====
def show_product(call: types.CallbackQuery, code: str):
    p = PRODUCTS[code]
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Ավելացնել զամբյուղ", callback_data=f"cart:add:{code}"))
    kb.add(types.InlineKeyboardButton("🛒 Դիտել զամբյուղ", callback_data="cart:show"))
    kb.add(
        types.InlineKeyboardButton("⬅ Վերադառնալ բաժին", callback_data="back:category"),
        types.InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="back:main")
    )
    caption = (
        f"{p['title']}\n\n"
        f"Հին գին — {p['old_price']}֏ ({p['discount']}%)\n"
        f"Նոր գին — {p['price']}֏\n"
        f"Վաճառված՝ {p['sold']} հատ\n"
        f"Կոդ՝ {code}"
    )
    bot.send_photo(call.message.chat.id, open(p["img"], "rb"), caption=caption, reply_markup=kb)

### END PART 3/8
### PART 4/8 START

# ===== CART HANDLER =====
@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("cart:"))
def cart_callbacks(c: types.CallbackQuery):
    uid = c.from_user.id
    parts = c.data.split(":")
    action = parts[1]
    code = parts[2] if len(parts) > 2 else None

    if action == "add" and code:
        CART[uid][code] = CART[uid].get(code, 0) + 1
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

    # show cart
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
        if CART[uid]:
            kb.row(
                types.InlineKeyboardButton("❌ Մաքրել", callback_data="cart:clear"),
                types.InlineKeyboardButton("✅ Պատվիրել", callback_data="checkout:start"),
            )
        kb.row(types.InlineKeyboardButton("⬅ Վերադառնալ գլխավոր մենյու", callback_data="back:main"))
        bot.send_message(c.message.chat.id, _cart_text(uid), reply_markup=kb, parse_mode="Markdown")
        bot.answer_callback_query(c.id)
    else:
        bot.answer_callback_query(c.id)


def _cart_text(uid: int) -> str:
    if not CART[uid]:
        return "🛒 Զամբյուղը դատարկ է։"
    lines = ["Ձեր զամբյուղը:"]
    total = 0
    for code, qty in CART[uid].items():
        p = PRODUCTS[code]
        lines.append(f"• {p['title']} × {qty} — {p['price']}֏")
        total += p['price'] * qty
    lines.append(f"\nԸնդամենը՝ {total}֏")
    return "\n".join(lines)

### END PART 4/8
### PART 5/8 START

# ===== CHECKOUT START =====
@bot.callback_query_handler(func=lambda c: c.data == "checkout:start")
def checkout_start(c: types.CallbackQuery):
    uid = c.from_user.id
    if not CART[uid]:
        bot.answer_callback_query(c.id, "Զամբյուղը դատարկ է")
        return

    ok, code, st = _check_stock(uid)
    if not ok:
        bot.answer_callback_query(c.id, "Պահեստում բավարար քանակ չկա")
        bot.send_message(c.message.chat.id, f"⚠️ {PRODUCTS[code]['title']} — հասանելի՝ {st} հատ")
        return

    order_id = _order_id()
    CHECKOUT_STATE[uid] = {
        "step": "name",
        "order": {
            "order_id": order_id,
            "user_id": uid,
            "username": c.from_user.username,
            "fullname": "",
            "phone": "",
            "country": "",
            "city": "",
            "address": "",
            "comment": "",
            "items": [{"code": code, "qty": qty} for code, qty in CART[uid].items()],
            "total": _cart_total(uid),
            "status": "Draft",
            "payment": {"method": "", "amount": 0, "tx": "", "state": "Pending"},
            "created_at": datetime.utcnow().isoformat()
        }
    }
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, f"🧾 Պատվեր {order_id}\nԳրեք ձեր **Անուն Ազգանուն**:")

### END PART 5/8
### PART 6/8 START

@bot.message_handler(content_types=['text', 'contact'], func=lambda m: m.from_user.id in CHECKOUT_STATE)
def checkout_flow(m: types.Message):
    uid = m.from_user.id
    st = CHECKOUT_STATE.get(uid)
    if not st:
        return
    step  = st["step"]
    order = st["order"]

    # universal back
    if m.text == BTN_BACK_MAIN:
        CHECKOUT_STATE.pop(uid, None)
        show_main_menu(m.chat.id, "Վերադարձաք գլխավոր մենյու։")
        return

    # STEP: name
    if step == "name":
        txt = (m.text or "").strip()
        if not NAME_RE.match(txt):
            bot.send_message(m.chat.id, "❗ Անուն/Ազգանուն՝ միայն տառերով (3–60 նշան). Կրկին փորձեք։")
            return
        order["fullname"] = txt
        st["step"] = "phone"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(types.KeyboardButton("📱 Ուղարկել կոնտակտ", request_contact=True))
        kb.add(BTN_BACK_MAIN)
        bot.send_message(m.chat.id, "📞 Գրեք հեռախոսահամարը (+374xxxxxxxx կամ 0xxxxxxxx) կամ սեղմեք «📱 Ուղարկել կոնտակտ».", reply_markup=kb)
        return

    # STEP: phone
    if step == "phone":
        phone = None
        if m.contact and m.contact.phone_number:
            phone = m.contact.phone_number.replace(" ", "")
            if not phone.startswith("+"):
                phone = "+" + phone
        else:
            phone = (m.text or "").replace(" ", "")
        if not PHONE_RE.match(phone):
            bot.send_message(m.chat.id, "❗ Սխալ հեռախոսահամար. օրինակ՝ +374441112233 կամ 0441112233։ Կրկին գրեք։")
            return
        order["phone"] = phone
        st["step"] = "country"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for c in COUNTRIES:
            kb.add(c)
        kb.add(BTN_BACK_MAIN)
        bot.send_message(m.chat.id, "🌍 Ընտրեք երկիրը՝", reply_markup=kb)
        return

    # STEP: country
    if step == "country":
        if m.text not in COUNTRIES:
            bot.send_message(m.chat.id, "Խնդրում ենք ընտրել առաջարկվող կոճակներից։")
            return
        order["country"] = m.text
        st["step"] = "city"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for i in range(0, len(CITIES), 2):
            row = [types.KeyboardButton(x) for x in CITIES[i:i+2]]
            kb.row(*row)
        kb.add(BTN_BACK_MAIN)
        bot.send_message(m.chat.id, "🏙️ Ընտրեք քաղաքը՝", reply_markup=kb)
        return

    # STEP: city
    if step == "city":
        if m.text not in CITIES:
            bot.send_message(m.chat.id, "Խնդրում ենք ընտրել առաջարկվող քաղաքներից։")
            return
        order["city"] = m.text
        st["step"] = "address"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(BTN_BACK_MAIN)
        bot.send_message(m.chat.id, "🏡 Գրեք հասցեն (փողոց, տուն, մուտք, բնակարան)․", reply_markup=kb)
        return

    # STEP: address
    if step == "address":
        txt = (m.text or "").strip()
        if len(txt) < 5:
            bot.send_message(m.chat.id, "❗ Գրեք ավելի մանր հասցե (առնվազն 5 նշան)։")
            return
        order["address"] = txt
        st["step"] = "comment"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add("—")
        kb.add(BTN_BACK_MAIN)
        bot.send_message(m.chat.id, "📝 Լրացուցիչ մեկնաբանություն (կամ գրեք «—», եթե չկա)։", reply_markup=kb)
        return

    # STEP: comment (final)
    if step == "comment":
        order["comment"] = "" if (m.text or "").strip() in {"", "—", "-"} else (m.text or "").strip()
        order["status"] = "Pending"
        order["created_at"] = datetime.utcnow().isoformat()

        # պահպանում ենք պատվերը (demo)
        ORDERS.append(order)

        # մաքրում ենք state-ը և զամբյուղը
        CART[uid].clear()
        CHECKOUT_STATE.pop(uid, None)

        bot.send_message(
            m.chat.id,
            f"✅ Պատվերը գրանցվեց։ Մեր օպերատորը շուտով կկապվի։\nՊատվերի ID: {order['order_id']}",
            reply_markup=types.ReplyKeyboardRemove()
        )
        # ⬇️ Ավտոմատ բացում ենք ԳԼԽԱՎՈՐ ՄԵՆՅՈւ
        show_main_menu(m.chat.id)
        return

### END PART 6/8
### PART 7/8 START

# ===== MAIN MENU HANDLERS =====
@bot.message_handler(func=lambda m: m.text == "🛍 Խանութ")
def shop_menu(m: types.Message):
    kb = types.InlineKeyboardMarkup()
    for cat in CATEGORIES:
        kb.add(types.InlineKeyboardButton(cat["title"], callback_data=f"cat:{cat['id']}"))
    bot.send_message(m.chat.id, "🏬 Ընտրեք բաժինը 👇", reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "💱 Փոխարկումներ")
def exchanges(m: types.Message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🌐 PI ➝ USDT", callback_data="ex:pi"))
    kb.add(types.InlineKeyboardButton("💳 FTN ➝ AMD", callback_data="ex:ftn"))
    kb.add(types.InlineKeyboardButton("💠 AliPay լիցքավորում", callback_data="ex:alipay"))
    kb.add(types.InlineKeyboardButton("⬅ Վերադառնալ գլխավոր մենյու", callback_data="back:main"))
    bot.send_message(m.chat.id, "Ընտրեք փոխարկման տեսակը 👇", reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "💡 Խոհուն մտքեր")
def good_thoughts(m: types.Message):
    kb = types.InlineKeyboardMarkup()
    for idx, q in enumerate(THOUGHTS, start=1):
        kb.add(types.InlineKeyboardButton(f"{idx}. {q[:20]}...", callback_data=f"thought:{idx}"))
    kb.add(types.InlineKeyboardButton("⬅ Վերադառնալ գլխավոր մենյու", callback_data="back:main"))
    bot.send_message(m.chat.id, "✨ Խոհուն մտքեր բաժին", reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "📈 Օրվա կուրսեր")
def daily_rates(m: types.Message):
    try:
        usd = get_rate("USD")
        rub = get_rate("RUB")
        txt = f"📊 Օրվա կուրսեր\n\n💵 USD = {usd}֏\n💴 RUB = {rub}֏"
    except:
        txt = "Չհաջողվեց ստանալ օրվա կուրսերը։"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅ Վերադառնալ գլխավոր մենյու", callback_data="back:main"))
    bot.send_message(m.chat.id, txt, reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "📢 Բիզնես գործընկերներ")
def partners(m: types.Message):
    txt = "📢 Մեր բիզնես գործընկերները:\n\n1. Company A\n2. Company B\n3. Company C"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅ Վերադառնալ գլխավոր մենյու", callback_data="back:main"))
    bot.send_message(m.chat.id, txt, reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "👥 Հրավիրել ընկերների")
def invite_friends(m: types.Message):
    user_id = m.from_user.id
    invite_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⬅ Վերադառնալ գլխավոր մենյու", callback_data="back:main"))
    bot.send_message(m.chat.id, f"👥 Հրավիրեք ընկերներին այս հղումով:\n{invite_link}", reply_markup=kb)


# ===== BACK TO MAIN MENU CALLBACK =====
@bot.callback_query_handler(func=lambda c: c.data == "back:main")
def back_main_cb(c: types.CallbackQuery):
    bot.answer_callback_query(c.id)
    show_main_menu(c.message.chat.id)

### END PART 7/8
### PART 8/8 START

# ===== SAMPLE PRODUCTS =====
PRODUCTS = {
    "BA100810": {
        "title": "🌸 Գորգ – Ծաղկային դիզայն",
        "old_price": 2560,
        "price": 1690,
        "discount": -34,
        "sold": 320,
        "stock": 50,
        "img": "media/products/BA100810.jpg"
    },
    "BA100811": {
        "title": "🌸 Գորգ – Թիթեռներով դիզայն",
        "old_price": 2560,
        "price": 1690,
        "discount": -34,
        "sold": 250,
        "stock": 30,
        "img": "media/products/BA100811.jpg"
    }
    # ... այստեղ կարող ես ավելացնել մնացած ապրանքները
}

# ===== SAMPLE CATEGORIES =====
CATEGORIES = [
    {"id": 1, "title": "Կենցաղային պարագաներ"},
    {"id": 2, "title": "Խոհանոցային տեխնիկա"},
    {"id": 3, "title": "Աքսեսուարներ"},
]

# ===== GOOD THOUGHTS =====
THOUGHTS = [
    "Ամեն օր մի նոր հնարավորություն է։",
    "Արևը միշտ նորից ծագում է։",
    "Համբերությունը հաջողության բանալին է։",
    "Քաջությունը միշտ վարձատրվում է։",
    "Ուժեղ մարդիկ չեն հանձնվում։",
    "Կյանքը նվեր է՝ վայելիր այն։",
    "Մեծ հաջողությունները գալիս են փոքր քայլերից։",
    "Ժպիտը հոգու դեղամիջոցն է։",
    "Սեր տարածիր, ոչ թե ատելություն։",
    "Երջանկությունը ներսից է սկսվում։"
]

# ===== RATES FUNCTION =====
def get_rate(symbol: str):
    if symbol == "USD":
        return 390
    if symbol == "RUB":
        return 4.2
    return 0

# ===== BOT START / HELP =====
@bot.message_handler(commands=['start', 'help'])
def send_welcome(m: types.Message):
    kb = main_menu_kb()
    bot.send_message(
        m.chat.id,
        "🐰 Բարի գալուստ BabyAngels 🛍️\n\n"
        "Դուք արդեն մեր սիրելի հաճախորդն եք ❤️\n\n"
        "Ընտրեք բաժինը 👇",
        reply_markup=kb
    )


# ===== POLLING START =====
print("🤖 Bot is running 24/7 ...")
bot.infinity_polling(timeout=60, long_polling_timeout=60)

### END PART 8/8
