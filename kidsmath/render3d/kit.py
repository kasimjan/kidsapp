"""Reusable ManimGL building blocks for child-friendly 3D lessons (original code).

Techniques studied in 3b1b/videos and re-implemented here from scratch:
Surface shading (`set_shading`), `fix_in_frame` HUD, camera `reorient`,
`z_index` ordering, and `UpdateFromAlphaFunc` for custom easing.
"""
import math

import numpy as np
from manimlib import *  # noqa: F401,F403

from kidsmath.render3d.projection import project_point
from kidsmath.render3d.subtitles import active_word, word_windows, wrap_words

INK = "#2B2D42"
BACKGROUND = "#E6F4FF"
GROUND = "#FFF1D6"
COLORS = {
    "red": "#FF4D5E", "orange": "#FF9A3C", "yellow": "#FFC928", "green": "#34C98B",
    "blue": "#3D8BFF", "purple": "#9B5DE5", "pink": "#FF7EB6", "teal": "#1CC7D0",
}
FONT = "Arial Rounded MT Bold"
HUD_Z = 100            # draw order: HUD above every 3D object
RADIUS = 0.46          # ball radius; other toys are sized to match
SHADING = (0.25, 0.6, 0.3)   # reflectiveness, gloss, shadow: a glossy toy look
FLAT_FACE_SHADING = (0.2, 0.25, 0.3)  # flat tops would wash out with strong gloss


def hud(mob, z=HUD_Z):
    """Pin a mobject to the screen (ignores the 3D camera) and keep it on top."""
    mob.fix_in_frame()
    mob.set_z_index(z)
    return mob


def label(text, size, color=INK):
    t = Text(text, font=FONT, font_size=size)
    t.set_color(color)  # Text ignores a color= kwarg in ManimGL 1.7
    return t


# ---------------------------------------------------------------- toys

def make_body(shape: str, color: str):
    c = COLORS[color]
    if shape in ("circle", "heart"):
        body = Sphere(radius=RADIUS, resolution=(64, 32))
    elif shape == "square":
        body = Cube(color=c, side_length=0.8, shading=SHADING)
    elif shape == "triangle":
        # ManimGL's Cone is an open shell (base at z=-0.5, apex at z=1.5): cap the base.
        base = Disk3D(radius=1).shift(-0.5 * OUT)
        body = Group(Cone(resolution=(64, 12)), base)
        body.set_width(0.98)
    else:  # star -> a thick golden coin: a Cylinder is only the side wall, so add both faces
        h, r = 0.22, 0.47
        body = Group(Cylinder(height=h, radius=r, resolution=(64, 6)),
                     Disk3D(radius=r).shift(h / 2 * OUT), Disk3D(radius=r).shift(-h / 2 * OUT))
    body.set_color(c)
    body.set_shading(*(FLAT_FACE_SHADING if shape in ("triangle", "star") else SHADING))
    body.move_to(ORIGIN)
    return body


class Token(Group):
    """A toy standing on the ground with a soft shadow that follows it.

    Animate `token.body` (lift, scale, move); the shadow keeps up by itself.
    """

    def __init__(self, shape: str, color: str, ground_xy=(0.0, 0.0)):
        self.body = make_body(shape, color)
        self.rest_z = self.body.get_depth() / 2
        self.shape_name, self.color_name = shape, color
        self._base_width = self.body.get_width()
        # two stacked discs give a soft-edged contact shadow
        self.shadow = Group(*[Circle(radius=0.5).set_fill(INK, opacity=0.1).set_stroke(width=0)
                              for _ in range(2)])
        super().__init__(self.shadow, self.body)
        self.body.move_to([ground_xy[0], ground_xy[1], self.rest_z])
        self.shadow.add_updater(self._follow)
        self._follow(self.shadow)

    def _follow(self, shadow, dt=0):
        x, y, z = self.body.get_center()
        lift = max(0.0, z - self.rest_z)
        size = max(0.01, self.body.get_width() / self._base_width)
        shown = self.body_opacity()
        base = RADIUS * 1.8 * (1 + 0.25 * lift) * size
        fade = max(0.03, 1 / (1 + 1.2 * lift)) * min(1.0, size) * shown
        for disc, scale, op in zip(shadow, (1.0, 0.68), (0.07, 0.09)):
            disc.set_width(base * scale)
            disc.set_fill(INK, opacity=op * fade)
            disc.move_to([x, y, 0.012])

    def body_opacity(self) -> float:
        try:
            return float(np.clip(self.body.get_opacity(), 0, 1))
        except Exception:
            return 1.0

    def ground_position(self):
        x, y, _ = self.body.get_center()
        return np.array([x, y, self.rest_z])


def make_stage():
    """Soft sand-colored play mat with target rings."""
    disc = Circle(radius=11).set_fill(GROUND, opacity=1).set_stroke(width=0)
    disc.move_to([0, 0, -0.02])
    rings = Group(*[
        Circle(radius=r).set_fill(opacity=0).set_stroke("#FFE0A6", width=4, opacity=0.8).move_to([0, 0, -0.01])
        for r in (3.0, 5.2, 7.4)
    ])
    return Group(disc, rings)


# -------------------------------------------------------------- tags & HUD

class Badge(Group):
    """A round number badge pinned to the screen, glued to a 3D point."""

    def __init__(self, text: str, color: str, anchor_fn, frame, offset=0.78):
        circle = Circle(radius=0.34).set_fill(WHITE, 1).set_stroke(COLORS[color], width=8)
        num = label(text, 44, INK)
        num.move_to(circle)
        super().__init__(circle, num)
        self.frame, self.anchor_fn, self.offset = frame, anchor_fn, offset
        hud(self)
        self.add_updater(self._track)
        self._track(self)

    def _track(self, m, dt=0):
        p = np.array(self.anchor_fn()) + OUT * self.offset
        f = self.frame
        x, y = project_point(f.get_view_matrix(), f.get_scale(), f.get_focal_distance(), p)
        m.move_to([x, y, 0])


class Subtitle(Group):
    """Karaoke-style subtitle bar: spoken words light up as the voice says them."""

    def __init__(self, text: str, audio_seconds: float, start_time: float, clock, duration: float = 4.0):
        lines = wrap_words(text, 46)
        rows = []
        self.words = []
        for line in lines:
            row = Group(*[label(w, 38, WHITE) for w in line]).arrange(RIGHT, buff=0.16)
            rows.append(row)
            self.words += list(row)
        block = Group(*rows).arrange(DOWN, buff=0.1, aligned_edge=ORIGIN)
        bar = RoundedRectangle(width=block.get_width() + 0.7, height=block.get_height() + 0.4,
                               corner_radius=0.28)
        bar.set_fill(INK, opacity=0.8).set_stroke(width=0)
        bar.move_to(block)
        super().__init__(bar, block)
        self.move_to([0.4, -3.25, 0])
        flat = [w for line in lines for w in line]
        self.windows = word_windows(flat, audio_seconds)
        self.start_time, self.clock, self.duration = start_time, clock, duration
        self.bar = bar
        hud(self)
        self.add_updater(self._highlight)
        self._highlight(self)

    def _highlight(self, m, dt=0):
        now = self.clock() - self.start_time
        fade = min(1.0, max(0.0, now / 0.15), max(0.0, (self.duration - now) / 0.15))
        i = active_word(self.windows, now)
        self.bar.set_fill(INK, opacity=0.8 * fade)
        for k, w in enumerate(self.words):
            if k == i:
                w.set_color(COLORS["yellow"]).set_opacity(fade)
            elif k < i:
                w.set_color(WHITE).set_opacity(fade)
            else:
                w.set_color(WHITE).set_opacity(0.55 * fade)


# ----------------------------------------------------------------- effects

def arc_move(body, target, lift=0.6):
    """Move a body to `target` along a hop (start/end remembered at creation)."""
    start = body.get_center().copy()
    target = np.array(target, dtype=float)

    def update(m, alpha):
        a = smooth(alpha)
        pos = (1 - a) * start + a * target
        pos[2] += lift * math.sin(math.pi * a)
        m.move_to(pos)
    return UpdateFromAlphaFunc(body, update)


def drop_in(token: Token, height=3.2):
    """Fall from above with a squash-free bounce while fading in."""
    final = token.body.get_center().copy()
    token.body.move_to(final + OUT * height)

    def update(m, alpha):
        a = min(1.0, alpha / 0.72)
        z = height * (1 - a) ** 2 if alpha < 0.72 else 0.28 * math.sin((alpha - 0.72) / 0.28 * math.pi) * 0.6
        m.move_to(final + OUT * max(z, 0))
        m.set_opacity(min(1.0, alpha * 4))
    return UpdateFromAlphaFunc(token.body, update)


def hop(body, height=0.55):
    """Jump up and land back on the same spot (with a little squash on landing)."""
    start = body.get_center().copy()

    def update(m, alpha):
        m.move_to(start + OUT * height * math.sin(math.pi * alpha))
    return UpdateFromAlphaFunc(body, update)


def spotlight_ring(token: Token, color="yellow"):
    ring = Circle(radius=0.74).set_fill(opacity=0).set_stroke(COLORS[color], width=16)
    ring.add_updater(lambda r: r.move_to([*token.body.get_center()[:2], 0.03]))
    ring.move_to([*token.body.get_center()[:2], 0.03])
    return ring


def sparkles(center, n=18, seed=3):
    """Small glowing confetti floating above the toys."""
    rng = np.random.default_rng(seed)
    dots = Group()
    names = list(COLORS)
    for i in range(n):
        d = GlowDot(radius=0.2, color=COLORS[names[i % len(names)]])
        d.move_to(center + np.array([rng.uniform(-4.0, 4.0), rng.uniform(-1.2, 1.4), rng.uniform(1.4, 3.0)]))
        dots.add(d)
    return dots
