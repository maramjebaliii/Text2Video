import requests
import time
from uuid import uuid4
from typing import Optional

def guiji_text2speech(
    api_key: str,         # API密钥，格式为 Bearer <your api key>
    text: str,            # 输入文本
    model: str = "FunAudioLLM/CosyVoice2-0.5B",  # 语音合成模型名称
    voice: str = "david",    # 只传发音人名，如 "david"
    out_dir: str = "audio_output",   # 输出目录
    filename: Optional[str] = None,   # 可选：外部指定文件名(不含扩展名)，便于缓存/去重
    response_format: str = "mp3",  # 音频输出格式，可选 mp3, opus, wav, pcm
    sample_rate: int = 44100,       # 音频采样率
    stream: bool = False,           # 是否流式输出
    speed: float = 1.0,             # 语速 0.25~4.0
    gain: float = 0                 # 音量增益 -10~10
) -> str:
    """调用 SiliconFlow 文本转语音 API 并落盘，返回音频文件绝对路径。

    """
    if not text or not text.strip():
        raise ValueError("text 不能为空")
    os.makedirs(out_dir, exist_ok=True)

    # 生成文件名（不含扩展名）
    if filename:
        base_name = filename
    else:
        base_name = f"guiji_{int(time.time())}_{uuid4().hex[:8]}"

    url = "https://api.siliconflow.cn/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": text,
        "response_format": response_format,
        "sample_rate": sample_rate,
        "stream": stream,
        "speed": speed,
        "gain": gain,
    }
    if voice:
        payload["voice"] = f"{model}:{voice}"  # API 需要完整格式

    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"guiji_text2speech 调用失败：{resp.status_code} {resp.text[:200]}")

    audio_path = os.path.abspath(os.path.join(out_dir, f"{base_name}.{response_format}"))

    # 如果文件已存在（极少数 hash 碰撞或并发写入），追加 uuid 重新生成一次
    if os.path.exists(audio_path):
        base_name = f"{base_name}_{uuid4().hex[:6]}"
        audio_path = os.path.abspath(os.path.join(out_dir, f"{base_name}.{response_format}"))

    with open(audio_path, "wb") as f:
        f.write(resp.content)
    return audio_path


import os
import time
from uuid import uuid4
from typing import Optional
import hashlib

import dashscope  # 全局设置 api_key 使用
from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat



def aliyun_text2speech(
    text: str,
    dashtoken: str,
    out_dir: str = "audio_output",
    filename: Optional[str] = None,
    model: str = "cosyvoice-v1",
    voice: str = "longxiaochun",
    audio_format: AudioFormat = AudioFormat.MP3_24000HZ_MONO_256KBPS,
) -> str:
    """将文本合成语音并保存为 mp3，返回绝对路径。

    Parameters
    ----------
    text : str
        待合成文本
    dashtoken : str
        DashScope API Key
    out_dir : str
        输出目录
    filename : Optional[str]
        输出文件名(不含扩展名)，为空自动生成
    model : str
        TTS 模型名
    voice : str
        发音人
    audio_format : AudioFormat
        输出音频格式(采样率/码率), 这里使用 SDK Enum
    """
    if not text or not text.strip():
        raise ValueError("输入文本为空。")
    if not dashtoken or not dashtoken.strip():
        raise ValueError("必须提供 DashScope Token(dashtoken)。")

    os.makedirs(out_dir, exist_ok=True)

    base = os.path.splitext(filename)[0] if filename else f"speech_{int(time.time())}_{uuid4().hex[:8]}"
    out_abs = os.path.abspath(os.path.join(out_dir, base + ".mp3"))

    # 设置全局 api_key（SDK 内部使用）
    dashscope.api_key = dashtoken

    synth = SpeechSynthesizer(
        model=model,
        voice=voice,
        format=audio_format,
    )

    audio_bytes = synth.call(text)
    if not audio_bytes:
        raise RuntimeError("合成失败，未获得音频数据。")

    if isinstance(audio_bytes, str):  # 容错处理
        audio_bytes = audio_bytes.encode("utf-8")

    with open(out_abs, "wb") as f:
        f.write(audio_bytes)
    return out_abs




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

    first_sentence = script_data[0]['content'][0]
    print('合成第一条语音：', first_sentence)
    audio_path = aliyun_text2speech(first_sentence, dashtoken=dashtoken)
    print('合成成功，保存到：', audio_path)



    from dotenv import load_dotenv
    import os
    load_dotenv()
    api_key = os.getenv("GUIJI_KEY")
    text_en = "I'm so happy, Spring Festival is coming!"
    text_cn = "我太开心了，春节快到了！"
    voices = [
        "FunAudioLLM/CosyVoice2-0.5B:anna",
        "FunAudioLLM/CosyVoice2-0.5B:bella",
        "FunAudioLLM/CosyVoice2-0.5B:benjamin",
        "FunAudioLLM/CosyVoice2-0.5B:charles",
        "FunAudioLLM/CosyVoice2-0.5B:claire",
        "FunAudioLLM/CosyVoice2-0.5B:david",
        "FunAudioLLM/CosyVoice2-0.5B:diana"
    ]
    out_dir = "audio_output"
    os.makedirs(out_dir, exist_ok=True)
    for voice in voices:
        try:
            path_en = guiji_text2speech(api_key, text_en, voice=voice, out_dir=out_dir)
            print(path_en)
        except Exception as e:
            print(f"{voice} 英文生成失败: {e}")
        try:
            path_cn = guiji_text2speech(api_key, text_cn, voice=voice, out_dir=out_dir)
            print(path_cn)
        except Exception as e:
            print(f"{voice} 中文生成失败: {e}")
