from typing import List, Dict, Any
from dataclasses import dataclass
from openai import AsyncOpenAI, APIConnectionError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .common_components import BaseRateLimiter, ModelBasedLimiterManager  # type: ignore

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

class OpenAILLMClient:
    """OpenAI LLM 专用客户端（按模型分离限流）"""
    def __init__(self, 
                 api_key: str = None,
                 base_url: str = None,
                 config: LLMRateLimitConfig = None,
                 model_configs: Dict[str, LLMRateLimitConfig] = None):
        
        self.config = config or LLMRateLimitConfig()
        self.model_configs = model_configs or {}
        
        # 使用按模型分离的限流器管理器
        self.limiter_manager = ModelBasedLimiterManager(
            limiter_class=LLMLimiter,
            default_config=self.config,
            model_configs=self.model_configs
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
                             **kwargs) -> str:
        
        # 使用指定模型的限流器
        model_limiter = self.limiter_manager.get_limiter(model)
        
        await model_limiter.wait_if_needed(estimated_tokens=max_tokens)
        
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # 更新实际消耗的 token
        if response.usage and hasattr(response.usage, 'total_tokens'):
            model_limiter.update_actual_tokens(response.usage.total_tokens)
        
        return response.choices[0].message.content
    
    async def simple_complete(self,
                             prompt: str,
                             system_prompt: str = None,
                             model: str = "gpt-4o-mini",
                             **kwargs) -> str:
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return await self.chat_completion(messages, model=model, **kwargs)
    
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
_llm_client = None

def get_llm_client(api_key: str = None,
                   base_url: str = None,
                   config: LLMRateLimitConfig = None) -> OpenAILLMClient:
    """获取全局 LLM 客户端实例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = OpenAILLMClient(
            api_key=api_key,
            base_url=base_url,
            config=config
        )
    return _llm_client
