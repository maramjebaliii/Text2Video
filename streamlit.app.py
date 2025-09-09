from __future__ import annotations

import os
import traceback
import streamlit as st
from dotenv import load_dotenv

from app.core.config import CONFIG
from app.core.pipeline import build_blocks_from_markdown
from app.core.script_generate import generate_markdown_script
from app.core.video import assemble_video_from_blocks
from app.core.provider_factory import create_providers


load_dotenv()

st.set_page_config(page_title="Text2Video Debug", page_icon="🎬", layout="wide")
st.title("Text2Video (测试版) 🎬")

# 基础环境检查
if not os.getenv("GUIJI_API_KEY"):
    st.error("未检测到 GUIJI_API_KEY，请在项目根目录创建 .env 并设置 GUIJI_API_KEY=...，或在系统环境变量中设置。")

with st.sidebar:
    st.header("运行设置")
    default_output = str(CONFIG.path.output_dir)
    output_path = st.text_input("输出路径(可选，文件或目录)", value="")
    show_debug = st.toggle("显示调试日志", value=True)
    st.caption("若留空，将使用配置中的默认输出路径与文件名。")

tab_md, tab_topic = st.tabs(["Markdown → 视频", "Topic → 视频"])


def _safe_output_path(path: str | None) -> str | None:
    p = (path or "").strip()
    return p or None


with tab_md:
    st.subheader("Markdown → 视频")
    sample_md = """
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
    md_text = st.text_area("Markdown 内容", value=sample_md, height=220)
    if st.button("生成视频 (Markdown)"):
        if not md_text.strip():
            st.warning("请输入 Markdown 内容。")
        else:
            try:
                with st.status("初始化 Provider...", expanded=show_debug):
                    llm, tts, image = create_providers()
                    st.write("LLM / TTS / Image 已就绪")
                with st.status("构建 blocks...", expanded=show_debug):
                    blocks = build_blocks_from_markdown(md_text, llm=llm, tts=tts, image=image)
                    st.write(f"blocks 数量: {len(blocks)}")
                with st.status("拼接视频...", expanded=show_debug):
                    out = assemble_video_from_blocks(blocks, output_path=_safe_output_path(output_path))
                st.success(f"视频已生成: {out}")
                try:
                    st.video(str(out))
                except Exception:
                    st.info("无法内嵌预览，可手动在文件管理器中打开输出文件。")
            except Exception as e:
                st.error(f"生成失败: {e}")
                if show_debug:
                    st.code(traceback.format_exc())


with tab_topic:
    st.subheader("Topic → 视频")
    topic = st.text_input("主题", value="边缘计算与云计算的协同")
    col1, col2 = st.columns(2)
    with col1:
        language = st.text_input("语言", value="zh")
    with col2:
        max_sections = st.slider("最大段落数", min_value=1, max_value=12, value=5)
    show_md = st.checkbox("生成后显示 Markdown")
    if st.button("生成视频 (Topic)"):
        if not topic.strip():
            st.warning("请输入主题。")
        else:
            try:
                with st.status("初始化 Provider...", expanded=show_debug):
                    llm, tts, image = create_providers()
                    st.write("LLM / TTS / Image 已就绪")
                with st.status("生成 Markdown 脚本...", expanded=show_debug):
                    md = generate_markdown_script(llm=llm, topic=topic, language=language, max_sections=int(max_sections))
                    if show_md:
                        st.code(md, language="markdown")
                with st.status("构建 blocks...", expanded=show_debug):
                    blocks = build_blocks_from_markdown(md, llm=llm, tts=tts, image=image)
                    st.write(f"blocks 数量: {len(blocks)}")
                with st.status("拼接视频...", expanded=show_debug):
                    out = assemble_video_from_blocks(blocks, output_path=_safe_output_path(output_path))
                st.success(f"视频已生成: {out}")
                try:
                    st.video(str(out))
                except Exception:
                    st.info("无法内嵌预览，可手动在文件管理器中打开输出文件。")
            except Exception as e:
                st.error(f"生成失败: {e}")
                if show_debug:
                    st.code(traceback.format_exc())
