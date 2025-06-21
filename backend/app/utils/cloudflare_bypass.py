from typing import Dict, Optional
import curl_cffi.requests as requests
from app.config import settings, logger


class CloudflareBypasser:
    """用于绕过Cloudflare保护的客户端"""

    async def get_request(self, url: str, params: Optional[Dict] = None, max_retries: int = 3) -> str:
        """
        获取指定URL的内容，自动绕过Cloudflare保护
        
        Args:
            url: 目标URL
            params: 查询参数字典
            max_retries: 最大重试次数，默认3次
            
        Returns:
            页面HTML内容
        """
        retries = 0
        while retries < max_retries:
            try:
                # 配置代理
                proxies = None
                if settings.USE_PROXY and settings.PROXY_URL:
                    proxies = {"https": settings.PROXY_URL, "http": settings.PROXY_URL}

                import time
                start_time = time.time()
                logger.debug(f"开始请求URL: {url}")
                logger.debug(f"请求参数: {params}")

                # 使用curl_cffi发送请求并模拟Chrome浏览器
                response = requests.get(
                    url,
                    params=params,
                    impersonate="chrome",
                    proxies=proxies,
                    timeout=30
                )

                # 计算请求时间并打印
                elapsed_time = time.time() - start_time
                logger.debug(f"请求完成，URL: {url}, 耗时: {elapsed_time:.2f}秒")
                # 成功获取内容
                return response.text

            except Exception as e:
                retries += 1
                logger.error(f"curl_cffi请求失败 (尝试 {retries}/{max_retries}): {str(e)}, URL: {url}")
                if retries >= max_retries:
                    logger.error(f"已达到最大重试次数({max_retries})，请求失败: {url}")
                    break
        return ""

    async def post_request(self, url: str, data: Dict, headers: Optional[Dict] = None, max_retries: int = 3) -> Dict:
        """
        发送POST请求到指定URL，自动绕过Cloudflare保护
        
        Args:
            url: 目标URL
            data: 请求数据
            headers: 额外的请求头
            max_retries: 最大重试次数，默认3次
            
        Returns:
            APIResponse对象
        """
        retries = 0
        while retries < max_retries:
            try:
                # 合并请求头
                request_headers = {}
                if headers:
                    request_headers.update(headers)

                # 配置代理
                proxies = None
                if settings.USE_PROXY and settings.PROXY_URL:
                    proxies = {"https": settings.PROXY_URL, "http": settings.PROXY_URL}

                import time
                start_time = time.time()
                logger.debug(f"开始POST请求: {url}")

                # 使用curl_cffi发送POST请求并模拟Chrome浏览器
                response = requests.post(
                    url,
                    data=data,
                    headers=request_headers,
                    impersonate="chrome",
                    proxies=proxies,
                    timeout=30
                )

                # 计算请求时间并打印
                elapsed_time = time.time() - start_time
                logger.debug(f"POST请求完成，URL: {url}, 耗时: {elapsed_time:.2f}秒")

                return response.json()

            except Exception as e:
                retries += 1
                logger.error(f"curl_cffi POST请求失败 (尝试 {retries}/{max_retries}): {str(e)}, URL: {url}")
                if retries >= max_retries:
                    logger.error(f"已达到最大重试次数({max_retries})，POST请求失败: {url}")
                    break
        return {}
