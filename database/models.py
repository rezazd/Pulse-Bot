from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, String, Integer, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.sql import func
from datetime import datetime
from typing import List

# کلاس پایه برای تمام مدل‌ها
class Base(DeclarativeBase):
    pass

# جدول کاربران ربات
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    
    # سیستم مالی و کیف پول
    wallet_balance: Mapped[float] = mapped_column(Float, default=0.0)
    
    # سیستم زیرمجموعه‌گیری
    referral_code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    invited_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True) # آیدی کسی که دعوتش کرده
    
    # وضعیت کاربر
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    has_received_test: Mapped[bool] = mapped_column(Boolean, default=False) # آیا اکانت تست گرفته؟
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # ارتباطات (با lazy="selectin" برای جلوگیری از خطای Async)
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    services: Mapped[List["Service"]] = relationship(back_populates="user", cascade="all, delete-orphan", lazy="selectin")

# جدول فاکتورها و پرداخت‌ها (کارت به کارت)
class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    photo_file_id: Mapped[str | None] = mapped_column(String(255)) # آیدی عکس فیش در تلگرام
    status: Mapped[str] = mapped_column(String(50), default="pending") # pending, approved, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="invoices", lazy="selectin")

# جدول تنظیمات ربات (برای تغییر متن‌ها توسط ادمین بدون دستکاری کد)
class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

# جدول پلن‌های فروشگاه (برای مدیریت داینامیک توسط ادمین)
class Plan(Base):
    __tablename__ = "plans"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100)) # مثلا: "یک ماهه ۵۰ گیگ"
    price: Mapped[float] = mapped_column(Float) # قیمت به تومان
    data_limit_gb: Mapped[float] = mapped_column(Float) # حجم به گیگابایت (0 = نامحدود)
    duration_days: Mapped[int] = mapped_column(Integer) # زمان به روز (0 = نامحدود)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True) # فعال/غیرفعال برای فروش

# جدول سرویس‌های خریداری شده
class Service(Base):
    __tablename__ = "services"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    marzban_username: Mapped[str] = mapped_column(String(255), unique=True, index=True) # یوزرنیم در مرزبان
    
    plan_name: Mapped[str] = mapped_column(String(100)) # نام پلن در زمان خرید
    data_limit: Mapped[int] = mapped_column(BigInteger) # تغییر به BigInteger چون بایت عدد بزرگی است
    expire_date: Mapped[int | None] = mapped_column(BigInteger, nullable=True) # Timestamp انقضا
    
    # فلگ‌های هوشمندسازی
    notified_80_percent: Mapped[bool] = mapped_column(Boolean, default=False)
    notified_expiry: Mapped[bool] = mapped_column(Boolean, default=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="services", lazy="selectin")