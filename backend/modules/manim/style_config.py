# modules/manim/style_config.py
from manim import *

# CHALKBOARD STYLE (matching your reference images 1 & 2)
CHALK_CONFIG = {
    "background_color": "#1C1C1E",      # dark slate, not pure black
    "frame_rate": 30,
    "pixel_height": 1080,
    "pixel_width": 1920,
}

# Color palette
CHALK_WHITE   = "#F0EFE8"
CHALK_PINK    = "#E8A0A0"
CHALK_BLUE    = "#7BA7C2"
CHALK_YELLOW  = "#E8D87A"
CHALK_GREEN   = "#7AC2A0"
SLATE_BG      = "#1C1C1E"
CARD_BG       = "#252530"
CARD_BORDER   = "#3A3A4A"

# Typography
TITLE_FONT    = "Montserrat"
BODY_FONT     = "Outfit"
MONO_FONT     = "JetBrains Mono"

def chalk_text(content, size=36, color=CHALK_WHITE, font=BODY_FONT):
    return Text(content, font=font, font_size=size, color=color)

def chalk_title(content, color=CHALK_WHITE):
    return Text(content, font=TITLE_FONT, font_size=48,
                color=color, weight=BOLD)
