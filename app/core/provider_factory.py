"""Provider 工厂：集中创建 LLM / Image / TTS 提供者实例。

从环境变量读取：
- GUIJI_API_KEY（必填）
- GUIJI_BASE_URL（可选，默认 https://api.siliconflow.cn/v1）
"""
from __future__ import annotations

import os
from app.core.config import CONFIG
from app.providers import (
    GuijiTTSProvider,
    AliyunTTSProvider,
    SiliconFlowImageProvider,
    SiliconFlowLLMProvider,
)


def create_providers():
    api_key = os.getenv("GUIJI_API_KEY", "")
    if not api_key:
        raise RuntimeError("缺少 GUIJI_API_KEY 环境变量 (请在 .env 中设置)")
    base_url = os.getenv("GUIJI_BASE_URL", "https://api.siliconflow.cn/v1")
    image_base = "https://api.siliconflow.cn/v1/images/generations"

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


__all__ = ["create_providers"]
