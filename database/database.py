import logging
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from core.config import config

# تنظیم لاگر برای دیتابیس
logger = logging.getLogger(__name__)

# ایجاد موتور دیتابیس با تنظیمات بهینه
engine = create_async_engine(
    config.DATABASE_URL, 
    echo=False, 
    pool_recycle=1800,   # زمان بازیافت کانکشن‌ها (نیم ساعت)
    pool_pre_ping=False, # 🔴 خاموش کردن پینگ برای حل باگ aiomysql
    pool_size=10,        # تعداد کانکشن‌های همزمان
    max_overflow=20      # حداکثر کانکشن‌های مازاد
)

# ایجاد Session ساز برای عملیات‌های دیتابیس
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autoflush=False
)

async def get_db():
    """
    یک Generator برای تولید Session دیتابیس.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """این تابع جداول را در دیتابیس می‌سازد. دارای سیستم Retry برای هماهنگی با داکر."""
    from database.models import Base
    
    max_retries = 5
    retry_delay = 3  # ثانیه
    
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables checked/created successfully.")
            return  # خروج از حلقه در صورت موفقیت
        except Exception as e:
            logger.warning(f"⚠️ Database connection attempt {attempt}/{max_retries} failed. Retrying in {retry_delay}s...")
            if attempt == max_retries:
                logger.error(f"❌ Failed to initialize database after {max_retries} attempts: {e}")
                raise e
            await asyncio.sleep(retry_delay)
