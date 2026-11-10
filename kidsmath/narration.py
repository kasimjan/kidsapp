"""Text-to-speech narration. One WAV per step so each step can be timed exactly."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Protocol

import math

import numpy as np

from .spec import LessonSpec

SAMPLE_RATE = 22050


class TTSBackend(Protocol):
    name: str

    def synthesize(self, text: str, out_wav: Path) -> None: ...


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


class MacSayBackend:
    """Offline English voice from macOS `say`. Slower rate suits young listeners."""

    def __init__(self, voice: str = "Samantha", rate: int = 150):
        self.voice, self.rate = voice, rate
        self.name = f"say:{voice}:{rate}"

    @staticmethod
    def available() -> bool:
        return shutil.which("say") is not None

    def synthesize(self, text: str, out_wav: Path) -> None:
        # Arguments are passed as a list (no shell); the text follows '--' so it
        # can never be mistaken for an option.
        subprocess.run(
            ["say", "-v", self.voice, "-r", str(self.rate),
             "--file-format=WAVE", f"--data-format=LEI16@{SAMPLE_RATE}",
             "-o", str(out_wav), "--", text],
            check=True, capture_output=True, timeout=60,
        )


class SilentBackend:
    """Writes silence sized to the text. For tests and machines without TTS."""
    name = "silent"

    def __init__(self, words_per_second: float = 2.3):
        self.wps = words_per_second

    def synthesize(self, text: str, out_wav: Path) -> None:
        seconds = max(0.4, len(text.split()) / self.wps)
        with wave.open(str(out_wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(b"\x00\x00" * int(seconds * SAMPLE_RATE))


def default_backend(voice: str = "Samantha") -> TTSBackend:
    return MacSayBackend(voice) if MacSayBackend.available() else SilentBackend()


def synthesize_lesson(spec: LessonSpec, backend: TTSBackend, workdir: Path,
                      cache_dir: Path | None = None) -> list[Path]:
    """Produce one WAV per step; returns paths in step order."""
    workdir.mkdir(parents=True, exist_ok=True)
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, step in enumerate(spec.steps):
        out = workdir / f"step_{i:02d}.wav"
        key = hashlib.sha256(f"{backend.name}\0{step.narration}".encode()).hexdigest()[:24]
        cached = cache_dir / f"{key}.wav" if cache_dir else None
        if cached and cached.exists():
            shutil.copyfile(cached, out)
        else:
            backend.synthesize(step.narration, out)
            if cached:
                shutil.copyfile(out, cached)
        paths.append(out)
    return paths


def mouth_envelope(wav_path: Path, fps: int = 30) -> list[float]:
    """Mouth-openness (0..1) for each video frame, from the narration loudness.

    Silent audio (the SilentBackend) gets a gentle synthetic flap instead, so
    the mascot still looks like it is talking.
    """
    with wave.open(str(wav_path), "rb") as w:
        rate = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
    hop = max(1, rate // fps)
    n = len(data) // hop
    if n == 0:
        return []
    rms = np.sqrt((data[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
    peak = np.percentile(rms, 95)
    if peak < 50:  # silence
        return [round(0.5 + 0.5 * math.sin(i * 0.9), 3) * (0.6 + 0.4 * math.sin(i * 0.23)) for i in range(n)]
    env = np.clip(rms / peak, 0, 1)
    env = np.convolve(env, np.ones(3) / 3, mode="same")  # smooth jitter
    return [round(float(v), 3) for v in env]


def synthetic_envelope(seconds: float, fps: int = 30) -> list[float]:
    """Gentle talking motion for previews that have no audio."""
    n = int(seconds * fps)
    return [round(max(0.0, 0.5 + 0.5 * math.sin(i * 0.9)) * (0.6 + 0.4 * math.sin(i * 0.23)), 3) for i in range(n)]
