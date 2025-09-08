"""数据合并：语音数据 + 插图数据 -> 视频块结构。"""
from __future__ import annotations
from typing import List, Dict


def merge_speech_and_images(speech_data: list, illustration_data: list) -> list:
    """按索引合并语音数据与插图数据生成最终区块列表。"""
    merged = []
    for i in range(min(len(speech_data), len(illustration_data))):
        merged.append({
            "title": speech_data[i]["title"],
            "image": illustration_data[i]["image_path"],
            "content": speech_data[i]["content"],
        })
    return merged
