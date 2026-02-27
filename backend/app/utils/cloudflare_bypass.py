from typing import Dict, Optional
import httpx
import time
from app.config import settings, logger


# CF 挑战页面特征码
CF_CHALLENGE_MARKERS = [
    "Just a moment...",
    "challenges.cloudflare.com",
    "cf-browser-verification",
    "cf_chl_opt",
    "_cf_chl_tk",
]


class CloudflareChallengedException(Exception):
    """CF 5s 盾拦截异常"""
    pass


class CloudflareBypasser:
    """用于绕过Cloudflare保护的客户端，通过外部 cf-bypass 服务转发请求"""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    @property
    async def client(self) -> httpx.AsyncClient:
        """懒加载并复用 httpx 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self):
        """关闭 HTTP 客户端连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _build_bypass_url(self, target_url: str) -> tuple[str, str]:
        """
        构造 Bypass 服务的 URL 和 hostname

        Returns:
            (bypass_url, hostname)
        """
        from urllib.parse import urlparse
        parsed = urlparse(target_url)

        bypass_base = settings.CLOUDFLARE_BYPASS_SERVICE_URL.rstrip('/')
        path_query = target_url.replace(f"{parsed.scheme}://{parsed.netloc}", "")
        if not path_query.startswith('/'):
            path_query = '/' + path_query

        return f"{bypass_base}{path_query}", parsed.netloc

    def _build_headers(self, hostname: str, force_refresh: bool = False) -> dict:
        """构造请求头"""
        headers = {"x-hostname": hostname}

        if force_refresh:
            headers["x-bypass-cache"] = "true"

        if settings.USE_PROXY and settings.PROXY_URL:
            headers["x-proxy"] = settings.PROXY_URL

        return headers

    @staticmethod
    def _is_cf_challenge(content: str) -> bool:
        """检测响应内容是否是 CF 挑战页面"""
        if not content or len(content) < 50:
            return False
        # 只检查前 5000 个字符，避免大页面性能问题
        snippet = content[:5000]
        return any(marker in snippet for marker in CF_CHALLENGE_MARKERS)

    async def get_request(self, url: str, params: Optional[Dict] = None, max_retries: int = 3) -> str:
        """
        通过 Bypass 服务发送 GET 请求

        首次使用缓存 cookie，如果检测到 CF 挑战页面则自动强制刷新重试。
        """
        bypass_url, hostname = self._build_bypass_url(url)
        client = await self.client

        for attempt in range(1, max_retries + 1):
            try:
                # 第一次用缓存，后续强制刷新
                force_refresh = attempt > 1
                headers = self._build_headers(hostname, force_refresh=force_refresh)

                logger.debug(f"[CF] GET {url} (第{attempt}次请求, 强制刷新={force_refresh})")

                start_time = time.time()
                response = await client.get(bypass_url, params=params, headers=headers)
                elapsed = time.time() - start_time

                logger.debug(f"[CF] 响应 {response.status_code}, 耗时 {elapsed:.2f}s")

                # 服务端错误直接重试
                if response.status_code >= 500:
                    logger.warning(f"[CF] Bypass 服务返回 {response.status_code}, 将重试")
                    continue

                content = response.text

                # 检测是否返回了 CF 挑战页面（而非真正内容）
                if self._is_cf_challenge(content):
                    logger.warning(f"[CF] 检测到 CF 挑战页面, 将强制刷新 cookie 重试")
                    continue

                return content

            except httpx.TimeoutException:
                logger.warning(f"[CF] 请求超时 (attempt {attempt}/{max_retries}), URL: {url}")
            except httpx.ConnectError as e:
                logger.error(f"[CF] 连接 Bypass 服务失败: {e}")
                # 连接都失败了，重建客户端
                await self.close()
                client = await self.client
            except Exception as e:
                logger.error(f"[CF] 请求异常 (attempt {attempt}/{max_retries}): {e}, URL: {url}")

        logger.error(f"[CF] 已达最大重试次数({max_retries})，请求失败: {url}")
        return ""

    async def post_request(self, url: str, data: Dict, headers: Optional[Dict] = None,
                           max_retries: int = 3) -> Dict:
        """
        通过 Bypass 服务发送 POST 请求
        """
        bypass_url, hostname = self._build_bypass_url(url)
        client = await self.client

        for attempt in range(1, max_retries + 1):
            try:
                force_refresh = attempt > 1
                req_headers = self._build_headers(hostname, force_refresh=force_refresh)

                if headers:
                    req_headers.update(headers)

                logger.debug(f"[CF] POST {url} (attempt {attempt}/{max_retries})")

                start_time = time.time()
                response = await client.post(bypass_url, data=data, headers=req_headers)
                elapsed = time.time() - start_time

                logger.debug(f"[CF] POST 响应 {response.status_code}, 耗时 {elapsed:.2f}s")

                if response.status_code >= 500:
                    logger.warning(f"[CF] Bypass 服务返回 {response.status_code}, 将重试")
                    continue

                # 检测 CF 挑战
                if self._is_cf_challenge(response.text):
                    logger.warning(f"[CF] POST 检测到 CF 挑战页面, 将强制刷新 cookie 重试")
                    continue

                try:
                    return response.json()
                except Exception:
                    logger.warning(f"[CF] POST 响应非 JSON: {response.text[:100]}...")
                    return {}

            except httpx.TimeoutException:
                logger.warning(f"[CF] POST 超时 (attempt {attempt}/{max_retries}), URL: {url}")
            except httpx.ConnectError as e:
                logger.error(f"[CF] 连接 Bypass 服务失败: {e}")
                await self.close()
                client = await self.client
            except Exception as e:
                logger.error(f"[CF] POST 异常 (attempt {attempt}/{max_retries}): {e}, URL: {url}")

        logger.error(f"[CF] POST 已达最大重试次数({max_retries})，请求失败: {url}")
        return {}


# 全局单例，所有 service 共享同一个实例和连接
cf_bypasser = CloudflareBypasser()
