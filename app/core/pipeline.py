"""高层流水线：从 Markdown / 已有脚本构建视频用 blocks。

持久化产物说明（按生成顺序）：
1) script_raw.json              原始解析/输入脚本（title+content 原文）
2) script_optimized.json        LLM 优化（口语化）后脚本
3) script_expanded.json         每条加入 sentences: list[str]（清理拆句结果），保留原 content
4) speech/speech_manifest.json  语音清单：title + sentences + audio_files + durations + total_duration
5) speech/script_items.json     与 script_expanded.json 相同内容副本，便于靠近音频调试
6) images/illustration_prompts.json  基于原文(或优化后)生成的插画提示词
7) images/illustration_assets.json  图像生成结果（路径等）
8) blocks_merged.json           语音+插图合并后的区块（供视频拼装）
9) subtitles.json               逐句时间轴字幕（index/start/end/text/title）
10) subtitles.srt               标准 SRT 字幕文本
"""

from __future__ import annotations
import json
import os
from typing import Sequence, Any

from . import script_preprocess as sp
from .speech_batch import batch_synthesize
from .illustration import generate_illustration_prompts, build_illustration_assets
from .merge import merge_speech_and_images
from .interfaces import TTSProvider, ImageProvider, LLMProvider
from .config import CONFIG


def _fmt_time(t: float) -> str:
    ms = int(round((t - int(t)) * 1000))
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _expand_with_sentences(script_items: list[dict]) -> list[dict]:
    """为每条记录添加 sentences 字段，保留原 content。"""
    result: list[dict] = []
    for it in script_items:
        raw = it.get("content", "")
        sentences = sp.split_text_for_tts(raw)
        result.append({
            "title": it.get("title", ""),
            "content": raw,
            "sentences": sentences,
        })
    return result


def _write_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _generate_subtitles(speech_dataset: list[dict]) -> tuple[list[dict], str]:
    subtitles: list[dict] = []
    srt_lines: list[str] = []
    idx = 1
    for block in speech_dataset:
        title = block.get("title", "")
        sents = block.get("sentences", [])
        durs = block.get("durations", [])
        cur = 0.0
        for i, sent in enumerate(sents):
            dur = durs[i] if i < len(durs) else 0.0
            start = cur
            end = cur + dur
            subtitles.append({
                "index": idx,
                "title": title,
                "start": start,
                "end": end,
                "text": sent,
            })
            srt_lines.append(str(idx))
            srt_lines.append(f"{_fmt_time(start)} --> {_fmt_time(end)}")
            srt_lines.append(sent)
            srt_lines.append("")
            idx += 1
            cur = end
    return subtitles, "\n".join(srt_lines)


def build_blocks_from_markdown(
    markdown_text: str,
    *,
    llm: LLMProvider,
    tts: TTSProvider,
    image: ImageProvider,
    voice: str | None = None,
) -> list[dict]:
    """从 Markdown 文本构建带语音与插图的合并区块列表。"""
    # 确保本次运行的输出目录存在
    os.makedirs(CONFIG.path.output_dir, exist_ok=True)
    script_items = sp.markdown_to_script(markdown_text)
    _write_json(os.path.join(CONFIG.path.output_dir, "script_raw.json"), script_items)
    # 口语化优化
    script_items = sp.optimize_script_for_speech(script_items, llm)
    _write_json(os.path.join(CONFIG.path.output_dir, "script_optimized.json"), script_items)
    expanded_records = _expand_with_sentences(script_items) 
    _write_json(os.path.join(CONFIG.path.output_dir, "script_expanded.json"), expanded_records)
    # 语音批处理输入
    tts_input = [{"title": r["title"], "sentences": r["sentences"]} for r in expanded_records]
    os.makedirs(CONFIG.path.speech_dir, exist_ok=True)
    os.makedirs(CONFIG.path.image_dir, exist_ok=True)
    speech_dataset = batch_synthesize(
        tts_input,
        tts,
        out_dir=CONFIG.path.speech_dir,
        voice=voice,
        manifest_path=os.path.join(CONFIG.path.speech_dir, "speech_manifest.json"),
        reuse_manifest=True,
    )
    # 保存带 sentences 的脚本副本
    _write_json(os.path.join(CONFIG.path.speech_dir, "script_items.json"), expanded_records)
    # 插图 prompts 使用未拆句版本
    prompts = generate_illustration_prompts(json.dumps(script_items, ensure_ascii=False), llm)
    _write_json(os.path.join(CONFIG.path.image_dir, "illustration_prompts.json"), prompts)
    illustration_assets = build_illustration_assets(prompts, image)
    _write_json(os.path.join(CONFIG.path.image_dir, "illustration_assets.json"), illustration_assets)
    merged = merge_speech_and_images(speech_dataset, illustration_assets)
    subtitles, srt_text = _generate_subtitles(speech_dataset)
    _write_json(os.path.join(CONFIG.path.output_dir, "subtitles.json"), subtitles)
    with open(os.path.join(CONFIG.path.output_dir, "subtitles.srt"), "w", encoding="utf-8") as f:
        f.write(srt_text)
    _write_json(os.path.join(CONFIG.path.output_dir, "blocks_merged.json"), merged)
    return merged


def build_blocks_from_script_json(
    script_json: str,
    *,
    llm: LLMProvider,
    tts: TTSProvider,
    image: ImageProvider,
    voice: str | None = None,
) -> list[dict]:
    """从已有脚本 JSON 构建带语音与插图的合并区块列表。"""
    os.makedirs(CONFIG.path.output_dir, exist_ok=True)
    script_items = json.loads(script_json)
    _write_json(os.path.join(CONFIG.path.output_dir, "script_raw.json"), script_items)
    # 强制开启口语化优化
    script_items = sp.optimize_script_for_speech(script_items, llm)
    _write_json(os.path.join(CONFIG.path.output_dir, "script_optimized.json"), script_items)
    expanded_records = _expand_with_sentences(script_items)
    _write_json(os.path.join(CONFIG.path.output_dir, "script_expanded.json"), expanded_records)
    tts_input = [{"title": r["title"], "sentences": r["sentences"]} for r in expanded_records]
    os.makedirs(CONFIG.path.speech_dir, exist_ok=True)
    os.makedirs(CONFIG.path.image_dir, exist_ok=True)
    speech_dataset = batch_synthesize(
        tts_input,
        tts,
        out_dir=CONFIG.path.speech_dir,
        voice=voice,
        manifest_path=os.path.join(CONFIG.path.speech_dir, "speech_manifest.json"),
        reuse_manifest=True,
    )
    _write_json(os.path.join(CONFIG.path.speech_dir, "script_items.json"), expanded_records)
    prompts = generate_illustration_prompts(script_json, llm)
    _write_json(os.path.join(CONFIG.path.image_dir, "illustration_prompts.json"), prompts)
    illustration_assets = build_illustration_assets(prompts, image)
    _write_json(os.path.join(CONFIG.path.image_dir, "illustration_assets.json"), illustration_assets)
    merged = merge_speech_and_images(speech_dataset, illustration_assets)
    subtitles, srt_text = _generate_subtitles(speech_dataset)
    _write_json(os.path.join(CONFIG.path.output_dir, "subtitles.json"), subtitles)
    with open(os.path.join(CONFIG.path.output_dir, "subtitles.srt"), "w", encoding="utf-8") as f:
        f.write(srt_text)
    _write_json(os.path.join(CONFIG.path.output_dir, "blocks_merged.json"), merged)
    return merged
