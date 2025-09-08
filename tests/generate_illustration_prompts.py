"""
给定微课程脚本，生成插图提示，并通过 API 获取详细插图信息。
"""

def generate_illustration_prompts(script, client,model) -> str:
    """
    根据给定的脚本生成插图提示，并通过 API 获取详细插图信息。

    :param script: str，微课程的主题或内容脚本，用于生成插图提示。

    :return: str，生成的插图提示，包含详细的插图信息和格式的 JSON 字符串。
    """

    # 系统消息，指定模型的角色和任务
    system_message = (
        "您是一位插图提示生成专家，专注于为微课程生成详细的插图提示。"
    )

    # 构建插图生成提示
    prompt = f"""生成关于 {script} 的插图。返回仅包含多个插图详细信息的 JSON 数组。
    ### 插图描述要素:
    - **主题:** 中心概念。
    - **描述:** 详细叙述重点元素、情感和氛围。
    - **场景:** 特定环境（如自然、城市、太空），包括颜色、光线和情绪。
    - **对象:** 主要主题和特征（如人、动物、物体）。
    - **动作:** 对象的动态（如飞行、跳跃、闲逛）。
    - **风格:** 艺术技巧（如抽象、超现实主义、水彩、矢量）。
    - **细节:** 其他特定信息（如纹理、背景元素）。
    ### 生成的提示结构:
    “描述, 场景, 包含对象, 动作. 以风格呈现, 强调细节。”
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

    # 调用 API 获取插图数据
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        stream=True
    )

    # 解析 API 返回结果
    generated_content = ""
    for chunk in completion:
        chunk_content = chunk.choices[0].delta.content
        generated_content += chunk_content
        # print(chunk_content, end="")

    # print("生成的插画提示词:", generated_content)  # 打印生成的提示
    # 去掉```json前后的标记
    if generated_content.startswith("```json"):
        generated_content = generated_content[len("```json"):].strip()
    if generated_content.endswith("```"):
        generated_content = generated_content[:-len("```")].strip()
    # 返回生成的插图提示
    return generated_content



if __name__ == '__main__':
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
    client = OpenAI(api_key=os.getenv('API_KEY'), base_url=os.getenv('BASE_URL'))
    optimized = prepare_script_for_recording(script_json, client)
    # 继续优化，把 content 字段拆成更小的句子，方便 TTS 处理
    import json
    script_data = json.loads(optimized)
    for item in script_data:
        content = item['content']
        sentences = split_text_for_tts(content)
        item['content'] = sentences
    optimized_split = json.dumps(script_data, ensure_ascii=False, indent=4)
    print('拆分完成：')
    print(optimized_split)
    # 写入output目录下，作为json文件
    with open(os.path.join(os.path.dirname(__file__), 'output', 'optimized_split_script.json'), 'w', encoding='utf-8') as f:
        f.write(optimized_split)

    
    # 开始生成插图提示
    illustration_prompts = generate_illustration_prompts(optimized, client)
    print("最终生成的插图提示词:", illustration_prompts)
    
    # 写入output目录下，作为json文件
    with open(os.path.join(os.path.dirname(__file__), 'output', 'illustration_prompts.json'), 'w', encoding='utf-8') as f:
        f.write(illustration_prompts)