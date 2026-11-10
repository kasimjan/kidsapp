import json
import subprocess

import pytest

from kidsmath.lessons import generate_lesson
from kidsmath.narration import SilentBackend
from kidsmath.render.pipeline import render_lesson


@pytest.mark.slow
def test_render_3_plus_2(tmp_path):
    spec = generate_lesson("addition", 0, numbers=[3, 2])
    result = render_lesson(spec, tmp_path / "out.mp4", backend=SilentBackend())
    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
         "-of", "json", str(result.video)], capture_output=True, text=True, check=True).stdout)
    kinds = {s["codec_type"] for s in info["streams"]}
    assert kinds == {"video", "audio"}
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (1920, 1080)
    assert result.duration > 10


@pytest.mark.slow
def test_render_3d_with_subtitles(tmp_path):
    spec = generate_lesson("addition", 0, numbers=[3, 2], style="3d")
    result = render_lesson(spec, tmp_path / "out3d.mp4", backend=SilentBackend(), style="3d")
    srt = (tmp_path / "out3d.srt").read_text()
    assert "3 plus 2 equals 5!" in srt and "-->" in srt
    assert result.duration > 10
    # the subtitle track ends inside the video
    h, m, sec = srt.strip().split("\n")[-2].split(" --> ")[1].replace(",", ".").split(":")
    assert float(sec) + 60 * int(m) + 3600 * int(h) <= result.duration + 0.2
