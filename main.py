"""Text2Video FastAPI 应用入口：在此定义 app 并挂载路由。"""
from __future__ import annotations

from fastapi import FastAPI
from dotenv import load_dotenv

# 先加载 .env，供路由中的 Provider 工厂读取
load_dotenv()

from app.core.provider_factory import configure_providers
import os
from pathlib import Path

# 优先尝试从根目录的 config.yaml 读取 provider 配置，如果不可用则回退到环境变量
_root = Path(__file__).resolve().parent.parent
_cfg_api_key = None
_cfg_base = None
try:
	import yaml

	cfg_path = _root / "config.yaml"
	if cfg_path.exists():
		with cfg_path.open("r", encoding="utf-8") as f:
			data = yaml.safe_load(f) or {}
			_cfg_api_key = data.get("GUIJI_API_KEY")
			_cfg_base = data.get("GUIJI_BASE_URL") or data.get("GUIJI_BASE_URL")
except Exception:
	# 无 PyYAML 或解析异常时，保持为 None 并回退到环境变量
	_cfg_api_key = None
	_cfg_base = None

# 最终注入（优先使用 yaml 中的值）
configure_providers(api_key=_cfg_api_key or os.getenv("GUIJI_API_KEY"), base_url=_cfg_base or os.getenv("GUIJI_BASE_URL"))

# 创建应用
app = FastAPI(title="Text2Video API", version="0.1.0")

# 挂载路由
from app.routers.video_from_markdown import router as markdown_router  
from app.routers.video_from_topic import router as topic_router 

app.include_router(markdown_router, prefix="/video", tags=["video"]) 
app.include_router(topic_router, prefix="/video", tags=["video"]) 

# 可选：支持直接运行启动开发服务器（uvicorn）
if __name__ == "__main__":
	import uvicorn

	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

