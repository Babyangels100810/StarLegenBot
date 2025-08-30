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
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, InputMediaVideo, FSInputFile
)
import json, os

# --- ուղիներ / կոնֆիգ ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PRODUCTS_JSON = os.path.join(DATA_DIR, "products.json")
ITEMS_PER_PAGE = 6  # քանի ապրանք տեսնեմ մեկ էջում

# ---------- ՕԳՆԱԿԱՆՆԵՐ ----------
def _load_json_file(fp: str) -> dict:
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)

def get_categories() -> list[dict]:
    data = _load_json_file(PRODUCTS_JSON)
    return data.get("categories", [])

def get_products_by_cat(cat_id: int) -> list[dict]:
    data = _load_json_file(PRODUCTS_JSON)
    prods = data.get("products", [])
    return [p for p in prods if int(p.get("category_id", 0)) == int(cat_id)]

def get_product_by_code(code: str) -> dict | None:
    data = _load_json_file(PRODUCTS_JSON)
    for p in data.get("products", []):
        if str(p.get("code")) == str(code):
            return p
    return None

def product_caption(p: dict, lang: str) -> str:
    title = p.get("title", "")
    price = p.get("price")
    old = p.get("price_old")
    code = p.get("code")
    desc = p.get("description_md") or ""
    line_price = f"<s>{old}֏</s> {price}֏" if old else f"{price}֏"
    return (
        f"<b>{title}</b>\n"
        f"{line_price}\n"
        f"<b>ID</b> {code}\n\n"
        f"{desc}"
    )

def _resolve_file(path: str) -> FSInputFile:
    # path-ը products.json-ում հարաբերական է նախագծին
    real = os.path.join(BASE_DIR, path) if not os.path.isabs(path) else path
    return FSInputFile(real)

# ---------- ՔԼԱՎԻԱՏՈՒՐԱՆԵՐ ----------
def categories_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"🗂 {c['title']}", callback_data=f"shop:cat:{c['id']}:p:1")]
        for c in get_categories()
    ]
    rows.append([InlineKeyboardButton(text=t("btn.close", lang), callback_data="shop:close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def products_page_kb(lang: str, cat_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text=t("btn.prev", lang), callback_data=f"shop:cat:{cat_id}:p:{page-1}"))
    nav.append(InlineKeyboardButton(text=t("btn.close", lang), callback_data="shop:close"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text=t("btn.next", lang), callback_data=f"shop:cat:{cat_id}:p:{page+1}"))
    return InlineKeyboardMarkup(inline_keyboard=[nav])

def product_kb(p: dict, lang: str, cat_id: int, page: int, idx: int) -> InlineKeyboardMarkup:
    gallery = (p.get("images") or []) + (p.get("promo_images") or [])
    has_prev = idx > 0
    has_next = idx + 1 < len(gallery)

    row_nav = []
    if has_prev:
        row_nav.append(InlineKeyboardButton(text=t("btn.prev", lang),
                                            callback_data=f"shop:view:{p['code']}:{cat_id}:{page}:i:{idx-1}"))
    if has_next:
        row_nav.append(InlineKeyboardButton(text=t("btn.next", lang),
                                            callback_data=f"shop:view:{p['code']}:{cat_id}:{page}:i:{idx+1}"))

    rows = []
    if row_nav:
        rows.append(row_nav)

    # եթե վիդեո կա՝ հավելյալ կոճակ
    if p.get("video"):
        rows.append([InlineKeyboardButton(text=t("btn.video", lang),
                                          callback_data=f"shop:vid:{p['code']}:{cat_id}:{page}")])

    rows.append([InlineKeyboardButton(text=t("btn.back", lang),
                                      callback_data=f"shop:back:{cat_id}:{page}")])
    rows.append([InlineKeyboardButton(text=t("btn.close", lang), callback_data="shop:close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ---------- ԲԱՑԵԼ ԽԱՆՈՒԹ ----------
OPEN_SHOP_TEXTS = {
    "🛍 Խանութ", "Խանութ",
    "🛍 Магазин", "Магазин",
    "🛍 Shop", "Shop",
}

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

# ---------- ՑՈՒՑԱԴՐԵԼ ԿԱՏԵԳՈՐԻԱ ----------
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
        slice_ = prods[start:start + ITEMS_PER_PAGE]

        # ցուցակի տեքստը
        lines = [
            f"📦 <b>{t('catalog.products', lang)}</b> • "
            + t('catalog.page', lang).replace('{p}', str(page)).replace('{t}', str(total_pages)),
            ""
        ]
        for p in slice_:
            lines.append(f"• <b>{p.get('title')}</b> — {p.get('price')}֏  <code>{p.get('code')}</code>")

        # սրան տակ՝ յուրաքանչյուրի համար «Դիտել» կոճակ
        btn_rows = [[InlineKeyboardButton(text=f"👁 {t('btn.view', lang)}: {p['code']}",
                                          callback_data=f"shop:view:{p['code']}:{cat_id}:{page}:i:0")]
                    for p in slice_]
        btn_rows.append([InlineKeyboardButton(text=t("btn.close", lang), callback_data="shop:close")])
        kb = InlineKeyboardMarkup(inline_keyboard=btn_rows)

        try:
            await call.message.edit_text("\n".join(lines), reply_markup=kb)
        except Exception:
            # եթե նախորդը մեդիա էր և edit_text չի ստացվում՝ ուղարկենք նորը
            await call.message.answer("\n".join(lines), reply_markup=kb)
        await call.answer()
    except Exception as e:
        await call.answer("⚠️ Error")
        await call.message.answer(f"⚠️ Shop error: {e}")

# ---------- ԴԻՏԵԼ ԱՊՐԱՆՔ (սլայդ) ----------
@dp.callback_query(F.data.startswith("shop:view:"))
async def view_product(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    try:
        # shop:view:{code}:{cat_id}:{page}:i:{idx}
        parts = call.data.split(":")
        code = parts[2]
        cat_id = int(parts[3])
        page = int(parts[4])
        idx = int(parts[6]) if len(parts) >= 7 else 0

        p = get_product_by_code(code)
        if not p:
            await call.answer("Not found"); return

        gallery = (p.get("images") or []) + (p.get("promo_images") or [])
        if not gallery:
            await call.answer("No images"); return

        idx = max(0, min(idx, len(gallery) - 1))
        path = gallery[idx]
        caption = product_caption(p, lang)
        kb = product_kb(p, lang, cat_id, page, idx)

        # ՓՈՐՁՈՒՄՆԵՐ՝ նախ փորձենք edit_media, եթե չստացվեց՝ ուղարկենք նոր
        try:
            media = InputMediaPhoto(media=_resolve_file(path), caption=caption, parse_mode="HTML")
            await call.message.edit_media(media=media, reply_markup=kb)
        except Exception:
            await call.message.answer_photo(_resolve_file(path), caption=caption, reply_markup=kb, parse_mode="HTML")

        await call.answer()
    except Exception as e:
        await call.answer("⚠️ Error")
        await call.message.answer(f"⚠️ Shop error: {e}")

# ---------- ՎԻԴԵՈ ----------
@dp.callback_query(F.data.startswith("shop:vid:"))
async def view_video(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    try:
        # shop:vid:{code}:{cat_id}:{page}
        parts = call.data.split(":")
        code = parts[2]
        cat_id = int(parts[3])
        page = int(parts[4])

        p = get_product_by_code(code)
        if not p or not p.get("video"):
            await call.answer("No video"); return

        caption = product_caption(p, lang)
        kb = product_kb(p, lang, cat_id, page, 0)
        try:
            media = InputMediaVideo(media=_resolve_file(p["video"]), caption=caption, parse_mode="HTML")
            await call.message.edit_media(media=media, reply_markup=kb)
        except Exception:
            await call.message.answer_video(_resolve_file(p["video"]), caption=caption, reply_markup=kb, parse_mode="HTML")

        await call.answer()
    except Exception as e:
        await call.answer("⚠️ Error")
        await call.message.answer(f"⚠️ Shop error: {e}")

# ---------- ՎԵՐԱԴԱՌՆԱԼ ԿԱՏԵԳՈՐԻԱՅԻ ԼԻՍՏ ----------
@dp.callback_query(F.data.startswith("shop:back:"))
async def back_to_list(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    try:
        # shop:back:{cat_id}:{page}
        parts = call.data.split(":")
        cat_id = int(parts[2])
        page = int(parts[3])
        # պարզապես կանչում ենք նույն handler-ը
        call.data = f"shop:cat:{cat_id}:p:{page}"
        await show_category(call)
    except Exception as e:
        await call.answer("⚠️ Error")
        await call.message.answer(f"⚠️ Shop error: {e}")

# ---------- ՓԱԿԵԼ ----------
@dp.callback_query(F.data == "shop:close")
async def shop_close(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    try:
        await call.message.delete()
    except Exception:
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
