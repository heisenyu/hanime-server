import time
import functools
import asyncio
from typing import Any, Callable, Dict, Optional, TypeVar, Union, cast
from collections import OrderedDict
from app.config import logger

T = TypeVar('T')

class LRUCache:
    """
    LRU缓存实现，支持设置过期时间和最大容量
    """
    def __init__(self, maxsize: int = 128, ttl: int = 3600):
        """
        初始化LRU缓存
        
        Args:
            maxsize: 缓存最大容量，默认128
            ttl: 缓存过期时间（秒），默认3600秒（1小时）
        """
        self.cache: OrderedDict = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any:
        """获取缓存项，如果不存在或已过期则返回None"""
        if key not in self.cache:
            self.misses += 1
            return None
        
        value, timestamp = self.cache[key]
        
        # 检查是否过期
        if self.ttl > 0 and time.time() - timestamp > self.ttl:
            self.cache.pop(key)
            self.misses += 1
            return None
        
        # 更新使用顺序（将项移到末尾表示最近使用）
        self.cache.move_to_end(key)
        self.hits += 1
        return value

    def set(self, key: str, value: Any) -> None:
        """设置缓存项"""
        # 如果键已存在，先移除再添加，以更新顺序
        if key in self.cache:
            self.cache.pop(key)
        
        # 如果缓存已满，移除最久未使用的项（第一个）
        if len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)
        
        # 添加新项，带上时间戳
        self.cache[key] = (value, time.time())

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        
    def remove(self, key: str) -> None:
        """移除指定的缓存项"""
        if key in self.cache:
            self.cache.pop(key)
            
    def get_stats(self) -> Dict[str, Union[int, float]]:
        """获取缓存统计信息"""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate": hit_rate,
            "size": len(self.cache),
            "maxsize": self.maxsize
        }


def lru_cache(
    maxsize: int = 128, 
    ttl: int = 3600, 
    key_builder: Optional[Callable] = None
) -> Callable:
    """
    LRU缓存装饰器，支持设置过期时间和最大容量
    
    Args:
        maxsize: 缓存最大容量，默认128
        ttl: 缓存过期时间（秒），默认3600秒（1小时）
        key_builder: 自定义缓存键生成函数，默认使用函数参数作为键
    
    Returns:
        装饰器函数
    """
    cache_instance = LRUCache(maxsize=maxsize, ttl=ttl)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            # 生成缓存键
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # 默认使用函数名和参数作为键
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # 尝试从缓存获取
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {func.__name__}, key={cache_key}")
                return cached_result
            
            # 缓存未命中，执行函数
            logger.debug(f"缓存未命中: {func.__name__}, key={cache_key}")
            result = await func(*args, **kwargs)
            
            # 存储结果到缓存
            cache_instance.set(cache_key, result)
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            # 生成缓存键
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # 默认使用函数名和参数作为键
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # 尝试从缓存获取
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {func.__name__}, key={cache_key}")
                return cached_result
            
            # 缓存未命中，执行函数
            logger.debug(f"缓存未命中: {func.__name__}, key={cache_key}")
            result = func(*args, **kwargs)
            
            # 存储结果到缓存
            cache_instance.set(cache_key, result)
            return result
        
        # 添加缓存控制方法到包装函数
        wrapper = async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        wrapper.cache = cache_instance  # type: ignore
        wrapper.cache_clear = cache_instance.clear  # type: ignore
        wrapper.cache_remove = cache_instance.remove  # type: ignore
        wrapper.cache_stats = cache_instance.get_stats  # type: ignore
        
        return cast(Callable[..., T], wrapper)
    
    return decorator