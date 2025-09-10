# """阿里云 DashScope TTS 提供者实现。"""
# from __future__ import annotations

# import os
# import time
# from uuid import uuid4
# from typing import Optional

# import dashscope
# from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat

# __all__ = ["AliyunTTSProvider"]


# class AliyunTTSProvider:
#     """阿里云 DashScope 文本转语音提供者封装。"""

#     def __init__(
#         self,
#         dashtoken: str,
#         model: str = "cosyvoice-v1",
#         default_voice: str = "longxiaochun",
#     ) -> None:
#         """初始化 Provider。

#         参数:
#             dashtoken: DashScope API Key
#             model: 模型名称
#             default_voice: 默认发音人
#         """
#         self.dashtoken = dashtoken
#         self.model = model
#         self.default_voice = default_voice

#     def synthesize(
#         self,
#         text: str,
#         *,
#         voice: str | None = None,
#         out_dir: str = "audio_output",
#         filename: Optional[str] = None,
#         audio_format: AudioFormat = AudioFormat.MP3_24000HZ_MONO_256KBPS,
#     ) -> str:
#         """合成单条文本为 MP3 文件并返回绝对路径。"""
#         if not text.strip():
#             raise ValueError("text 不能为空")
#         os.makedirs(out_dir, exist_ok=True)
#         base = filename or f"speech_{int(time.time())}_{uuid4().hex[:8]}"
#         dashscope.api_key = self.dashtoken
#         synth = SpeechSynthesizer(
#             model=self.model,
#             voice=voice or self.default_voice,
#             format=audio_format,
#         )
#         audio_bytes = synth.call(text)
#         if not audio_bytes:
#             raise RuntimeError("语音合成失败，未返回数据")
#         if isinstance(audio_bytes, str):
#             audio_bytes = audio_bytes.encode("utf-8")
#         out_abs = os.path.abspath(os.path.join(out_dir, base + ".mp3"))
#         if os.path.exists(out_abs):  # 少量冲突情形加后缀
#             out_abs = os.path.abspath(os.path.join(out_dir, base + "_1.mp3"))
#         with open(out_abs, "wb") as f:
#             f.write(audio_bytes)
#         return out_abs
