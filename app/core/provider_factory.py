"""Provider 工厂：集中创建 LLM / Image / TTS 提供者实例。

从环境变量读取：
- GUIJI_API_KEY（必填）
- GUIJI_BASE_URL（可选，默认 https://api.siliconflow.cn/v1）
"""
from __future__ import annotations

import os
from typing import Optional
from app.core.config import CONFIG
from app.providers import (
    GuijiTTSProvider,
    # AliyunTTSProvider,
    SiliconFlowImageProvider,
    SiliconFlowLLMProvider,
)


# Module-level defaults that can be set at application startup (e.g. from main.py)
DEFAULT_GUJI_API_KEY: Optional[str] = None
DEFAULT_GUJI_BASE_URL: Optional[str] = None
DEFAULT_IMAGE_BASE: Optional[str] = None


def configure_providers(api_key: Optional[str] = None, base_url: Optional[str] = None, image_base: Optional[str] = None) -> None:
    """在应用启动时由 main 或其他入口调用以注入默认配置。

    优先级 (高 -> 低):
      1. 直接传给 create_providers 的参数
      2. 调用 configure_providers 设置的模块默认值
      3. 环境变量
    """
    global DEFAULT_GUJI_API_KEY, DEFAULT_GUJI_BASE_URL, DEFAULT_IMAGE_BASE
    if api_key is not None:
        DEFAULT_GUJI_API_KEY = api_key
    if base_url is not None:
        DEFAULT_GUJI_BASE_URL = base_url
    if image_base is not None:
        DEFAULT_IMAGE_BASE = image_base


def create_providers(api_key: Optional[str] = None, base_url: Optional[str] = None, image_base: Optional[str] = None):
    """创建 LLM / Image / TTS 提供者实例。

    支持三种配置来源（优先级见 configure_providers 注释）：直接参数 -> configure_providers 设置 -> 环境变量。
    向后兼容：若不传任何参数且没有调用 configure_providers，则行为与之前相同（从环境变量读取）。
    """
    # 优先：函数参数 -> 模块默认 -> 环境变量
    api_key = api_key or DEFAULT_GUJI_API_KEY or os.getenv("GUIJI_API_KEY", "")
    if not api_key:
        raise RuntimeError("缺少 GUIJI_API_KEY 环境变量或未在应用启动时通过 configure_providers 注入 API key")

    base_url = base_url or DEFAULT_GUJI_BASE_URL or os.getenv("GUIJI_BASE_URL", "https://api.siliconflow.cn/v1")
    image_base = image_base or DEFAULT_IMAGE_BASE or "https://api.siliconflow.cn/v1/images/generations"

    llm = SiliconFlowLLMProvider(api_key=api_key, base_url=base_url)
    image = SiliconFlowImageProvider(
        api_key=api_key,
        model=CONFIG.model.image_model,
        ipm=CONFIG.rate.image_ipm,
        base_url=image_base,
        output_dir=CONFIG.path.image_dir,
    )
    tts = GuijiTTSProvider(api_key=api_key)
    # 如需改用阿里云，请改为：
    # tts = AliyunTTSProvider(
    #     access_key_id=os.getenv("ALIBABA_CLOUD_AK", ""),
    #     access_key_secret=os.getenv("ALIBABA_CLOUD_SK", ""),
    # )
    return llm, tts, image


__all__ = ["create_providers", "configure_providers"]
