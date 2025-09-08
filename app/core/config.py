"""统一配置加载。

后续可扩展：读取 .env / 命令行 / 数据库。
当前仅提供简单默认值与环境变量读取辅助。
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ModelConfig:
    chat_model: str = os.getenv("GUIJI_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    tts_model_guiji: str = os.getenv("GUIJI_TTS_MODEL", "FunAudioLLM/CosyVoice2-0.5B")
    tts_model_aliyun: str = os.getenv("ALIYUN_TTS_MODEL", "cosyvoice-v1")
    image_model: str = os.getenv("GUIJI_IMAGE_MODEL", "Kwai-Kolors/Kolors")


@dataclass(slots=True)
class PathConfig:
    base_dir: str = os.getcwd()
    output_dir: str = os.path.join(base_dir, "output")
    speech_dir: str = os.path.join(output_dir, "speech")
    image_dir: str = os.path.join(output_dir, "images")
    video_segments_dir: str = os.path.join(output_dir, "segments")  # 保存中间视频片段/overlay 资源


@dataclass(slots=True)
class VideoConfig:
    """视频相关配置。"""
    width: int = int(os.getenv("VIDEO_WIDTH", "1280"))
    height: int = int(os.getenv("VIDEO_HEIGHT", "720"))
    debug: bool = os.getenv("VIDEO_DEBUG", "0") == "1"
    font_path: str | None = os.getenv("VIDEO_FONT_PATH") or None
    output_file: Path = Path(os.getenv("VIDEO_OUTPUT", "output/final_video.mp4"))


@dataclass(slots=True)
class RateConfig:
    image_ipm: int = int(os.getenv("IMAGE_IPM", "2"))


@dataclass(slots=True)
class AppConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    path: PathConfig = field(default_factory=PathConfig)
    rate: RateConfig = field(default_factory=RateConfig)
    video: VideoConfig = field(default_factory=VideoConfig)


CONFIG = AppConfig()
