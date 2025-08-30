# main.py — Part 1: /start + меню + language switch + bunny photo
import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, FSInputFile
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dotenv import load_dotenv
from aiogram.client.default import DefaultBotProperties

# --- ENV ---
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DEFAULT_LANG = (os.getenv("DEFAULT_LANG") or "hy").lower()

# --- i18n ---
# tools/i18n.py պետք է ունենա t(key, lang)
from tools.i18n import t

# --- Bot/DP ---
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# --- user language storage (պարզ in-memory, Մաս 6-ում կարող ենք պահել ֆայլում) ---
user_lang: dict[int, str] = {}

def get_lang(user_id: int) -> str:
    return user_lang.get(user_id, DEFAULT_LANG)

def set_lang(user_id: int, lang: str):
    user_lang[user_id] = lang

# --- UI helpers ---
def main_menu(lang: str):
    kb = ReplyKeyboardBuilder()
    kb.button(text=t("menu.shop", lang))
    kb.button(text=t("menu.cart", lang))
    kb.button(text=t("menu.exchanges", lang))
    kb.button(text=t("menu.thoughts", lang))
    kb.button(text=t("menu.rates", lang))
    kb.button(text=t("menu.profile", lang))
    kb.button(text=t("menu.contact", lang))
    kb.button(text=t("menu.partners", lang))
    kb.button(text=t("menu.search", lang))
    kb.button(text=t("menu.invite", lang))
    kb.button(text=t("menu.lang", lang))
    # ⬇️ նոր՝ երկու կրիտիկ կոճակ
    kb.button(text=t("menu.main", lang))
    kb.button(text=t("menu.back", lang))
    # դասավորություն՝ վերջին շարքում 2 կոճակ (Main, Back)
    kb.adjust(2, 2, 2, 2, 2, 1, 2)
    return kb.as_markup(resize_keyboard=True)


def lang_picker_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇦🇲 Հայերեն", callback_data="lang:hy")
    kb.button(text="🇷🇺 Русский", callback_data="lang:ru")
    kb.button(text="🇬🇧 English", callback_data="lang:en")
    kb.adjust(1)
    return kb.as_markup()

# --- Handlers ---

@dp.message(F.text == "/start")
async def on_start(message: Message):
    uid = message.from_user.id
    lang = get_lang(uid)

    # 1) bunny photo
    photo_path = "media/bunny.jpg"
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        await message.answer_photo(photo)

    # 2) welcome text + main menu
    customer_no = 1008
    await message.answer(
        t("start.welcome", lang).replace("{no}", str(customer_no)),
        reply_markup=main_menu(lang)
    )

# Լեզվի կոճակ (ReplyKeyboard-ում)
@dp.message(F.text.in_(["🌐 Լեզու", "🌐 Язык", "🌐 Language"]))
async def ask_language(message: Message):
    await message.answer(
        "Ընտրեք լեզուն / Choose language / Выберите язык:",
        reply_markup=lang_picker_keyboard()
    )

# Լեզվի ընտրության callback
@dp.callback_query(F.data.startswith("lang:"))
async def set_language(cb: CallbackQuery):
    uid = cb.from_user.id
    lang = cb.data.split(":", 1)[1].lower()
    if lang not in ("hy", "ru", "en"):
        await cb.answer("Unknown language")
        return
    set_lang(uid, lang)
    msg = {"hy": "Լեզուն փոխվեց 🇦🇲",
           "ru": "Язык изменён 🇷🇺",
           "en": "Language changed 🇬🇧"}[lang]
    await cb.answer(msg)
    customer_no = 1008
    await cb.message.answer(
        t("start.welcome", lang).replace("{no}", str(customer_no)),
        reply_markup=main_menu(lang)
    )
@dp.message(F.text.in_(["🏠 Գլխավոր մենյու", "🏠 Главное меню", "🏠 Main menu"]))
async def go_main(message: Message):
    lang = get_lang(message.from_user.id)
    customer_no = 1008
    await message.answer(
        t("start.welcome", lang).replace("{no}", str(customer_no)),
        reply_markup=main_menu(lang)
    )

@dp.message(F.text.in_(["⬅️ Վերադառնալ", "⬅️ Назад", "⬅️ Back"]))
async def go_back(message: Message):
    # Քանի դեռ submenu history չունենք, Back = վերադառնալ գլխավոր
    await go_main(message)
# =========================
# =========================
# ՄԱՍ 2 — ԽԱՆՈՒԹ (CATALOG)
# =========================
from aiogram import F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
)
import os, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PRODUCTS_JSON = os.path.join(DATA_DIR, "products.json")
ITEMS_PER_PAGE = 20  # մի անգամում քանի քարտ ցույց տալ

# ---------- helpers ----------
def _load_json_file(fp: str) -> dict:
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)

def _abs_media_path(p: str) -> str:
    """ընդունում է ինչպես 'media/products/BA100810.jpg', այնպես էլ 'BA100810.jpg'"""
    p = p.lstrip("/\\")
    if p.startswith("media/"):
        return os.path.join(BASE_DIR, p)
    return os.path.join(BASE_DIR, "media", "products", p)

def get_categories() -> list[dict]:
    return _load_json_file(PRODUCTS_JSON).get("categories", [])

def get_products_by_cat(cat_id: int) -> list[dict]:
    data = _load_json_file(PRODUCTS_JSON)
    return [p for p in data.get("products", []) if int(p.get("category_id", 0)) == int(cat_id)]

def get_product_by_code(code: str) -> dict | None:
    data = _load_json_file(PRODUCTS_JSON)
    for p in data.get("products", []):
        if str(p.get("code")) == str(code):
            return p
    return None

# ---------- keyboards ----------
def categories_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"📂 {c['title']}", callback_data=f"shop:cat:{c['id']}")] for c in get_categories()]
    rows.append([InlineKeyboardButton(text=t("btn.close", lang), callback_data="shop:close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def product_card_kb(code: str, cat_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn.view", lang) if t("btn.view", lang) else "👁 Դիտել",
                              callback_data=f"shop:detail:{code}:{cat_id}")],
        [InlineKeyboardButton(text=t("menu.back", lang), callback_data=f"shop:back:{cat_id}")],
        [InlineKeyboardButton(text=t("btn.close", lang), callback_data="shop:close")]
    ])

# ---------- open shop ----------
@dp.message(Command("shop"))
@dp.message(F.text.in_(["🛍 Խանութ", "🛍 Магазин", "🛍 Shop", "Խանութ", "Магазин", "Shop"]))
async def open_shop(message: Message):
    lang = get_lang(message.from_user.id)
    cats = get_categories()
    if not cats:
        await message.answer(t("catalog.noprod", lang))
        return
    await message.answer(t("catalog.choose", lang), reply_markup=categories_kb(lang))

# ----- helper: show list of product CARDS for a category -----
async def _show_category_cards(target_message, cat_id: int, lang: str):
    prods = get_products_by_cat(cat_id)
    if not prods:
        await target_message.answer(t("catalog.noprod", lang))
        return

    # վերնագիր
    await target_message.answer(f"📦 <b>{t('catalog.products', lang) or 'Ապրանքներ'}</b>")

    # քարտերով ցուցադրում
    for p in prods[:ITEMS_PER_PAGE]:
        # առաջին նկարը
        first_img = None
        imgs = p.get("images", [])
        if imgs:
            img_path = _abs_media_path(imgs[0])
            if os.path.exists(img_path):
                first_img = FSInputFile(img_path)

        title = p.get("title", "Без названия")
        price = p.get("price", "")
        old = p.get("price_old") or p.get("old_price")
        code = p.get("code")

        caption = f"<b>{title}</b>\n"
        if old:
            caption += f"<s>{old}֏</s> "
        caption += f"{price}֏\nID {code}"

        if first_img:
            await target_message.answer_photo(
                first_img,
                caption=caption,
                reply_markup=product_card_kb(code, cat_id, lang)
            )
        else:
            await target_message.answer(
                caption, reply_markup=product_card_kb(code, cat_id, lang)
            )

# ---------- choose category ----------
@dp.callback_query(F.data.startswith("shop:cat:"))
async def show_category(cb: CallbackQuery):
    lang = get_lang(cb.from_user.id)
    cat_id = int(cb.data.split(":")[2])
    try:
        # չփորձենք edit անել ֆոտո/թեքստ՝ ուղարկում ենք նոր
        await cb.message.delete()
    except Exception:
        pass
    await _show_category_cards(cb.message, cat_id, lang)
    await cb.answer()

# ---------- view details (slideshow + video + description) ----------
@dp.callback_query(F.data.startswith("shop:detail:"))
async def view_product(cb: CallbackQuery):
    lang = get_lang(cb.from_user.id)
    _, _, code, cat_id = cb.data.split(":")
    cat_id = int(cat_id)
    product = get_product_by_code(code)
    if not product:
        await cb.answer("Չի գտնվել")
        return

    # ուղարկում ենք ԲՈԼՈՐ նկարները (images + promo_images)
    all_imgs = list(product.get("images", [])) + list(product.get("promo_images", []))
    sent_any = False
    for img in all_imgs:
        p = _abs_media_path(img)
        if os.path.exists(p):
            await cb.message.answer_photo(FSInputFile(p))
            sent_any = True

    # video, եթե կա
    v = product.get("video")
    if v:
        vp = _abs_media_path(v)
        if os.path.exists(vp):
            await cb.message.answer_video(FSInputFile(vp))

    # վերջնական տեքստ քարտ (անուն, գներ, ID, նկարագրություն)
    title = product.get("title", "")
    price = product.get("price", "")
    old = product.get("price_old") or product.get("old_price")
    desc = product.get("description_md") or product.get("description") or ""
    code = product.get("code")

    text = f"<b>{title}</b>\n"
    if old:
        text += f"<s>{old}֏</s> "
    text += f"{price}֏\nID {code}\n\n{desc}"

    await cb.message.answer(
        text,
        reply_markup=product_card_kb(code, cat_id, lang)
    )
    await cb.answer()

# ---------- back to category ----------
@dp.callback_query(F.data.startswith("shop:back:"))
async def shop_back(cb: CallbackQuery):
    lang = get_lang(cb.from_user.id)
    cat_id = int(cb.data.split(":")[2])
    try:
        await cb.message.delete()
    except Exception:
        pass
    await _show_category_cards(cb.message, cat_id, lang)
    await cb.answer()

# ---------- close and go home ----------
@dp.callback_query(F.data == "shop:close")
async def shop_close(cb: CallbackQuery):
    lang = get_lang(cb.from_user.id)
    try:
        await cb.message.delete()
    except Exception:
        pass
    await cb.message.answer(t("menu.main", lang), reply_markup=main_menu(lang))
    await cb.answer()

# --- entry ---
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN/TELEGRAM_BOT_TOKEN չգտնվեց .env-ում")
    print("Bot is up. Default lang:", DEFAULT_LANG)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
