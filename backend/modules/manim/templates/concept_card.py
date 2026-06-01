# modules/manim/templates/concept_card.py
from manim import *
import numpy as np
from ..style_config import *

_DEFAULT_COLORS = [CHALK_BLUE, CHALK_GREEN, CHALK_YELLOW, CHALK_PINK]


class ConceptCardScene(Scene):
    """Shows a concept broken into labeled sub-cards."""

    def setup_background(self):
        bg = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color=SLATE_BG,
            fill_opacity=1,
            stroke_width=0,
        )
        dots = VGroup(*[
            Dot(
                point=[np.random.uniform(-7, 7), np.random.uniform(-4, 4), 0],
                radius=0.02,
                color=CHALK_WHITE,
                fill_opacity=np.random.uniform(0.1, 0.3),
            )
            for _ in range(40)
        ])
        self.add(bg, dots)

    def make_card(self, title, content, accent_color, width=3.2, height=2.8):
        card_bg = RoundedRectangle(
            corner_radius=0.3,
            width=width,
            height=height,
            fill_color=CARD_BG,
            fill_opacity=1,
            stroke_color=accent_color,
            stroke_width=1.5,
        )
        card_title = Text(
            str(title)[:40],
            font=TITLE_FONT,
            font_size=26,
            color=accent_color,
            weight=BOLD,
        ).move_to(card_bg.get_top() + DOWN * 0.45)
        card_text = Text(
            str(content)[:120],
            font=BODY_FONT,
            font_size=16,
            color=CHALK_WHITE,
            line_spacing=1.3,
        ).move_to(card_bg.get_center() + DOWN * 0.25)
        return VGroup(card_bg, card_title, card_text)

    def build_scene(self, main_title: str, cards: list, audio_duration: float = 0.0):
        self.setup_background()
        if not cards:
            cards = [
                {"title": "Part 1", "content": main_title, "color": CHALK_BLUE},
                {"title": "Part 2", "content": "Key idea", "color": CHALK_GREEN},
            ]

        outer_box = RoundedRectangle(
            corner_radius=0.4,
            width=13,
            height=7.2,
            fill_opacity=0,
            stroke_color=CARD_BORDER,
            stroke_width=1,
        )
        title = chalk_title(str(main_title)[:60]).to_edge(UP, buff=0.4)
        self.play(DrawBorderThenFill(outer_box), Write(title), run_time=1.0)

        normalized = []
        for i, c in enumerate(cards[:4]):
            if isinstance(c, dict):
                normalized.append({
                    "title": c.get("title", f"Part {i + 1}"),
                    "content": c.get("content", ""),
                    "color": c.get("color", _DEFAULT_COLORS[i % len(_DEFAULT_COLORS)]),
                })
            else:
                normalized.append({
                    "title": f"Part {i + 1}",
                    "content": str(c),
                    "color": _DEFAULT_COLORS[i % len(_DEFAULT_COLORS)],
                })

        card_group = VGroup(*[
            self.make_card(c["title"], c["content"], c["color"])
            for c in normalized
        ]).arrange(RIGHT, buff=0.4).move_to(ORIGIN + DOWN * 0.3)

        arrows = VGroup(*[
            Arrow(
                card_group[i].get_right(),
                card_group[i + 1].get_left(),
                color=CHALK_WHITE,
                stroke_width=2,
                buff=0.1,
            )
            for i in range(len(card_group) - 1)
        ])

        for i, card in enumerate(card_group):
            self.play(FadeIn(card, shift=UP * 0.3), run_time=0.6)
            if i < len(arrows):
                self.play(GrowArrow(arrows[i]), run_time=0.4)

        tail = max(0.5, audio_duration - 3.5) if audio_duration > 0 else 1.5
        self.wait(tail)
