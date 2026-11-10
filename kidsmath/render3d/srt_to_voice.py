"""Narrate an .srt with Kokoro TTS and mux the voice into a new MP4.

    python -m kidsmath.render3d.srt_to_voice output/add_3_2_3d.mp4
    python -m kidsmath.render3d.srt_to_voice video.mp4 --srt subs.srt --out voiced.mp4

Kokoro-82M (~330 MB) runs on CPU with well under 2 GB of RAM, so it fits an 8 GB Mac.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import srt

SAMPLE_RATE = 24000


def build_narration(srt_path: Path, voice: str = "af_heart", speed: float = 0.9) -> np.ndarray:
    from kokoro import KPipeline

    subtitles = list(srt.parse(srt_path.read_text(encoding="utf-8-sig")))
    if not subtitles:
        raise ValueError(f"no subtitles found in {srt_path}")

    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    segments: list[tuple[int, np.ndarray]] = []

    for sub in subtitles:
        chunks = [np.asarray(audio, dtype=np.float32)
                  for _, _, audio in pipeline(sub.content.replace("\n", " "),
                                              voice=voice, speed=speed)]
        if not chunks:
            continue
        audio = np.concatenate(chunks)
        start = int(sub.start.total_seconds() * SAMPLE_RATE)
        end = int(sub.end.total_seconds() * SAMPLE_RATE)
        if len(audio) > end - start:
            print(f"Warning: subtitle {sub.index} exceeds its time slot", file=sys.stderr)
        segments.append((start, audio))

    total = max(int(subtitles[-1].end.total_seconds() * SAMPLE_RATE),
                max((s + len(a) for s, a in segments), default=0))
    out = np.zeros(total, dtype=np.float32)
    for start, audio in segments:
        out[start:start + len(audio)] += audio
    return np.clip(out, -1, 1)


def mux(video: Path, wav: Path, out: Path) -> None:
    """Replace the video's audio track with `wav`; the video stream is copied untouched."""
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         str(out)],
        check=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("video", type=Path, help="input MP4")
    p.add_argument("--srt", type=Path, help="subtitle file (default: next to the video)")
    p.add_argument("--out", type=Path, help="output MP4 (default: <video>_voiced.mp4)")
    p.add_argument("--voice", default="af_heart")
    p.add_argument("--speed", type=float, default=0.9)
    args = p.parse_args(argv)

    srt_path = args.srt or args.video.with_suffix(".srt")
    out = args.out or args.video.with_name(args.video.stem + "_voiced.mp4")
    if not args.video.exists() or not srt_path.exists():
        print(f"error: need both {args.video} and {srt_path}", file=sys.stderr)
        return 2

    wav = out.with_suffix(".wav")
    audio = build_narration(srt_path, args.voice, args.speed)
    sf.write(wav, audio, SAMPLE_RATE)
    mux(args.video, wav, out)
    print(f"Wrote {out} (narration: {wav})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
