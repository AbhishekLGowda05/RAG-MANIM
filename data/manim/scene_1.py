from manim import *
import numpy as np


class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#0f1117"

        title = Text("Magnetism Introduction", font_size=52, weight=BOLD, color="#e0e6f0")
        title.to_edge(UP, buff=0.8)
        subtitle = Text("Understanding Magnetism and Its Effects", font_size=30, color="#c8d3e6")
        subtitle.next_to(title, DOWN, buff=0.5)
        key_term_box = RoundedRectangle(corner_radius=0.2, width=4.5, height=1.0, color="#4f8ef7", fill_opacity=0.12, stroke_width=2)
        key_term_text = Text("Magnetism", font_size=36, color="#4f8ef7", weight=BOLD)
        key_term_box.move_to(ORIGIN + DOWN*0.4)
        key_term_text.move_to(key_term_box.get_center())

        self.play(Write(title), run_time=2.000)
        self.play(FadeIn(subtitle, shift=UP*0.2), run_time=1.400)
        self.play(FadeIn(key_term_box), Write(key_term_text), run_time=0.950)
        self.wait(3.447)

        self.play(FadeOut(*self.mobjects), run_time=0.40)
