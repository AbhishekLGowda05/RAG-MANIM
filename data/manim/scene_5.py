from manim import *
import numpy as np


class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#0f1117"

        title = Text("Magnetism Summary", font_size=44, weight=BOLD, color="#e0e6f0")
        title.to_edge(UP, buff=0.4)

        pt_0 = Text("• Magnetism arises from moving charges", font_size=28, color="#c8d3e6")
        pt_0.set_opacity(0)
        pt_1 = Text("• Magnetic fields interact with charges and other magnetic fields", font_size=28, color="#c8d3e6")
        pt_1.set_opacity(0)
        pt_2 = Text("• Electromagnetic induction is a fundamental concept in electromagnetism", font_size=28, color="#c8d3e6")
        pt_2.set_opacity(0)
        all_pts = VGroup(pt_0, pt_1, pt_2)
        all_pts.arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        all_pts.next_to(title, DOWN, buff=0.5).shift(LEFT*0.5)

        self.play(Write(title), run_time=2.000)
        pt_0.set_opacity(1)
        self.play(FadeIn(pt_0, shift=RIGHT*0.3), run_time=1.400)
        pt_1.set_opacity(1)
        self.play(FadeIn(pt_1, shift=RIGHT*0.3), run_time=1.400)
        self.wait(1.624)
        pt_2.set_opacity(1)
        self.play(FadeIn(pt_2, shift=RIGHT*0.3), run_time=0.583)
        self.wait(1.254)

        self.play(FadeOut(*self.mobjects), run_time=0.40)
