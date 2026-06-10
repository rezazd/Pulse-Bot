from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List

class Settings(BaseSettings):
    # --- تنظیمات تلگرام ---
    BOT_TOKEN: str
    ADMIN_IDS: List[int]

    # --- تنظیمات دیتابیس (با مقادیر پیش‌فرض برای نصب آسان‌تر) ---
    DB_USER: str = "pulse_user"
    DB_PASS: str = "pulse_pass"
    DB_HOST: str = "mariadb"  # نام سرویس در داکر
    DB_PORT: int = 3306
    DB_NAME: str = "pulse_db"

    # --- تنظیمات مرزبان ---
    MARZBAN_URL: str
    MARZBAN_USERNAME: str
    MARZBAN_PASSWORD: str

    # تنظیمات خواندن از فایل .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # تبدیل خودکار رشته ادمین‌ها (مثلاً "123,456") به لیست اعداد [123, 456]
    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, value):
        if isinstance(value, str):
            return [int(admin_id.strip()) for admin_id in value.split(",") if admin_id.strip()]
        return value

    # ساخت خودکار URL دیتابیس
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# ساخت یک نمونه از تنظیمات برای استفاده در کل پروژه
config = Settings()