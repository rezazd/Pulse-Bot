from aiogram.fsm.state import State, StatesGroup

class WalletState(StatesGroup):
    """وضعیت‌های مربوط به شارژ کیف پول"""
    waiting_for_amount = State()
    waiting_for_receipt = State()

class AdminState(StatesGroup):
    """وضعیت‌های مربوط به پنل مدیریت"""
    waiting_for_broadcast_message = State()
    waiting_for_plan_name = State()
    waiting_for_plan_price = State()
    # در صورت نیاز وضعیت‌های بیشتری اینجا اضافه می‌شود