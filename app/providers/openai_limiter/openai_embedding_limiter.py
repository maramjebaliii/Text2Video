import time
from typing import List, Dict, Any
from dataclasses import dataclass
from openai import AsyncOpenAI, APIConnectionError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .common_components import BaseRateLimiter, ModelBasedLimiterManager  # type: ignore

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

class OpenAIEmbeddingClient:
    """OpenAI Embedding 专用客户端（按模型分离限流）"""
    def __init__(self, 
                 api_key: str = None,
                 base_url: str = None,
                 config: EmbeddingRateLimitConfig = None,
                 model_configs: Dict[str, EmbeddingRateLimitConfig] = None):
        
        self.config = config or EmbeddingRateLimitConfig()
        self.model_configs = model_configs or {}
        
        # 使用按模型分离的限流器管理器
        self.limiter_manager = ModelBasedLimiterManager(
            limiter_class=EmbeddingLimiter,
            default_config=self.config,
            model_configs=self.model_configs
        )
        
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    )
    async def embedding(self,
                       texts: List[str],
                       model: str = "text-embedding-3-small") -> List[List[float]]:
        
        # 使用指定模型的限流器
        model_limiter = self.limiter_manager.get_limiter(model)
        
        estimated_tokens = sum(len(text.split()) for text in texts) * 1.3  # 粗略估算
        await model_limiter.wait_if_needed(estimated_tokens=int(estimated_tokens))
        
        response = await self.client.embeddings.create(
            model=model,
            input=texts,
            encoding_format="float"
        )
        
        # 更新实际消耗的 token
        if response.usage and hasattr(response.usage, 'total_tokens'):
            model_limiter.update_actual_tokens(response.usage.total_tokens)
        
        return [data.embedding for data in response.data]
    
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

# 全局实例
_embedding_client = None

def get_embedding_client(api_key: str = None,
                         base_url: str = None,
                         config: EmbeddingRateLimitConfig = None) -> OpenAIEmbeddingClient:
    """获取全局 Embedding 客户端实例"""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = OpenAIEmbeddingClient(
            api_key=api_key,
            base_url=base_url,
            config=config
        )
    return _embedding_client