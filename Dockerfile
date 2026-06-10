# استفاده از نسخه سبک پایتون 3.11
FROM python:3.11-slim

# تنظیم متغیرهای محیطی برای جلوگیری از کش شدن پایتون و لاگ‌گیری بهتر
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tehran

# تنظیم پوشه کاری داخل کانتینر
WORKDIR /app

# نصب پیش‌نیازهای سیستمی و تنظیم تایم‌زون
RUN apt-get update && apt-get install -y \
    gcc \
    libmariadb-dev \
    pkg-config \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# کپی کردن فایل پیش‌نیازها و نصب آن‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کردن کل کدهای پروژه به داخل کانتینر
COPY . .

# اجرای فایل اصلی ربات
CMD ["python", "main.py"]