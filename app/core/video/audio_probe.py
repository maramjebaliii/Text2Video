"""音频时长探测。"""
from __future__ import annotations
from typing import Optional
from pathlib import Path
import subprocess


def probe_audio_duration(audio_file: str) -> Optional[float]:
    """ffprobe 探测音频时长。"""
    if not audio_file or not Path(audio_file).exists():
        return None
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_file
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
        return float(out)
    except Exception:
        return None
