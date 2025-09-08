"""文本与字体工具。"""
from __future__ import annotations
from typing import List, Optional
from pathlib import Path
import os
from PIL import ImageDraw, ImageFont


def find_font(user_font: Optional[str] = None) -> Optional[str]:
    """返回可用字体路径。"""
    if user_font and Path(user_font).is_file():
        return user_font
    candidates = [
        r"C:\\Windows\\Fonts\\msyh.ttc",
        r"C:\\Windows\\Fonts\\msyh.ttf",
        r"C:\\Windows\\Fonts\\simhei.ttf",
        r"C:\\Windows\\Fonts\\simkai.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def measure_text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    """测量文本像素宽度。"""
    if not text:
        return 0
    if hasattr(draw, "textlength"):
        try:
            return int(draw.textlength(text, font=font))
        except Exception:
            pass
    if hasattr(draw, "textbbox"):
        try:
            left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
            return right - left
        except Exception:
            pass
    if hasattr(draw, "textsize"):
        try:
            w, _ = draw.textsize(text, font=font)
            return int(w)
        except Exception:
            return len(text) * 10
    return len(text) * 10


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    """按像素宽度换行。"""
    lines: List[str] = []
    cur = ""
    for ch in text:
        test = cur + ch
        w = measure_text_width(draw, test, font)
        if w <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines
