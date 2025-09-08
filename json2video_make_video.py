"""入口脚本：通过函数调用启动从 JSON 生成视频的流程。"""

from tests.json2video import assemble_video_from_blocks
from pathlib import Path
import json


DEFAULT_JSON_PATH = Path(r"merged_speech_and_images.json")


def main(json_file_path: str | None = None):
	"""读取 JSON 内容并调用 assemble_video_from_blocks。"""
	if json_file_path is None and DEFAULT_JSON_PATH.exists():
		json_file_path = str(DEFAULT_JSON_PATH)
	blocks = None
	if json_file_path:
		with open(json_file_path, 'r', encoding='utf-8') as f:
			blocks = json.load(f)
	else:
		raise RuntimeError('必须提供 JSON 文件路径或在项目根目录放置 merged_speech_and_images.json')
	assemble_video_from_blocks(blocks)


if __name__ == '__main__':
	main()

