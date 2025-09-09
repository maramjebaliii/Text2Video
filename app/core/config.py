"""统一配置加载。

后续可扩展：读取 .env / 命令行 / 数据库。
当前仅提供简单默认值与环境变量读取辅助。
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from uuid import uuid4
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
    # 为每次运行生成一个短 UUID（或可通过环境变量 RUN_ID 指定），用于隔离并发输出
    run_id: str = field(default_factory=lambda: os.getenv("RUN_ID") or uuid4().hex[:8])
    # 以下路径在 __post_init__ 中基于 run_id 构建
    output_dir: str = ""
    speech_dir: str = ""
    image_dir: str = ""
    video_segments_dir: str = ""  # 保存中间视频片段/overlay 资源

    def __post_init__(self) -> None:
        # 统一输出根目录: <base>/output/<run_id>
        self.output_dir = os.path.join(self.base_dir, "output", self.run_id)
        self.speech_dir = os.path.join(self.output_dir, "speech")
        self.image_dir = os.path.join(self.output_dir, "images")
        self.video_segments_dir = os.path.join(self.output_dir, "segments")


@dataclass(slots=True)
class VideoConfig:
    """视频相关配置。"""
    width: int = int(os.getenv("VIDEO_WIDTH", "1280"))
    height: int = int(os.getenv("VIDEO_HEIGHT", "720"))
    debug: bool = os.getenv("VIDEO_DEBUG", "0") == "1"
    font_path: str | None = os.getenv("VIDEO_FONT_PATH") or None
    # 默认只给文件名，实际落盘位置在拼装器中与 PathConfig.output_dir 组合
    output_file: Path = Path(os.getenv("VIDEO_OUTPUT", "final_video.mp4"))
    # ffmpeg 日志控制
    ffmpeg_log_level: str = os.getenv("FFMPEG_LOGLEVEL", "error")  # quiet|panic|fatal|error|warning|info|verbose|debug
    ffmpeg_hide_banner: bool = os.getenv("FFMPEG_HIDE_BANNER", "1") == "1"
    ffmpeg_no_stats: bool = os.getenv("FFMPEG_NOSTATS", "1") == "1"


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

# 可选: 同一进程内的多次并发/多请求，若希望为每次请求隔离输出目录，
# 可在调用前设置新的 run_id。
def set_run_id(run_id: str | None = None) -> None:
    """重设当前运行的 run_id，并重建相关输出目录路径。

    用法:
        from app.core.config import set_run_id
        set_run_id()  # 随机
        # 或者 set_run_id("abcd1234")
    """
    rid = run_id or uuid4().hex[:8]
    base = CONFIG.path.base_dir
    CONFIG.path = PathConfig(base_dir=base, run_id=rid)
