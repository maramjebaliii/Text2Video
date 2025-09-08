def merge_speech_and_images_to_video(speech_data: list, illustration_data: list):
    """
    speech_data: 语音数据列表（如 speech_dataset.json 的内容）
    illustration_data: 插图数据列表（如 illustration_assets_for_video.json 的内容）
    return: 合并后的列表
    """
    merged = []
    for i in range(len(speech_data)):
        item = {
            "title": speech_data[i]["title"],
            "image": illustration_data[i]["image_path"],
            "content": speech_data[i]["content"]
        }
        merged.append(item)
    return merged


if __name__ == "__main__":
    from batch_script_to_speech import batch_script_to_guiji_speech
    from prepare_illustration_assets_for_video import (
        prepare_illustration_assets_for_video,
    )
    import json

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
    import os
    from dotenv import load_dotenv

    load_dotenv()
    from text2image import ImageGenerator

    image_generator = ImageGenerator(
        api_key=os.getenv("GUIJI_API_KEY"),
        base_url=os.getenv("GUIJI_IMAGE_BASE_URL"),
        model=os.getenv("GUIJI_IMAGE_MODEL", "Kwai-Kolors/Kolors"),
        output_dir=os.path.join(os.path.dirname(__file__), "output", "images"),
    )

    client = OpenAI(
        api_key=os.getenv("GUIJI_API_KEY"), base_url=os.getenv("GUIJI_BASE_URL")
    )

    # 生成 JSON 字符串格式的脚本
    md_script_json = md2script(markdown_text)

    # 用大模型逐条优化 content 字段,口语化
    script_for_recording = prepare_script_for_recording(
        md_script_json, client, model_name=os.getenv("GUIJI_CHAT_MODEL")
    )
    script_data: list = json.loads(script_for_recording)

    # 把 content 字段拆成更小的句子，方便 TTS 处理,去掉标点符号
    for item in script_data:
        content = item["content"]
        sentences = split_text_for_tts(content)
        item["content"] = sentences

    split_script_content: str = json.dumps(script_data, ensure_ascii=False, indent=4)

    # 1. 生成语音数据
    speech_dataset = batch_script_to_guiji_speech(
        script_data,
        api_key=os.getenv("GUIJI_API_KEY"),
        out_dir=os.path.join(os.path.dirname(__file__), "output", "speech"),
        model="FunAudioLLM/CosyVoice2-0.5B",
        voice="david",
        reuse_cache=True,
    )
    print("语音生成数据：", speech_dataset)
    # 2. 生成插图数据
    illustration_assets = prepare_illustration_assets_for_video(
        image_generator=image_generator,
        script=split_script_content,
        client=client,
        model="Qwen/Qwen2.5-7B-Instruct",
        output_path="output",
    )
    print("插图生成数据：", illustration_assets)

    # 3. 合并数据
    merged_data = merge_speech_and_images_to_video(speech_dataset, illustration_assets)
    # 4. 输出为 json 文件
    with open("merged_speech_and_images.json", "w", encoding="utf-8") as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
