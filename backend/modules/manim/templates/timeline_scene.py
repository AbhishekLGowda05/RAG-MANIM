# modules/manim/templates/timeline_scene.py

from manim import *
import numpy as np
from ..style_config import *


class TimelineScene(Scene):

    def build_scene(
        self,
        title_text: str,
        events: list,
        audio_duration: float = 0.0,
    ):
        self.camera.background_color = SLATE_BG
        event_labels = [
            str(e.get("label", e) if isinstance(e, dict) else e)[:36]
            for e in (events or [])
        ]
        if not event_labels:
            event_labels = ["Step 1", "Step 2", "Step 3"]
        event_labels = event_labels[:6]

        title = Text(
            str(title_text)[:60],
            font=TITLE_FONT,
            font_size=36,
            color=CHALK_WHITE,
            weight=BOLD,
        ).to_edge(UP, buff=0.4)
        self.play(Write(title), run_time=0.8)

        n = len(event_labels)
        span = min(9.0, max(6.0, n * 2.0))
        timeline = Line(LEFT * span / 2, RIGHT * span / 2, color=CHALK_WHITE, stroke_width=2)
        timeline.shift(DOWN * 0.5)
        self.play(Create(timeline), run_time=0.6)

        xs = list(np.linspace(-span / 2 + 0.5, span / 2 - 0.5, n)) if n > 1 else [0.0]
        line_y = timeline.get_center()[1]
        for event, x in zip(event_labels, xs):
            dot = Dot(point=np.array([x, line_y, 0]), color=CHALK_YELLOW, radius=0.08)
            label = Text(
                event,
                font=BODY_FONT,
                font_size=16,
                color=CHALK_WHITE,
            )
            label.next_to(dot, UP, buff=0.25)
            self.play(FadeIn(dot), FadeIn(label), run_time=0.45)

        tail = max(0.5, audio_duration - (2.0 + n * 0.5)) if audio_duration > 0 else 1.5
        self.wait(tail)
