# modules/manim/templates/concept_card.py
from manim import *
from ..style_config import *

class ConceptCardScene(Scene):
    """
    Template: Shows a concept broken into labeled sub-cards
    Usage: LLM provides title + list of (label, description, color) tuples
    """
    
    def setup_background(self):
        # Dark gradient background with subtle particle dots
        bg = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color=SLATE_BG,
            fill_opacity=1,
            stroke_width=0
        )
        # Add subtle dot particles
        dots = VGroup(*[
            Dot(
                point=[np.random.uniform(-7, 7), 
                       np.random.uniform(-4, 4), 0],
                radius=0.02,
                color=CHALK_WHITE,
                fill_opacity=np.random.uniform(0.1, 0.3)
            )
            for _ in range(40)
        ])
        self.add(bg, dots)
    
    def make_card(self, title, content, accent_color, width=3.5, height=3.0):
        card_bg = RoundedRectangle(
            corner_radius=0.3,
            width=width, height=height,
            fill_color=CARD_BG,
            fill_opacity=1,
            stroke_color=accent_color,
            stroke_width=1.5
        )
        card_title = Text(
            title, font=TITLE_FONT,
            font_size=28, color=accent_color,
            weight=BOLD
        ).move_to(card_bg.get_top() + DOWN * 0.5)
        
        card_text = Text(
            content, font=BODY_FONT,
            font_size=18, color=CHALK_WHITE,
            line_spacing=1.4
        ).move_to(card_bg.get_center() + DOWN * 0.2)
        
        return VGroup(card_bg, card_title, card_text)
    
    def build_scene(self, main_title: str, cards: list):
        """
        cards = [
            {"title": "Convolution", "content": "Extracts features", 
             "color": CHALK_BLUE, "visual": "grid"},
            ...
        ]
        """
        self.setup_background()
        
        # Main title with outer border
        outer_box = RoundedRectangle(
            corner_radius=0.4,
            width=13, height=7.2,
            fill_opacity=0,
            stroke_color=CARD_BORDER,
            stroke_width=1
        )
        title = chalk_title(main_title).to_edge(UP, buff=0.4)
        
        self.play(
            DrawBorderThenFill(outer_box),
            Write(title),
            run_time=1.0
        )
        
        # Arrange cards horizontally
        card_group = VGroup(*[
            self.make_card(
                c["title"], c["content"], c["color"]
            )
            for c in cards
        ]).arrange(RIGHT, buff=0.5).move_to(ORIGIN + DOWN * 0.3)
        
        # Animated arrows between cards
        arrows = VGroup(*[
            Arrow(
                card_group[i].get_right(),
                card_group[i+1].get_left(),
                color=CHALK_WHITE,
                stroke_width=2,
                buff=0.1
            )
            for i in range(len(card_group) - 1)
        ])
        
        # Animate cards in sequence
        for i, card in enumerate(card_group):
            self.play(FadeIn(card, shift=UP * 0.3), run_time=0.6)
            if i < len(arrows):
                self.play(GrowArrow(arrows[i]), run_time=0.4)
        
        self.wait(2)
