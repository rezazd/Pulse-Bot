#!/bin/bash

# رنگ‌ها برای زیبایی خروجی ترمینال
GREEN="\e[32m"
BLUE="\e[34m"
YELLOW="\e[33m"
RED="\e[31m"
CYAN="\e[36m"
RESET="\e[0m"

echo -e "${BLUE}=================================================${RESET}"
echo -e "${GREEN}      🚀 Welcome to Pulse Bot Auto-Installer     ${RESET}"
echo -e "${BLUE}=================================================${RESET}"

# 1. بررسی دسترسی Root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ Please run this script as root (sudo -i)${RESET}"
  exit 1
fi

# 2. نصب پیش‌نیازهای اولیه (Git و Curl)
echo -e "${YELLOW}⏳ Checking prerequisites (git, curl)...${RESET}"
apt-get update -y &> /dev/null
apt-get install -y git curl &> /dev/null

# 3. نصب داکر در صورت عدم وجود
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⏳ Installing Docker & Docker Compose...${RESET}"
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# 4. دریافت اطلاعات از کاربر (با اعتبارسنجی خالی نبودن)
echo -e "\n${CYAN}📝 Please enter your bot details:${RESET}"

while [ -z "$BOT_TOKEN" ]; do
    read -p "Telegram Bot Token: " BOT_TOKEN
done

while [ -z "$ADMIN_IDS" ]; do
    read -p "Admin Telegram ID (e.g. 123456789): " ADMIN_IDS
done

read -p "Admin Bank Card Number (Optional, press Enter to skip): " ADMIN_CARD_NUMBER

while [ -z "$MARZBAN_URL" ]; do
    read -p "Marzban Panel URL (e.g. https://panel.com:8000): " MARZBAN_URL
done

while [ -z "$MARZBAN_USERNAME" ]; do
    read -p "Marzban Username: " MARZBAN_USERNAME
done

while [ -z "$MARZBAN_PASSWORD" ]; do
    read -p "Marzban Password: " MARZBAN_PASSWORD
done

# تولید پسورد رندوم و قدرتمند برای دیتابیس
DB_PASS=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 16)

# 5. دانلود یا آپدیت سورس کد از گیت‌هاب
REPO_URL="https://github.com/rezazd/Pulse-Bot.git"
DEST_DIR="/opt/pulse-bot"

echo -e "\n${YELLOW}📥 Fetching source code...${RESET}"
if [ -d "$DEST_DIR" ]; then
    echo -e "${CYAN}Directory exists. Pulling latest changes...${RESET}"
    cd $DEST_DIR
    git pull
else
    git clone $REPO_URL $DEST_DIR
    cd $DEST_DIR
fi

# 6. ساخت فایل .env
echo -e "${YELLOW}⚙️ Generating .env file...${RESET}"
cat <<EOF > .env
# --- Telegram Config ---
BOT_TOKEN=$BOT_TOKEN
ADMIN_IDS=$ADMIN_IDS
ADMIN_CARD_NUMBER=$ADMIN_CARD_NUMBER

# --- Database Config ---
DB_USER=pulse_user
DB_PASS=$DB_PASS
DB_HOST=mariadb
DB_PORT=3306
DB_NAME=pulse_bot_db

# --- Marzban Config ---
MARZBAN_URL=$MARZBAN_URL
MARZBAN_USERNAME=$MARZBAN_USERNAME
MARZBAN_PASSWORD=$MARZBAN_PASSWORD
EOF

# 7. اجرای پروژه با داکر
echo -e "${YELLOW}🐳 Starting Docker containers...${RESET}"
docker compose down # خاموش کردن کانتینرهای قبلی در صورت وجود
docker compose up -d --build

echo -e "${BLUE}=================================================${RESET}"
echo -e "${GREEN}✅ Pulse Bot has been successfully installed and is running!${RESET}"
echo -e "${GREEN}👉 Send /start to your bot in Telegram.${RESET}"
echo -e "${CYAN}📂 Project Directory: $DEST_DIR${RESET}"
echo -e "${BLUE}=================================================${RESET}"
