"""FastAPI server exposing the governed MiniMax agent over a chat interface."""

from __future__ import annotations

import asyncio
import base64
import uuid
from pathlib import Path
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator

from governed_agent import invoke_agent
from minimax_media import (
    MiniMaxAPIError,
    MiniMaxConfigError,
    generate_video,
    text_to_speech,
)

# ── Models ───────────────────────────────────────────────────────────────────


class ChatMessage(BaseModel):
    role: str = Field(pattern=r"^(user|ai|system|tool)$", description="message role")
    content: str = Field(min_length=1, description="message content")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="latest user message")
    session_id: Optional[str] = Field(default=None, description="client session identifier")
    history: List[ChatMessage] = Field(default_factory=list, description="prior chat history")

    @validator("history")
    def ensure_alternating_roles(cls, value: List[ChatMessage]):  # noqa: N805 (pydantic requirement)
        # Optional: sanity check alternating user/ai roles
        if not value:
            return value
        # Only allow roles from the set; pattern already enforces, but ensure semantics
        allowed = {"user", "ai", "system", "tool"}
        for msg in value:
            if msg.role not in allowed:
                raise ValueError(f"Unsupported role: {msg.role}")
        return value


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    messages: List[ChatMessage]


class AudioRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000, description="text to synthesize")
    voice_id: Optional[str] = Field(default=None, description="MiniMax voice id")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="speech speed")


class AudioResponse(BaseModel):
    audio_base64: str = Field(description="base64-encoded mp3 audio")
    mime_type: str = "audio/mpeg"


class VideoRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000, description="video prompt")
    duration: int = Field(default=6, ge=1, le=10, description="clip length in seconds")
    resolution: str = Field(default="768P", description="video resolution")


class VideoResponse(BaseModel):
    download_url: str = Field(description="URL to the generated mp4 video")


# ── FastAPI application ──────────────────────────────────────────────────────

app = FastAPI(title="MiniMax OpenBox Agent", version="1.0.0")

# Allow local dev UIs to hit the API; adjust origins as needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend assets (SPA-like chat UI)
static_dir = Path(__file__).parent / "web"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")


@app.get("/", response_class=HTMLResponse)
async def root_page():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>MiniMax OpenBox Agent</h1><p>Frontend bundle not found.</p>")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid.uuid4())

    history_payload: List[ChatMessage] = request.history.copy()
    history_payload.append(ChatMessage(role="user", content=request.message))

    try:
        final, _ = await invoke_agent(
            [(msg.role, msg.content) for msg in history_payload],
            session_id=session_id,
        )
    except RuntimeError as exc:  # propagate safe message to client
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not final:
        raise HTTPException(status_code=502, detail="Agent returned no response")

    history_payload.append(ChatMessage(role="ai", content=final))

    return ChatResponse(session_id=session_id, reply=final, messages=history_payload)


@app.post("/api/audio", response_model=AudioResponse)
async def audio(request: AudioRequest) -> AudioResponse:
    """Generate speech audio from text using MiniMax Text-to-Speech."""
    try:
        kwargs = {"speed": request.speed}
        if request.voice_id:
            kwargs["voice_id"] = request.voice_id
        audio_bytes = await text_to_speech(request.text, **kwargs)
    except MiniMaxConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (MiniMaxAPIError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"MiniMax API error: {exc.response.status_code} {exc.response.text}",
        ) from exc

    encoded = base64.b64encode(audio_bytes).decode("ascii")
    return AudioResponse(audio_base64=encoded)


@app.post("/api/video", response_model=VideoResponse)
async def video(request: VideoRequest) -> VideoResponse:
    """Generate a short video from a text prompt using MiniMax video models."""
    try:
        download_url = await generate_video(
            request.prompt,
            duration=request.duration,
            resolution=request.resolution,
        )
    except MiniMaxConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (MiniMaxAPIError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"MiniMax API error: {exc.response.status_code} {exc.response.text}",
        ) from exc

    return VideoResponse(download_url=download_url)


# Convenience entry point for `python server.py`
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
