from aiogram import Router, F, types, Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.config import config
from database.database import AsyncSessionLocal
from database.models import Invoice
from bot.keyboards.inline import admin_main_kb

router = Router()

# فیلتر سفارشی برای بررسی ادمین بودن
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@router.message(F.text == "⚙️ پنل مدیریت (Admin)")
async def show_admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("👨‍💻 <b>پنل مدیریت ربات</b>\n\nیک گزینه را انتخاب کنید:", reply_markup=admin_main_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("approve_receipt_"))
async def approve_receipt(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return

    invoice_id = int(callback.data.split("_")[2])

    async with AsyncSessionLocal() as session:
        stmt = select(Invoice).options(selectinload(Invoice.user)).where(Invoice.id == invoice_id)
        invoice = (await session.execute(stmt)).scalar_one_or_none()

        if not invoice or invoice.status != "pending":
            await callback.answer("❌ این فیش قبلاً بررسی شده است.", show_alert=True)
            return

        invoice.user.wallet_balance += invoice.amount
        invoice.status = "approved"
        await session.commit()

        # جلوگیری از کرش در صورت نداشتن کپشن و حذف دکمه‌ها پس از تایید
        current_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=current_caption + "\n\n✅ <b>تایید و شارژ شد.</b>", 
            reply_markup=None, 
            parse_mode="HTML"
        )

        try:
            await bot.send_message(
                chat_id=invoice.user.telegram_id,
                text=f"🎉 <b>پرداخت تایید شد!</b>\nمبلغ <code>{invoice.amount:,.0f}</code> تومان به کیف پول شما اضافه گردید.",
                parse_mode="HTML"
            )
        except Exception:
            pass

@router.callback_query(F.data.startswith("reject_receipt_"))
async def reject_receipt(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return

    invoice_id = int(callback.data.split("_")[2])

    async with AsyncSessionLocal() as session:
        stmt = select(Invoice).options(selectinload(Invoice.user)).where(Invoice.id == invoice_id)
        invoice = (await session.execute(stmt)).scalar_one_or_none()

        if invoice and invoice.status == "pending":
            invoice.status = "rejected"
            await session.commit()

            current_caption = callback.message.caption or ""
            await callback.message.edit_caption(
                caption=current_caption + "\n\n❌ <b>رد شد.</b>", 
                reply_markup=None, 
                parse_mode="HTML"
            )

            try:
                await bot.send_message(
                    chat_id=invoice.user.telegram_id,
                    text="❌ <b>فیش شما توسط مدیریت رد شد.</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass