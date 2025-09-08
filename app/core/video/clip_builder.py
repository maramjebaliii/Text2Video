"""单片段视频生成。

职责说明:
1. 创建字幕面板(透明 PNG 覆盖层)
2. (可选) 读取音频并探测时长 (由 ffprobe 完成, 在 audio_probe.probe_audio_duration 内)
3. 组装 ffmpeg 命令: 背景图(循环) + 覆盖层 + 音频 -> 输出单个 mp4 片段
4. 若无音频则使用 fallback_duration 作为片段时长

设计要点:
- 不做复杂的异常处理: 失败直接抛出, 由上层汇总
- overlay 通过 filter_complex 将字幕面板叠加在缩放后的背景图上
- 使用 "-shortest" 让视频长度随音频截断, 避免静止尾巴

可改进方向(暂未实现):
- 支持淡入淡出 / Ken Burns 效果
- 自动根据文本长度微调字体大小
- 音频起止空白裁剪
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
import subprocess
from .caption_panel import create_caption_panel
from .audio_probe import probe_audio_duration


def create_video_clip(
    work_dir: Path,
    segment_index: int,
    bg_image: str,
    caption_text: str,
    audio_file: str,
    fallback_duration: float,
    resolution: Tuple[int, int],
    font_file: Optional[str],
    is_title: bool,
    debug: bool = False,
) -> Path:
    """生成单个 mp4 片段。

    参数:
        work_dir: 临时工作目录 (写出 overlay 与片段 mp4)
        segment_index: 片段序号 (用于命名)
        bg_image: 背景图片路径 (会被缩放到目标分辨率)
        caption_text: 要渲染到字幕面板的文字
        audio_file: 可选音频文件 (存在则对齐时长, 不存在用 fallback_duration)
        fallback_duration: 无音频时的回退时长 (秒)
        resolution: (width, height)
        font_file: 字体路径 (None 时由 PIL 默认字体, 可能不支持中文)
        is_title: 是否标题块 (影响字体比例 / 面板透明度等)
        debug: 调试模式 (打印命令, ffmpeg 出错不 raise)

    返回:
        生成的 mp4 文件路径
    """
    width, height = resolution
    clip_id = f"seg_{segment_index:04d}"
    overlay_image_path = work_dir / f"{clip_id}_overlay.png"
    # 先生成字幕面板 PNG (透明背景 + 半透明遮罩 + 文本)
    panel_image = create_caption_panel(
        text=caption_text,
        resolution=resolution,
        font_file=font_file,
        top=is_title,
        font_ratio=0.065 if is_title else 0.045,
        bg_alpha=150 if is_title else 170,
    )
    panel_image.save(overlay_image_path)
    # 判断音频是否存在, 并在存在时尝试探测真实时长
    has_audio = bool(audio_file and Path(audio_file).exists())
    audio_duration = probe_audio_duration(audio_file) if has_audio else None
    # 若探测失败 (None) 则使用 fallback_duration
    duration = audio_duration or fallback_duration
    if duration <= 0:
        duration = fallback_duration if fallback_duration > 0 else 2.0
    out_mp4_path = work_dir / f"{clip_id}.mp4"
    # 输入顺序: 背景图(循环) + 覆盖字幕图 + (可选)音频
    ffmpeg_inputs = ["-loop", "1", "-i", bg_image, "-i", str(overlay_image_path)]
    if has_audio:
        ffmpeg_inputs += ["-i", audio_file]
    # filter: 缩放背景 -> overlay 叠加字幕 -> 输出标记为 vout
    filter_complex = f"[0:v]scale={width}:{height},setsar=1[bg];[bg][1:v]overlay=0:0:format=auto[vout]"
    ffmpeg_cmd = ["ffmpeg", "-y", *ffmpeg_inputs, "-filter_complex", filter_complex, "-map", "[vout]"]
    if has_audio:
        # -shortest 让视频在任一流结束时终止 (通常是音频先结束)
        ffmpeg_cmd += ["-map", "2:a", "-c:a", "aac", "-shortest"]
    else:
        # 无音频, 用 -t 控制时长
        ffmpeg_cmd += ["-t", f"{duration:.3f}"]
    ffmpeg_cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "23", str(out_mp4_path)]
    print(f"[FFMPEG] 生成片段 {clip_id} (≈{duration:.2f}s, audio={'Y' if has_audio else 'N'})")
    if debug:
        print('[DEBUG] ' + ' '.join(ffmpeg_cmd))
    subprocess.run(ffmpeg_cmd, check=True if not debug else False)
    if not out_mp4_path.exists():
        raise RuntimeError(f"片段未生成: {out_mp4_path}")
    return out_mp4_path
