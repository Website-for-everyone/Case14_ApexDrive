"""
Apex Drive — Aiogram 3.x Telegram Bot Companion
Handles supercar fleet cards, date availability checker, and driver license photo KYC upload.
"""

import asyncio
import os
import sys
from datetime import datetime, date, timedelta
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8217851677:AAHN34TMuC1P4e6SppuazFN8BIiLHa_RyIc")
OWNER_ID = int(os.environ.get("TELEGRAM_OWNER_ID", "1387913438"))
OWNER_USERNAME = os.environ.get("TELEGRAM_OWNER_USERNAME", "@Idrisov_prod")

router = Router()

class KycPhotoState(StatesGroup):
    waiting_for_license_front = State()
    waiting_for_driver_info = State()

class AvailabilityCheckState(StatesGroup):
    waiting_for_car = State()
    waiting_for_dates = State()

def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏎 Автопарк суперкаров", callback_data="fleet_list")],
        [InlineKeyboardButton(text="📅 Проверить доступность дат", callback_data="check_dates")],
        [InlineKeyboardButton(text="📄 Пройти KYC (Загрузить права)", callback_data="start_kyc")],
        [InlineKeyboardButton(text="💬 Персональный менеджер", url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}")]
    ])

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        "🏁 <b>Apex Drive — Аренда премиальных суперкаров</b>\n\n"
        "Добро пожаловать в закрытый гараж Apex Drive. В нашем парке собраны лучшие трековые болиды и суперкары:\n"
        "• Porsche 911 GT3 RS (992)\n"
        "• Ferrari F8 Tributo (720 HP)\n"
        "• Lamborghini Huracán EVO V10\n"
        "• McLaren 720S Spider\n"
        "• Audi R8 V10 Performance\n\n"
        "📍 Выдача авто: Москва-Сити или доставка к вашему отелю.\n"
        "Выберите действие в меню:"
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_menu())

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🏁 <b>Главное меню Apex Drive:</b>", parse_mode="HTML", reply_markup=get_main_menu())
    await call.answer()

# --- Fleet Cards ---
@router.callback_query(F.data == "fleet_list")
async def cb_fleet_list(call: CallbackQuery):
    cars = database.get_all_cars()
    kb = []
    for c in cars:
        btn_text = f"{c['name']} — {c['daily_rate_rub']:,} ₽/сут".replace(",", " ")
        kb.append([InlineKeyboardButton(text=btn_text, callback_data=f"car_info_{c['slug']}")])
    kb.append([InlineKeyboardButton(text="⬅️ В главное меню", callback_data="main_menu")])
    
    await call.message.edit_text(
        "🏎 <b>Наш суперкар-парк:</b>\nВыберите автомобиль для просмотра телеметрии и бронирования:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await call.answer()

@router.callback_query(F.data.startswith("car_info_"))
async def cb_car_detail(call: CallbackQuery):
    slug = call.data.replace("car_info_", "")
    car = database.get_car_by_slug(slug)
    if not car:
        await call.answer("Автомобиль не найден", show_alert=True)
        return
        
    text = (
        f"🏎 <b>{car['name']}</b>\n\n"
        f"🔧 <b>Двигатель:</b> {car['engine']}\n"
        f"⚡ <b>Мощность:</b> {car['horsepower']} л.с. | Крутящий момент: {car['torque_nm']} Нм\n"
        f"⏱ <b>Разгон 0–100 км/ч:</b> {car['accel_0_100']} сек\n"
        f"🏁 <b>Макс. скорость:</b> {car['top_speed_kmh']} км/ч\n\n"
        f"📝 <i>{car['description']}</i>\n\n"
        f"💰 <b>Тариф:</b> {car['daily_rate_rub']:,} ₽ в сутки\n"
        f"🛡 <b>Страховой залог:</b> {car['deposit_rub']:,} ₽ (возвратный)\n"
    ).replace(",", " ")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Забронировать этот суперкар", callback_data=f"rent_car_{car['id']}")],
        [InlineKeyboardButton(text="📅 Проверить свободные даты", callback_data=f"avail_car_{car['id']}")],
        [InlineKeyboardButton(text="⬅️ К списку авто", callback_data="fleet_list")]
    ])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

# --- Quick Rent Request ---
@router.callback_query(F.data.startswith("rent_car_"))
async def cb_rent_car_direct(call: CallbackQuery):
    car_id = int(call.data.replace("rent_car_", ""))
    car = database.get_car_by_id(car_id)
    user = call.from_user
    username = f"@{user.username}" if user.username else f"ID {user.id}"

    today_str = date.today().strftime("%Y-%m-%d")
    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    booking_data = {
        "car_id": car["id"],
        "client_name": user.full_name,
        "phone": username,
        "driver_age": 28,
        "start_date": today_str,
        "end_date": tomorrow_str,
        "rental_days": 1,
        "mileage_package": "200km",
        "insurance_tier": "standard",
        "daily_rate_rub": car["daily_rate_rub"],
        "total_rent_rub": car["daily_rate_rub"],
        "deposit_rub": car["deposit_rub"],
        "kyc_status": "pending_driver_license"
    }
    booking = database.create_rental_booking(booking_data)

    text = (
        f"🏁 <b>Заявка на бронирование #{booking['booking_code']} принята!</b>\n\n"
        f"Суперкар: <b>{car['name']}</b>\n"
        f"Тариф: <b>{car['daily_rate_rub']:,} ₽/сутки</b>\n"
        f"Залог: <b>{car['deposit_rub']:,} ₽</b>\n\n"
        f"Для завершения оформления и подтверждения брони необходимо загрузить фото водительского удостоверения (KYC)."
    ).replace(",", " ")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Загрузить права прямо сейчас", callback_data="start_kyc")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
    ])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

# --- Availability Check Flow ---
@router.callback_query(F.data == "check_dates" | F.data.startswith("avail_car_"))
async def cb_avail_start(call: CallbackQuery, state: FSMContext):
    if call.data.startswith("avail_car_"):
        car_id = int(call.data.replace("avail_car_", ""))
        await state.update_data(car_id=car_id)
    else:
        cars = database.get_all_cars()
        kb = [[InlineKeyboardButton(text=c["name"], callback_data=f"avail_car_{c['id']}")] for c in cars]
        kb.append([InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")])
        await call.message.edit_text("Выберите интересующий автомобиль:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await call.answer()
        return

    await state.set_state(AvailabilityCheckState.waiting_for_dates)
    await call.message.edit_text(
        "📅 <b>Проверка доступности суперкара</b>\n\n"
        "Отправьте даты аренды в формате: <i>2026-11-20 2026-11-22</i> (начало и конец через пробел):",
        parse_mode="HTML"
    )
    await call.answer()

@router.message(AvailabilityCheckState.waiting_for_dates)
async def process_avail_dates(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("⚠️ Неверный формат. Отправьте две даты через пробел (например: <code>2026-11-20 2026-11-22</code>):", parse_mode="HTML")
        return
        
    s_date, e_date = parts[0], parts[1]
    data = await state.get_data()
    car_id = data.get("car_id", 1)
    car = database.get_car_by_id(car_id)
    
    is_free = database.check_dates_availability(car_id, s_date, e_date)
    await state.clear()
    
    if is_free:
        status_msg = f"🟢 <b>{car['name']} СВОБОДЕН</b> на даты {s_date} — {e_date}!"
        kb = [
            [InlineKeyboardButton(text="⚡ Забронировать сейчас", callback_data=f"rent_car_{car['id']}")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
        ]
    else:
        status_msg = f"🔴 <b>{car['name']} ЗАНЯТ</b> на выбранные даты. Попробуйте другие даты или другой суперкар."
        kb = [
            [InlineKeyboardButton(text="🔄 Выбрать другой автомобиль", callback_data="fleet_list")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
        ]
        
    await message.answer(status_msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# --- KYC Driver License Photo Intake ---
@router.callback_query(F.data == "start_kyc")
async def cb_kyc_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(KycPhotoState.waiting_for_license_front)
    await call.message.edit_text(
        "📄 <b>KYC-верификация водителя Apex Drive</b>\n\n"
        "Требования к арендатору:\n"
        "• Возраст от 21 года\n"
        "• Водительский стаж категории 'B' от 2 лет\n\n"
        "Пожалуйста, отправьте четкое фото вашего водительского удостоверения (формат JPG / PNG):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="main_menu")]
        ])
    )
    await call.answer()

@router.message(KycPhotoState.waiting_for_license_front, F.photo)
async def process_kyc_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await state.update_data(license_photo_id=photo.file_id)
    await state.set_state(KycPhotoState.waiting_for_driver_info)
    await message.answer(
        "✅ Фотография водительского удостоверения принята!\n\n"
        "Укажите ваш возраст и стаж вождения (например: <i>27 лет, стаж 6 лет</i>):",
        parse_mode="HTML"
    )

@router.message(KycPhotoState.waiting_for_license_front, ~F.photo)
async def process_kyc_invalid(message: Message):
    await message.answer("⚠️ Фотография не распознана как водительское удостоверение. Пожалуйста, отправьте четкое фото обеих сторон в формате JPG или PNG.")

@router.message(KycPhotoState.waiting_for_driver_info)
async def process_kyc_complete(message: Message, state: FSMContext):
    info = message.text.strip()
    data = await state.get_data()
    user = message.from_user
    username = f"@{user.username}" if user.username else f"ID {user.id}"
    
    await state.clear()
    
    await message.answer(
        "🎉 <b>Документы успешно переданы в службу безопасности Apex Drive!</b>\n\n"
        f"Водитель: {user.full_name} ({username})\n"
        f"Данные: {info}\n"
        f"Статус проверки: <b>Одобрено предварительно</b>\n\n"
        f"Менеджер клуба ({OWNER_USERNAME}) свяжется с вами для подписания договора и выдачи ключей.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
        ])
    )

def create_bot_and_dispatcher():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    return bot, dp

async def main():
    bot, dp = create_bot_and_dispatcher()
    print("Starting Apex Drive Telegram Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
