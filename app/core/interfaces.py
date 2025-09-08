"""核心抽象协议定义。

提供给 pipeline 统一依赖注入，避免直接耦合具体厂商实现。
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable, Iterable, Sequence, Any, Optional, Type


@runtime_checkable
class TTSProvider(Protocol):
    """文本转语音提供者。

    必须实现 synthesize(text: str, *, voice: str | None = None, **kwargs) -> str
    返回值为生成的本地音频文件绝对路径。
    """
    def synthesize(self, text: str, *, voice: str | None = None, **kwargs) -> str: ...


@runtime_checkable
class ImageProvider(Protocol):
    """图片生成提供者。"""
    def generate(self, prompt: str, **kwargs) -> str: ...  # 返回生成的图片本地绝对路径


@runtime_checkable
class LLMProvider(Protocol):
    """大模型对话/补全提供者。"""
    def chat(self, messages: Sequence[dict[str, str]], **kwargs) -> str: ...


class BatchCache(Protocol):
    """批处理缓存接口。"""
    def get(self, key: str) -> Optional[tuple[str, Optional[float]]]: ...
    def put(self, key: str, path: str, duration: Optional[float]): ...


def ensure_protocol(obj: Any, proto: Type[Any]) -> None:
    if not isinstance(obj, proto):  # type: ignore[arg-type]
        raise TypeError(f"对象 {obj!r} 未实现协议 {proto.__name__}")
