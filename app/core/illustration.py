"""插图提示生成与图片资产构建。"""
from __future__ import annotations
import json
import re
from typing import List, Dict
from .interfaces import LLMProvider, ImageProvider


def generate_illustration_prompts(script_json: str, llm: LLMProvider, model: str | None = None) -> list[dict]:
    """调用 LLM 生成插图提示 JSON 数组。"""
    system_message = (
        "您是一位插图提示生成专家，专注于为微课程生成详细的插图提示。"
    )
    prompt = f"""
### 任务
生成关于 {script_json} 的插图。返回仅包含多个插图详细信息的 JSON 数组。
### 插图描述要素:
- **主题:** 中心概念。
- **描述:** 详细叙述重点元素、情感和氛围。
- **场景:** 特定环境（如自然、城市、太空），包括颜色、光线和情绪。
- **对象:** 主要主题和特征（如人、动物、物体）。
- **动作:** 对象的动态（如飞行、跳跃、闲逛）。
- **风格:** 艺术技巧（如抽象、超现实主义、水彩、矢量）。
- **细节:** 其他特定信息（如纹理、背景元素）。
### 生成的提示结构:
描述, 场景, 包含对象, 动作. 以风格呈现, 强调细节。
### 输出格式要求
[
    {{
        "illustration_id": 1,
        "title": "阳光明媚的日子",
        "description": "一幅富有创意的数字艺术作品，描绘了一只由埃菲尔铁塔构建的长颈鹿。"
    }},
    {{
        "illustration_id": 2,
        "title": "繁星之夜",
        "description": "一幅黑暗幻想肖像，呈现了一匹马奔跑在风暴中，背景火焰般的景观。"
    }}
]
输出格式为JSON。不包含任何额外的文字、解释或评论。
"""
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]
    raw = llm.chat(messages, model=model)  # 允许 provider 内部忽略 model
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[len("```json"):].strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()
    try:
        data = json.loads(raw)
    except Exception as e:
        raise ValueError(f"插图提示解析失败: {raw[:200]} ... -> {e}") from e
    return data


def build_illustration_assets(
    prompts: list[dict],
    image_provider: ImageProvider,
    image_size: str = "1024x1024",
    num_inference_steps: int = 20,
    guidance_scale: float = 7.5,
) -> list[dict]:
    """根据插图提示批量生成图片并返回带本地路径的资产列表。"""
    results: list[dict] = []
    for item in prompts:
        scene_index = item.get("illustration_id")
        title = item.get("title") or ""
        desc = item.get("description") or ""
        path = image_provider.generate(
            prompt=desc,
            image_size=image_size,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        )
        results.append({
            "scene_index": scene_index,
            "title": title,
            "prompt": desc,
            "image_path": path,
        })
    return results
