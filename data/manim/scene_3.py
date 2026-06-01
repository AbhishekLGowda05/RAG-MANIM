from manim import *
import numpy as np


class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#0f1117"

        title = Text("Magnetic Field Interactions", font_size=38, weight=BOLD, color="#e0e6f0")
        title.to_edge(UP, buff=0.3)

        mag_l_body = Rectangle(width=1.40, height=0.65, color="#8b6914", fill_color="#8b6914", fill_opacity=0.85)
        mag_l_body.move_to(np.array([-1.50, 0.50, 0]))
        mag_l_north = Rectangle(width=0.48, height=0.65, color="#ff5252", fill_color="#ff5252", fill_opacity=0.9)
        mag_l_north.move_to(np.array([-1.04, 0.50, 0]))
        mag_l_north_lbl = Text("N", font_size=20, color=WHITE, weight=BOLD)
        mag_l_north_lbl.move_to(mag_l_north.get_center())
        mag_l_south = Rectangle(width=0.48, height=0.65, color="#4f8ef7", fill_color="#4f8ef7", fill_opacity=0.9)
        mag_l_south.move_to(np.array([-1.96, 0.50, 0]))
        mag_l_south_lbl = Text("S", font_size=20, color=WHITE, weight=BOLD)
        mag_l_south_lbl.move_to(mag_l_south.get_center())
        mag_l = VGroup(mag_l_body, mag_l_north, mag_l_south, mag_l_north_lbl, mag_l_south_lbl)

        mag_r_body = Rectangle(width=1.40, height=0.65, color="#8b6914", fill_color="#8b6914", fill_opacity=0.85)
        mag_r_body.move_to(np.array([1.50, 0.50, 0]))
        mag_r_north = Rectangle(width=0.48, height=0.65, color="#ff5252", fill_color="#ff5252", fill_opacity=0.9)
        mag_r_north.move_to(np.array([1.96, 0.50, 0]))
        mag_r_north_lbl = Text("N", font_size=20, color=WHITE, weight=BOLD)
        mag_r_north_lbl.move_to(mag_r_north.get_center())
        mag_r_south = Rectangle(width=0.48, height=0.65, color="#4f8ef7", fill_color="#4f8ef7", fill_opacity=0.9)
        mag_r_south.move_to(np.array([1.04, 0.50, 0]))
        mag_r_south_lbl = Text("S", font_size=20, color=WHITE, weight=BOLD)
        mag_r_south_lbl.move_to(mag_r_south.get_center())
        mag_r = VGroup(mag_r_body, mag_r_north, mag_r_south, mag_r_north_lbl, mag_r_south_lbl)

        mag_r_swapped_body = Rectangle(width=1.40, height=0.65, color="#8b6914", fill_color="#8b6914", fill_opacity=0.85)
        mag_r_swapped_body.move_to(np.array([1.50, 0.50, 0]))
        mag_r_swapped_north = Rectangle(width=0.48, height=0.65, color="#ff5252", fill_color="#ff5252", fill_opacity=0.9)
        mag_r_swapped_north.move_to(np.array([1.04, 0.50, 0]))
        mag_r_swapped_north_lbl = Text("N", font_size=20, color=WHITE, weight=BOLD)
        mag_r_swapped_north_lbl.move_to(mag_r_swapped_north.get_center())
        mag_r_swapped_south = Rectangle(width=0.48, height=0.65, color="#4f8ef7", fill_color="#4f8ef7", fill_opacity=0.9)
        mag_r_swapped_south.move_to(np.array([1.96, 0.50, 0]))
        mag_r_swapped_south_lbl = Text("S", font_size=20, color=WHITE, weight=BOLD)
        mag_r_swapped_south_lbl.move_to(mag_r_swapped_south.get_center())
        mag_r_swapped = VGroup(mag_r_swapped_body, mag_r_swapped_north, mag_r_swapped_south, mag_r_swapped_north_lbl, mag_r_swapped_south_lbl)

        attr_arr_l = Arrow(
            np.array([-0.65, 0.50, 0]),
            np.array([-0.15, 0.50, 0]),
            color="#41d4a8", stroke_width=5, buff=0
        )
        attr_arr_r = Arrow(
            np.array([0.65, 0.50, 0]),
            np.array([0.15, 0.50, 0]),
            color="#41d4a8", stroke_width=5, buff=0
        )
        attr_lbl = Text("Attraction", font_size=22, color="#41d4a8")
        attr_lbl.move_to(np.array([0, -0.60, 0]))
        attr_grp = VGroup(attr_arr_l, attr_arr_r, attr_lbl)
        attr_grp.set_opacity(0)

        rep_arr_l = Arrow(
            np.array([-1.50, 0.50, 0]),
            np.array([-2.80, 0.50, 0]),
            color="#ff7a59", stroke_width=5, buff=0
        )
        rep_arr_r = Arrow(
            np.array([1.50, 0.50, 0]),
            np.array([2.80, 0.50, 0]),
            color="#ff7a59", stroke_width=5, buff=0
        )
        rep_lbl = Text("Repulsion", font_size=22, color="#ff7a59")
        rep_lbl.move_to(np.array([0, -0.60, 0]))
        rep_grp = VGroup(rep_arr_l, rep_arr_r, rep_lbl)
        rep_grp.set_opacity(0)

        field_arcs = VGroup(*[
            Arc(radius=0.3 + i*0.22, start_angle=PI*0.15, angle=PI*0.7,
                color="#f7c948", stroke_width=1.5, stroke_opacity=0.6)
            .move_arc_center_to(np.array([0, 0.50, 0]))
            for i in range(4)
        ])
        field_arcs.set_opacity(0)

        rule_box = RoundedRectangle(corner_radius=0.18, width=6.8, height=0.85,
            color="#4f8ef7", fill_opacity=0.10, stroke_width=1.5)
        rule_text = Text("Like poles repel • Unlike poles attract",
            font_size=22, color="#c8d3e6", weight=BOLD)
        rule_box.to_edge(DOWN, buff=0.45)
        rule_text.move_to(rule_box.get_center())
        rule_grp = VGroup(rule_box, rule_text)
        rule_grp.set_opacity(0)

        self.play(Write(title), FadeIn(mag_l, mag_r), run_time=2.000)
        attr_grp.set_opacity(1)
        self.play(
            GrowArrow(attr_arr_l), GrowArrow(attr_arr_r), FadeIn(attr_lbl),
            run_time=2.000
        )
        self.play(
            mag_l.animate.shift(RIGHT*0.55),
            mag_r.animate.shift(LEFT*0.55),
            FadeOut(attr_grp),
            run_time=1.400,
            rate_func=rate_functions.ease_in_quad
        )
        self.play(
            mag_l.animate.shift(LEFT*0.55),
            mag_r.animate.shift(RIGHT*0.55),
            run_time=0.950
        )
        self.play(
            ReplacementTransform(mag_r, mag_r_swapped),
            run_time=0.55
        )
        mag_r = mag_r_swapped
        rep_grp.set_opacity(1)
        self.play(
            GrowArrow(rep_arr_l), GrowArrow(rep_arr_r), FadeIn(rep_lbl),
            run_time=1.400
        )
        self.play(
            mag_l.animate.shift(LEFT*0.70),
            mag_r.animate.shift(RIGHT*0.70),
            FadeOut(rep_grp),
            run_time=2.000,
            rate_func=rate_functions.ease_out_quad
        )
        field_arcs.set_opacity(1)
        self.play(Create(field_arcs), run_time=2.000)
        rule_grp.set_opacity(1)
        self.play(FadeIn(rule_box), Write(rule_text), run_time=0.700)
        self.wait(0.840)
        self.wait(2.978)

        self.play(FadeOut(*self.mobjects), run_time=0.40)
