"""批量语音合成逻辑，与具体 TTS Provider 解耦。

改进: 针对音频时长(duration)的探测只在第一次需要时进行，后续运行复用持久化缓存，避免重复解析 mp3。
缓存策略:
1. 运行开始时尝试读取 ``out_dir/duration_cache.json`` (结构 {"<abs_path>": duration(float|null)})
2. 合成/命中文件后优先查缓存；若存在即直接返回，不再用 pydub 重新探测
3. 若缓存无且需要 -> 进行一次探测并写入内存
4. 结束后写回文件 (原子写)
"""
from __future__ import annotations
import os
import hashlib
import json
from uuid import uuid4
from pathlib import Path
from typing import Optional
from pydub import AudioSegment
from .interfaces import TTSProvider


def _hash_key(text: str) -> str:
    """生成文本内容的短哈希。"""
    return hashlib.md5(text.strip().encode('utf-8')).hexdigest()[:10]


def _derive_filename(text: str, prefix: str, *, unique: bool) -> str:
        """生成音频文件名。

        目标:
        1. 可选唯一: 避免同一文本覆盖 (unique=True, 默认)
        2. 可选确定: 支持跨运行复用缓存 (unique=False)

        结构:
            - unique=True  -> <prefix>_<hash>_<rand6>
            - unique=False -> <prefix>_<hash>
        """
        h = _hash_key(text)
        if unique:
                return f"{prefix}_{h}_{uuid4().hex[:6]}"
        return f"{prefix}_{h}"


def _probe_duration(path: str) -> Optional[float]:
    """探测音频文件时长（秒）。失败返回 None，由调用方再做估算兜底。"""
    try:
        audio = AudioSegment.from_file(path)
        return len(audio) / 1000.0
    except Exception:
        return None


def batch_synthesize(
    script_items: list[dict],
    provider: TTSProvider,
    out_dir: str,
    voice: str | None = None,
    filename_prefix: str = "clip",
    reuse_cache: bool = True,
    persist_duration: bool = True,
    duration_cache_filename: str = "duration_cache.json",
    manifest_path: str | None = None,
    reuse_manifest: bool = True,
    unique_filenames: bool = True,
) -> list[dict]:
    """批量合成脚本项语音并返回包含音频路径与时长的结构 (持久化)。"""
    if not isinstance(script_items, list):
        raise TypeError("script_items 必须是 list")
    if not script_items:
        return []
    os.makedirs(out_dir, exist_ok=True)

    # 若存在可复用的 manifest 则直接返回
    if manifest_path and reuse_manifest and Path(manifest_path).exists():
        try:
            cached_dataset = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
            # 简单校验字段结构
            if isinstance(cached_dataset, list):
                return cached_dataset  # 直接复用
        except Exception:
            pass  # 读取失败则继续正常流程
    cache: dict[str, tuple[str, Optional[float]]] = {}

    # 持久化缓存加载 (音频绝对路径 -> duration)
    duration_cache_path = Path(out_dir) / duration_cache_filename
    duration_cache: dict[str, Optional[float]] = {}
    if persist_duration and duration_cache_path.exists():
        try:
            duration_cache = json.loads(duration_cache_path.read_text(encoding="utf-8"))  # type: ignore[assignment]
        except Exception:
            duration_cache = {}

    def _estimate_duration(text: str, speed: float = 1.0) -> float:
        """根据中文/混合文本长度粗估时长（秒）。
        经验系数: 每个汉字/全角 ≈0.28s, 英文 token/词粗略按 0.18s 处理，再除以语速。
        """
        if not text:
            return 1.0
        cn_len = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        others = len(text) - cn_len
        base = cn_len * 0.28 + others * 0.18
        est = base / max(speed, 0.5)
        return max(est, 0.6)

    def _synth(text: str) -> tuple[str, float]:
        key = text.strip()
        if reuse_cache and key in cache:
            path_cached, dur_cached = cache[key]
            if dur_cached is None:
                dur_cached = _estimate_duration(key)
            return path_cached, dur_cached
        filename = _derive_filename(key, filename_prefix, unique=unique_filenames)
        target = os.path.abspath(os.path.join(out_dir, filename + '.mp3'))
        if reuse_cache and os.path.exists(target):
            if persist_duration and target in duration_cache:
                dur_hit = duration_cache[target]
                if dur_hit is None:
                    dur_hit = _estimate_duration(key)
                cache[key] = (target, dur_hit)
                return cache[key]
            dur = _probe_duration(target)
            if persist_duration:
                duration_cache[target] = dur
            if dur is None:
                dur = _estimate_duration(key)
            cache[key] = (target, dur)
            return target, dur
        path = provider.synthesize(key, voice=voice, filename=filename, out_dir=out_dir)
        if persist_duration and path in duration_cache:
            dur = duration_cache[path]
        else:
            dur = _probe_duration(path)
            if persist_duration:
                duration_cache[path] = dur
        if dur is None:
            dur = _estimate_duration(key)
        cache[key] = (path, dur)
        return path, dur

    result = []
    for item in script_items:
        title_text = item.get('title', '').strip()
        sentences = item.get('sentences', []) or []
        if title_text:
            title_path, title_dur = _synth(title_text)
            title_entry = {"text": title_text, "audio_path": title_path, "duration": float(title_dur)}
        else:
            title_entry = {"text": "", "audio_path": None, "duration": None}
        content_entries = []
        for sent in sentences:
            sent_str = str(sent).strip()
            if not sent_str:
                continue
            sent_path, sent_dur = _synth(sent_str)
            content_entries.append({
                "text": sent_str,
                "audio_path": sent_path,
                "duration": float(sent_dur),
            })
        result.append({
            "title": title_entry,
            "content": content_entries
        })
    # 写回持久化缓存 (原子写)
    if persist_duration:
        try:
            tmp_file = duration_cache_path.with_suffix(".tmp")
            tmp_file.write_text(json.dumps(duration_cache, ensure_ascii=False), encoding="utf-8")
            tmp_file.replace(duration_cache_path)
        except Exception:
            pass
    # 写出 manifest
    if manifest_path:
        try:
            Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
            tmp_manifest = Path(manifest_path + ".tmp")
            tmp_manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_manifest.replace(Path(manifest_path))
        except Exception:
            pass
    return result
