"""
markdown 转演讲稿脚本
"""

import json
import re
from typing import TypedDict, List


class ScriptItem(TypedDict):
    """单个脚本项的类型定义。

    字段:
    - title: 标题
    - content: 对应的去除 Markdown 的文本内容
    """
    title: str
    content: str


def md2script(course_script: str) -> str:
    """
    创建演讲稿脚本，从给定的课程脚本中提取标题和内容。

    该函数将输入的课程脚本按行拆分，并提取其中的标题和内容，
    形成一个结构化的输出，包含标题及其对应的内容（去除 Markdown 格式）。

    参数:
    course_script (str): 包含课程内容的 Markdown 格式字符串。

    返回:
    str: 返回一个 JSON 格式的字符串，包含所有标题和内容。
    """
    # output 的内存结构为 List[ScriptItem]，最终返回 JSON 字符串
    output: List[ScriptItem] = []  # 用于保存输出的最终结果
    lines = course_script.splitlines()  # 将脚本按行拆分
    current_title = None  # 当前标题
    current_content = []  # 当前内容列表

    for line in lines:
        line = line.strip()  # 去除每行的首尾空白字符

        # 处理图片标签，去除 Markdown 图片格式
        if line.startswith('!['):
            continue  # 跳过图片行，直接进入下一个循环

        # 处理一级标题
        if line.startswith('# '):  # 检测到一级标题
            if current_title:  # 如果已有标题，保存当前内容
                output.append({
                    "title": current_title,
                    "content": "\n".join(current_content).replace('*', '').replace('**', '')
                })
                current_content = []  # 重置内容
            current_title = line[2:]  # 获取当前标题的文本内容（跳过 '# '）

        # 处理二级标题
        elif line.startswith('## '):  # 检测到二级标题
            if current_title:  # 如果已有标题，保存当前内容
                output.append({
                    "title": current_title,
                    "content": "\n".join(current_content).replace('*', '').replace('**', '')
                })
                current_content = []  # 重置内容
            current_title = line[3:]  # 获取当前标题的文本内容（跳过 '## '）

        else:
            # 处理列表和其他 Markdown 内容，移除多余的符号
            clean_line = re.sub(r'\*\s*', '', line)  # 移除以 '*' 开头的内容
            clean_line = re.sub(r'#+\s*', '', clean_line)  # 移除 Markdown 标题格式
            clean_line = clean_line.strip()  # 去除多余的空白字符

            if clean_line:  # 确保不添加空行
                current_content.append(clean_line)  # 将清理后的内容添加到当前内容列表

    # 辐忘记添加最后一个标题与内容
    if current_title:
        output.append({
            "title": current_title,
            "content": "\n".join(current_content).replace('*', '').replace('**', '')
        })

    # 将输出转换为 JSON 格式并返回
    generated_content = json.dumps(output, ensure_ascii=False, indent=4)



    return generated_content




# 示例：介绍云计算的 Markdown 文本（包含标题与列表）
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

if __name__ == "__main__":
    # 生成演讲稿脚本
    res = md2script(markdown_text)
    print("生成完毕。")
    print(res)
    