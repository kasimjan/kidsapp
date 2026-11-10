"""Let's Solve 7 + 5! A make-ten explainer for ages 6-8 (Grades 1-2).

Beat sheet (one beat per narration line in narration.md)
  hook   : "Can you solve this?"  7 + 5 = ?  appears token by token
  sevens : seven red apples pop in, "7" above, counted 1..7
  fives  : the row slides left, five green apples are added, "7 + 5" at the bottom
  tens   : apples move into a ten-frame; 3 greens fill it (7 + 3 = 10); 2 are left (10 + 2 = 12)
  win    : "7 + 5 = 12", all twelve apples in a neat 2 x 6 grid, confetti
  recap  : 7 + 5 / = 7 + 3 + 2 / = 10 + 2 / = 12  and "Make ten!"

Every apple count is built from the constants below, so the picture always matches the maths.
"""
import random

from st_manim import *

A, B = 7, 5                     # the problem
TEN = 10
LEFT_OVER = A + B - TEN         # 2
TAKE = TEN - A                  # 3 green apples travel to the red group

BG = "#22307A"
RED_C = "#FF5A5F"
GREEN_C = "#5BD96A"
YELLOW_C = "#FFD93D"
PINK_C = "#FF8FD2"
SKY_C = "#6EC8FF"

SPACING = 0.95                  # apple centre to apple centre in a row
ROW_Y = -0.2


# ---------------------------------------------------------------- reusable builders
def apple(color):
    """A friendly apple: round body, brown stem, green leaf, white outline."""
    body = Circle(radius=0.4, fill_color=color, fill_opacity=1, stroke_color=WHITE, stroke_width=3)
    stem = Line(body.get_top() + DOWN * 0.03, body.get_top() + UP * 0.14, color="#7A4A21", stroke_width=5)
    leaf = Ellipse(width=0.26, height=0.13, fill_color="#3DBE55", fill_opacity=1, stroke_width=0)
    leaf.rotate(0.5).move_to(body.get_top() + UP * 0.1 + RIGHT * 0.13)
    shine = Circle(radius=0.07, fill_color=WHITE, fill_opacity=0.55, stroke_width=0)
    shine.move_to(body.get_center() + UL * 0.2)
    return VGroup(body, stem, leaf, shine)


def token(text, color=WHITE, scale=1.0):
    m = title(text)
    m.set_color(color)
    return m.scale(scale)


def eq_row(items, scale=1.0, buff=0.3):
    """items: [(text, color), ...] -> one row of big friendly text tokens."""
    return VGroup(*[token(t, c, scale) for t, c in items]).arrange(RIGHT, buff=buff)


def count_label(n):
    return token(str(n), WHITE, 0.7)


def at_xy(mob, x, y):
    return mob.move_to(np.array([x, y, 0.0]))


def grid_pos(k, per_row=6, x0=-2.5, y0=0.9, dx=1.0, dy=1.0):
    return np.array([x0 + dx * (k % per_row), y0 - dy * (k // per_row), 0.0])


def ten_frame_cell(r, c):
    return np.array([-4.1 + c, 0.9 - r, 0.0])


def confetti(n=26):
    random.seed(7)
    colors = [RED_C, GREEN_C, YELLOW_C, PINK_C, SKY_C]
    dots = VGroup(*[
        Circle(radius=random.uniform(0.06, 0.13), fill_color=random.choice(colors),
               fill_opacity=1, stroke_width=0)
        for _ in range(n)
    ])
    return dots


class Main(ShowScene):
    def construct(self):
        random.seed(3)
        np.random.seed(3)

        # ============================================================== 1. hook
        self.beat("hook")
        bg = Rectangle(width=15, height=9, fill_color=BG, fill_opacity=1, stroke_width=0).set_z_index(-10)
        decor = VGroup(*[
            Circle(radius=random.uniform(0.15, 0.4), fill_opacity=0.22, stroke_width=0,
                   fill_color=random.choice([PINK_C, SKY_C, YELLOW_C, GREEN_C]))
            .move_to(np.array([random.uniform(-6.6, 6.6), random.uniform(-3.4, 3.4), 0]))
            for _ in range(16)
        ]).set_z_index(-9)
        bg._st_bleed = True
        for d in decor:
            d._st_bleed = True
        hook_title = token("Can you solve this?", YELLOW_C, 1.1)
        place(hook_title, "top")
        self.add(bg, hook_title)
        q = eq_row([("7", RED_C), ("+", WHITE), ("5", GREEN_C), ("=", WHITE), ("?", YELLOW_C)], scale=2.4, buff=0.55)
        place(q, "center")
        self.play(LaggedStart(*[FadeIn(d, scale=0.4) for d in decor], lag_ratio=0.08),
                  hook_title.animate.scale(1.06), run_time=2.0)
        for w, i in (("seven", 0), ("plus", 1), ("five", 2)):
            self.at(w)
            self.play(FadeIn(q[i], scale=0.5), run_time=0.28)
        self.at("are")
        self.play(FadeIn(q[3], scale=0.5), run_time=0.25)
        self.at("ready")
        self.play(FadeIn(q[4], scale=0.4), run_time=0.4)
        self.play(Indicate(q, color=YELLOW_C), run_time=0.8)

        # ============================================================== 2. seven red apples
        self.beat("sevens")
        self.play(FadeOut(hook_title), FadeOut(q), run_time=0.6)
        reds = [apple(RED_C) for _ in range(A)]
        for i, a in enumerate(reds):
            at_xy(a, -2.85 + SPACING * i, ROW_Y)
        reds_group = VGroup(*reds)
        seven_lbl = token("7", RED_C, 2.2)
        at_xy(seven_lbl, 0, 1.6)
        self.at("seven")
        self.play(FadeIn(seven_lbl, scale=0.4), run_time=0.5)
        self.at("red")
        self.play(LaggedStart(*[GrowFromCenter(a) for a in reds], lag_ratio=0.15), run_time=1.3)
        self.play(Indicate(reds_group, scale_factor=1.08), run_time=0.9)
        red_nums = []
        for i, w in enumerate(["one", "two", "three", "four", "five", "six", "seven#2"]):
            n = count_label(i + 1)
            n.next_to(reds[i], DOWN, buff=0.25)
            red_nums.append(n)
            self.at(w)
            self.play(Indicate(reds[i], scale_factor=1.3), FadeIn(n), run_time=0.25)
        self.play(Indicate(seven_lbl, color=YELLOW_C), run_time=0.9)

        # ============================================================== 3. add five green apples
        self.beat("fives")
        red_x = [-5.675 + SPACING * i for i in range(A)]
        green_x = [1.875 + SPACING * j for j in range(B)]
        self.play(
            *[FadeOut(n) for n in red_nums],
            *[reds[i].animate.move_to(np.array([red_x[i], ROW_Y, 0])) for i in range(A)],
            seven_lbl.animate.move_to(np.array([sum(red_x) / A, 1.6, 0])),
            run_time=0.7,
        )
        greens = [apple(GREEN_C) for _ in range(B)]
        for j, g in enumerate(greens):
            at_xy(g, green_x[j], ROW_Y)
        five_lbl = token("5", GREEN_C, 2.2)
        at_xy(five_lbl, sum(green_x) / B, 1.6)
        eq1 = eq_row([("7", RED_C), ("+", WHITE), ("5", GREEN_C), ("=", WHITE), ("?", YELLOW_C)], scale=1.3)
        at_xy(eq1, 0, -3.0)
        self.at("five")
        self.play(FadeIn(five_lbl, scale=0.4), FadeIn(VGroup(eq1[0], eq1[1], eq1[2]), shift=UP * 0.3), run_time=0.5)
        self.play(Indicate(VGroup(eq1[0], eq1[1], eq1[2]), color=YELLOW_C), run_time=0.8)
        ghosts = VGroup(*[DashedVMobject(Circle(radius=0.4, stroke_color=WHITE, stroke_width=3, stroke_opacity=0.7))
                          .move_to(np.array([green_x[j], ROW_Y, 0])) for j in range(B)])
        self.play(FadeIn(ghosts), run_time=0.7)
        self.at("green")
        self.play(FadeOut(ghosts), LaggedStart(*[GrowFromCenter(g) for g in greens], lag_ratio=0.2), run_time=1.1)
        green_nums = []
        for j, w in enumerate(["one", "two", "three", "four", "five#2"]):
            n = count_label(j + 1)
            n.next_to(greens[j], DOWN, buff=0.25)
            green_nums.append(n)
            self.at(w)
            self.play(Indicate(greens[j], scale_factor=1.3), FadeIn(n), run_time=0.25)
        self.at("how")
        self.play(FadeIn(VGroup(eq1[3], eq1[4]), scale=0.5), *[FadeOut(n) for n in green_nums], run_time=0.5)
        self.play(LaggedStart(*[Indicate(a, scale_factor=1.2) for a in reds + greens], lag_ratio=0.08), run_time=1.3)

        # ============================================================== 4. make ten
        self.beat("tens")
        frame_cells = VGroup(*[
            Square(side_length=1.0, stroke_color=WHITE, stroke_width=3, fill_color=WHITE, fill_opacity=0.06)
            .move_to(ten_frame_cell(r, c))
            for r in range(2) for c in range(5)
        ])
        red_cells = [ten_frame_cell(0, k) if k < 5 else ten_frame_cell(1, k - 5) for k in range(A)]
        green_cells = [ten_frame_cell(1, 2 + j) for j in range(TAKE)]
        left_pos = [np.array([3.7, ROW_Y + 0.0, 0]), np.array([4.9, ROW_Y + 0.0, 0])]
        three_pos = [np.array([3.1 + 1.1 * j, 1.0, 0]) for j in range(TAKE)]
        self.play(
            FadeOut(seven_lbl), FadeOut(five_lbl),
            FadeIn(frame_cells),
            *[reds[k].animate.move_to(red_cells[k]) for k in range(A)],
            *[greens[j].animate.move_to(three_pos[j]) for j in range(TAKE)],
            *[greens[TAKE + j].animate.move_to(left_pos[j]) for j in range(LEFT_OVER)],
            run_time=0.7,
        )
        empties = [frame_cells[5 + 2 + j] for j in range(TAKE)]      # row 1, cols 2-4
        self.at("more")
        self.play(*[c.animate.set_fill(YELLOW_C, opacity=0.4) for c in empties], run_time=0.6)
        ten_lbl = token("10", YELLOW_C, 1.8)
        at_xy(ten_lbl, -2.6, 2.3)
        self.at("ten")
        self.play(FadeIn(ten_lbl, scale=0.5), run_time=0.4)
        self.play(Indicate(ten_lbl), run_time=0.5)
        self.at("three#2")
        self.play(
            *[greens[j].animate.move_to(green_cells[j]) for j in range(TAKE)],
            *[c.animate.set_fill(WHITE, opacity=0.06) for c in empties],
            run_time=1.3,
        )
        eq2 = eq_row([("7", RED_C), ("+", WHITE), ("3", GREEN_C), ("=", WHITE), ("10", YELLOW_C)], scale=1.1)
        at_xy(eq2, 0, -2.55)
        self.at("we#2")
        self.play(ReplacementTransform(eq1, eq2), run_time=0.9)
        ten_apples = VGroup(*reds, *greens[:TAKE])
        left_apples = VGroup(*greens[TAKE:])
        two_lbl = count_label(LEFT_OVER)
        two_lbl.set_color(GREEN_C).next_to(left_apples, DOWN, buff=0.3)
        self.at("two")
        self.play(Indicate(left_apples, scale_factor=1.25), FadeIn(two_lbl), run_time=0.7)
        self.play(Indicate(ten_apples, scale_factor=1.05), run_time=0.6)
        eq3 = eq_row([("10", YELLOW_C), ("+", WHITE), ("2", GREEN_C), ("=", WHITE), ("12", WHITE)], scale=1.1)
        at_xy(eq3, 0, -3.35)
        self.at("ten#3")
        self.play(FadeIn(VGroup(eq3[0], eq3[1], eq3[2], eq3[3]), shift=UP * 0.25), run_time=0.5)
        self.at("twelve")
        self.play(FadeIn(eq3[4], scale=0.5), eq3[4].animate.set_color(YELLOW_C), run_time=0.6)
        self.play(Indicate(eq3, color=YELLOW_C), run_time=0.9)

        # ============================================================== 5. final answer
        self.beat("win")
        all_apples = reds + greens
        self.play(
            FadeOut(frame_cells), FadeOut(ten_lbl), FadeOut(two_lbl), FadeOut(eq2), FadeOut(eq3),
            *[all_apples[k].animate.move_to(grid_pos(k)) for k in range(A + B)],
            run_time=0.7,
        )
        final = eq_row([("7", RED_C), ("+", WHITE), ("5", GREEN_C), ("=", WHITE), ("12", YELLOW_C)], scale=1.8, buff=0.4)
        at_xy(final, 0, -2.6)
        for w, i in (("seven", 0), ("plus", 1), ("five", 2), ("equals", 3)):
            self.at(w)
            self.play(FadeIn(final[i], scale=0.6), run_time=0.28)
        bits = confetti()
        for d in bits:
            d.move_to(final[4].get_center() + UP * 0.2)
        self.at("twelve")
        self.add(bits)
        self.play(FadeIn(final[4], scale=0.4),
                  *[d.animate.shift(np.array([random.uniform(-6, 6), random.uniform(-2.5, 3.5), 0])).set_opacity(0)
                    for d in bits],
                  run_time=0.9)
        self.remove(*bits)
        self.mark("poster")
        self.at("all")
        self.play(LaggedStart(*[Indicate(a, scale_factor=1.25) for a in all_apples], lag_ratio=0.08), run_time=1.4)

        # ============================================================== 6. recap
        self.beat("recap")
        apples_group = VGroup(*all_apples)
        self.play(FadeOut(final), apples_group.animate.scale(0.5).move_to(np.array([4.2, 2.2, 0])), run_time=0.8)
        r1 = eq_row([("7", RED_C), ("+", WHITE), ("5", GREEN_C)], scale=1.4)
        r2 = eq_row([("=", WHITE), ("7", RED_C), ("+", WHITE), ("3", GREEN_C), ("+", WHITE), ("2", GREEN_C)], scale=1.4)
        r3 = eq_row([("=", WHITE), ("10", YELLOW_C), ("+", WHITE), ("2", GREEN_C)], scale=1.4)
        r4 = eq_row([("=", WHITE), ("12", YELLOW_C)], scale=1.4)
        rows = VGroup(r1, r2, r3, r4).arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        rows.move_to(np.array([-1.8, -0.5, 0]))
        rows.to_edge(LEFT, buff=0.9)
        self.play(Indicate(apples_group, scale_factor=1.08), run_time=0.8)
        self.at("seven")
        self.play(FadeIn(r1, shift=RIGHT * 0.3), run_time=0.6)
        self.at("seven#2")
        self.play(FadeIn(r2, shift=RIGHT * 0.3), run_time=0.8)
        self.play(Indicate(VGroup(r2[3], r2[5]), color=YELLOW_C), run_time=0.9)
        self.at("seven#3")
        self.play(Indicate(VGroup(r2[1], r2[2], r2[3]), color=YELLOW_C), run_time=0.9)
        self.at("ten")
        self.play(FadeIn(r3[0]),
                  TransformFromCopy(VGroup(r2[1], r2[2], r2[3]), r3[1]),
                  TransformFromCopy(VGroup(r2[4], r2[5]), VGroup(r3[2], r3[3])),
                  run_time=0.8)
        self.at("twelve")
        self.play(FadeIn(r4[0]), TransformFromCopy(VGroup(r3[1], r3[2], r3[3]), r4[1]), run_time=0.7)
        make_ten = token("Make ten!", YELLOW_C, 1.2)
        place(make_ten, "top")
        make_ten.to_edge(LEFT, buff=0.9)
        self.at("remember#2")
        self.play(FadeIn(make_ten, scale=0.6), run_time=0.6)
        box = SurroundingRectangle(r3[1], color=YELLOW_C, buff=0.15, stroke_width=5)
        self.at("ten#3")
        self.play(Create(box), Indicate(r4, color=YELLOW_C), run_time=0.8)
        self.play(rows.animate.scale(1.05), box.animate.scale(1.05), Indicate(apples_group, scale_factor=1.08),
                  run_time=2.5)
