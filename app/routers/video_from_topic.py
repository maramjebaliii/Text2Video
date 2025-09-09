from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.script_generate import generate_markdown_script
from app.core.pipeline import build_blocks_from_markdown
from app.core.video import assemble_video_from_blocks
from app.core.provider_factory import create_providers


router = APIRouter()


class TopicVideoRequest(BaseModel):
    topic: str
    language: str | None = "zh"
    max_sections: int | None = 5
    output: str | None = None


class VideoResponse(BaseModel):
    output_path: str
    blocks_count: int


@router.post("/from-topic", response_model=VideoResponse)
def video_from_topic(payload: TopicVideoRequest):
    if not payload.topic or not payload.topic.strip():
        raise HTTPException(status_code=400, detail="topic 不能为空")
    llm, tts, image = create_providers()
    markdown_text = generate_markdown_script(
        llm=llm, topic=payload.topic, language=payload.language or "zh", max_sections=payload.max_sections or 5
    )
    blocks = build_blocks_from_markdown(markdown_text, llm=llm, tts=tts, image=image)
    out = assemble_video_from_blocks(blocks, output_path=payload.output)
    return VideoResponse(output_path=str(out), blocks_count=len(blocks))
