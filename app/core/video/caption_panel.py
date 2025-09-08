"""字幕面板生成。"""
from __future__ import annotations
from typing import Optional, Tuple
from pathlib import Path
import os
from PIL import Image, ImageDraw, ImageFont
from ..utils.text import wrap_text, measure_text_width


def create_caption_panel(
    text: str,
    resolution: Tuple[int, int],
    font_file: Optional[str],
    font_ratio: float = 0.045,
    padding: int = 32,
    line_spacing_ratio: float = 1.3,
    bg_alpha: int = 170,
    top: bool = False,
):
    """生成字幕面板图层。"""
    width, height = resolution
    img = Image.new("RGBA", resolution, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    base_font_size = max(16, int(height * font_ratio))
    if font_file and Path(font_file).exists():
        try:
            font = ImageFont.truetype(font_file, base_font_size)
        except Exception:
            font = ImageFont.load_default()
    else:
        try:
            font = ImageFont.truetype(font="arial.ttf", size=base_font_size) if os.name == "nt" else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
    max_text_width = width - padding * 2
    lines = wrap_text(draw, text, font, max_text_width)
    line_height = int(base_font_size * line_spacing_ratio)
    panel_height = line_height * len(lines) + padding * 2
    y0 = 0 if top else (height - panel_height)
    rect = Image.new("RGBA", (width, panel_height), (0, 0, 0, bg_alpha))
    img.paste(rect, (0, y0))
    y_text = y0 + padding
    for line in lines:
        w = measure_text_width(draw, line, font)
        x = (width - w) // 2
        draw.text((x, y_text), line, font=font, fill=(255, 255, 255, 255))
        y_text += line_height
    return img
