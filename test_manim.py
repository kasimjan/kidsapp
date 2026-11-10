from manimlib import *

class HelloMath(Scene):
    def construct(self):
        title = Text("Let's Learn Math!", font_size=60)
        title.set_color(BLUE)

        equation = Tex("3 + 2 = 5")
        equation.scale(2)
        equation.next_to(title, DOWN, buff=1)

        self.play(Write(title))
        self.play(Write(equation))
        self.wait(2)