from typing import Dict, Optional
import httpx
from app.config import settings, logger


class CloudflareBypasser:
    """用于绕过Cloudflare保护的客户端"""

    async def _get_bypass_url(self, target_url: str) -> tuple[str, str]:
        """
        构造Bypass服务的URL和Header
        
        Args:
            target_url: 目标URL
            
        Returns:
            (bypass_url, hostname)
        """
        from urllib.parse import urlparse
        parsed = urlparse(target_url)
        
        # 构造Bypass服务URL：将Target URL的Path和Query拼接到Bypass Base URL后面
        # 例如 Target: https://hanime1.me/watch?v=123
        # Bypass Service: http://cf-bypass:8000/watch?v=123
        bypass_base = settings.CLOUDFLARE_BYPASS_SERVICE_URL.rstrip('/')
        path_query = target_url.replace(f"{parsed.scheme}://{parsed.netloc}", "")
        if not path_query.startswith('/'):
            path_query = '/' + path_query
            
        bypass_url = f"{bypass_base}{path_query}"
        hostname = parsed.netloc
        
        return bypass_url, hostname

    async def get_request(self, url: str, params: Optional[Dict] = None, max_retries: int = 3) -> str:
        """
        获取指定URL的内容，通过Bypass服务绕过Cloudflare保护
        """
        retries = 0
        while retries < max_retries:
            try:
                import time
                start_time = time.time()
                
                # 构造Bypass请求
                bypass_url, hostname = await self._get_bypass_url(url)
                
                # 构造Headers
                headers = {
                    "x-hostname": hostname,
                    # "x-bypass-cache": "true" # 默认不强制刷新
                }
                
                # 只有重试时才强制刷新Token
                if retries > 0:
                    headers["x-bypass-cache"] = "true"
                
                # 如果配置了代理，透传给Bypass服务
                if settings.USE_PROXY and settings.PROXY_URL:
                    headers["x-proxy"] = settings.PROXY_URL

                logger.debug(f"通过Bypass服务请求URL: {url}")
                logger.debug(f"Bypass URL: {bypass_url}")
                logger.debug(f"Headers: {headers}")

                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(
                        bypass_url,
                        params=params,
                        headers=headers
                    )

                elapsed_time = time.time() - start_time
                logger.debug(f"请求完成，耗时: {elapsed_time:.2f}秒")
                
                if response.status_code == 200:
                    return response.text
                else:
                    logger.warning(f"Bypass服务返回非200状态码: {response.status_code}")
                    # 如果是500等错误，可能需要重试
                    if response.status_code >= 500:
                        raise Exception(f"Service Error: {response.status_code}")
                    return response.text

            except Exception as e:
                retries += 1
                logger.error(f"请求失败 (尝试 {retries}/{max_retries}): {str(e)}, URL: {url}")
                if retries >= max_retries:
                    logger.error(f"已达到最大重试次数({max_retries})，请求失败")
                    break
        return ""

    async def post_request(self, url: str, data: Dict, headers: Optional[Dict] = None, max_retries: int = 3) -> Dict:
        """
        发送POST请求，通过Bypass服务绕过Cloudflare保护
        """
        retries = 0
        while retries < max_retries:
            try:
                import time
                start_time = time.time()
                
                # 构造Bypass请求
                bypass_url, hostname = await self._get_bypass_url(url)
                
                # 构造Headers
                req_headers = {
                    "x-hostname": hostname,
                    # "x-bypass-cache": "true"
                }
                
                # 只有重试时才强制刷新Token
                if retries > 0:
                    req_headers["x-bypass-cache"] = "true"

                if headers:
                    req_headers.update(headers)
                    
                if settings.USE_PROXY and settings.PROXY_URL:
                    req_headers["x-proxy"] = settings.PROXY_URL

                logger.debug(f"通过Bypass服务发送POST: {url}")

                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        bypass_url,
                        data=data,
                        headers=req_headers
                    )

                elapsed_time = time.time() - start_time
                logger.debug(f"POST请求完成，耗时: {elapsed_time:.2f}秒")

                try:
                    return response.json()
                except:
                    logger.warning(f"响应非JSON格式: {response.text[:100]}...")
                    return {}

            except Exception as e:
                retries += 1
                logger.error(f"POST请求失败 (尝试 {retries}/{max_retries}): {str(e)}, URL: {url}")
                if retries >= max_retries:
                    break
        return {}
