import os
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from core.config import config
from database.database import AsyncSessionLocal
from database.models import User, Invoice
from bot.keyboards.inline import cancel_kb, admin_receipt_kb
from bot.states import WalletState

router = Router()

@router.message(F.text == "💳 شارژ کیف پول")
@router.callback_query(F.data == "charge_wallet")
async def ask_for_amount(message_or_call, state: FSMContext):
    text = "💳 لطفاً مبلغ شارژ را <b>به تومان و عدد</b> وارد کنید:\n<i>(حداقل 10,000)</i>"
    if isinstance(message_or_call, types.CallbackQuery):
        await message_or_call.message.answer(text, reply_markup=cancel_kb(), parse_mode="HTML")
        await message_or_call.answer()
    else:
        await message_or_call.answer(text, reply_markup=cancel_kb(), parse_mode="HTML")
    await state.set_state(WalletState.waiting_for_amount)

@router.message(WalletState.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    # بررسی اینکه کاربر حتماً عدد وارد کرده باشد
    if not message.text.isdigit():
        await message.answer("❌ لطفاً فقط عدد وارد کنید (بدون حروف و کاما).")
        return

    amount = float(message.text)
    if amount < 10000:
        await message.answer("❌ مبلغ نامعتبر است. حداقل 10,000 تومان وارد کنید.")
        return

    await state.update_data(amount=amount)
    
    # خواندن شماره کارت از متغیرهای محیطی
    admin_card = os.getenv("ADMIN_CARD_NUMBER", "شماره کارت در تنظیمات ثبت نشده است")
    text = f"💳 مبلغ: <code>{amount:,.0f}</code> تومان\n\nلطفاً به کارت زیر واریز کرده و <b>عکس فیش</b> را بفرستید:\n💳 <code>{admin_card}</code>"
    await message.answer(text, reply_markup=cancel_kb(), parse_mode="HTML")
    await state.set_state(WalletState.waiting_for_receipt)

@router.message(WalletState.waiting_for_receipt, F.photo)
async def process_receipt(message: types.Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    amount = user_data.get("amount")
    telegram_id = message.from_user.id
    photo_id = message.photo[-1].file_id

    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
        
        new_invoice = Invoice(
            user_id=user.id,
            amount=amount,
            photo_file_id=photo_id,
            status="pending"
        )
        session.add(new_invoice)
        await session.commit()
        await session.refresh(new_invoice)
        invoice_id = new_invoice.id

    await message.answer("✅ فیش دریافت شد و در انتظار تایید مدیریت است.")
    await state.clear()

    # ارسال فیش برای تمام ادمین‌ها
    if config.ADMIN_IDS:
        admin_text = f"🧾 <b>فیش جدید</b>\n👤 کاربر: <code>{telegram_id}</code>\n💰 مبلغ: <code>{amount:,.0f}</code> تومان"
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_photo(
                    chat_id=admin_id, photo=photo_id, caption=admin_text,
                    reply_markup=admin_receipt_kb(invoice_id), parse_mode="HTML"
                )
            except Exception:
                pass # اگر ادمین ربات را بلاک کرده بود، ربات کرش نکند

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer("عملیات لغو شد.", show_alert=False)