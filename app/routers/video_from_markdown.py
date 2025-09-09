from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.pipeline import build_blocks_from_markdown
from app.core.video import assemble_video_from_blocks
from app.core.provider_factory import create_providers


router = APIRouter()


class MarkdownVideoRequest(BaseModel):
    markdown: str
    output: str | None = None  # 可为文件或目录




# 修改接口，直接返回视频文件流
@router.post("/from-markdown")
def video_from_markdown(payload: MarkdownVideoRequest):
    if not payload.markdown or not payload.markdown.strip():
        raise HTTPException(status_code=400, detail="markdown 不能为空")
    llm, tts, image = create_providers()
    blocks = build_blocks_from_markdown(payload.markdown, llm=llm, tts=tts, image=image)
    out = assemble_video_from_blocks(blocks, output_path=payload.output)
    # 直接返回 mp4 文件流
    return FileResponse(
        path=str(out),
        media_type="video/mp4",
        filename="result.mp4"
    )
