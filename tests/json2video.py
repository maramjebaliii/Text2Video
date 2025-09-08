"""入口脚本：通过函数调用启动从 JSON 生成视频的流程。"""

from tests.json2video import assemble_video_from_blocks
from pathlib import Path
import json


def main(json_file_path: str | None = None, output_path: str | None = None):
	"""读取 JSON 内容并调用 assemble_video_from_blocks。

	参数 json_file_path 可为文件或目录：
	- 如果为文件路径，则直接使用该文件（必须存在）。

	output_path 可选，用于指定最终视频输出路径。
	"""
	# 解析输入：json_file_path 必须为文件或目录
	if not json_file_path:
		raise RuntimeError('必须提供 JSON 文件路径或目录')

	p = Path(json_file_path)
	if not p.exists():
		raise RuntimeError(f'提供的路径不存在: {p}')

	if p.is_dir():
		json_files = list(p.glob('*.json'))
		if len(json_files) == 1:
			json_path_obj = json_files[0]
		elif len(json_files) == 0:
			raise RuntimeError(f'目录中没有 JSON 文件: {p}')
		else:
			raise RuntimeError(f'目录中存在多个 JSON 文件，请传入具体文件路径: {p}')
	else:
		json_path_obj = p

	with open(json_path_obj, 'r', encoding='utf-8') as f:
		blocks = json.load(f)

	assemble_video_from_blocks(blocks, output_path=output_path)


if __name__ == '__main__':
	# 直接运行时使用相对路径（相对于仓库根）
	main('merged_speech_and_images.json', output_path='./output/video.mp4')

