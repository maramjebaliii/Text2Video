"""公共基础组件：通用限流与缓存基类

提供：
 - BaseRateLimiter：时间窗口内请求数与 token 数双指标限流
 - BaseResponseCache：TTL + 容量限制 + 可选持久化 的异步缓存
 - ModelBasedManager：按模型名分离限流器和缓存的管理器

"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, List, TypeVar, Callable


# ----------------------------- 限流 ----------------------------- #
class HasMaxConfig(Protocol):  # 为类型提示约束 config
    max_requests_per_minute: int
    max_tokens_per_minute: int


class BaseRateLimiter:
    """通用限流器（滑动 60s 窗口）

    子类只需提供 label（打印用）。
    """

    label: str = "Generic"

    def __init__(self, config: HasMaxConfig):
        self.config = config
        self.request_timestamps: List[float] = []
        self.token_usage: List[tuple[float, int]] = []
        self._lock = asyncio.Lock()

    async def wait_if_needed(self, estimated_tokens: int = 0):
        async with self._lock:
            now = time.time()
            minute_ago = now - 60

            # 清理过期记录
            self.request_timestamps = [t for t in self.request_timestamps if t > minute_ago]
            self.token_usage = [(t, tk) for t, tk in self.token_usage if t > minute_ago]

            # 请求数限制
            if len(self.request_timestamps) >= self.config.max_requests_per_minute:
                sleep_time = 60 - (now - self.request_timestamps[0])
                if sleep_time > 0:
                    print(f"⏳ 达到 {self.label} 请求限制 ({self.config.max_requests_per_minute}/分钟)，等待 {sleep_time:.1f} 秒...")
                    await asyncio.sleep(sleep_time)

            # token 限制
            current_tokens = sum(tokens for _, tokens in self.token_usage)
            if current_tokens + estimated_tokens >= self.config.max_tokens_per_minute:
                sleep_time = 60 - (now - self.token_usage[0][0]) if self.token_usage else 60
                if sleep_time > 0:
                    print(f"⏳ 达到 {self.label} Token 限制 ({self.config.max_tokens_per_minute}/分钟)，等待 {sleep_time:.1f} 秒...")
                    await asyncio.sleep(sleep_time)

            # 记录当前请求（先记录估算值，后续可 update）
            now2 = time.time()
            self.request_timestamps.append(now2)
            self.token_usage.append((now2, estimated_tokens))

    def update_actual_tokens(self, actual_tokens: int):
        if self.token_usage:
            last_time, _ = self.token_usage[-1]
            self.token_usage[-1] = (last_time, actual_tokens)

    def get_stats(self) -> Dict[str, Any]:
        now = time.time()
        minute_ago = now - 60
        active_requests = len([t for t in self.request_timestamps if t > minute_ago])
        active_tokens = sum(tokens for t, tokens in self.token_usage if t > minute_ago)
        return {
            "current_requests": active_requests,
            "current_tokens": active_tokens,
            "max_requests_per_minute": self.config.max_requests_per_minute,
            "max_tokens_per_minute": self.config.max_tokens_per_minute,
            "label": self.label,
        }


# ----------------------------- 缓存 ----------------------------- #

@dataclass
class BaseCacheConfig:
    enabled: bool = True
    max_size: int = 1000
    ttl_seconds: int = 3600
    persist_to_file: bool = False
    cache_file_path: str = "generic_cache.json"


class BaseResponseCache:
    """通用响应缓存基类

    依赖子类实现 _generate_key。
    存储结构：{ key: { "timestamp": float, ...payload... } }
    """

    label: str = "Cache"

    def __init__(self, config: BaseCacheConfig):
        self.config = config
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        if self.config.persist_to_file:
            self._load_cache()

    # --- 留给子类的接口 ---
    def _generate_key(self, *args, **kwargs) -> str:  # pragma: no cover - 子类实现
        raise NotImplementedError

    # --- 基础实现 ---
    def _load_cache(self):
        try:
            with open(self.config.cache_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                now = time.time()
                self.cache = {
                    k: v for k, v in data.items()
                    if now - v.get("timestamp", 0) < self.config.ttl_seconds
                }
        except (FileNotFoundError, json.JSONDecodeError):
            self.cache = {}

    def _save_cache(self):
        if not self.config.persist_to_file:
            print("⚠️  未启用持久化，跳过保存缓存。")
            return
        try:
            with open(self.config.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            # 打印下目前有多少个缓存
            print(f"💾 已保存 {self.label} 缓存，共 {len(self.cache)} 条。")
        except Exception as e:  
            print(f"⚠️  保存 {self.label} 缓存失败: {e}")
    

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            if key not in self.cache:
                return None
            data = self.cache[key]
            if time.time() - data.get("timestamp", 0) > self.config.ttl_seconds:
                del self.cache[key]
                self._save_cache()
                return None
            print(f"🎯 {self.label} 缓存命中: {key[:16]}...")
            return data

    async def set(self, key: str, value: Dict[str, Any]):
        async with self._lock:
            if len(self.cache) >= self.config.max_size:
                # 移除最旧
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].get("timestamp", 0))
                del self.cache[oldest_key]
            value["timestamp"] = time.time()
            self.cache[key] = value
            if self.config.persist_to_file:
                self._save_cache()
            print(f"💾 {self.label} 缓存存储: {key[:16]}...")

    def clear(self):
        self.cache.clear()
        if self.config.persist_to_file:
            try:
                import os
                if os.path.exists(self.config.cache_file_path):
                    os.remove(self.config.cache_file_path)
            except Exception as e:  # pragma: no cover
                print(f"⚠️  清空 {self.label} 缓存文件失败: {e}")

    def get_stats(self) -> Dict[str, Any]:
        now = time.time()
        valid_entries = sum(
            1 for v in self.cache.values() if now - v.get("timestamp", 0) < self.config.ttl_seconds
        )
        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "max_size": self.config.max_size,
            "ttl_seconds": self.config.ttl_seconds,
            "persist_to_file": self.config.persist_to_file,
            "label": self.label,
        }


__all__ = [
    "BaseRateLimiter",
    "BaseResponseCache", 
    "BaseCacheConfig",
    "ModelBasedLimiterManager",
    "ModelBasedCacheManager",
]


# ----------------------------- 按模型分离管理器 ----------------------------- #

T = TypeVar('T')
ConfigType = TypeVar('ConfigType')

class ModelBasedLimiterManager:
    """按模型名管理独立限流器的管理器
    
    用法：
    manager = ModelBasedLimiterManager(EmbeddingLimiter, default_config)
    limiter = manager.get_limiter("text-embedding-3-small", model_specific_config)
    """
    
    def __init__(self, 
                 limiter_class: type[BaseRateLimiter],
                 default_config: Any,
                 model_configs: Dict[str, Any] = None):
        self.limiter_class = limiter_class
        self.default_config = default_config
        self.model_configs = model_configs or {}
        self.limiters: Dict[str, BaseRateLimiter] = {}
    
    def get_limiter(self, model: str) -> BaseRateLimiter:
        """获取指定模型的限流器（懒加载）"""
        if model not in self.limiters:
            config = self.model_configs.get(model, self.default_config)
            self.limiters[model] = self.limiter_class(config)
        return self.limiters[model]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型的限流统计"""
        return {model: limiter.get_stats() for model, limiter in self.limiters.items()}


class ModelBasedCacheManager:
    """按模型名管理独立缓存的管理器
    
    用法：
    manager = ModelBasedCacheManager(EmbeddingResponseCache, default_config)
    cache = manager.get_cache("text-embedding-3-small", model_specific_config)
    """
    
    def __init__(self,
                 cache_class: type[BaseResponseCache], 
                 default_config: Any,
                 model_configs: Dict[str, Any] = None):
        self.cache_class = cache_class
        self.default_config = default_config
        self.model_configs = model_configs or {}
        self.caches: Dict[str, BaseResponseCache] = {}
    
    def get_cache(self, model: str) -> BaseResponseCache:
        """获取指定模型的缓存（懒加载）"""
        if model not in self.caches:
            config = self.model_configs.get(model, self.default_config)
            # 为每个模型使用不同的缓存文件路径
            if hasattr(config, 'cache_file_path') and config.persist_to_file:
                # 在文件名中插入模型名避免冲突
                original_path = config.cache_file_path
                name, ext = original_path.rsplit('.', 1) if '.' in original_path else (original_path, 'json')
                model_safe = model.replace('/', '_').replace(':', '_')  # 处理模型名中的特殊字符
                config.cache_file_path = f"{name}_{model_safe}.{ext}"
            
            self.caches[model] = self.cache_class(config)
        return self.caches[model]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型的缓存统计"""
        return {model: cache.get_stats() for model, cache in self.caches.items()}
    
    def clear_all(self):
        """清空所有模型的缓存"""
        for cache in self.caches.values():
            cache.clear()
        self.caches.clear()
