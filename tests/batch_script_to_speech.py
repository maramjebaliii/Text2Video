"""
批量将脚本结构(title + sentences)转语音并返回带音频路径的新结构。
"""
import hashlib
import os

from text2speech import aliyun_text2speech, guiji_text2speech
import os
import time
from uuid import uuid4
from typing import Optional
import hashlib
from pydub import AudioSegment

from dashscope.audio.tts_v2 import AudioFormat


def _gen_filename(text: str, prefix: str = "clip") -> str:
    h = hashlib.md5(text.strip().encode('utf-8')).hexdigest()[:10]
    head = ''.join(c for c in text.strip()[:8] if c.isalnum()) or 'clip'
    return f"{prefix}_{head}_{h}"

def _get_duration(path: str) -> Optional[float]:
    try:
        audio = AudioSegment.from_file(path)
        return len(audio) / 1000.0
    except Exception:
        return None

def _batch_script_to_speech_common(
    script_items: list,
    synth_func,
    out_dir: str,
    filename_prefix: str = "clip",
    reuse_cache: bool = True,
) -> list:
    """
    通用批量语音合成逻辑，synth_func(text) -> audio_path
    """
    if not isinstance(script_items, list):
        raise TypeError("script_items 必须是 list")
    if not script_items:
        return []
    os.makedirs(out_dir, exist_ok=True)
    cache: dict[str, tuple[str, Optional[float]]] = {}
    def _synth(text: str) -> tuple[str, Optional[float]]:
        key = text.strip()
        if reuse_cache and key in cache:
            return cache[key]
        filename = _gen_filename(key, prefix=filename_prefix)
        target_path = os.path.abspath(os.path.join(out_dir, filename + '.mp3'))
        if reuse_cache and os.path.exists(target_path):
            duration = _get_duration(target_path)
            cache[key] = (target_path, duration)
            return cache[key]
        path = synth_func(key, filename=filename)
        duration = _get_duration(path)
        cache[key] = (path, duration)
        return cache[key]
    result = []
    for item in script_items:
        title_text = item.get('title', '').strip()
        sentences = item.get('content', []) or []
        if title_text:
            title_path, title_dur = _synth(title_text)
            title_entry = {"text": title_text, "audio_path": title_path, "duration": title_dur}
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
                "duration": sent_dur,
            })
        result.append({
            "title": title_entry,
            "content": content_entries
        })
    return result

def batch_script_to_aliyun_speech(
    script_items: list,
    dashtoken: str,
    out_dir: str = "audio_output",
    model: str = "cosyvoice-v1",
    voice: str = "longxiaochun",
    audio_format: AudioFormat = AudioFormat.MP3_24000HZ_MONO_256KBPS,
    reuse_cache: bool = True,
) -> list:
    """批量将脚本结构(title + sentences)转语音并返回带音频路径的新结构。

    输入示例(script_items)：
    [
        {"title": "云计算简介", "content": ["句子1", "句子2"]},
        ...
    ]

    返回：
    [
        {
          "title": {"text": "云计算简介", "audio_path": "..."},
          "content": [
             {"text": "句子1", "audio_path": "..."},
             {"text": "句子2", "audio_path": "..."}
          ]
        }, ...
    ]
    """
    if not isinstance(script_items, list):
        raise TypeError("script_items 必须是 list")
    if not script_items:
        return []

    def synth_func(text, filename):
        return aliyun_text2speech(
            text,
            dashtoken=dashtoken,
            out_dir=out_dir,
            filename=filename,
            model=model,
            voice=voice,
            audio_format=audio_format,
        )
    return _batch_script_to_speech_common(
        script_items,
        synth_func,
        out_dir,
        filename_prefix="clip",
        reuse_cache=reuse_cache,
    )


# 基于 guiji_text2speech 的批量语音转换
def batch_script_to_guiji_speech(
    script_items: list,
    api_key: str,
    out_dir: str = "audio_output",
    model: str = "FunAudioLLM/CosyVoice2-0.5B",
    voice: str = "david",
    response_format: str = "mp3",
    sample_rate: int = 44100,
    speed: float = 1.0,
    gain: float = 0,
    reuse_cache: bool = True,
) -> list:
    def synth_func(text, filename):
        # 传入批处理统一生成的 filename，避免之前固定文件名覆盖
        return guiji_text2speech(
            api_key=api_key,
            text=text,
            model=model,
            voice=voice,
            out_dir=out_dir,
            filename=filename,  
            response_format=response_format,
            sample_rate=sample_rate,
            speed=speed,
            gain=gain,
        )
    return _batch_script_to_speech_common(
        script_items,
        synth_func,
        out_dir,
        filename_prefix="guiji",
        reuse_cache=reuse_cache,
    )





if __name__ == '__main__':

    # 示例文本，可替换为你的 Markdown 内容
    markdown_text = """
# 云计算简介

云计算是一种通过互联网按需提供计算资源（例如服务器、存储、数据库、网络和软件）的方法。
它使企业可以更灵活地扩展资源并降低基础设施成本。

## 什么是云计算？

云计算将传统本地部署的计算资源迁移到远程数据中心，由云服务提供商管理和维护。
用户可以根据需要申请或释放资源，而无需关心底层硬件的运维。

## 云计算的主要类型

- 公有云：由第三方云服务提供商向多个租户提供服务。
- 私有云：为单个组织专属使用，通常部署在防火墙后面。
- 混合云：结合公有云与私有云的优势，支持在不同环境之间迁移工作负载。

## 云计算的优点

- 弹性伸缩：根据负载动态调整资源，避免资源浪费。
- 成本优化：按需付费，减少初始投资和运维成本。
- 高可用性：多可用区和灾备方案提升业务连续性。

了解这些基本概念后，你就可以开始评估云服务提供商并设计适合自己业务的云架构了。
"""

    from prepare_script_for_recording import prepare_script_for_recording
    from md2script import md2script
    from openai import OpenAI
    from split_text_for_tts import split_text_for_tts
    import json
    from dotenv import load_dotenv
    load_dotenv()  # 从 .env 文件加载环境变量

    script_json = md2script(markdown_text)
    client = OpenAI(api_key=os.getenv('API_KEY'), base_url=os.getenv('BASE_URL'))
    optimized = prepare_script_for_recording(script_json, client)

    script_data = json.loads(optimized)
    for item in script_data:
        content = item['content']
        sentences = split_text_for_tts(content)
        item['content'] = sentences
    optimized_split = json.dumps(script_data, ensure_ascii=False, indent=4)
    print('拆分完成：')
    print(optimized_split)

    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'optimized_split_script.json'), 'w', encoding='utf-8') as f:
        f.write(optimized_split)

    # 获取 token（支持 DASHTOKEN 或 API_KEY）
    dashtoken = os.getenv('DASHTOKEN') or os.getenv('API_KEY')
    if not dashtoken:
        raise ValueError("请设置环境变量 DASHTOKEN 或 API_KEY 为 DashScope Token。")

    # first_sentence = script_data[0]['content'][0]
    # print('合成第一条语音：', first_sentence)
    # audio_path = text_to_speech(first_sentence, dashtoken=dashtoken)
    # print('合成成功，保存到：', audio_path)

    # 批量合成全部标题与句子
    print('开始批量合成全部标题与句子...')
    speech_dataset = batch_script_to_aliyun_speech(script_data, dashtoken=dashtoken)
    print('批量合成完成：')
    import json as _json
    print(_json.dumps(speech_dataset, ensure_ascii=False, indent=4))

    # 保存结果 JSON（可选）
    with open(os.path.join(output_dir, 'speech_dataset.json'), 'w', encoding='utf-8') as f:
        f.write(_json.dumps(speech_dataset, ensure_ascii=False, indent=4))
    print('数据集已保存 ->', os.path.join(output_dir, 'speech_dataset.json'))


    # 基于 guiji 的批量语音合成演示
    guiji_key = os.getenv('GUIJI_KEY')
    if not guiji_key:
        print('未设置 GUIJI_KEY，跳过 guiji 批量语音合成演示。')
    else:
        print('开始基于 guiji 的批量语音合成...')
        guiji_dataset = batch_script_to_guiji_speech(
            script_data,
            api_key=guiji_key,
            out_dir=output_dir,
            model="FunAudioLLM/CosyVoice2-0.5B",
            voice="alex",
            response_format="mp3",
            sample_rate=44100,
            speed=1.0,
            gain=0,
        )
        print('guiji 批量合成完成：')
        print(_json.dumps(guiji_dataset, ensure_ascii=False, indent=4))
        with open(os.path.join(output_dir, 'guiji_speech_dataset.json'), 'w', encoding='utf-8') as f:
            f.write(_json.dumps(guiji_dataset, ensure_ascii=False, indent=4))
        print('guiji 数据集已保存 ->', os.path.join(output_dir, 'guiji_speech_dataset.json'))

