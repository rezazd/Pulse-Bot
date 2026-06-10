import asyncio
import time
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.config import config
from database.database import init_db, AsyncSessionLocal
from database.models import Service
from bot.bot_main import get_bot_and_dp
from marzban.api import marzban_api

# تنظیمات لاگ‌گیری
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PulseBot")

# ==========================================
# سیستم هوشمند کرون‌جاب (Cronjobs)
# ==========================================
async def check_services_usage(bot):
    """این تابع هر چند ساعت یکبار اجرا می‌شود تا حجم و زمان کاربران را چک کند"""
    logger.info("🔄 Running Cronjob: Checking services usage and expiry...")
    
    async with AsyncSessionLocal() as session:
        stmt = select(Service).options(selectinload(Service.user)).where(Service.is_active == True)
        services = (await session.execute(stmt)).scalars().all()

        for svc in services:
            # وقفه کوتاه برای جلوگیری از فشار به API مرزبان
            await asyncio.sleep(0.1)
            
            mz_res = await marzban_api.get_user(svc.marzban_username)
            if mz_res["status"] != 200:
                continue
            
            data = mz_res["data"]
            used_traffic = data.get("used_traffic", 0)
            data_limit = data.get("data_limit", 0)
            expire_time = data.get("expire", 0)
            
            # ۱. بررسی اخطار ۸۰ درصد حجم
            if data_limit > 0 and not svc.notified_80_percent:
                if (used_traffic / data_limit) >= 0.8:
                    try:
                        await bot.send_message(
                            chat_id=svc.user.telegram_id,
                            text=f"⚠️ <b>اخطار مصرف حجم</b>\n\nکاربر گرامی، بیش از ۸۰٪ از حجم سرویس <code>{svc.plan_name}</code> شما مصرف شده است. لطفاً جهت جلوگیری از قطعی، نسبت به تمدید اقدام نمایید."
                        )
                        svc.notified_80_percent = True
                        await session.commit()
                    except Exception as e:
                        logger.error(f"Failed to send 80% warning to {svc.user.telegram_id}: {e}")

            # ۲. بررسی اخطار ۳ روز مانده به انقضا
            if expire_time > 0 and not svc.notified_expiry:
                current_time = int(time.time())
                days_left = (expire_time - current_time) / 86400
                if 0 < days_left <= 3:
                    try:
                        await bot.send_message(
                            chat_id=svc.user.telegram_id,
                            text=f"⏳ <b>اخطار اتمام زمان</b>\n\nکاربر گرامی، کمتر از ۳ روز به پایان اشتراک <code>{svc.plan_name}</code> شما باقی مانده است. لطفاً سرویس خود را تمدید کنید."
                        )
                        svc.notified_expiry = True
                        await session.commit()
                    except Exception as e:
                        logger.error(f"Failed to send expiry warning to {svc.user.telegram_id}: {e}")

# ==========================================
# اجرای همزمان (Concurrency & Graceful Shutdown)
# ==========================================
async def main():
    logger.info("🚀 Starting Pulse Bot System...")
    
    if not config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN is missing in .env file! Exiting...")
        return

    # ۱. ساخت جداول دیتابیس (جادوی نصب آسان)
    await init_db()

    # ۲. دریافت ربات و دیسپچر
    bot, dp = get_bot_and_dp()
    if not bot:
        return

    # تنظیم تایم‌زون ایران برای کرون‌جاب‌ها
    scheduler = AsyncIOScheduler(timezone="Asia/Tehran")

    try:
        # پاک کردن پیام‌های قدیمی که در زمان خاموشی ربات ارسال شده‌اند
        await bot.delete_webhook(drop_pending_updates=True)
        
        # تنظیم و روشن کردن کرون‌جاب (هر ۴ ساعت یکبار چک می‌کند)
        scheduler.add_job(check_services_usage, 'interval', hours=4, args=[bot])
        scheduler.start()
        logger.info("⏰ Cronjobs scheduler started.")

        # اجرای ربات
        logger.info("🤖 Telegram Bot is running and polling...")
        await dp.start_polling(bot)

    finally:
        # عملیات خاموش شدن ایمن (Graceful Shutdown)
        logger.info("🛑 Shutting down gracefully...")
        scheduler.shutdown()
        await bot.session.close()
        await marzban_api.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 System exited.")