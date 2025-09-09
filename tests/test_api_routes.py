


# 兼容未来的注解语法
from __future__ import annotations


# 导入标准库
import os
import sys
import time


# 检查并导入 requests 库
try:
	import requests
except Exception:  # pragma: no cover - helpful message when requests missing
	print("需要安装 'requests' 包。请使用: pip install requests")
	raise


# API 基础地址，可通过环境变量 BASE_URL 覆盖
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")



# 发送 POST 请求的辅助函数
def _post(path: str, payload: dict, timeout: float = 500) -> requests.Response:
	url = BASE_URL.rstrip("/") + path
	start = time.monotonic()
	resp = requests.post(url, json=payload, timeout=timeout)
	elapsed = time.monotonic() - start
	try:
		setattr(resp, "elapsed_seconds", elapsed)
	except Exception:
		pass
	print(f"[TIMING] POST {path} -> {resp.status_code} in {elapsed:.3f}s")
	return resp



# 测试：markdown 为空时，接口应返回 400 和正确的错误信息

# 测试：从 markdown 生成视频，应返回视频流
def test_from_markdown_basic():
	"""POST /video/from-markdown，传入 markdown 应返回视频流。"""
	r = _post("/video/from-markdown", {"markdown": """
                                    
                                    
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

了解这些基本概念后，你就可以开始评估云服务提供商并设计适合自己业务的云架构了。"""})
	if r.headers.get("Content-Type") == "video/mp4":
		with open("output_from_markdown.mp4", "wb") as f:
			f.write(r.content)
		print("已保存视频到 output_from_markdown.mp4")
	else:
		# 如果不是直接返回视频流，则应返回 400（参数为空时）。
		assert r.status_code == 400, f"预期 400，实际 {r.status_code}, body: {r.text}"
		data = r.json()
		assert data.get("detail") == "markdown 不能为空"



# 测试：从 topic 生成视频，应返回 200 和 JSON（包含输出路径与块数量）
def test_from_topic_basic():
	"""POST /video/from-topic，传入合法 topic 应返回 200 与结果 JSON。"""
	r = _post("/video/from-topic", {"topic": "边缘部署"})
	assert r.status_code == 200, f"预期 200，实际 {r.status_code}, body: {r.text}"
	data = r.json()
	# 返回的数据结构：{"output_path": str, "blocks_count": int}
	assert isinstance(data.get("output_path"), str) and data["output_path"].lower().endswith(".mp4"), "output_path 应为 mp4 文件路径"
	assert isinstance(data.get("blocks_count"), int) and data["blocks_count"] > 0, "blocks_count 应为正整数"



# 主程序入口，支持直接运行脚本进行测试
if __name__ == "__main__":
	# 需要测试的函数列表
	tests = [
	("test_from_markdown_basic", test_from_markdown_basic),
	("test_from_topic_basic", test_from_topic_basic),
	]
	failures = []
	print(f"Base URL: {BASE_URL}")
	for name, fn in tests:
		try:
			fn()
			print(f"{name}: 通过")
		except AssertionError as exc:
			print(f"{name}: 失败 -> {exc}")
			failures.append((name, exc))
		except Exception as exc:  # 网络或其他异常
			print(f"{name}: 错误 -> {exc}")
			failures.append((name, exc))

	if failures:
		print('\n汇总:')
		for name, exc in failures:
			print(f" - {name}: {exc}")
		sys.exit(1)
	print('\n所有测试通过')

