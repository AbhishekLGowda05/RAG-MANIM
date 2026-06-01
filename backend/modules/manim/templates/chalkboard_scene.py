# modules/manim/templates/chalkboard_scene.py

from manim import *
from ..style_config import *


class ChalkboardScene(Scene):
    """
    Base chalkboard template.

    Used by:
    - Momentum
    - Force
    - Inertia
    - Friction
    - Gravity
    - Diagram scenes
    - Educational explanations
    """

    def setup_chalkboard(self):
        """
        Standard chalkboard background.
        Called automatically from _HEADER.
        """

        self.camera.background_color = "#1C1C1E"

        self.board_frame = Rectangle(
            width=13,
            height=7,
            color="#4A6080",
            stroke_width=2
        )

        self.board_frame.set_fill(opacity=0)

        self.add(self.board_frame)

    def chalk_title(self, text):
        """
        Standard chalk-style title.
        """

        return Text(
            text,
            font_size=38,
            weight=BOLD,
            color=CHALK_WHITE
        ).to_edge(UP, buff=0.3)

    def chalk_stroke(self, mobject, color=CHALK_WHITE):
        """
        Convert any object into chalk style.
        """

        mobject.set_stroke(
            color=color,
            width=2.5,
            opacity=0.9
        )

        mobject.set_fill(opacity=0)

        return mobject

    def draw_label_arrow(
        self,
        label_text,
        target_point,
        label_position,
        color=CHALK_WHITE
    ):
        """
        Creates chalk-style annotation arrow.
        """

        label = Text(
            label_text,
            font=MONO_FONT,
            font_size=20,
            color=color
        )

        label.move_to(label_position)

        arrow = Line(
            label.get_edge_center(DOWN),
            target_point,
            color=color,
            stroke_width=1.5
        )

        tip = ArrowTip(color=color).scale(0.5)

        tip.move_to(target_point)
        tip.rotate(arrow.get_angle() + PI)

        return VGroup(label, arrow, tip)

    def build_anatomy_scene(
        self,
        shapes: list,
        labels: list | None = None
    ):
        """
        Generic chalkboard anatomy renderer.
        """

        self.setup_chalkboard()

        for shape_data in shapes:

            shape = self.chalk_stroke(
                Rectangle(
                    width=2,
                    height=1
                ),
                color=shape_data.get(
                    "color",
                    CHALK_WHITE
                )
            )

            label = self.draw_label_arrow(
                shape_data.get("label", ""),
                shape.get_center(),
                shape.get_top() + UP * 0.4
            )

            self.play(
                Create(shape),
                run_time=shape_data.get(
                    "draw_time",
                    0.8
                )
            )

            self.play(
                FadeIn(label),
                run_time=0.4
            )