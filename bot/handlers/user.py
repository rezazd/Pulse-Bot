import uuid
from aiogram import Router, F, types, Bot
from aiogram.filters import CommandStart, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from core.config import config
from database.database import AsyncSessionLocal
from database.models import User, Service
from bot.keyboards.reply import get_main_menu
from bot.keyboards.inline import profile_inline_kb, my_services_list_kb, manage_service_kb
from marzban.api import marzban_api

router = Router()

@router.message(CommandStart(), StateFilter("*"))
async def cmd_start(message: types.Message, command: CommandObject, state: FSMContext):
    await state.clear() # خروج از هرگونه وضعیت گیر کرده
    telegram_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name or "کاربر"
    is_admin = (telegram_id in config.ADMIN_IDS)

    invited_by_id = None
    if command.args and command.args.startswith("ref_"):
        invited_by_id = command.args.split("_")[1]

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        user = (await session.execute(stmt)).scalar_one_or_none()

        if not user:
            ref_code = str(uuid.uuid4())[:8]
            inviter_db_id = None
            if invited_by_id and invited_by_id.isdigit():
                stmt_inv = select(User).where(User.telegram_id == int(invited_by_id))
                inviter = (await session.execute(stmt_inv)).scalar_one_or_none()
                if inviter:
                    inviter_db_id = inviter.id

            new_user = User(
                telegram_id=telegram_id, username=username, full_name=full_name,
                is_admin=is_admin, referral_code=ref_code, invited_by=inviter_db_id
            )
            session.add(new_user)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()

    welcome_text = (
        f"سلام {full_name} عزیز! 🌹\n"
        f"به ربات هوشمند مدیریت و فروش اشتراک V2Ray خوش آمدید.\n\n"
        f"🔹 شناسه کاربری شما: <code>{telegram_id}</code>\n\n"
        f"لطفاً از منوی زیر یک گزینه را انتخاب کنید:"
    )
    await message.answer(text=welcome_text, reply_markup=get_main_menu(is_admin=is_admin), parse_mode="HTML")

@router.message(F.text.contains("پروفایل"), StateFilter("*"))
@router.callback_query(F.data == "back_to_profile", StateFilter("*"))
async def show_profile(message_or_call, state: FSMContext):
    await state.clear()
    telegram_id = message_or_call.from_user.id
    full_name = message_or_call.from_user.full_name or "کاربر"
    
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if not user:
            text = "❌ اطلاعات شما یافت نشد. لطفاً /start را بزنید."
            if isinstance(message_or_call, types.CallbackQuery):
                await message_or_call.answer(text, show_alert=True)
            else:
                await message_or_call.answer(text)
            return

    text = (
        f"👤 <b>پروفایل کاربری شما</b>\n\n"
        f"🔹 <b>نام:</b> {full_name}\n"
        f"🆔 <b>شناسه کاربری:</b> <code>{telegram_id}</code>\n"
        f"💰 <b>موجودی کیف پول:</b> <code>{user.wallet_balance:,.0f}</code> تومان\n\n"
        f"👇 برای مدیریت حساب خود از دکمه‌های زیر استفاده کنید:"
    )
    
    if isinstance(message_or_call, types.CallbackQuery):
        await message_or_call.message.edit_text(text, reply_markup=profile_inline_kb(), parse_mode="HTML")
        await message_or_call.answer()
    else:
        await message_or_call.answer(text, reply_markup=profile_inline_kb(), parse_mode="HTML")

@router.callback_query(F.data == "referral_link", StateFilter("*"))
async def show_referral_link(callback: types.CallbackQuery, bot: Bot):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    text = f"🔗 <b>لینک دعوت اختصاصی شما:</b>\n\n<code>{ref_link}</code>\n\n🎁 با دعوت از دوستان خود، درصدی از خریدهای آن‌ها به کیف پول شما اضافه خواهد شد!"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "my_services", StateFilter("*"))
async def show_my_services(callback: types.CallbackQuery):
    async with AsyncSessionLocal() as session:
        stmt = select(User).options(selectinload(User.services)).where(User.telegram_id == callback.from_user.id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if not user or not user.services:
            await callback.answer("📦 شما هنوز سرویس فعالی ندارید.", show_alert=True)
            return
        await callback.message.edit_text(
            "📦 <b>لیست سرویس‌های شما:</b>\nبرای مدیریت، روی سرویس مورد نظر کلیک کنید:",
            reply_markup=my_services_list_kb(list(user.services)), parse_mode="HTML"
        )
        await callback.answer()

@router.callback_query(F.data.startswith("manage_svc_"), StateFilter("*"))
async def manage_service(callback: types.CallbackQuery):
    svc_id = int(callback.data.split("_")[2])
    async with AsyncSessionLocal() as session:
        svc = (await session.execute(select(Service).where(Service.id == svc_id))).scalar_one_or_none()
        if not svc:
            return await callback.answer("❌ سرویس یافت نشد!", show_alert=True)

    mz_res = await marzban_api.get_user(svc.marzban_username)
    if mz_res["status"] != 200:
        return await callback.answer("❌ خطا در ارتباط با سرور مرزبان.", show_alert=True)
        
    mz_data = mz_res["data"]
    used_gb = mz_data.get("used_traffic", 0) / 1073741824
    total_gb = mz_data.get("data_limit", 0) / 1073741824
    status = "🟢 فعال" if mz_data.get("status") == "active" else "🔴 غیرفعال/منقضی"

    text = (
        f"⚙️ <b>مدیریت سرویس</b>\n\n🔖 <b>نام پلن:</b> {svc.plan_name}\n"
        f"👤 <b>یوزرنیم:</b> <code>{svc.marzban_username}</code>\n📊 <b>وضعیت:</b> {status}\n"
        f"مصرف: <code>{used_gb:.2f} GB</code> از <code>{total_gb:.2f} GB</code>\n"
    )
    await callback.message.edit_text(text, reply_markup=manage_service_kb(svc.id), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("get_sub_"), StateFilter("*"))
async def get_subscription(callback: types.CallbackQuery):
    svc_id = int(callback.data.split("_")[2])
    async with AsyncSessionLocal() as session:
        svc = (await session.execute(select(Service).where(Service.id == svc_id))).scalar_one_or_none()
        
    mz_res = await marzban_api.get_user(svc.marzban_username)
    if mz_res["status"] != 200:
        return await callback.answer("❌ خطا در دریافت اطلاعات از مرزبان.", show_alert=True)

    sub_link = mz_res["data"].get("subscription_url", "لینک یافت نشد")
    await callback.message.answer(f"🔗 <b>لینک اتصال شما:</b>\n\n<code>{sub_link}</code>", parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("revoke_svc_"), StateFilter("*"))
async def revoke_service(callback: types.CallbackQuery):
    svc_id = int(callback.data.split("_")[2])
    async with AsyncSessionLocal() as session:
        svc = (await session.execute(select(Service).where(Service.id == svc_id))).scalar_one_or_none()
    
    if not svc:
        return await callback.answer("❌ سرویس یافت نشد!", show_alert=True)

    await callback.message.edit_text("⏳ در حال تغییر لینک اتصال...")
    mz_res = await marzban_api.revoke_sub(svc.marzban_username)
    if mz_res["status"] == 200:
        await callback.message.answer("✅ لینک اتصال شما با موفقیت تغییر کرد. لطفاً مجدداً لینک اتصال را دریافت کنید.")
    else:
        await callback.message.answer("❌ خطا در تغییر لینک در سرور مرزبان.")
    await callback.answer()

@router.callback_query(F.data.startswith("renew_svc_"), StateFilter("*"))
async def renew_service(callback: types.CallbackQuery):
    await callback.answer("🔄 قابلیت تمدید سرویس به زودی در آپدیت بعدی اضافه خواهد شد!", show_alert=True)

# ==========================================
# هندلرهای کیبورد پایین صفحه (با فیلترهای ضدگلوله)
# ==========================================

@router.message(F.text.contains("سرویس"), StateFilter("*"))
async def show_my_services_reply_kb(message: types.Message, state: FSMContext):
    await state.clear()
    async with AsyncSessionLocal() as session:
        stmt = select(User).options(selectinload(User.services)).where(User.telegram_id == message.from_user.id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if not user or not user.services:
            return await message.answer("📦 شما هنوز سرویس فعالی ندارید.")
            
        await message.answer(
            "📦 <b>لیست سرویس‌های شما:</b>\nبرای مدیریت، روی سرویس مورد نظر کلیک کنید:",
            reply_markup=my_services_list_kb(list(user.services)), parse_mode="HTML"
        )

@router.message(F.text.contains("تست رایگان"), StateFilter("*"))
async def free_test_placeholder(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🎁 <b>اکانت تست رایگان</b>\n\nاین قابلیت در آپدیت‌های بعدی ربات (نسخه 2.0) فعال خواهد شد! 🚀", parse_mode="HTML")

@router.message(F.text.contains("پشتیبانی"), StateFilter("*"))
async def support_placeholder(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🎧 <b>پشتیبانی</b>\n\nبرای ارتباط با مدیریت و رفع مشکلات، به آیدی زیر پیام دهید:\n💬 @YourAdminID", parse_mode="HTML")

@router.message(F.text.contains("آموزش اتصال"), StateFilter("*"))
async def tutorial_placeholder(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("📚 <b>آموزش اتصال</b>\n\nلینک آموزش‌های اتصال به زودی در این بخش قرار می‌گیرد.", parse_mode="HTML")
