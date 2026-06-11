from aiogram.fsm.state import State, StatesGroup

class WalletState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_receipt = State()
