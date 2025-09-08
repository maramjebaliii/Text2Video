import json
import hashlib
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from openai import AsyncOpenAI, APIConnectionError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .common_components import (
    BaseResponseCache, BaseCacheConfig, BaseRateLimiter,
    ModelBasedLimiterManager, ModelBasedCacheManager  # type: ignore
)

@dataclass
class EmbeddingCacheConfig(BaseCacheConfig):
    max_size: int = 2000
    ttl_seconds: int = 7200
    cache_file_path: str = "embedding_cache.json"

class EmbeddingResponseCache(BaseResponseCache):
    label = "Embedding"
    def __init__(self, config: EmbeddingCacheConfig | None = None):
        super().__init__(config or EmbeddingCacheConfig())

    def _generate_key(self, model: str, texts: List[str], **kwargs) -> str:  # type: ignore[override]
        cache_data = {
            "model": model,
            "texts": texts,
            **{k: v for k, v in kwargs.items() if k not in ["encoding_format"]},
        }
        cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
        import hashlib as _hashlib
        return _hashlib.md5(cache_str.encode("utf-8")).hexdigest()

@dataclass
class EmbeddingRateLimitConfig:
    """Embedding 限流配置"""
    max_requests_per_minute: int = 2000
    max_tokens_per_minute: int = 500000
    retry_attempts: int = 5
    retry_min_wait: float = 4.0
    retry_max_wait: float = 10.0

class EmbeddingLimiter(BaseRateLimiter):
    label = "Embedding"
    def __init__(self, config: EmbeddingRateLimitConfig | None = None):
        super().__init__(config or EmbeddingRateLimitConfig())

class OpenAIEmbeddingClientWithCache:
    """OpenAI Embedding 客户端（带缓存，按模型分离限流和缓存）"""
    def __init__(self, 
                 api_key: str = None,
                 base_url: str = None,
                 rate_limit_config: EmbeddingRateLimitConfig = None,
                 cache_config: EmbeddingCacheConfig = None,
                 rate_limit_model_configs: Dict[str, EmbeddingRateLimitConfig] = None,
                 cache_model_configs: Dict[str, EmbeddingCacheConfig] = None):
        
        self.rate_limit_config = rate_limit_config or EmbeddingRateLimitConfig()
        self.cache_config = cache_config or EmbeddingCacheConfig()
        self.rate_limit_model_configs = rate_limit_model_configs or {}
        self.cache_model_configs = cache_model_configs or {}
        
        # 使用按模型分离的管理器
        self.limiter_manager = ModelBasedLimiterManager(
            limiter_class=EmbeddingLimiter,
            default_config=self.rate_limit_config,
            model_configs=self.rate_limit_model_configs
        )
        
        self.cache_manager = None
        if self.cache_config.enabled:
            self.cache_manager = ModelBasedCacheManager(
                cache_class=EmbeddingResponseCache,
                default_config=self.cache_config,
                model_configs=self.cache_model_configs
            )
        
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        # 为了兼容旧测试，保留这些属性
        self._default_model = "text-embedding-3-small"
    
    @property
    def limiter(self) -> BaseRateLimiter:
        """兼容性属性：返回默认模型的限流器"""
        return self.limiter_manager.get_limiter(self._default_model)
    
    @property 
    def cache(self) -> Optional[BaseResponseCache]:
        """兼容性属性：返回默认模型的缓存"""
        if self.cache_manager:
            return self.cache_manager.get_cache(self._default_model)
        return None
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    )
    async def embedding(self,
                       texts: List[str],
                       model: str = "text-embedding-3-small",
                       use_cache: bool = True,
                       **kwargs) -> List[List[float]]:
        
        # 使用指定模型的限流器和缓存
        model_limiter = self.limiter_manager.get_limiter(model)
        model_cache = self.cache_manager.get_cache(model) if self.cache_manager else None
        
        cache_key = None
        if model_cache and use_cache:
            cache_key = model_cache._generate_key(model, texts, **kwargs)
            cached_result = await model_cache.get(cache_key)
            if cached_result:
                return cached_result["embeddings"]
        
        estimated_tokens = sum(len(text.split()) for text in texts) * 1.3
        await model_limiter.wait_if_needed(estimated_tokens=int(estimated_tokens))
        
        response = await self.client.embeddings.create(
            model=model,
            input=texts,
            encoding_format="float",
            **kwargs
        )
        
        embeddings = [data.embedding for data in response.data]
        
        # 更新实际消耗的 token
        if response.usage and hasattr(response.usage, 'total_tokens'):
            model_limiter.update_actual_tokens(response.usage.total_tokens)
        
        if model_cache and use_cache and cache_key:
            await model_cache.set(cache_key, {
                "embeddings": embeddings,
                "model": model,
                "usage": dict(response.usage) if response.usage else {}
            })
        
        return embeddings
    
    async def embedding_single(self,
                             text: str,
                             model: str = "text-embedding-3-small",
                             use_cache: bool = True,
                             **kwargs) -> List[float]:
        """单个文本的 embedding"""
        result = await self.embedding([text], model=model, use_cache=use_cache, **kwargs)
        return result[0] if result else []
    
    def get_rate_limit_stats(self, model: str = None) -> Dict[str, Any]:
        """获取限流统计信息
        
        Args:
            model: 指定模型名，为 None 时返回默认模型统计
        """
        target_model = model or self._default_model
        return self.limiter_manager.get_limiter(target_model).get_stats()
    
    def get_all_rate_limit_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型的限流统计"""
        return self.limiter_manager.get_all_stats()
    
    def get_cache_stats(self, model: str = None) -> Optional[Dict[str, Any]]:
        """获取缓存统计信息
        
        Args:
            model: 指定模型名，为 None 时返回默认模型统计
        """
        if self.cache_manager:
            target_model = model or self._default_model
            return self.cache_manager.get_cache(target_model).get_stats()
        return None
    
    def get_all_cache_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型的缓存统计"""
        if self.cache_manager:
            return self.cache_manager.get_all_stats()
        return {}
    
    def clear_cache(self, model: str = None):
        """清空缓存
        
        Args:
            model: 指定模型名，为 None 时清空所有模型缓存
        """
        if self.cache_manager:
            if model:
                self.cache_manager.get_cache(model).clear()
                print(f"🗑️  {model} Embedding 缓存已清空")
            else:
                self.cache_manager.clear_all()
                print("🗑️  所有 Embedding 缓存已清空")

# 全局实例
_embedding_client_with_cache = None

def get_embedding_client_with_cache(api_key: str = None,
                                   base_url: str = None,
                                   rate_limit_config: EmbeddingRateLimitConfig = None,
                                   cache_config: EmbeddingCacheConfig = None) -> OpenAIEmbeddingClientWithCache:
    """获取全局 Embedding 客户端实例（带缓存）"""
    global _embedding_client_with_cache
    if _embedding_client_with_cache is None:
        _embedding_client_with_cache = OpenAIEmbeddingClientWithCache(
            api_key=api_key,
            base_url=base_url,
            rate_limit_config=rate_limit_config,
            cache_config=cache_config
        )
    return _embedding_client_with_cache