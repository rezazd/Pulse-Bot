from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List
from database.models import Plan, Service

# ==========================================
# کیبوردهای بخش کاربری
# ==========================================

def profile_inline_kb() -> InlineKeyboardMarkup:
    """دکمه‌های زیر پیام پروفایل"""
    keyboard = [
        [InlineKeyboardButton(text="📦 سرویس‌های من", callback_data="my_services")],
        [InlineKeyboardButton(text="💳 شارژ کیف پول", callback_data="charge_wallet")],
        [InlineKeyboardButton(text="🔗 لینک دعوت (زیرمجموعه‌گیری)", callback_data="referral_link")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def dynamic_shop_kb(plans: List[Plan]) -> InlineKeyboardMarkup:
    """دکمه‌های لیست پلن‌های فروشگاه (داینامیک از دیتابیس با استفاده از Builder)"""
    builder = InlineKeyboardBuilder()
    
    for plan in plans:
        btn_text = f"🛒 {plan.name} - {int(plan.price):,} تومان"
        # هر پلن در یک ردیف مجزا قرار می‌گیرد
        builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"buy_plan_{plan.id}"))
    
    # دکمه انصراف در ردیف آخر
    builder.row(InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_action"))
    return builder.as_markup()

def confirm_buy_kb(plan_id: int) -> InlineKeyboardMarkup:
    """دکمه تایید نهایی خرید پس از انتخاب پلن"""
    keyboard = [
        [InlineKeyboardButton(text="✅ تایید و کسر از کیف پول", callback_data=f"confirm_buy_{plan_id}")],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_action")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def my_services_list_kb(services: List[Service]) -> InlineKeyboardMarkup:
    """نمایش لیست سرویس‌های خریداری شده کاربر (با استفاده از Builder)"""
    builder = InlineKeyboardBuilder()
    
    for svc in services:
        status_emoji = "🟢" if svc.is_active else "🔴"
        btn_text = f"{status_emoji} {svc.plan_name} ({svc.marzban_username})"
        builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"manage_svc_{svc.id}"))
        
    builder.row(InlineKeyboardButton(text="🔙 بازگشت به پروفایل", callback_data="back_to_profile"))
    return builder.as_markup()

def manage_service_kb(service_id: int) -> InlineKeyboardMarkup:
    """دکمه‌های مدیریت یک سرویس خاص"""
    keyboard = [
        [InlineKeyboardButton(text="🔗 دریافت لینک اتصال", callback_data=f"get_sub_{service_id}")],
        [InlineKeyboardButton(text="🔄 تمدید این سرویس", callback_data=f"renew_svc_{service_id}")],
        [InlineKeyboardButton(text="♻️ تغییر لینک (رفع فیلتر)", callback_data=f"revoke_svc_{service_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت به لیست", callback_data="my_services")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def cancel_kb() -> InlineKeyboardMarkup:
    """یک دکمه ساده برای انصراف از عملیات (مثل FSM)"""
    keyboard = [[InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_action")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ==========================================
# کیبوردهای بخش مدیریت (Admin)
# ==========================================

def admin_main_kb() -> InlineKeyboardMarkup:
    """منوی اصلی پنل مدیریت"""
    keyboard = [
        [InlineKeyboardButton(text="📊 آمار سرور و ربات", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 مدیریت کاربران", callback_data="admin_users")],
        [InlineKeyboardButton(text="📝 مدیریت پلن‌ها (فروشگاه)", callback_data="admin_plans")],
        [InlineKeyboardButton(text="📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="❌ بستن پنل", callback_data="cancel_action")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_receipt_kb(invoice_id: int) -> InlineKeyboardMarkup:
    """دکمه‌های زیر فیش واریزی برای ادمین (تایید یا رد)"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ تایید فیش", callback_data=f"approve_receipt_{invoice_id}"),
            InlineKeyboardButton(text="❌ رد فیش", callback_data=f"reject_receipt_{invoice_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)