"""FastAPI backend: generate lessons and retrieve rendered videos.

Run:  uvicorn kidsmath.api:app --reload
Docs: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Literal

from fastapi import FastAPI, HTTPException, Path as PathParam
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from . import limits
from .lessons import TEMPLATES, generate_lesson
from .narration import MacSayBackend, SilentBackend
from .spec import LessonSpec
from .validate import SpecValidationError, validate_spec

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAX_PENDING = 20
LessonId = PathParam(pattern=r"^[0-9a-f]{32}$")


class LessonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = Field(examples=["addition"])
    grade: Literal[0, 1, 2] = Field(default=0, description="0 = Kindergarten")
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    numbers: list[int] | None = Field(default=None, max_length=3, examples=[[3, 2]])
    seed: int | None = None
    shape: str | None = Field(default=None, max_length=20)
    operation: Literal["add", "subtract"] | None = None
    mascot: Literal["milo", "none"] = Field(default="milo", description="who explains the lesson")
    style: Literal["2d", "3d"] = Field(default="2d", description="flat or 3D animation")
    voice: str = Field(default="Samantha", pattern=r"^[A-Za-z][A-Za-z ()-]{0,29}$")
    silent: bool = Field(default=False, description="skip text-to-speech")


class LessonStatus(BaseModel):
    id: str
    status: Literal["queued", "rendering", "done", "failed"]
    error: str | None = None
    video_url: str | None = None
    duration: float | None = None
    spec: LessonSpec | None = None


def _default_renderer(spec, out_path, voice, silent, cache_dir, style="2d"):
    from .render.pipeline import render_lesson
    backend = SilentBackend() if silent or not MacSayBackend.available() else MacSayBackend(voice)
    return render_lesson(spec, out_path, backend=backend, cache_dir=cache_dir, style=style)


def check_style_or_422(spec: LessonSpec, style: str) -> None:
    from .render.pipeline import check_style
    try:
        check_style(spec, style)
    except ValueError as e:
        raise HTTPException(422, str(e))


def create_app(output_dir: Path | None = None, renderer: Callable = _default_renderer) -> FastAPI:
    root = Path(output_dir or os.environ.get("KIDSMATH_OUTPUT_DIR", PROJECT_ROOT / "output")) / "lessons"
    root.mkdir(parents=True, exist_ok=True)
    cache_dir = root.parent / ".tts_cache"
    pool = ThreadPoolExecutor(max_workers=1)  # ManimGL renders are heavy: one at a time
    lock = threading.Lock()

    app = FastAPI(title="Kids Math Lessons", version="0.1.0",
                  description="Generate animated, narrated K-2 math videos.")

    def status_path(lid: str) -> Path:
        return root / lid / "status.json"

    def write_status(st: LessonStatus) -> None:
        p = status_path(st.id)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(st.model_dump_json())
        tmp.replace(p)

    def read_status(lid: str) -> LessonStatus:
        p = status_path(lid)
        if not p.exists():
            raise HTTPException(404, "lesson not found")
        return LessonStatus.model_validate_json(p.read_text())

    def pending_count() -> int:
        n = 0
        for p in root.glob("*/status.json"):
            try:
                if json.loads(p.read_text()).get("status") in ("queued", "rendering"):
                    n += 1
            except (OSError, ValueError):
                pass
        return n

    def enqueue(spec: LessonSpec, voice: str, silent: bool, style: str = "2d") -> LessonStatus:
        with lock:
            if pending_count() >= MAX_PENDING:
                raise HTTPException(429, "too many lessons are rendering; try again soon")
            lid = uuid.uuid4().hex
            st = LessonStatus(id=lid, status="queued", spec=spec)
            write_status(st)
        pool.submit(run_job, lid, spec, voice, silent, style)
        return st

    def run_job(lid: str, spec: LessonSpec, voice: str, silent: bool, style: str = "2d") -> None:
        st = read_status(lid)
        write_status(st.model_copy(update={"status": "rendering"}))
        try:
            result = renderer(spec, root / lid / "lesson.mp4", voice, silent, cache_dir, style)
            write_status(st.model_copy(update={
                "status": "done", "video_url": f"/lessons/{lid}/video",
                "duration": result.duration, "spec": result.spec}))
        except Exception as e:  # report any failure to the client instead of dying
            write_status(st.model_copy(update={"status": "failed", "error": str(e)[-1500:]}))

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/topics")
    def topics():
        return {
            "topics": sorted(TEMPLATES),
            "grades": limits.GRADE_NAMES,
            "difficulties": list(limits.DIFFICULTIES),
            "limits": {"max_add_sub": limits.MAX_ADD_SUB, "max_compare": limits.MAX_COMPARE,
                       "max_place_value": limits.MAX_PLACE_VALUE},
        }

    @app.post("/lessons", response_model=LessonStatus, status_code=202)
    def create_lesson(req: LessonRequest):
        """Generate a validated lesson from a topic and queue its video render."""
        try:
            spec = generate_lesson(req.topic, req.grade, req.difficulty, req.numbers,
                                   req.seed, req.shape, req.operation, req.mascot, req.style)
        except SpecValidationError as e:
            raise HTTPException(422, {"message": "lesson failed validation", "issues": e.issues})
        except ValueError as e:
            raise HTTPException(422, str(e))
        check_style_or_422(spec, req.style)
        return enqueue(spec, req.voice, req.silent, req.style)

    @app.post("/lessons/from-spec", response_model=LessonStatus, status_code=202)
    def create_from_spec(spec: LessonSpec, voice: str = "Samantha", silent: bool = False,
                         style: Literal["2d", "3d"] = "2d"):
        """Queue a render of a hand- or machine-written spec (validated first)."""
        try:
            validate_spec(spec)
        except SpecValidationError as e:
            raise HTTPException(422, {"message": "spec failed validation", "issues": e.issues})
        check_style_or_422(spec, style)
        return enqueue(spec, voice if voice.replace(" ", "").isalpha() else "Samantha", silent, style)

    @app.get("/lessons/{lesson_id}", response_model=LessonStatus)
    def get_lesson(lesson_id: str = LessonId):
        return read_status(lesson_id)

    @app.get("/lessons/{lesson_id}/spec", response_model=LessonSpec)
    def get_spec(lesson_id: str = LessonId):
        st = read_status(lesson_id)
        return st.spec

    @app.get("/lessons/{lesson_id}/video")
    def get_video(lesson_id: str = LessonId):
        st = read_status(lesson_id)
        if st.status == "failed":
            raise HTTPException(410, st.error or "render failed")
        video = root / lesson_id / "lesson.mp4"
        if st.status != "done" or not video.exists():
            raise HTTPException(409, f"video not ready (status: {st.status})")
        return FileResponse(video, media_type="video/mp4", filename=f"lesson_{lesson_id[:8]}.mp4")

    return app


app = create_app()
