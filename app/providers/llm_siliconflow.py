"""SiliconFlow(OpenAI 兼容) LLM Provider。"""
from __future__ import annotations

from typing import Sequence
from openai import OpenAI

__all__ = ["SiliconFlowLLMProvider"]


class SiliconFlowLLMProvider:
    """简单 LLM 封装。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str = "Qwen/Qwen2.5-7B-Instruct",
    ) -> None:
        """保存客户端与默认模型。"""
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.default_model = default_model

    def chat(self, messages: Sequence[dict[str, str]], **kwargs) -> str:
        """发送消息并返回回复。"""
        model = kwargs.get("model") or self.default_model
        completion = self.client.chat.completions.create(
            model=model,
            messages=list(messages),
            stream=False,
        )
        return completion.choices[0].message.content
