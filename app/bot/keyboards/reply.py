from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """تولید کیبورد اصلی ربات بر اساس سطح دسترسی کاربر"""
    
    keyboard = [
        [KeyboardButton(text="🛒 خرید اشتراک"), KeyboardButton(text="👤 پروفایل من")],
        [KeyboardButton(text="📦 سرویس‌های من"), KeyboardButton(text="💳 شارژ کیف پول")],
        [KeyboardButton(text="🎁 دریافت تست رایگان"), KeyboardButton(text="🎧 پشتیبانی")],
        [KeyboardButton(text="📚 آموزش اتصال")]
    ]
    
    # اگر کاربر ادمین بود، دکمه پنل مدیریت هم به او نمایش داده شود
    if is_admin:
        keyboard.append([KeyboardButton(text="⚙️ پنل مدیریت (Admin)")])
        
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,      # تغییر اندازه خودکار دکمه‌ها
        is_persistent=True,        # جلوگیری از ناپدید شدن کیبورد در دسکتاپ
        input_field_placeholder="یک گزینه را انتخاب کنید 👇"
    )