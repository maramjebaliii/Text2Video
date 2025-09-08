import os
from openai import OpenAI




def split_text_for_tts(text):
    # 中文标点符号列表
    punctuation = ['，', '。', '；', '？', '！']
    brackets = {'(': ')', '[': ']', '{': '}', '（': '）', '【': '】', '《': '》'}

    # 初始化结果列表和临时句子存储
    sentences = []
    temp_sentence = ''
    bracket_stack = []

    # 遍历文本中的每一个字符
    for char in text:
        # 如果是左括号，压入栈
        if char in brackets:
            bracket_stack.append(char)
        # 如果是右括号且与栈顶匹配，弹出栈
        elif char in brackets.values() and bracket_stack and brackets[bracket_stack[-1]] == char:
            bracket_stack.pop()

        # 如果字符是中文标点之一且括号栈为空，表示句子结束
        if char in punctuation and not bracket_stack:
            # 添加临时句子到结果列表，并清空临时句子
            sentences.append(temp_sentence.strip())
            temp_sentence = ''
        # 如果字符是空格，也可以视为句子结束
        elif char == ' ':
            # 如果临时句子不是空，将其添加到结果列表
            if temp_sentence.strip():  # 仅在临时句子不为空时添加
                sentences.append(temp_sentence.strip())
                temp_sentence = ''
        else:
            # 否则，将字符添加到临时句子中
            temp_sentence += char

    # 处理最后一个可能没有标点结尾的句子
    if temp_sentence:
        sentences.append(temp_sentence.strip())

    return sentences



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
