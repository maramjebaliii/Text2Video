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
class LLMCacheConfig(BaseCacheConfig):
    max_size: int = 1000
    ttl_seconds: int = 3600
    cache_file_path: str = "llm_cache.json"

class LLMResponseCache(BaseResponseCache):
    label = "LLM"
    def __init__(self, config: LLMCacheConfig | None = None):
        super().__init__(config or LLMCacheConfig())

    def _generate_key(self, model: str, messages: List[dict], **kwargs) -> str:  # type: ignore[override]
        cache_data = {
            "model": model,
            "messages": messages,
            **{k: v for k, v in kwargs.items() if k not in ["stream", "n"]},
        }
        cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
        import hashlib as _hashlib
        return _hashlib.md5(cache_str.encode("utf-8")).hexdigest()

@dataclass
class LLMRateLimitConfig:
    """LLM 限流配置"""
    max_requests_per_minute: int = 60
    max_tokens_per_minute: int = 90000
    retry_attempts: int = 5
    retry_min_wait: float = 4.0
    retry_max_wait: float = 10.0

class LLMLimiter(BaseRateLimiter):
    label = "LLM"
    def __init__(self, config: LLMRateLimitConfig | None = None):
        super().__init__(config or LLMRateLimitConfig())

class OpenAILLMClientWithCache:
    """OpenAI LLM 客户端（带缓存，按模型分离限流和缓存）"""
    def __init__(self, 
                 api_key: str = None,
                 base_url: str = None,
                 rate_limit_config: LLMRateLimitConfig = None,
                 cache_config: LLMCacheConfig = None,
                 rate_limit_model_configs: Dict[str, LLMRateLimitConfig] = None,
                 cache_model_configs: Dict[str, LLMCacheConfig] = None):
        
        self.rate_limit_config = rate_limit_config or LLMRateLimitConfig()
        self.cache_config = cache_config or LLMCacheConfig()
        self.rate_limit_model_configs = rate_limit_model_configs or {}
        self.cache_model_configs = cache_model_configs or {}
        
        # 使用按模型分离的管理器
        self.limiter_manager = ModelBasedLimiterManager(
            limiter_class=LLMLimiter,
            default_config=self.rate_limit_config,
            model_configs=self.rate_limit_model_configs
        )
        
        self.cache_manager = None
        if self.cache_config.enabled:
            self.cache_manager = ModelBasedCacheManager(
                cache_class=LLMResponseCache,
                default_config=self.cache_config,
                model_configs=self.cache_model_configs
            )
        
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)


    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    )
    async def chat_completion(self,
                             messages: List[dict],
                             model: str = "gpt-4o-mini",
                             temperature: float = 0.7,
                             max_tokens: int = 1000,
                             use_cache: bool = True,
                             **kwargs) -> str:
        
        # 使用指定模型的限流器和缓存
        model_limiter = self.limiter_manager.get_limiter(model)
        model_cache = self.cache_manager.get_cache(model) if self.cache_manager else None
        
        cache_key = None
        if model_cache and use_cache:
            cache_key = model_cache._generate_key(model, messages, temperature=temperature, max_tokens=max_tokens, **kwargs)
            cached_result = await model_cache.get(cache_key)
            if cached_result:
                return cached_result["content"]
        
        await model_limiter.wait_if_needed(estimated_tokens=max_tokens)
        
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        content = response.choices[0].message.content
        
        # 更新实际消耗的 token
        if response.usage and hasattr(response.usage, 'total_tokens'):
            model_limiter.update_actual_tokens(response.usage.total_tokens)
        
        if model_cache and use_cache and cache_key:
            await model_cache.set(cache_key, {
                "content": content,
                "model": model,
                "usage": dict(response.usage) if response.usage else {}
            })
        
        return content
    
    async def simple_complete(self,
                             prompt: str,
                             system_prompt: str = None,
                             model: str = None,
                             use_cache: bool = False,
                             **kwargs) -> str:
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return await self.chat_completion(messages, model=model, use_cache=use_cache, **kwargs)
    
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
                print(f"🗑️  {model} LLM 缓存已清空")
            else:
                self.cache_manager.clear_all()
                print("🗑️  所有 LLM 缓存已清空")

# 全局实例
_llm_client_with_cache = None

def get_llm_client_with_cache(api_key: str = None,
                             base_url: str = None,
                             rate_limit_config: LLMRateLimitConfig = None,
                             cache_config: LLMCacheConfig = None) -> OpenAILLMClientWithCache:
    """获取全局 LLM 客户端实例（带缓存）"""
    global _llm_client_with_cache
    if _llm_client_with_cache is None:
        _llm_client_with_cache = OpenAILLMClientWithCache(
            api_key=api_key,
            base_url=base_url,
            rate_limit_config=rate_limit_config,
            cache_config=cache_config
        )
    return _llm_client_with_cache