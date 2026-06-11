import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any
from core.config import config

logger = logging.getLogger(__name__)

class MarzbanAPI:
    def __init__(self):
        # خواندن امن متغیرها از config
        self.base_url = config.MARZBAN_URL.rstrip('/') if config.MARZBAN_URL else ""
        self.username = config.MARZBAN_USERNAME
        self.password = config.MARZBAN_PASSWORD
        self.token: Optional[str] = None
        
        # تنظیم تایم‌اوت برای جلوگیری از هنگ کردن ربات در صورت قطعی مرزبان
        self.timeout = aiohttp.ClientTimeout(total=15)
        
        # سشن دائمی برای افزایش چشمگیر سرعت درخواست‌ها
        self._session: Optional[aiohttp.ClientSession] = None
        
        # قفل برای جلوگیری از ارسال چندین درخواست لاگین همزمان (رفع باگ Thundering Herd)
        self._token_lock = asyncio.Lock()

    async def get_session(self) -> aiohttp.ClientSession:
        """ایجاد یا بازگرداندن سشن دائمی"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def close(self):
        """بستن امن سشن در زمان خاموش شدن ربات"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_token(self) -> bool:
        """دریافت توکن جدید از مرزبان با مدیریت همزمانی"""
        if not self.base_url or not self.username or not self.password:
            logger.error("❌ Marzban credentials are not set in .env file!")
            return False

        # استفاده از قفل تا اگر چند ریکوئست همزمان 401 گرفتند، فقط یک بار لاگین انجام شود
        async with self._token_lock:
            url = f"{self.base_url}/api/admin/token"
            data = {
                "username": self.username,
                "password": self.password,
                "grant_type": "password"
            }
            try:
                session = await self.get_session()
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.token = result.get("access_token")
                        logger.info("✅ Marzban Token generated successfully.")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Marzban Login Failed: {response.status} - {error_text}")
                        return False
            except asyncio.TimeoutError:
                logger.error("❌ Marzban Login Timeout: Server is not responding.")
                return False
            except aiohttp.ClientError as e:
                logger.error(f"❌ Marzban Connection Error (Token): {str(e)}")
                return False
            except Exception as e:
                logger.error(f"❌ Marzban Unexpected Error (Token): {str(e)}")
                return False

    async def _parse_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """متد کمکی برای استخراج امن دیتای خروجی"""
        try:
            data = await response.json()
        except aiohttp.ContentTypeError:
            data = await response.text()
        return {"status": response.status, "data": data}

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """متد مرکزی برای ارسال درخواست‌ها با مدیریت هوشمند توکن و خطاها"""
        if not self.token:
            if not await self._get_token():
                return {"status": 500, "data": {"detail": "Failed to connect to Marzban (Token Error)"}}

        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.token}", "accept": "application/json"}
        
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            session = await self.get_session()
            async with session.request(method, url, headers=headers, **kwargs) as response:
                # اگر توکن منقضی شده بود (خطای 401)، دوباره لاگین کن و درخواست را تکرار کن
                if response.status == 401:
                    logger.warning("⚠️ Marzban Token Expired. Refreshing...")
                    if await self._get_token():
                        headers["Authorization"] = f"Bearer {self.token}"
                        async with session.request(method, url, headers=headers, **kwargs) as retry_response:
                            return await self._parse_response(retry_response)
                    else:
                        return {"status": 401, "data": {"detail": "Unauthorized"}}
                
                return await self._parse_response(response)
                
        except asyncio.TimeoutError:
            logger.error(f"❌ Marzban API Timeout ({endpoint})")
            return {"status": 504, "data": {"detail": "Marzban Server Timeout"}}
        except aiohttp.ClientError as e:
            logger.error(f"❌ Marzban API Connection Error ({endpoint}): {str(e)}")
            return {"status": 502, "data": {"detail": "Marzban Connection Failed"}}
        except Exception as e:
            logger.error(f"❌ Marzban API Unexpected Error ({endpoint}): {str(e)}")
            return {"status": 500, "data": {"detail": f"Unexpected Error: {str(e)}"}}

    # ==========================================
    # متدهای کاربردی برای ربات تلگرام
    # ==========================================

    async def get_system_stats(self) -> Dict[str, Any]:
        """دریافت وضعیت سرور (رم، پردازنده، ترافیک کل)"""
        return await self._request("GET", "/api/system")

    async def add_user(self, username: str, data_limit: int, expire: int, proxies: dict = None, inbounds: dict = None) -> Dict[str, Any]:
        """ساخت کانفیگ جدید"""
        payload = {
            "username": username,
            "proxies": proxies or {"vless": {}},
            "inbounds": inbounds or {},
            "expire": expire,
            "data_limit": data_limit,
            "data_limit_reset_strategy": "no_reset"
        }
        return await self._request("POST", "/api/user", json=payload)

    async def get_user(self, username: str) -> Dict[str, Any]:
        """دریافت اطلاعات یک کاربر (حجم مصرفی، لینک ساب و...)"""
        return await self._request("GET", f"/api/user/{username}")

    async def get_users(self, offset: int = 0, limit: int = 50) -> Dict[str, Any]:
        """دریافت لیست کاربران (برای آمار پنل ادمین)"""
        return await self._request("GET", f"/api/users?offset={offset}&limit={limit}")

    async def modify_user(self, username: str, data_limit: Optional[int] = None, expire: Optional[int] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """ویرایش کاربر (تمدید اشتراک یا فعال/غیرفعال کردن)"""
        payload = {}
        if data_limit is not None: payload["data_limit"] = data_limit
        if expire is not None: payload["expire"] = expire
        if status is not None: payload["status"] = status # active, disabled
            
        return await self._request("PUT", f"/api/user/{username}", json=payload)

    async def delete_user(self, username: str) -> Dict[str, Any]:
        """حذف کامل کاربر از مرزبان"""
        return await self._request("DELETE", f"/api/user/{username}")

    async def reset_user_usage(self, username: str) -> Dict[str, Any]:
        """صفر کردن حجم مصرفی کاربر"""
        return await self._request("POST", f"/api/user/{username}/reset")
        
    async def revoke_sub(self, username: str) -> Dict[str, Any]:
        """تغییر لینک سابسکریپشن (برای زمانی که لینک کاربر لو رفته)"""
        return await self._request("POST", f"/api/user/{username}/revoke_sub")

# ساخت یک نمونه (Instance) برای استفاده در کل پروژه
marzban_api = MarzbanAPI()