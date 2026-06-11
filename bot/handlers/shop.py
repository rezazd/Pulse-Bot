import time
from aiogram import Router, F, types
from sqlalchemy import select
from database.database import AsyncSessionLocal
from database.models import User, Plan, Service
from bot.keyboards.inline import dynamic_shop_kb, confirm_buy_kb
from marzban.api import marzban_api

router = Router()

@router.message(F.text == "🛒 خرید اشتراک")
async def show_shop(message: types.Message):
    async with AsyncSessionLocal() as session:
        stmt = select(Plan).where(Plan.is_active == True)
        plans = (await session.execute(stmt)).scalars().all()
        
        if not plans:
            await message.answer("🛒 در حال حاضر هیچ پلنی برای فروش وجود ندارد.")
            return

    text = "🛒 <b>فروشگاه سرویس‌های V2Ray</b>\n\nلطفاً یکی از پلن‌های زیر را انتخاب کنید:"
    await message.answer(text, reply_markup=dynamic_shop_kb(list(plans)), parse_mode="HTML")

@router.callback_query(F.data.startswith("buy_plan_"))
async def process_buy_plan(callback: types.CallbackQuery):
    plan_id = int(callback.data.split("_")[2])
    
    async with AsyncSessionLocal() as session:
        plan = (await session.execute(select(Plan).where(Plan.id == plan_id))).scalar_one_or_none()
        if not plan:
            await callback.answer("❌ پلن نامعتبر است!", show_alert=True)
            return
            
    text = (
        f"🧾 <b>تایید پیش‌فاکتور</b>\n\n"
        f"📦 <b>پلن:</b> {plan.name}\n"
        f"💰 <b>قیمت:</b> <code>{int(plan.price):,}</code> تومان\n\n"
        f"آیا از خرید این سرویس اطمینان دارید؟"
    )
    await callback.message.edit_text(text, reply_markup=confirm_buy_kb(plan.id), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_buy_"))
async def confirm_buy(callback: types.CallbackQuery):
    plan_id = int(callback.data.split("_")[2])
    telegram_id = callback.from_user.id

    await callback.message.edit_text("⏳ در حال ساخت کانفیگ و ارتباط با سرور...")

    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
        plan = (await session.execute(select(Plan).where(Plan.id == plan_id))).scalar_one_or_none()

        if not user or not plan:
            await callback.message.edit_text("❌ <b>خطا در یافتن اطلاعات کاربر یا پلن.</b>", parse_mode="HTML")
            await callback.answer()
            return

        if user.wallet_balance < plan.price:
            await callback.message.edit_text("❌ <b>موجودی کافی نیست!</b> لطفاً کیف پول خود را شارژ کنید.", parse_mode="HTML")
            await callback.answer()
            return

        # کسر از کیف پول
        user.wallet_balance -= plan.price
        
        username = f"User_{user.id}_{int(time.time())}"
        data_limit_bytes = int(plan.data_limit_gb * 1073741824) if plan.data_limit_gb > 0 else 0
        expire_timestamp = int(time.time()) + (plan.duration_days * 86400) if plan.duration_days > 0 else 0

        try:
            # ساخت در مرزبان
            mz_res = await marzban_api.add_user(
                username=username,
                data_limit=data_limit_bytes,
                expire=expire_timestamp
            )

            if mz_res["status"] == 200:
                new_service = Service(
                    user_id=user.id,
                    marzban_username=username,
                    plan_name=plan.name,
                    data_limit=data_limit_bytes,
                    expire_date=expire_timestamp
                )
                session.add(new_service)
                await session.commit()
                
                sub_link = mz_res["data"].get("subscription_url", "لینک یافت نشد")
                success_text = (
                    f"✅ <b>خرید با موفقیت انجام شد!</b>\n\n"
                    f"📦 <b>پلن:</b> {plan.name}\n"
                    f"🔗 <b>لینک اتصال:</b>\n<code>{sub_link}</code>\n\n"
                    f"💡 <i>این لینک در بخش (پروفایل > سرویس‌های من) نیز در دسترس است.</i>"
                )
                await callback.message.edit_text(success_text, parse_mode="HTML")
            else:
                await session.rollback()
                await callback.message.edit_text("❌ <b>خطا در سرور مرزبان!</b> موجودی شما کسر نشد.", parse_mode="HTML")
        except Exception as e:
            await session.rollback()
            await callback.message.edit_text("❌ <b>خطای سیستمی رخ داد!</b> موجودی شما کسر نشد.", parse_mode="HTML")
            
    await callback.answer() # پایان موفقیت آمیز کلیک
