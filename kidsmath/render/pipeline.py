"""End-to-end rendering: spec -> narration -> ManimGL video -> muxed MP4."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..narration import TTSBackend, default_backend, mouth_envelope, synthesize_lesson, wav_duration
from ..spec import LessonSpec
from ..validate import validate_spec
from ..render3d.subtitles import build_cues, to_srt
from . import timing

ROOT = Path(__file__).resolve().parents[1]
# style -> (scene file, scene class, background color)
STYLES = {
    "2d": (ROOT / "render" / "scene.py", "LessonScene", "#FFF6E5"),
    "3d": (ROOT / "render3d" / "scene3d.py", "Lesson3DScene", "#E6F4FF"),
}
UNSUPPORTED_3D = {"shape": "shapes", "blocks": "tens-and-ones blocks"}
RENDER_TIMEOUT = 900


class RenderError(RuntimeError):
    pass


@dataclass
class RenderResult:
    video: Path
    spec: LessonSpec
    duration: float


def check_style(spec: LessonSpec, style: str) -> None:
    if style not in STYLES:
        raise ValueError(f"style must be one of {sorted(STYLES)}")
    if style == "3d":
        bad = sorted({UNSUPPORTED_3D[a.type] for st in spec.steps for a in st.actions
                      if a.type in UNSUPPORTED_3D})
        if bad:
            raise ValueError(f"3D style does not support {', '.join(bad)} yet; use style '2d'")


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True, timeout=30).stdout
    return float(out.strip())


def with_durations(spec: LessonSpec, audio_paths: list[Path]) -> LessonSpec:
    """Copy of the spec whose steps last exactly as long as their narration needs."""
    steps = [
        s.model_copy(update={"duration": timing.step_duration(s, wav_duration(p))})
        for s, p in zip(spec.steps, audio_paths)
    ]
    return spec.model_copy(update={"steps": steps})


def _mux(video: Path, audio_paths: list[Path], spec: LessonSpec, out: Path) -> None:
    durations = [s.duration for s in spec.steps]
    durations[-1] += timing.FINAL_HOLD
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(video)]
    for p in audio_paths:
        cmd += ["-i", str(p)]
    parts = [f"[{i + 1}:a]apad=whole_dur={d:.4f}[a{i}]" for i, d in enumerate(durations)]
    concat = "".join(f"[a{i}]" for i in range(len(durations)))
    graph = ";".join(parts) + f";{concat}concat=n={len(durations)}:v=0:a=1[aout]"
    cmd += ["-filter_complex", graph, "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest",
            "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, capture_output=True, timeout=300)


def render_lesson(spec: LessonSpec, out_path: Path, backend: TTSBackend | None = None,
                  workdir: Path | None = None, cache_dir: Path | None = None,
                  keep_workdir: bool = False, style: str = "2d") -> RenderResult:
    """Render `spec` to `out_path` (MP4 with narration + .srt). Raises RenderError."""
    validate_spec(spec)
    check_style(spec, style)
    scene_file, scene_class, background = STYLES[style]
    backend = backend or default_backend()
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    own_tmp = workdir is None
    work = Path(workdir or tempfile.mkdtemp(prefix="kidsmath_")).resolve()
    work.mkdir(parents=True, exist_ok=True)
    try:
        audio = synthesize_lesson(spec, backend, work / "audio", cache_dir)
        timed = with_durations(spec, audio)
        spec_file = work / "spec.json"
        spec_file.write_text(timed.model_dump_json(indent=2))

        sidecar = work / "sidecar.json"
        sidecar.write_text(json.dumps({
            "envelope": [mouth_envelope(p, timing.FPS) for p in audio],
            "audio_seconds": [wav_duration(p) for p in audio],
        }))
        env = {**os.environ, "KIDSMATH_SPEC": str(spec_file), "KIDSMATH_SIDECAR": str(sidecar)}
        cmd = [sys.executable, "-W", "ignore", "-m", "manimlib", str(scene_file), scene_class,
               "-w", "-q", "-r", "1920x1080",  # fps: ManimGL default (30); its --fps flag is broken in 1.7.2
               
               "-c", background, "--video_dir", str(work), "--file_name", "silent"]
        proc = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True,
                              timeout=RENDER_TIMEOUT)
        silent = work / "silent.mp4"
        if proc.returncode != 0 or not silent.exists():
            raise RenderError(f"ManimGL failed (exit {proc.returncode}):\n{proc.stderr[-2000:]}")

        _mux(silent, audio, timed, out_path)
        starts = [sum(x.duration for x in timed.steps[:i]) for i in range(len(timed.steps))]
        cues = build_cues([x.narration for x in timed.steps], starts, [wav_duration(p) for p in audio])
        out_path.with_suffix(".srt").write_text(to_srt(cues))
        duration = probe_duration(out_path)
        expected = sum(s.duration for s in timed.steps) + timing.FINAL_HOLD
        if abs(duration - expected) > 0.25:
            raise RenderError(f"video is {duration:.2f}s but narration timeline is {expected:.2f}s")
        return RenderResult(out_path, timed, duration)
    except subprocess.CalledProcessError as e:
        raise RenderError(f"{e.cmd[0]} failed: {(e.stderr or b'').decode(errors='replace')[-1500:]}") from e
    finally:
        if own_tmp and not keep_workdir:
            shutil.rmtree(work, ignore_errors=True)
