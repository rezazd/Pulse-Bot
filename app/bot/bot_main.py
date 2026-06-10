from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from core.config import config
# ایمپورت کردن تمام هندلرهایی که ساختیم
from bot.handlers import user, shop, wallet, admin

def get_bot_and_dp():
    """این تابع نمونه ربات و دیسپچر را می‌سازد و به main.py تحویل می‌دهد"""
    if not config.BOT_TOKEN:
        return None, None

    # تغییر به HTML برای جلوگیری از کرش‌های مربوط به کاراکترهای خاص در تلگرام
    bot = Bot(
        token=config.BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode="HTML")
    )
    
    # ساخت دیسپچر همراه با حافظه RAM برای ماشین وضعیت (FSM)
    dp = Dispatcher(storage=MemoryStorage())

    # 🔗 وصل کردن تمام فایل‌ها (روترها) به ربات
    dp.include_router(user.router)
    dp.include_router(shop.router)
    dp.include_router(wallet.router)
    dp.include_router(admin.router)

    return bot, dp