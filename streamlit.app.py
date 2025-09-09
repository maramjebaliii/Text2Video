from __future__ import annotations

import os
import traceback
from typing import Optional
import streamlit as st
from dotenv import load_dotenv

from app.core.config import CONFIG, set_run_id
from app.core.pipeline import build_blocks_from_markdown
from app.core.script_generate import generate_markdown_script
from app.core.video import assemble_video_from_blocks
from app.core.provider_factory import create_providers


load_dotenv()

# 固定 Web UI 的输出目录，避免每次随机 run_id 导致路径变化
try:
    set_run_id(os.getenv("RUN_ID") or "webui")
except Exception:
    # 容错：若导入/调用异常，不影响后续逻辑
    pass

st.set_page_config(page_title="Text2Video Debug", page_icon="🎬", layout="wide")
st.title("Text2Video (测试版) 🎬")

# 基础环境检查
if not os.getenv("GUIJI_API_KEY"):
    st.error("未检测到 GUIJI_API_KEY，请在项目根目录创建 .env 并设置 GUIJI_API_KEY=...，或在系统环境变量中设置。")

## 输出路径固定为默认配置（禁止前端设置）

tab_md, tab_topic = st.tabs(["Markdown → 视频", "Topic → 视频"])



def _text_stats(text: str) -> str:
    lines = text.strip().splitlines() if text else []
    chars = len(text)
    words = len(text.split()) if text else 0
    return f"{len(lines)} 行 · {words} 词 · {chars} 字符"


with tab_md:
    st.subheader("Markdown → 视频")

    # 左右两栏：左侧输入与说明，右侧操作与结果
    left, right = st.columns([3, 2], gap="large")

    # 全局运行锁：任一任务执行中则禁用所有提交按钮
    if 'global_running' not in st.session_state:
        st.session_state['global_running'] = False

    # 默认示例
    sample_md = (
        """
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
    ).strip()

    with left:
        st.caption("输入来源")
        input_mode = st.radio("选择输入方式", ["编辑器", "上传文件"], horizontal=True, label_visibility="collapsed")
        uploaded_md = None
        if input_mode == "上传文件":
            uploaded_md = st.file_uploader("上传 Markdown 文件", type=["md", "markdown", "txt"], accept_multiple_files=False)

        # 使用表单，避免每次输入都触发重跑
        # 按钮在全局运行或本页运行时禁用
        md_disabled = st.session_state.get("global_running", False)

        with st.form("md_form", clear_on_submit=False, border=True):
            if input_mode == "编辑器":
                md_text = st.text_area("Markdown 内容", value=sample_md, height=260, placeholder="# 在此粘贴或书写 Markdown…")
            else:
                file_text = ""
                if uploaded_md is not None:
                    try:
                        file_text = uploaded_md.getvalue().decode("utf-8", errors="ignore")
                    except Exception:
                        file_text = ""
                md_text = st.text_area("文件内容预览 (可编辑)", value=file_text or sample_md, height=260)

            # 仅在表单内保留提交按钮
            submit_md = st.form_submit_button(
                "生成视频 (Markdown)",
                disabled=md_disabled,
                help=("已有任务在执行，请稍候…" if md_disabled else None),
            )

        # 表单外：工具条（统计 + 下载）
        tc1, tc2 = st.columns([1, 1])
        with tc1:
            st.caption("统计")
            st.info(_text_stats(md_text))
        with tc2:
            st.caption("导出")
            st.download_button("下载 Markdown", data=md_text, file_name="script.md", mime="text/markdown")

    with right:
        # 顶部：结果预览；底部：进度
        st.caption("结果预览")
        md_preview = st.container()
        st.divider()
        st.caption("进度")
        md_progress = st.container()
        if 'md_running' not in st.session_state:
            st.session_state['md_running'] = False

        if 'md_output' not in st.session_state:
            st.session_state['md_output'] = None

        if 'md_error' not in st.session_state:
            st.session_state['md_error'] = None

        if 'md_blocks_count' not in st.session_state:
            st.session_state['md_blocks_count'] = 0

        # 在右侧触发运行，显示状态
        if 'submit_md' not in st.session_state:
            st.session_state['submit_md'] = False

        # 接收左侧提交事件
        try:
            submit_md  # noqa: F821 (defined in left form context)
            st.session_state['submit_md'] = submit_md
        except Exception:
            pass

        if st.session_state['submit_md']:
            if not md_text.strip():
                st.warning("请输入 Markdown 内容。")
            else:
                # 全局锁二次校验：若已有任务在执行则忽略
                if st.session_state.get('global_running', False) and not st.session_state.get('md_running', False):
                    st.info("当前有其它生成任务在执行，请稍后再试。")
                else:
                    st.session_state['global_running'] = True
                    st.session_state['md_running'] = True
                    st.session_state['md_output'] = None
                    st.session_state['md_error'] = None
                    try:
                        with md_progress:
                            with st.status("初始化 Provider...", expanded=False):
                                llm, tts, image = create_providers()
                                st.write("LLM / TTS / Image 已就绪")

                            with st.status("构建 blocks...", expanded=False):
                                blocks = build_blocks_from_markdown(md_text, llm=llm, tts=tts, image=image)
                                st.session_state['md_blocks_count'] = len(blocks)
                                st.write(f"blocks 数量: {len(blocks)}")

                            with st.status("拼接视频...", expanded=False):
                                out = assemble_video_from_blocks(blocks, output_path=None)

                        st.session_state['md_output'] = str(out)
                        with md_preview:
                            st.success("视频已生成")
                            try:
                                st.video(str(out))
                                with open(out, "rb") as vf:
                                    st.download_button("下载视频", data=vf.read(), file_name=os.path.basename(str(out)), mime="video/mp4")
                            except Exception:
                                st.info("无法内嵌预览，可手动在文件管理器中打开输出文件。")
                    except Exception as e:
                        st.session_state['md_error'] = str(e)
                        st.error(f"生成失败: {e}")
                    finally:
                        st.session_state['md_running'] = False
                        st.session_state['global_running'] = False
                # 重置提交状态，避免重复运行
                st.session_state['submit_md'] = False
        else:
            # 静态展示上次结果概要
            if st.session_state['md_output']:
                with md_preview:
                    st.success("最近一次输出可预览/下载")
                    st.caption(f"Blocks: {st.session_state['md_blocks_count']}")
                    try:
                        st.video(st.session_state['md_output'])
                        with open(st.session_state['md_output'], "rb") as vf:
                            st.download_button("下载视频", data=vf.read(), file_name=os.path.basename(st.session_state['md_output']), mime="video/mp4", key="dl_md_last")
                    except Exception:
                        pass


with tab_topic:
    st.subheader("Topic → 视频")

    # 右侧固定预览布局，左侧为输入表单（与 Markdown 页一致）
    left_t, right_t = st.columns([3, 2], gap="large")

    # 使用表单统一提交（左侧）
    with left_t:
        topic_disabled = st.session_state.get("global_running", False)

        with st.form("topic_form", clear_on_submit=False, border=True):
            topic = st.text_input("主题", value="边缘计算与云计算的协同")
            col1, col2 = st.columns(2)
            with col1:
                language = st.text_input("语言", value="zh")
            with col2:
                max_sections = st.slider("最大段落数", min_value=1, max_value=12, value=5)
            show_md = st.checkbox("生成后显示 Markdown")
            submit_topic = st.form_submit_button(
                "生成视频 (Topic)",
                disabled=topic_disabled,
                help=("已有任务在执行，请稍候…" if topic_disabled else None),
            )

    if 'topic_running' not in st.session_state:
        st.session_state['topic_running'] = False
    if 'topic_output' not in st.session_state:
        st.session_state['topic_output'] = None
    if 'topic_error' not in st.session_state:
        st.session_state['topic_error'] = None
    if 'topic_blocks_count' not in st.session_state:
        st.session_state['topic_blocks_count'] = 0

    # 右侧：预览在上、进度在下
    with right_t:
        st.caption("结果预览")
        topic_preview = st.container()
        st.divider()
        st.caption("进度")
        topic_progress = st.container()

    if submit_topic:
        if not topic.strip():
            st.warning("请输入主题。")
        else:
            # 全局锁二次校验：若已有任务在执行则忽略
            if st.session_state.get('global_running', False) and not st.session_state.get('topic_running', False):
                st.info("当前有其它生成任务在执行，请稍后再试。")
            else:
                st.session_state['global_running'] = True
                st.session_state['topic_running'] = True
                st.session_state['topic_output'] = None
                st.session_state['topic_error'] = None
                try:
                    with topic_progress:
                        with st.status("初始化 Provider...", expanded=False):
                            llm, tts, image = create_providers()
                            st.write("LLM / TTS / Image 已就绪")
                        with st.status("生成 Markdown 脚本...", expanded=False):
                            md = generate_markdown_script(llm=llm, topic=topic, language=language, max_sections=int(max_sections))
                            if show_md:
                                st.code(md, language="markdown")
                        with st.status("构建 blocks...", expanded=False):
                            blocks = build_blocks_from_markdown(md, llm=llm, tts=tts, image=image)
                            st.session_state['topic_blocks_count'] = len(blocks)
                            st.write(f"blocks 数量: {len(blocks)}")
                        with st.status("拼接视频...", expanded=False):
                            out = assemble_video_from_blocks(blocks, output_path=None)
                    st.session_state['topic_output'] = str(out)
                    with topic_preview:
                        st.success("视频已生成")
                        try:
                            st.video(str(out))
                            with open(out, "rb") as vf:
                                st.download_button("下载视频", data=vf.read(), file_name=os.path.basename(str(out)), mime="video/mp4", key="dl_topic")
                        except Exception:
                            st.info("无法内嵌预览，可手动在文件管理器中打开输出文件。")
                except Exception as e:
                    st.session_state['topic_error'] = str(e)
                    st.error(f"生成失败: {e}")
                finally:
                    st.session_state['topic_running'] = False
                    st.session_state['global_running'] = False
    else:
        if st.session_state['topic_output']:
            with topic_preview:
                st.success("最近一次输出可预览/下载")
                st.caption(f"Blocks: {st.session_state['topic_blocks_count']}")
                try:
                    st.video(st.session_state['topic_output'])
                    with open(st.session_state['topic_output'], "rb") as vf:
                        st.download_button("下载视频", data=vf.read(), file_name=os.path.basename(st.session_state['topic_output']), mime="video/mp4", key="dl_topic_last")
                except Exception:
                    pass
