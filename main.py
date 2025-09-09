"""示例入口：演示 markdown -> blocks -> 视频。

运行前请确保：
1. 已设置相关 API Key (环境变量)：
	- 硅基统一密钥: GUIJI_API_KEY
   - 阿里云 TTS: ALIBABA_CLOUD_AK / ALIBABA_CLOUD_SK (若使用)
2. 已安装 ffmpeg / ffprobe 并在 PATH 中。

本示例最小化流程：
markdown 文本 -> 构建 blocks -> 生成最终视频文件。
"""
from __future__ import annotations

import os
import argparse
from app.core.pipeline import build_blocks_from_markdown
from app.core.script_generate import generate_markdown_script
from app.core.video import assemble_video_from_blocks
from app.core.config import CONFIG
from app.providers import (
	GuijiTTSProvider,
	AliyunTTSProvider,
	SiliconFlowImageProvider,
	SiliconFlowLLMProvider,
)
from dotenv import load_dotenv

load_dotenv()  # 从 .env 文件加载环境变量


def create_providers():
	"""创建所需的 provider 实例。"""
	api_key = os.getenv("GUIJI_API_KEY", "")
	if not api_key:
		raise RuntimeError("缺少 GUIJI_API_KEY 环境变量 (请在 .env 中设置)")
	base_url = os.getenv("GUIJI_BASE_URL", "https://api.siliconflow.cn/v1")
	# 图片生成 endpoint 按硅基固定
	image_base = "https://api.siliconflow.cn/v1/images/generations"
	llm = SiliconFlowLLMProvider(api_key=api_key, base_url=base_url)
	# 统一图片输出目录到 pipeline 的 CONFIG.path.image_dir（默认为 output/images）
	image = SiliconFlowImageProvider(
		api_key=api_key,
		model=CONFIG.model.image_model,
		ipm=CONFIG.rate.image_ipm,
		base_url=image_base,
		output_dir=CONFIG.path.image_dir,
	)
	tts = GuijiTTSProvider(api_key=api_key)
	# 若使用阿里云：
	# tts = AliyunTTSProvider(access_key_id=os.getenv("ALIBABA_CLOUD_AK",""), access_key_secret=os.getenv("ALIBABA_CLOUD_SK",""))
	return llm, tts, image


def demo_markdown_to_video(output: str | None = None):
	"""执行从 markdown 到视频的演示。"""
	markdown_text = """# 云计算简介\n\n云计算是一种通过互联网按需提供计算资源的模式。\n\n## 优点\n弹性伸缩、成本优化和高可用。"""
	llm, tts, image = create_providers()
	print("[STEP] 构建 blocks ...")
	blocks = build_blocks_from_markdown(markdown_text, llm=llm, tts=tts, image=image)
	print(f"[INFO] blocks 数量: {len(blocks)}")
	print("[STEP] 生成视频 ...")
	assemble_video_from_blocks(blocks, output_path=output)


def demo_topic_to_video(topic: str = "边缘计算与云计算的协同", output: str | None = None):
	"""演示: 直接根据主题自动生成脚本再转视频。"""
	llm, tts, image = create_providers()
	print(f"[STEP] 生成主题脚本: {topic}")
	markdown_text = generate_markdown_script(llm=llm, topic=topic, language="zh", max_sections=5)
	print("[INFO] 生成的 Markdown:\n" + markdown_text)
	print("[STEP] 构建 blocks ...")
	blocks = build_blocks_from_markdown(markdown_text, llm=llm, tts=tts, image=image)
	print(f"[INFO] blocks 数量: {len(blocks)}")
	print("[STEP] 生成视频 ...")
	assemble_video_from_blocks(blocks, output_path=output)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Markdown / 主题 转 视频示例")
	parser.add_argument("--mode", choices=["markdown", "topic"], default="topic", help="运行示例模式")
	parser.add_argument("--topic", type=str, default="边缘计算与云计算的协同", help="当 mode=topic 时的主题")
	parser.add_argument("--output", type=str, default=None, help="视频输出路径(文件或目录)")
	args = parser.parse_args()
	if args.mode == "markdown":
		demo_markdown_to_video(output=args.output)
	else:
		demo_topic_to_video(topic=args.topic, output=args.output)

