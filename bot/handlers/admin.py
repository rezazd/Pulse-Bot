from aiogram import Router, F, types, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from core.config import config
from database.database import AsyncSessionLocal
from database.models import Invoice, User, Plan
from bot.keyboards.inline import admin_main_kb
from marzban.api import marzban_api

router = Router()

# تعریف وضعیت برای ارسال پیام همگانی
class AdminState(StatesGroup):
    waiting_for_broadcast = State()

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@router.message(F.text.contains("پنل مدیریت"), StateFilter("*"))
async def show_admin_panel(message: types.Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    await message.answer("👨‍💻 <b>پنل مدیریت ربات</b>\n\nیک گزینه را انتخاب کنید:", reply_markup=admin_main_kb(), parse_mode="HTML")

# ==========================================
# هندلرهای تایید و رد فیش بانکی
# ==========================================
@router.callback_query(F.data.startswith("approve_receipt_"), StateFilter("*"))
async def approve_receipt(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return

    invoice_id = int(callback.data.split("_")[2])
    async with AsyncSessionLocal() as session:
        stmt = select(Invoice).options(selectinload(Invoice.user)).where(Invoice.id == invoice_id)
        invoice = (await session.execute(stmt)).scalar_one_or_none()

        if not invoice or invoice.status != "pending":
            return await callback.answer("❌ این فیش قبلاً بررسی شده است.", show_alert=True)

        invoice.user.wallet_balance += invoice.amount
        invoice.status = "approved"
        await session.commit()

        current_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=current_caption + "\n\n✅ <b>تایید و شارژ شد.</b>", reply_markup=None, parse_mode="HTML"
        )

        try:
            await bot.send_message(
                chat_id=invoice.user.telegram_id,
                text=f"🎉 <b>پرداخت تایید شد!</b>\nمبلغ <code>{invoice.amount:,.0f}</code> تومان به کیف پول شما اضافه گردید.",
                parse_mode="HTML"
            )
        except Exception:
            pass
    await callback.answer("فیش تایید شد.", show_alert=False)

@router.callback_query(F.data.startswith("reject_receipt_"), StateFilter("*"))
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
                caption=current_caption + "\n\n❌ <b>رد شد.</b>", reply_markup=None, parse_mode="HTML"
            )

            try:
                await bot.send_message(
                    chat_id=invoice.user.telegram_id,
                    text="❌ <b>فیش شما توسط مدیریت رد شد.</b>", parse_mode="HTML"
                )
            except Exception:
                pass
    await callback.answer("فیش رد شد.", show_alert=False)

# ==========================================
# هندلرهای منوی اصلی ادمین
# ==========================================

@router.callback_query(F.data == "admin_stats", StateFilter("*"))
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    await callback.message.edit_text("⏳ در حال دریافت اطلاعات از سرور مرزبان...")
    
    # فراخوانی متدی که در api.py نوشته بودید
    stats = await marzban_api.get_system_stats()
    
    if stats["status"] == 200:
        data = stats["data"]
        cpu = data.get("cpu_usage", 0)
        mem_total = data.get("total_memory", 0) / (1024**3)
        mem_used = data.get("used_memory", 0) / (1024**3)
        version = data.get("version", "نامشخص")
        
        text = (
            f"📊 <b>آمار زنده سرور مرزبان</b>\n\n"
            f"🖥 <b>مصرف پردازنده:</b> <code>{cpu}%</code>\n"
            f"💽 <b>مصرف رم:</b> <code>{mem_used:.2f} GB</code> از <code>{mem_total:.2f} GB</code>\n"
            f"🌐 <b>نسخه مرزبان:</b> <code>{version}</code>\n"
        )
        await callback.message.edit_text(text, reply_markup=admin_main_kb(), parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ خطا در ارتباط با سرور مرزبان.", reply_markup=admin_main_kb())
    
    await callback.answer()

@router.callback_query(F.data == "admin_users", StateFilter("*"))
async def admin_users(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    async with AsyncSessionLocal() as session:
        # شمارش کل کاربران ربات از دیتابیس
        total_users = await session.scalar(select(func.count(User.id)))
        
    text = (
        f"👥 <b>آمار کاربران ربات</b>\n\n"
        f"تعداد کل کاربران ثبت‌نام شده: <code>{total_users}</code> نفر\n\n"
        f"<i>💡 برای مدیریت دقیق‌تر کانفیگ‌ها (حذف/ویرایش)، لطفاً از پنل وب مرزبان استفاده کنید.</i>"
    )
    await callback.message.edit_text(text, reply_markup=admin_main_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_plans", StateFilter("*"))
async def admin_plans(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    async with AsyncSessionLocal() as session:
        plans = (await session.execute(select(Plan))).scalars().all()
        
    if not plans:
        text = "📝 هیچ پلنی در دیتابیس تعریف نشده است."
    else:
        text = "📝 <b>لیست پلن‌های فروشگاه:</b>\n\n"
        for p in plans:
            status = "✅ فعال" if p.is_active else "❌ غیرفعال"
            text += f"▪️ <b>{p.name}</b> | <code>{p.price:,.0f}</code> تومان | {status}\n"
            
        text += "\n<i>💡 برای اضافه کردن پلن جدید، فعلاً باید از طریق دیتابیس (MariaDB) اقدام کنید.</i>"
        
    await callback.message.edit_text(text, reply_markup=admin_main_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast", StateFilter("*"))
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    
    await callback.message.answer(
        "📢 <b>ارسال پیام همگانی</b>\n\n"
        "لطفاً پیام خود را بفرستید (می‌تواند شامل عکس، ویدیو یا متن باشد).\n"
        "<i>برای لغو عملیات، کلمه <code>لغو</code> را ارسال کنید.</i>",
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_for_broadcast)
    await callback.answer()

@router.message(AdminState.waiting_for_broadcast, StateFilter("*"))
async def admin_broadcast_send(message: types.Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id): return
    
    if message.text == "لغو":
        await message.answer("❌ ارسال پیام همگانی لغو شد.")
        await state.clear()
        return
        
    await message.answer("⏳ در حال ارسال پیام به تمامی کاربران... لطفاً صبور باشید.")
    
    async with AsyncSessionLocal() as session:
        users = (await session.execute(select(User.telegram_id))).scalars().all()
        
    success_count = 0
    for telegram_id in users:
        try:
            # استفاده از copy_message تا اگر عکس یا ویدیو بود هم به درستی فوروارد شود
            await bot.copy_message(
                chat_id=telegram_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success_count += 1
        except Exception:
            # اگر کاربری ربات را بلاک کرده باشد، ارور می‌دهد که از آن رد می‌شویم
            pass
            
    await message.answer(f"✅ پیام شما با موفقیت به <b>{success_count}</b> کاربر ارسال شد.", parse_mode="HTML")
    await state.clear()
