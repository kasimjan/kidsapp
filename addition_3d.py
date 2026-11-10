"""3 + 2 = 5 in 3D, for children ages 5-8 (Kindergarten).

Quick preview (no narration audio; uses estimated timing, Milo, and subtitles):
    manimgl addition_3d.py Addition3D -w

Full lesson with a real English voice, synchronized subtitles and an .srt file:
    python -m kidsmath render --topic addition --grade 0 --numbers 3 2 --style 3d

Everything is built from the reusable framework in kidsmath/render3d/.
The original hand-written version is kept as addition_3d_v1.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kidsmath.lessons import generate_lesson
from kidsmath.render import timing
from kidsmath.render3d.scene3d import Lesson3DScene


class Addition3D(Lesson3DScene):
    def get_spec(self):
        spec = generate_lesson("addition", grade=0, numbers=[3, 2], style="3d")
        return timing.with_estimated_durations(spec)
