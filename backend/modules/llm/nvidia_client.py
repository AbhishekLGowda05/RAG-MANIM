"""NVIDIA NIM API client with transparent Google Gemini API fallback."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import requests
import google.generativeai as genai

from modules.config import GEMINI_API_KEY, NVIDIA_API_KEY, get_logger

logger = get_logger(__name__)

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


class NvidiaClient:
    """REST client for NVIDIA NIM chat completions with Gemini fallback."""

    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        # Dynamically fetch keys to avoid module-load caching
        self.nvidia_api_key = os.getenv("NVIDIA_API_KEY") or NVIDIA_API_KEY
        self.gemini_api_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or GEMINI_API_KEY
        )

        if not self.nvidia_api_key and not self.gemini_api_key:
            logger.warning("No LLM API keys found in active environmental context!")
        else:
            logger.info("NVIDIA NIM / Gemini client initialized successfully")

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int = 300,
    ) -> str:
        """Send a chat completion request to NVIDIA NIM, falling back to Gemini if needed."""
        self.nvidia_api_key = os.getenv("NVIDIA_API_KEY") or self.nvidia_api_key
        self.gemini_api_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or self.gemini_api_key
        )

        # If NVIDIA_API_KEY is not set but GEMINI_API_KEY is, route directly to Gemini fallback
        if not self.nvidia_api_key and self.gemini_api_key:
            return self._chat_gemini(messages, temperature)

        headers = {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    NIM_BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return (content or "").strip()
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else 0
                logger.warning(
                    "NVIDIA NIM attempt %d failed (%s): %s",
                    attempt + 1,
                    status,
                    exc,
                )
                # If we get a 401 or 403 authorization error on Nvidia and have Gemini key, try falling back!
                if status in (401, 403) and self.gemini_api_key:
                    logger.info("NVIDIA NIM authorization failed. Retrying with Gemini fallback...")
                    return self._chat_gemini(messages, temperature)

                if attempt < self.max_retries - 1:
                    backoff = 15 if status in (403, 429, 502, 503) else 2**attempt
                    time.sleep(backoff)
                else:
                    raise
            except Exception as exc:
                logger.warning("NVIDIA NIM attempt %d failed: %s", attempt + 1, exc)
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)
                else:
                    raise
        return ""

    def _chat_gemini(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        """Route Visual Planner & Compiler requests dynamically to Google Gemini."""
        logger.info("Routing visual planner request transparently to Google Gemini API (gemini-2.5-flash)...")
        genai.configure(api_key=self.gemini_api_key)
        
        system_instruction = ""
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction += content + "\n"
            else:
                gemini_role = "user" if role == "user" else "model"
                contents.append({"role": gemini_role, "parts": [content]})
        
        system_instruction = system_instruction.strip()
        
        for attempt in range(self.max_retries):
            try:
                model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    system_instruction=system_instruction if system_instruction else None
                )
                
                generation_config = genai.types.GenerationConfig(
                    temperature=temperature
                )
                
                response = model.generate_content(contents, generation_config=generation_config)
                text = (response.text or "").strip()
                if text:
                    return text
                raise ValueError("Received empty content from Gemini API")
            except Exception as exc:
                logger.warning("Gemini attempt %d failed: %s", attempt + 1, exc)
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)
                else:
                    raise
        return ""

    def chat_json(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Any:
        """Chat and parse JSON response."""
        text = self.chat(model, messages, temperature=temperature, max_tokens=max_tokens)
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
