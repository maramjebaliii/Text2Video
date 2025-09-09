"""脚本预处理：Markdown -> 结构化 -> 口语化优化 -> 拆句。

聚合原 md2script / prepare_script_for_recording / split_text_for_tts 逻辑。
"""
from __future__ import annotations
import json
import re
from typing import List
from .interfaces import LLMProvider


def markdown_to_script(markdown_text: str) -> list[dict[str, str]]:
    """Markdown 文本解析为标题+内容结构列表。"""
    lines = markdown_text.splitlines()
    output: list[dict[str, str]] = []
    current_title: str | None = None
    current_content: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith('!['):
            continue
        if line.startswith('# '):
            if current_title:
                output.append({"title": current_title, "content": "\n".join(current_content)})
                current_content = []
            current_title = line[2:]
        elif line.startswith('## '):
            if current_title:
                output.append({"title": current_title, "content": "\n".join(current_content)})
                current_content = []
            current_title = line[3:]
        else:
            clean = re.sub(r'\*\s*', '', line)
            clean = re.sub(r'#+\s*', '', clean).strip('*').strip()
            if clean:
                current_content.append(clean)
    if current_title:
        output.append({"title": current_title, "content": "\n".join(current_content)})
    return output


def optimize_script_for_speech(script_items: list[dict[str, str]], llm: LLMProvider) -> list[dict[str, str]]:
    """调用 LLM 对 content 口语化。"""
    system_message = "您是录音稿专家。"
    prompt = f"""处理以下 JSON 中的 content 字段，并将内容转换为适合录音的纯文本形式。
返回处理后的 JSON，不要任何额外的说明。内容格式要求：
1. 对于英文的专有术语缩写，替换为全称。
2. 去除星号、井号等 Markdown 格式。
3. 去除换行符和段落分隔。
4. 对于复杂的长难句，使用中文句号分割，便于口语表达。
content 中的内容使用于发言使用。
下面的内容是待处理的 JSON：
{json.dumps(script_items, ensure_ascii=False)}

输出格式为 JSON。不包含任何额外的文字、解释或评论。
非常重要：请严格返回可被 json.loads() 解析的 JSON。注意事项：
- 使用英文逗号分隔数组中的对象，数组元素之间不能缺少逗号。
- 字符串必须使用双引号。
- 不要在 JSON 外添加任何说明性文字或代码块说明（例如 ```json ```）。
下面给出一个合法输出示例（仅供格式参考）：
[
    {{"title": "云计算简介", "content": "云计算是一种通过互联网按需提供计算资源，例如服务器、存储、数据库、网络和软件。它使企业可以更灵活地扩展资源并降低基础设施成本。"}},
    {{"title": "什么是云计算", "content": "云计算将传统本地部署的计算资源迁移到远程数据中心，由云服务提供商管理和维护。用户可以根据需要申请或释放资源，而无需关心底层硬件的运维。"}}
]
"""
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]
    raw = llm.chat(messages)
    raw = raw.strip()
    if raw.startswith("```"):
        # 去掉 ```json 包装
        raw = re.sub(r'^```json', '', raw)
        raw = raw.removeprefix('```').strip('`')
    try:
        data = json.loads(raw)
    except Exception as e:  # 容错：如果模型返回非纯 JSON
        raise ValueError(f"LLM 返回内容解析失败: {raw[:200]} ... -> {e}") from e
    return data


_CHINESE_PUNCT = ['，', '。', '；', '？', '！']
_BRACKETS = {'(': ')', '[': ']', '{': '}', '（': '）', '【': '】', '《': '》'}

def split_text_for_tts(text: str) -> list[str]:
    """将长文本按中文标点与空格拆分为句子列表。"""
    sentences: list[str] = []
    temp = ''
    stack: list[str] = []
    for ch in text:
        if ch in _BRACKETS:
            stack.append(ch)
        elif ch in _BRACKETS.values() and stack and _BRACKETS[stack[-1]] == ch:
            stack.pop()
        if ch in _CHINESE_PUNCT and not stack:
            if temp.strip():
                sentences.append(temp.strip())
            temp = ''
        elif ch == ' ':
            if temp.strip():
                sentences.append(temp.strip())
                temp = ''
        else:
            temp += ch
    if temp.strip():
        sentences.append(temp.strip())
    return sentences


def expand_script_items(script_items: list[dict[str, str]]) -> list[dict[str, list[str]]]:
    """为每个脚本项生成 sentences 字段（拆句结果）。"""
    expanded: list[dict[str, list[str]]] = []
    for item in script_items:
        content = item.get('content', '')
        sentences = split_text_for_tts(content)
        expanded.append({"title": item.get('title', ''), "sentences": sentences})
    return expanded
