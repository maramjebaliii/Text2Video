"""视频拼接主流程。"""
from __future__ import annotations
from pathlib import Path
from typing import List, TypedDict
from typing import List, TypedDict
import subprocess
import os

from ..config import CONFIG
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
    # 使用配置中的持久化片段目录，避免临时目录丢失调试信息
    from ..config import CONFIG as _CFG
    temp_dir = Path(_CFG.path.video_segments_dir)
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
    if output_path:
        out_path = Path(output_path)
        if (out_path.exists() and out_path.is_dir()) or str(out_path).endswith(os.sep):
            out_path = out_path / CONFIG.video.output_file.name
    else:
        out_path = CONFIG.video.output_file
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
