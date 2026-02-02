import asyncio
import logging
import os
import re
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, List

from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp_socks import ProxyConnector

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID", ""))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

PROXY_FILE = "data.txt"
COOKIE_FILE = "cookies.txt"
DOWNLOAD_DIR = "downloads"
MAX_FILE_SIZE = 2000 * 1024 * 1024  # 2GB
MAX_CONCURRENT_DOWNLOADS = 3

TERA_REGEX = r"(https?://(?:www\.)?(?:terabox\.app|1024tera\.com|terafileshare\.com|terabox\.com)/\S+)"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("TeraboxBot")

# 确保下载目录存在
Path(DOWNLOAD_DIR).mkdir(exist_ok=True)

# ================= 会话管理 =================
class SessionManager:
    def __init__(self):
        self.cookie_header = None
        self.proxies: List[str] = []
        self.working_proxy: Optional[str] = None
        self.active_downloads = 0
        self.lock = asyncio.Lock()
        self.load_cookies()
        self.load_proxies()
    
    def load_cookies(self):
        try:
            if Path(COOKIE_FILE).exists():
                cookies = []
                with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and "terabox" in line.lower():
                            cookies.append(line)
                if cookies:
                    self.cookie_header = "; ".join(cookies)
                    log.info(f"✅ Loaded {len(cookies)} cookies")
                else:
                    log.error("❌ No valid cookies found in cookies.txt")
            else:
                log.error(f"❌ Cookie file not found: {COOKIE_FILE}")
        except Exception as e:
            log.error(f"❌ Failed to load cookies: {e}")
    
    def load_proxies(self):
        try:
            if Path(PROXY_FILE).exists():
                with open(PROXY_FILE, "r", encoding="utf-8") as f:
                    self.proxies = [line.strip() for line in f if line.strip()]
                log.info(f"✅ Loaded {len(self.proxies)} proxies")
            else:
                log.warning(f"⚠️ Proxy file not found: {PROXY_FILE}")
        except Exception as e:
            log.error(f"❌ Failed to load proxies: {e}")
    
    async def get_working_proxy(self, force_test: bool = False) -> Optional[str]:
        async with self.lock:
            if not force_test and self.working_proxy:
                return self.working_proxy
            
            if not self.proxies:
                log.warning("⚠️ No proxies available")
                return None
            
            log.info(f"🔍 Testing {len(self.proxies)} proxies...")
            
            # 并行测试代理
            tasks = [self.test_proxy(proxy) for proxy in self.proxies]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for proxy, result in zip(self.proxies, results):
                if result is True:
                    self.working_proxy = proxy
                    log.info(f"✅ Working proxy found: {proxy}")
                    return proxy
            
            log.error("❌ No working proxy found")
            return None
    
    async def test_proxy(self, proxy: str) -> bool:
        try:
            connector = ProxyConnector.from_url(proxy)
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                async with session.get("https://httpbin.org/ip", ssl=False) as r:
                    if r.status == 200:
                        data = await r.json()
                        log.debug(f"Proxy {proxy} returned IP: {data.get('origin')}")
                        return True
        except Exception as e:
            log.debug(f"Proxy {proxy} failed: {e}")
        return False
    
    async def acquire_download_slot(self) -> bool:
        async with self.lock:
            if self.active_downloads < MAX_CONCURRENT_DOWNLOADS:
                self.active_downloads += 1
                return True
            return False
    
    def release_download_slot(self):
        async with self.lock:
            self.active_downloads = max(0, self.active_downloads - 1)

# 全局管理器实例
session_manager = SessionManager()

# ================= 下载工具 =================
class TeraboxDownloader:
    @staticmethod
    async def extract_download_url(link: str) -> Optional[str]:
        proxy = await session_manager.get_working_proxy()
        if not proxy:
            raise Exception("没有可用的代理")
        
        if not session_manager.cookie_header:
            raise Exception("Cookie 未配置")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Cookie": session_manager.cookie_header,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        try:
            connector = ProxyConnector.from_url(proxy)
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(
                connector=connector,
                headers=headers,
                timeout=timeout
            ) as session:
                # 第一次请求获取页面
                async with session.get(link, allow_redirects=True, ssl=False) as r:
                    html = await r.text()
                
                # 尝试多种匹配模式
                patterns = [
                    r'"downloadUrl"\s*:\s*"([^"]+)"',
                    r'downloadUrl":"([^"]+)"',
                    r'video_url"\s*:\s*"([^"]+)"',
                    r'"url"\s*:\s*"([^"]+)"',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, html)
                    if match:
                        url = match.group(1).replace("\\/", "/")
                        if url.startswith("http"):
                            return url
                
                # 如果没有找到，尝试查找视频标签
                video_match = re.search(r'<video[^>]+src="([^"]+)"', html)
                if video_match:
                    return video_match.group(1)
                
                raise Exception("无法提取下载链接")
                
        except Exception as e:
            log.error(f"提取链接失败: {e}")
            raise Exception(f"提取链接失败: {str(e)}")
    
    @staticmethod
    async def download_file(url: str, file_path: str, message: Message):
        """下载文件并显示进度"""
        proxy = await session_manager.get_working_proxy()
        if not proxy:
            raise Exception("代理不可用")
        
        connector = ProxyConnector.from_url(proxy)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.terabox.com/",
        }
        
        try:
            async with aiohttp.ClientSession(
                connector=connector,
                headers=headers
            ) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3600)) as r:
                    if r.status != 200:
                        raise Exception(f"下载失败: HTTP {r.status}")
                    
                    total_size = int(r.headers.get('content-length', 0))
                    if total_size > MAX_FILE_SIZE:
                        raise Exception(f"文件太大 ({total_size//(1024*1024)}MB)，超过限制")
                    
                    downloaded = 0
                    last_update = 0
                    
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in r.content.iter_chunked(1024*1024):  # 1MB chunks
                            if chunk:
                                await f.write(chunk)
                                downloaded += len(chunk)
                                
                                # 每下载5%更新一次进度
                                if total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    if progress - last_update >= 5:
                                        await message.edit_text(
                                            f"📥 下载中... {progress:.1f}% "
                                            f"({downloaded//(1024*1024)}MB/{total_size//(1024*1024)}MB)"
                                        )
                                        last_update = progress
                    
                    return downloaded
                    
        except asyncio.TimeoutError:
            raise Exception("下载超时")
        except Exception as e:
            raise Exception(f"下载失败: {str(e)}")

# ================= BOT =================
app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

downloader = TeraboxDownloader()

@app.on_message(filters.command("start"))
async def start_command(_, message: Message):
    await message.reply_text(
        "🤖 Terabox 下载机器人\n\n"
        "发送 Terabox 链接给我，我会帮你下载视频。\n\n"
        "支持域名:\n"
        "• terabox.app\n"
        "• 1024tera.com\n"
        "• terabox.com\n\n"
        "状态:\n"
        f"• 代理: {'✅ 已配置' if session_manager.proxies else '❌ 未配置'}\n"
        f"• Cookie: {'✅ 已配置' if session_manager.cookie_header else '❌ 未配置'}\n"
        f"• 活跃下载: {session_manager.active_downloads}/{MAX_CONCURRENT_DOWNLOADS}"
    )

@app.on_message(filters.command("status"))
async def status_command(_, message: Message):
    proxy_status = "✅ 工作正常" if session_manager.working_proxy else "❌ 不可用"
    await message.reply_text(
        f"📊 机器人状态\n\n"
        f"• 代理状态: {proxy_status}\n"
        f"• 代理数量: {len(session_manager.proxies)}\n"
        f"• Cookie: {'✅ 已配置' if session_manager.cookie_header else '❌ 未配置'}\n"
        f"• 活跃下载: {session_manager.active_downloads}/{MAX_CONCURRENT_DOWNLOADS}\n"
        f"• 工作代理: {session_manager.working_proxy or '无'}"
    )

@app.on_message(filters.command("reload"))
async def reload_command(_, message: Message):
    if message.from_user.id not in [12345678]:  # 替换为你的用户ID
        return
    
    session_manager.load_cookies()
    session_manager.load_proxies()
    await session_manager.get_working_proxy(force_test=True)
    await message.reply_text("✅ 配置已重新加载")

@app.on_message(filters.private & filters.text)
async def handle_message(_, message: Message):
    match = re.search(TERA_REGEX, message.text, re.IGNORECASE)
    if not match:
        return
    
    link = match.group(0)
    user_id = message.from_user.id
    
    # 检查并发限制
    if not await session_manager.acquire_download_slot():
        await message.reply_text("⏳ 下载队列已满，请稍后再试")
        return
    
    status_msg = await message.reply_text("🔍 正在解析链接...")
    
    try:
        # 获取下载链接
        await status_msg.edit_text("🔗 正在获取下载地址...")
        download_url = await downloader.extract_download_url(link)
        
        if not download_url:
            await status_msg.edit_text("❌ 无法获取下载链接")
            return
        
        # 生成文件名
        file_name = f"terabox_{user_id}_{int(time.time())}.mp4"
        file_path = os.path.join(DOWNLOAD_DIR, file_name)
        
        # 开始下载
        await status_msg.edit_text("⬇️ 开始下载视频...")
        
        try:
            await downloader.download_file(download_url, file_path, status_msg)
            
            # 发送视频
            await status_msg.edit_text("📤 正在上传到 Telegram...")
            
            try:
                await message.reply_video(
                    video=file_path,
                    caption="✅ Terabox 视频下载完成",
                    progress=progress_callback,
                    progress_args=(status_msg,)
                )
                await status_msg.delete()
                
            except Exception as e:
                log.error(f"发送视频失败: {e}")
                await status_msg.edit_text("✅ 下载完成，但发送到 Telegram 失败")
                
        except Exception as e:
            await status_msg.edit_text(f"❌ 下载失败: {str(e)}")
            
    except Exception as e:
        log.exception("处理消息时出错")
        await status_msg.edit_text(f"❌ 错误: {str(e)}")
        
    finally:
        # 清理文件
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        # 释放下载槽位
        session_manager.release_download_slot()

async def progress_callback(current, total, message):
    try:
        percent = (current / total) * 100
        await message.edit_text(f"📤 上传中... {percent:.1f}%")
    except:
        pass

# ================= MAIN =================
async def main():
    # 检查必要配置
    if not API_ID or not API_HASH or not BOT_TOKEN:
        log.error("❌ 请设置 API_ID, API_HASH 和 BOT_TOKEN 环境变量")
        return
    
    if not session_manager.cookie_header:
        log.error("❌ 请配置 cookies.txt 文件")
        # 可以继续运行，但无法下载
    
    # 测试代理
    proxy = await session_manager.get_working_proxy()
    if proxy:
        log.info(f"✅ 工作代理: {proxy}")
    else:
        log.warning("⚠️ 没有可用的代理，将尝试直连")
    
    await app.start()
    bot_info = await app.get_me()
    log.info(f"🤖 机器人已启动: @{bot_info.username}")
    
    await idle()
    
    await app.stop()

if __name__ == "__main__":
    import time
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 机器人已停止")
