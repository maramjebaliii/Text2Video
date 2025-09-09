"""视频拼接主流程。"""
from __future__ import annotations
from pathlib import Path
from typing import List, TypedDict
from typing import List, TypedDict
import subprocess
import os

from ..config import CONFIG
from uuid import uuid4
from ..utils.text import find_font
from .clip_builder import create_video_clip


class ContentItem(TypedDict, total=False):
    text: str
    audio_path: str
    duration: float


class TitleBlock(TypedDict, total=False):
    text: str
    audio_path: str
    duration: float


class Block(TypedDict, total=False):
    image: str
    title: TitleBlock
    content: List[ContentItem]


def assemble_video_from_blocks(
    blocks: List[Block],
    *,
    resolution: tuple[int, int] | None = None,
    output_path: str | os.PathLike | None = None,
) -> Path:
    """把分块数据转为最终视频。"""
    if not blocks:
        raise ValueError("blocks 为空")
    vid_cfg = CONFIG.video
    resolution = resolution or (vid_cfg.width, vid_cfg.height)
    font_path = find_font(vid_cfg.font_path)
    if not font_path:
        print("[WARN] 未找到字体，可能出现方块字")
    # 使用配置中的持久化片段目录，按调用再细分一层 UUID，避免同一 run 内并发冲突
    from ..config import CONFIG as _CFG
    temp_dir = Path(_CFG.path.video_segments_dir) / uuid4().hex[:8]
    temp_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] 片段输出目录: {temp_dir}")
    clips: list[Path] = []
    seg_idx = 0
    for block in blocks:
        image_path = block.get("image") or ""
        title_block = block.get("title") or {}
        if title_block:
            # 直接使用上游提供的时长，若缺失应在上游修正
            title_dur = float(title_block["duration"])  
            clips.append(
                create_video_clip(
                    temp_dir,
                    seg_idx,
                    image_path,
                    title_block.get("text", ""),
                    title_block.get("audio_path", ""),
                    title_dur,
                    resolution,
                    font_path,
                    True,
                    vid_cfg.debug,
                )
            )
            seg_idx += 1
        for item in block.get("content", []) or []:
            item_dur = float(item["duration"]) 
            clips.append(
                create_video_clip(
                    temp_dir,
                    seg_idx,
                    image_path,
                    item.get("text", ""),
                    item.get("audio_path", ""),
                    item_dur,
                    resolution,
                    font_path,
                    False,
                    vid_cfg.debug,
                )
            )
            seg_idx += 1
    if not clips:
        raise RuntimeError("未生成任何片段")
    # 统一输出根目录 (按运行隔离)
    run_out_dir = CONFIG.path.output_dir
    if output_path:
        out_path = Path(output_path)
        # 若给的是目录或以分隔符结尾，则落到该目录下的默认文件名
        if (out_path.exists() and out_path.is_dir()) or str(out_path).endswith(os.sep):
            out_path = out_path / CONFIG.video.output_file.name
        # 相对路径则拼到本次运行的 output 目录，避免与工作区根目录混放
        if not out_path.is_absolute():
            out_path = Path(run_out_dir) / out_path
    else:
        # 未显式指定时，输出到本次运行目录下的默认文件名
        out_path = Path(run_out_dir) / CONFIG.video.output_file
    out_path.parent.mkdir(parents=True, exist_ok=True)
    concat_file = temp_dir / "concat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for seg in clips:
            f.write(f"file '{seg.as_posix()}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(out_path)
    ]
    print(f"[FFMPEG] 拼接输出: {out_path}")
    if vid_cfg.debug:
        print("[DEBUG] " + " ".join(cmd))
    subprocess.run(cmd, check=True if not vid_cfg.debug else False)
    print("[DONE] 视频生成 =>", out_path)
    return out_path


__all__ = ["assemble_video_from_blocks", "Block"]
