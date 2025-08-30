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
# ՄԱՍ 2 — ԽԱՆՈՒԹ (կատալոգ)
# =========================
import json, os
from aiogram import F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile, InputMediaPhoto
)

# --- ուղիներ ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
PRODUCTS_JSON = os.path.join(DATA_DIR, "products.json")
ITEMS_PER_PAGE = 6

# --- ֆայլերի ընթերցում ---
def _load_json_file(fp: str) -> dict:
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)

def get_categories() -> list[dict]:
    return _load_json_file(PRODUCTS_JSON).get("categories", [])

def get_products_by_cat(cat_id: int) -> list[dict]:
    prods = _load_json_file(PRODUCTS_JSON).get("products", [])
    return [p for p in prods if int(p.get("category_id", 0)) == int(cat_id)]

def get_product_by_code(code: str) -> dict | None:
    for p in _load_json_file(PRODUCTS_JSON).get("products", []):
        if str(p.get("code")) == str(code):
            return p
    return None

def _abs_media_path(rel: str) -> str:
    # թույլ ենք տալիս media/... կամ բացարձակ ուղի
    if not rel:
        return ""
    if os.path.isabs(rel):
        return rel
    # rel-ը կարող է սկսել "media/..."-ով
    return os.path.join(BASE_DIR, rel.replace("\\", "/"))

# --- Քլավիատուրաներ ---
def categories_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"🗂 {c['title']}", callback_data=f"shop:cat:{c['id']}:p:1")]
            for c in get_categories()]
    rows.append([InlineKeyboardButton(text=t("btn.close", lang), callback_data="shop:close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def products_list_kb(lang: str, cat_id: int, prods: list[dict], page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for p in prods:
        code = p.get("code")
        rows.append([InlineKeyboardButton(text=f"{t('btn.view', lang)} {code}",
                                          callback_data=f"shop:detail:{code}:{cat_id}:{page}")])
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text=t("btn.prev", lang), callback_data=f"shop:cat:{cat_id}:p:{page-1}"))
    nav.append(InlineKeyboardButton(text=t("btn.close", lang), callback_data="shop:close"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text=t("btn.next", lang), callback_data=f"shop:cat:{cat_id}:p:{page+1}"))
    rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def product_card_kb(code: str, cat_id: int, page: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn.back", lang),  callback_data=f"shop:cat:{cat_id}:p:{page}")],
        [InlineKeyboardButton(text=t("btn.close", lang), callback_data="shop:close")],
    ])

# --- Թույլ ենք տալիս բացել խանութը և /shop-ով, և կոճակով ---
OPEN_SHOP_TEXTS = {"🛍 Խանութ","Խանութ","🛍 Магазин","Магазин","🛍 Shop","Shop"}

@dp.message(Command("shop"))
@dp.message(F.text.in_(OPEN_SHOP_TEXTS))
async def open_shop(message: Message):
    lang = get_lang(message.from_user.id)
    try:
        cats = get_categories()
        if not cats:
            await message.answer(t("catalog.noprod", lang))
            return
        await message.answer(t("catalog.choose", lang), reply_markup=categories_kb(lang))
    except Exception as e:
        await message.answer(f"⚠️ Shop error: {e}")

# --- Կատեգորիայի ապրանքների ցուցակ ---
@dp.callback_query(F.data.startswith("shop:cat:"))
async def show_category(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    try:
        # shop:cat:{id}:p:{page}
        parts = call.data.split(":")
        cat_id = int(parts[2])
        page = int(parts[4]) if len(parts) >= 5 else 1

        prods = get_products_by_cat(cat_id)
        if not prods:
            await call.message.edit_text(t("catalog.noprod", lang))
            await call.answer()
            return

        total_pages = max(1, (len(prods) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        page = max(1, min(page, total_pages))
        start = (page - 1) * ITEMS_PER_PAGE
        slice_ = prods[start:start+ITEMS_PER_PAGE]

        lines = [
            f"📦 <b>{t('catalog.products', lang)}</b> • " +
            t('catalog.page', lang).replace('{p}', str(page)).replace('{t}', str(total_pages)),
            ""
        ]
        # ցուցակում տեքստը կարճ է՝ անուն, գին, ID
        for p in slice_:
            lines.append(f"• <b>{p.get('title')}</b> — {p.get('price')}֏  <code>{p.get('code')}</code>")

        await call.message.edit_text("\n".join(lines),
                                     reply_markup=products_list_kb(lang, cat_id, slice_, page, total_pages))
        await call.answer()
    except Exception as e:
        await call.message.answer(f"⚠️ Shop error: {e}")
        try: await call.answer("Error")
        except: pass

# --- Ապրանքի «Դիտել» — album + video + քարտ ---
@dp.callback_query(F.data.startswith("shop:detail:"))
async def view_product(cb: CallbackQuery):
    lang = get_lang(cb.from_user.id)
    try:
        # shop:detail:{code}:{cat_id}:{page}
        _, _, code, cat_id, page = cb.data.split(":")
        cat_id = int(cat_id)
        page = int(page)

        p = get_product_by_code(code)
        if not p:
            await cb.answer("Չի գտնվել")
            return

        # հավաքում ենք նկարները
        imgs = list(p.get("images", [])) + list(p.get("promo_images", []))
        media = []
        for img in imgs:
            ap = _abs_media_path(img)
            if ap and os.path.exists(ap):
                media.append(InputMediaPhoto(media=FSInputFile(ap)))

        # album (եթե ≥2), այլապես մեկ նկարը
        if len(media) >= 2:
            await cb.message.answer_media_group(media[:10])
        elif len(media) == 1:
            await cb.message.answer_photo(media[0].media)

        # video (եթե կա)
        vid = (p.get("video") or "").strip() or None
        if vid:
            vp = _abs_media_path(vid)
            if vp and os.path.exists(vp):
                await cb.message.answer_video(FSInputFile(vp))

        # Քարտը՝ վերնագիր, գներ, ID, նկարագրություն
        title = p.get("title", "")
        price = p.get("price", "")
        old = p.get("price_old") or p.get("old_price")
        desc = p.get("description_md") or p.get("description") or ""
        text = f"<b>{title}</b>\n"
        if old:
            text += f"<s>{old}֏</s> "
        text += f"{price}֏\nID {code}\n\n{desc}"

        await cb.message.answer(text, reply_markup=product_card_kb(code, cat_id, page, lang))
        await cb.answer()
    except Exception as e:
        await cb.message.answer(f"⚠️ Detail error: {e}")
        try: await cb.answer("Error")
        except: pass

# --- Փակել ---
@dp.callback_query(F.data == "shop:close")
async def shop_close(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    try:
        await call.message.delete()
    except:
        pass
    await call.message.answer(t("menu.main", lang), reply_markup=main_menu(lang))
    await call.answer()


# --- entry ---
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN/TELEGRAM_BOT_TOKEN չգտնվեց .env-ում")
    print("Bot is up. Default lang:", DEFAULT_LANG)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
