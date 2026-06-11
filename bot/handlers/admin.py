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
                # ==========================================
# رفع باگ دکمه‌های کیبورد پایین صفحه
# ==========================================

@router.message(F.text == "📦 سرویس‌های من")
async def show_my_services_reply_kb(message: types.Message):
    """هندلر دکمه 'سرویس‌های من' از کیبورد اصلی"""
    telegram_id = message.from_user.id
    
    async with AsyncSessionLocal() as session:
        stmt = select(User).options(selectinload(User.services)).where(User.telegram_id == telegram_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        
        if not user or not user.services:
            await message.answer("📦 شما هنوز سرویس فعالی ندارید.")
            return
            
        await message.answer(
            "📦 <b>لیست سرویس‌های شما:</b>\nبرای مدیریت، روی سرویس مورد نظر کلیک کنید:",
            reply_markup=my_services_list_kb(list(user.services)),
            parse_mode="HTML"
        )

@router.message(F.text == "🎁 دریافت تست رایگان")
async def free_test_placeholder(message: types.Message):
    await message.answer("🎁 <b>اکانت تست رایگان</b>\n\nاین قابلیت در آپدیت‌های بعدی ربات (نسخه 2.0) فعال خواهد شد! 🚀", parse_mode="HTML")

@router.message(F.text == "🎧 پشتیبانی")
async def support_placeholder(message: types.Message):
    # می‌تونی آیدی خودت رو اینجا جایگزین کنی
    await message.answer("🎧 <b>پشتیبانی</b>\n\nبرای ارتباط با مدیریت و رفع مشکلات، به آیدی زیر پیام دهید:\n💬 @YourAdminID", parse_mode="HTML")

@router.message(F.text == "📚 آموزش اتصال")
async def tutorial_placeholder(message: types.Message):
    await message.answer("📚 <b>آموزش اتصال</b>\n\nلینک آموزش‌های اتصال به زودی در این بخش قرار می‌گیرد.", parse_mode="HTML")
