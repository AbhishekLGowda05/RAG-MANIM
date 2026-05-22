"""Gemini API client for main reasoning and Manim repair."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import google.generativeai as genai

from modules.config import GEMINI_API_KEY, GEMINI_MODEL, get_logger

logger = get_logger(__name__)


class GeminiClient:
    """Wrapper around Google Generative AI (Gemini)."""

    def __init__(self, model: str | None = None, max_retries: int = 3) -> None:
        import os
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        genai.configure(api_key=api_key)
        self.model_name = model or GEMINI_MODEL
        self.model = genai.GenerativeModel(self.model_name)
        self.max_retries = max_retries
        logger.info("Gemini client initialized with model=%s", self.model_name)

    def generate_text(self, prompt: str, system: str | None = None) -> str:
        """Generate plain text from a prompt."""
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        for attempt in range(self.max_retries):
            try:
                response = self.model.generate_content(full_prompt)
                text = (response.text or "").strip()
                if text:
                    return text
                raise ValueError("Empty response from Gemini")
            except Exception as exc:
                logger.warning("Gemini attempt %d failed: %s", attempt + 1, exc)
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)
                else:
                    raise
        return ""

    def generate_json(self, prompt: str, system: str | None = None) -> Any:
        """Generate and parse JSON from Gemini."""
        system_hint = (system or "") + "\nRespond ONLY with valid JSON. No markdown fences."
        text = self.generate_text(prompt, system=system_hint)
        return _parse_json(text)


def _parse_json(text: str) -> Any:
    """Extract and parse JSON from LLM output."""
    cleaned = text.strip()
    if "```json" in cleaned:
        match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)
    elif "```" in cleaned:
        match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)
    return json.loads(cleaned)
