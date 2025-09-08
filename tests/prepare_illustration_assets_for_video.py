"""
为后续视频生成准备插图资产并批量生成图片。
"""

import json
import os
from typing import Any, List, Dict

from openai import OpenAI
from generate_illustration_prompts import generate_illustration_prompts
from text2image import ImageGenerator


def prepare_illustration_assets_for_video(
    image_generator: ImageGenerator,
    script: str,
    client: OpenAI,
    model: str,
    output_path: str,
    image_size: str = "1024x1024",
    num_inference_steps: int = 20,
    guidance_scale: float = 7.5,
) -> List[Dict]:
    """
    为后续视频生成准备插图资产并批量生成图片。
    参数:
      - image_generator: 必需，ImageGenerator 实例，用于实际生成并保存图片。
      - script: 传入给 generate_illustration_prompts 的脚本文本或脚本结构。
      - client: 用于调用大模型生成插图提示的客户端。
      - image_size, num_inference_steps, guidance_scale: 透传给 image_generator.generate_and_save。
      - output_path: 可选，结果 JSON 输出路径，默认 tests/output/illustration_assets_for_video.json。
    返回:
      - 列表，每项为字典，包含插图元数据与生成的本地图片路径，方便后续视频处理使用。
    """
    if image_generator is None:
        raise ValueError("必须传入 image_generator（ImageGenerator 实例）")

    # 调用已有函数生成插图提示（JSON 字符串）
    generated = generate_illustration_prompts(script, client, model=model)


    prompts = json.loads(generated)


    results: List[Dict] = []
    for idx, item in enumerate(prompts, start=1):
        scene_index = item.get("illustration_id")
        title = item.get("title") or item.get("插图标题") or ""
        desc = item.get("description") or item.get("插图描述") or ""

        entry = {
            "scene_index": scene_index,
            "title": title,
            "prompt": desc,
            "image_path": None,
        }

        path = image_generator.generate_and_save(
            prompt=desc,
            batch_size=1,
            image_size=image_size,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        )
        entry["image_path"] = path

        results.append(entry)

    return results


if __name__ == "__main__":
    # 示例：把 markdown 转成脚本后，用大模型逐条优化 content 字段
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
    import os
    from dotenv import load_dotenv

    load_dotenv()  # 从 .env 文件加载环境变量
    from split_text_for_tts import split_text_for_tts

    # 生成 JSON 字符串格式的脚本
    script_json = md2script(markdown_text)
    client = OpenAI(api_key=os.getenv("API_KEY"), base_url=os.getenv("BASE_URL"))
    optimized = prepare_script_for_recording(script_json, client)
    # 继续优化，把 content 字段拆成更小的句子，方便 TTS 处理
    import json

    script_data = json.loads(optimized)
    for item in script_data:
        content = item["content"]
        sentences = split_text_for_tts(content)
        item["content"] = sentences
    optimized_split = json.dumps(script_data, ensure_ascii=False, indent=4)

    # 开始生成插图提示
    illustration_prompts = generate_illustration_prompts(optimized_split, client)
    print("最终生成的插图提示词:", illustration_prompts)

    # 写入output目录下，作为json文件
    with open(
        os.path.join(os.path.dirname(__file__), "output", "illustration_prompts.json"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(illustration_prompts)

    # 准备插图资产并生成图片
    from text2image import ImageGenerator

    image_generator = ImageGenerator(
        api_key=os.getenv("GUIJI_KEY"),
        base_url=os.getenv("GUIJI_IMAGE_BASE_URL"),
        model=os.getenv("IMAGE_MODEL", "Kwai-Kolors/Kolors"),
        output_dir=os.path.join(os.path.dirname(__file__), "output", "images"),
    )

    assets = prepare_illustration_assets_for_video(
        image_generator=image_generator,
        script=optimized,
        client=client,
        output_path=os.path.join(os.path.dirname(__file__), "output"),
        image_size="1024x1024",
        num_inference_steps=20,
        guidance_scale=7.5,
    )
    print("准备的插图资产:", json.dumps(assets, ensure_ascii=False, indent=4))
    with open(
        os.path.join(
            os.path.dirname(__file__), "output", "illustration_assets_for_video.json"
        ),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(json.dumps(assets, ensure_ascii=False, indent=4))
