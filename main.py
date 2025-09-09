"""Text2Video FastAPI 应用入口：在此定义 app 并挂载路由。"""
from __future__ import annotations

from fastapi import FastAPI
from dotenv import load_dotenv

# 先加载 .env，供路由中的 Provider 工厂读取
load_dotenv()

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

