# modules/manim/templates/timeline_scene.py

from manim import *
from ..style_config import *

class TimelineScene(Scene):

    def build_scene(
        self,
        title_text,
        events
    ):

        self.camera.background_color = "#1C1C1E"

        title = Text(
            title_text,
            font_size=38
        ).to_edge(UP)

        self.play(Write(title))

        timeline = Line(
            LEFT*5,
            RIGHT*5,
            color=WHITE
        )

        self.play(Create(timeline))

        for idx, event in enumerate(events):

            x = -4 + idx*2

            dot = Dot(
                point=[x,0,0],
                color=YELLOW
            )

            label = Text(
                event,
                font_size=20
            ).next_to(dot, UP)

            self.play(
                FadeIn(dot),
                FadeIn(label)
            )

        self.wait(2)