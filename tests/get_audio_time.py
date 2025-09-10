from typing import Optional
from pydub import AudioSegment


def get_audio_duration(audio_path: str) -> float:
    """获取音频时长，单位秒"""
    audio = AudioSegment.from_file(audio_path)
    return audio.duration_seconds

def probe_duration(path: str) -> Optional[float]:
    """探测音频文件时长（秒）。失败返回 None，由调用方再做估算兜底。"""
    try:
        audio = AudioSegment.from_file(path)
        return len(audio) / 1000.0
    except Exception:
        return None

if __name__ == "__main__":
    audio_path = r"C:\Users\ke\Documents\projects\python_projects\Text2Video\tests\audio_output\guiji_1757503555_9b16f38e.mp3"
    duration = get_audio_duration(audio_path)
    print(f"音频时长: {duration:.2f} 秒")
    # 试试probe_duration
    duration2 = probe_duration(audio_path)
    print(f"探测时长: {duration2:.2f} 秒")