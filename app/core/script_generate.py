"""脚本内容自动生成.

提供将“主题”或“原始要点”转换成内部 markdown 脚本格式的便捷函数。

特点:
- Few-shot 提示: 内置一个示例, 引导模型输出符合我们期望的结构
- 可根据 topic(主题) 或 raw_content(一段内容/要点) 生成
- 约束输出: 必须包含一个一级标题(# ...) 与若干二级标题(## ...)
- 语言默认中文, 可扩展

后续可以在此文件继续扩展: 例如支持风格(style)、受众(audience)、时长估计、长度控制(token 长度) 等。
"""
from __future__ import annotations
from typing import Sequence
from .interfaces import LLMProvider

# 内置 few-shot 示例 (与 main.py 中一致, 作为对模型的格式暗示)
_FEW_SHOT_EXAMPLE =  """
## 云计算简介

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

_SYSTEM_INSTRUCTION = """
你是一个专业的视频脚本撰写助手, 需要基于给定的主题或要点, 生成结构化的 Markdown 内容。
要求:
1) 偏教程风格, 面向初学者;
2) 使用若干 ## 二级标题拆分要点; 
3) 语言自然、口语化、利于后续 TTS 配音;
4) 避免过长段落, 每段 1-3 句; 
5) 不要添加额外的解释性前后缀。
"""


def _build_user_prompt(*, topic: str | None, raw_content: str | None, language: str, max_sections: int | None) -> str:
    parts: list[str] = []
    if topic:
        parts.append(f"主题: {topic}")
    if raw_content:
        parts.append(f"补充要点: {raw_content}")
    if not parts:
        raise ValueError("必须提供 topic 或 raw_content 之一")
    sec_note = f" 期望最多 {max_sections} 个二级标题." if max_sections else ""
    parts.append(f"输出语言: {language}.{sec_note}")
    parts.append("请严格只输出 Markdown 正文, 不要解释。")
    parts.append("以下是一个格式示例 (不要照抄内容, 只参考结构):\n```\n" + _FEW_SHOT_EXAMPLE + "\n```")
    return "\n".join(parts)


def generate_markdown_script(
    *,
    llm: LLMProvider,
    topic: str | None = None,
    raw_content: str | None = None,
    language: str = "zh",
    max_sections: int | None = 4,
) -> str:
    """生成用于后续管线的 Markdown 文本。

    参数:
        llm: 实现 LLMProvider 协议的对象
        topic: 主题 (可选)
        raw_content: 一段待整理的原始内容/要点 (可选)
        language: 输出语言 (默认中文)
        max_sections: 限制标题数量 (None 表示不限制)
    
    返回:
        markdown 文本字符串
    """
    user_prompt = _build_user_prompt(topic=topic, raw_content=raw_content, language=language, max_sections=max_sections)
    messages: Sequence[dict[str, str]] = [
        {"role": "system", "content": _SYSTEM_INSTRUCTION},
        {"role": "user", "content": user_prompt},
    ]
    markdown = llm.chat(messages)

    return markdown


__all__ = ["generate_markdown_script"]
