"""
优化录音稿的内容，使其更适合口语表达。
"""
import json
import os
from typing import Optional
from openai import OpenAI

env_path = os.path.join(os.path.dirname(__file__), '.env')
from dotenv import load_dotenv

load_dotenv(env_path)



def prepare_script_for_recording(script: str, client: OpenAI, model_name) -> str:
    """
    优化录音稿的内容，使其更适合口语表达。

    此函数调用外部 API，对输入的录音稿 JSON 格式的内容进行处理，
    生成更适合发言的纯文本内容。

    参数:
    script (str): JSON 格式的字符串，包含待优化的内容。
    client: 已初始化的 API 客户端实例，用于发送请求。

    返回:
    str: 生成的优化后的口语化文本。
    """

    # 系统消息，设定机器人的角色
    system_message = "您是录音稿专家。"

    # 提示词创建，构建用于 API 请求的 prompt 字符串
    prompt = f"""处理以下 JSON 中的 content 字段，并将内容转换为适合录音的纯文本形式。
返回处理后的 JSON，不要任何额外的说明。内容格式要求：
1. 对于英文的专有术语缩写，替换为全称。
2. 去除星号、井号等 Markdown 格式。
3. 去除换行符和段落分隔。
4. 对于复杂的长难句，使用中文句号分割，便于口语表达。
content 中的内容使用于发言使用。
下面的内容是待处理的 JSON：
{script}
输出格式为 JSON。不包含任何额外的文字、解释或评论。
"""

    # 调用 API 获取插图数据，使用传入的 client 实例
    completion = client.chat.completions.create(
        model=model_name,  # 使用环境变量中配置的模型
        messages=[
            {"role": "system", "content": system_message},  # 系统角色消息
            {"role": "user", "content": prompt},  # 用户请求部分
        ],
    )

    # 从 OpenAI 响应中提取生成的内容
    generated_content = completion.choices[0].message.content

    # 去掉```json前后的标记
    if generated_content.startswith("```json"):
        generated_content = generated_content[len("```json"):].strip()
    if generated_content.endswith("```"):
        generated_content = generated_content[:-len("```")].strip()

    return generated_content  # 返回优化后的文本





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


    from md2script import md2script


    # 生成 JSON 字符串格式的脚本
    script_json = md2script(markdown_text)
    client = OpenAI(api_key=os.getenv('API_KEY'), base_url=os.getenv('BASE_URL'))
    optimized = prepare_script_for_recording(script_json, client, model_name=os.getenv('MODEL_NAME'))
    print('优化完成：')
    print(optimized)
    # 写入output目录下，作为json文件
    with open(os.path.join(os.path.dirname(__file__), 'output', 'optimized_script.json'), 'w', encoding='utf-8') as f:
        f.write(optimized)
