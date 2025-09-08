"""Guiji / SiliconFlow TTS 提供者实现。"""
from __future__ import annotations

import os
import time
from uuid import uuid4
from typing import Optional

import requests

__all__ = ["GuijiTTSProvider"]


class GuijiTTSProvider:
    """Guiji (SiliconFlow) 文本转语音提供者封装。"""

    def __init__(
        self,
        api_key: str,
        model: str = "FunAudioLLM/CosyVoice2-0.5B",
        default_voice: str = "david",
        timeout: int = 120,
    ) -> None:
        """初始化 Provider。

        参数:
            api_key: 平台 API Key
            model: 语音模型名称
            default_voice: 默认发音人
            timeout: 请求超时时间(秒)
        """
        self.api_key = api_key
        self.model = model
        self.default_voice = default_voice
        self.timeout = timeout

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        out_dir: str = "audio_output",
        filename: Optional[str] = None,
        response_format: str = "mp3",
        sample_rate: int = 44100,
        stream: bool = False,
        speed: float = 1.0,
        gain: float = 0.0,
    ) -> str:
        """合成单条文本语音并保存为本地文件，返回绝对路径。"""
        if not text.strip():
            raise ValueError("text 不能为空")
        os.makedirs(out_dir, exist_ok=True)
        base_name = filename or f"guiji_{int(time.time())}_{uuid4().hex[:8]}"
        url = "https://api.siliconflow.cn/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": text,
            "response_format": response_format,
            "sample_rate": sample_rate,
            "stream": stream,
            "speed": speed,
            "gain": gain,
        }
        use_voice = voice or self.default_voice
        if use_voice:
            payload["voice"] = f"{self.model}:{use_voice}"
        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(
                f"guiji TTS 请求失败: {resp.status_code} {resp.text[:200]}"
            )
        audio_path = os.path.abspath(os.path.join(out_dir, f"{base_name}.{response_format}"))
        if os.path.exists(audio_path):  # 极少数情况下名称冲突
            audio_path = os.path.abspath(
                os.path.join(out_dir, f"{base_name}_{uuid4().hex[:6]}.{response_format}")
            )
        with open(audio_path, "wb") as f:
            f.write(resp.content)
        return audio_path
