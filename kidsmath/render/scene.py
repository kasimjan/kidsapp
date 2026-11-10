"""ManimGL scene that interprets a LessonSpec.

Run through `kidsmath.render.pipeline` (which sets KIDSMATH_SPEC); never from
untrusted code. The spec is re-validated here, and the only things it can do
are the fixed actions handled in `_do_*` below.
"""
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from manimlib import *  # noqa: F401,F403  (ManimGL scene API)

from kidsmath import spec as S
from kidsmath.render import layout, timing
from kidsmath.render.mascot import attach_milo
from kidsmath.validate import validate_spec

INK = "#2B2D42"
PALETTE = {
    "red": "#EF476F", "orange": "#FF9F1C", "yellow": "#FFD23F", "green": "#2EC4B6",
    "blue": "#3A86FF", "purple": "#8338EC", "pink": "#FF70A6", "teal": "#06B6D4",
}
FONT = "Arial Rounded MT Bold"
EPS = 1e-3  # keeps ManimGL's np.arange from adding an extra frame


def label(text, size, color=INK):
    t = Text(text, font=FONT, font_size=size)
    t.set_color(color)  # Text ignores a color= kwarg in ManimGL 1.7
    return t


def make_object(shape, color):
    c = PALETTE[color]
    if shape == "circle":
        m = Circle(radius=0.42)
    elif shape == "square":
        m = Square(side_length=0.78)
    elif shape == "triangle":
        m = RegularPolygon(3, radius=0.55)
    elif shape == "star":
        pts = []
        for k in range(10):
            r = 0.52 if k % 2 == 0 else 0.22
            a = math.pi / 2 + k * math.pi / 5
            pts.append([r * math.cos(a), r * math.sin(a), 0])
        m = Polygon(*pts)
    else:  # heart
        t = np.linspace(0, 2 * math.pi, 60)
        x = 16 * np.sin(t) ** 3
        y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
        m = VMobject()
        m.set_points_smoothly(np.array([[a, b, 0] for a, b in zip(x, y)]) * 0.027)
    m.set_fill(c, opacity=1)
    m.set_stroke(INK, width=2, opacity=0.35)
    return m


def make_shape(name, color):
    if name == "circle":
        m = Circle(radius=1.6)
    elif name == "square":
        m = Square(side_length=3.0)
    elif name == "rectangle":
        m = Rectangle(width=4.6, height=2.6)
    else:
        m = RegularPolygon({"triangle": 3, "pentagon": 5, "hexagon": 6}[name], radius=2.0)
    m.set_fill(PALETTE[color], opacity=0.85)
    m.set_stroke(INK, width=5)
    m.move_to([0, 0.2, 0])
    return m


def make_blocks(h, t, o):
    parts = []
    if h:
        flats = VGroup(*[Square(0.6).set_fill(PALETTE["blue"], 1).set_stroke(INK, 2) for _ in range(h)])
        parts.append(flats.arrange(RIGHT, buff=0.1))
    lower = []
    if t:
        rods = VGroup()
        for _ in range(t):
            rod = Rectangle(0.22, 1.3).set_fill(PALETTE["orange"], 1).set_stroke(INK, 2)
            ticks = VGroup(*[Line(rod.get_corner(DL) + RIGHT * 0 + UP * 0.13 * k,
                                  rod.get_corner(DR) + UP * 0.13 * k).set_stroke(INK, 1, 0.5)
                             for k in range(1, 10)])
            rods.add(VGroup(rod, ticks))
        lower.append(rods.arrange(RIGHT, buff=0.1))
    if o:
        cubes = VGroup(*[Square(0.22).set_fill(PALETTE["green"], 1).set_stroke(INK, 2) for _ in range(o)])
        lower.append(cubes.arrange_in_grid(n_cols=3, buff=0.08))
    if lower:
        parts.append(VGroup(*lower).arrange(RIGHT, buff=0.5, aligned_edge=DOWN))
    if not parts:
        parts.append(label("0", 60))
    return VGroup(*parts).arrange(DOWN, buff=0.4)


class LessonScene(Scene):
    def construct(self):
        spec = validate_spec(S.LessonSpec.model_validate_json(
            Path(os.environ["KIDSMATH_SPEC"]).read_text()))
        self.groups = {}      # name -> list of mobjects (objects) or [VGroup] (blocks)
        self.alive = {}       # name -> objects not yet crossed out
        self.captions = {}    # region -> Text
        self.title_mob = None
        self.equation_mob = None
        self.sign_mob = None
        self.shape_key = None
        self.shape_mob = None
        self.shape_name = None
        self.overlays = []
        self._start_mascot(spec)

        for step in spec.steps:
            used = 0.0
            for action in step.actions:
                t = timing.action_time(action)
                self._run(action, t)
                used += t
            rest = step.duration - used
            if rest > EPS:
                self.wait(rest - EPS)
        self.wait(timing.FINAL_HOLD - EPS)

    # ---- mascot ----
    def _start_mascot(self, spec):
        envelopes = []
        path = os.environ.get("KIDSMATH_SIDECAR")
        if path and Path(path).exists():
            envelopes = json.loads(Path(path).read_text())["envelope"]
        self.mascot = attach_milo(self, spec, envelopes)

    # ---- helpers ----
    def _lead_out(self):
        """Animations that clear the title card, if one is showing."""
        if self.title_mob is None:
            return []
        out, self.title_mob = FadeOut(self.title_mob), None
        return [out]

    def _run(self, a, t):
        handler = getattr(self, "_do_" + a.type)
        anims = handler(a, t)
        if anims:
            self.play(*anims, run_time=t - EPS)
        else:
            self.wait(t - EPS)

    # ---- actions: each returns a list of animations ----
    def _do_title(self, a, t):
        self.title_mob = label(a.text, 96, PALETTE["purple"]).move_to([0, 0.5, 0])
        return [FadeIn(self.title_mob, scale=0.7)]

    def _do_text(self, a, t):
        anims = self._lead_out()
        old = self.captions.get(a.region)
        if old is not None and a.replace:
            anims.append(FadeOut(old))
        mob = label(a.text, 72, PALETTE[a.color]).move_to([0, layout.CAPTION_Y[a.region], 0])
        self.captions[a.region] = mob
        anims.append(FadeIn(mob, shift=0.2 * UP))
        return anims

    def _do_objects(self, a, t):
        anims = self._lead_out()
        pts = layout.group_positions(a.count, a.position)
        objs = [make_object(a.shape, a.color).move_to([x, y, 0]) for x, y in pts]
        self.groups[a.group] = objs
        self.alive[a.group] = list(objs)
        anims.append(LaggedStart(*[FadeIn(o, scale=0.3) for o in objs], lag_ratio=0.15))
        return anims

    def _do_count_item(self, a, t):
        obj = self.groups[a.group][a.index - 1]
        num = label(str(a.number or a.index), 52).next_to(obj, UP, buff=0.12)
        return [FadeIn(num, shift=0.15 * DOWN), obj.animate.set_stroke(INK, 5, 1.0)]

    def _do_merge(self, a, t):
        target, source = self.groups[a.target], self.groups[a.source]
        pts = layout.merged_positions(len(target) + len(source))
        return [o.animate.move_to([x, y, 0]) for o, (x, y) in zip(target + source, pts)]

    def _do_cross_out(self, a, t):
        victims = self.alive[a.group][-a.count:]
        self.alive[a.group] = self.alive[a.group][:-a.count]
        crosses = [Cross(o, stroke_color=PALETTE["red"], stroke_width=[0, 7, 0]) for o in victims]
        return [LaggedStart(*[ShowCreation(c) for c in crosses], lag_ratio=0.3)] + \
               [o.animate.set_opacity(0.35) for o in victims]

    def _do_equation(self, a, t):
        anims = self._lead_out()
        if self.equation_mob is not None:
            anims.append(FadeOut(self.equation_mob))
        self.equation_mob = label(a.text, 88, PALETTE[a.color]).move_to([0, layout.EQUATION_Y, 0])
        anims.append(Write(self.equation_mob))
        return anims

    def _do_sign(self, a, t):
        self.sign_mob = label(a.sign, 150, PALETTE["purple"]).move_to([0, layout.OBJECT_Y, 0])
        return [FadeIn(self.sign_mob, scale=0.3)]

    def _do_shape(self, a, t):
        anims = self._lead_out()
        anims += [FadeOut(m) for m in self.overlays]
        self.overlays = []
        key = (a.name, a.color)
        if key != self.shape_key:
            if self.shape_mob is not None:
                anims += [FadeOut(self.shape_mob), FadeOut(self.shape_name)]
            self.shape_mob = make_shape(a.name, a.color)
            self.shape_name = label(a.name.title(), 64).move_to([0, -2.6, 0])
            self.shape_key = key
            anims += [ShowCreation(self.shape_mob), FadeIn(self.shape_name, shift=0.2 * UP)]
        if a.highlight != "none" and a.name != "circle":
            verts = list(self.shape_mob.get_vertices())
            if a.highlight == "sides":
                colors = [PALETTE[c] for c in ("red", "yellow", "green", "purple", "pink", "teal")]
                for i, v in enumerate(verts):
                    line = Line(v, verts[(i + 1) % len(verts)]).set_stroke(colors[i % 6], 12)
                    self.overlays.append(line)
                anims.append(LaggedStart(*[ShowCreation(m) for m in self.overlays], lag_ratio=0.3))
            else:
                for v in verts:
                    self.overlays.append(Dot(v, radius=0.17).set_fill(PALETTE["red"], 1).set_stroke(INK, 3))
                anims.append(LaggedStart(*[FadeIn(m, scale=0.2) for m in self.overlays], lag_ratio=0.3))
        return anims

    def _do_blocks(self, a, t):
        anims = self._lead_out()
        old = self.groups.get(a.group)
        if old:
            anims += [FadeOut(m) for m in old]
        mob = make_blocks(a.hundreds, a.tens, a.ones)
        max_w = 11.0 if a.position == "center" else 4.8
        mob.scale(min(1.5, max_w / mob.get_width()))
        mob.move_to([layout.ANCHOR_X[a.position], 0.45, 0])
        self.groups[a.group] = [mob]
        anims.append(FadeIn(mob, scale=0.8))
        return anims

    def _do_clear(self, a, t):
        everything = [m for m in self.mobjects if m is not self.mascot]
        self.groups, self.alive, self.captions = {}, {}, {}
        self.title_mob = self.equation_mob = self.sign_mob = None
        self.shape_key = self.shape_mob = self.shape_name = None
        self.overlays = []
        return [FadeOut(m) for m in everything]
