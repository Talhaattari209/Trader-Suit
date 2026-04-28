"""
LLM client for Intelligence Layer agents (Librarian, Strategist).

Default client: GeminiLLMClient (GEMINI_API_KEY).
AnthropicLLMClient kept for optional use but NOT the default — no ANTHROPIC_API_KEY required.

Debug logging: every call writes to console and DataStore/debug.log.
"""
from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── Logging setup ─────────────────────────────────────────────────────────────

def _get_logger() -> logging.Logger:
    log = logging.getLogger("llm_debug")
    if not log.handlers:
        log.setLevel(logging.DEBUG)
        log.addHandler(logging.StreamHandler())
        debug_log = Path("DataStore/debug.log")
        debug_log.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(debug_log, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        log.addHandler(fh)
    return log


# ── Base class ────────────────────────────────────────────────────────────────

class BaseLLMClient(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        """Return model completion for the given prompt and optional system message."""
        pass


# ── Gemini (DEFAULT) ──────────────────────────────────────────────────────────

class GeminiLLMClient(BaseLLMClient):
    """Google Gemini via Generative AI SDK. Requires GEMINI_API_KEY.

    This is the DEFAULT LLM client for all agents.
    """

    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        self.model_name = model_name
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self._api_key:
            try:
                from dotenv import load_dotenv
                load_dotenv()
                self._api_key = os.environ.get("GEMINI_API_KEY")
            except ImportError:
                pass

    def _configure(self):
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY not set; cannot call Gemini.")
        import google.generativeai as genai
        genai.configure(api_key=self._api_key)
        return genai

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        log = _get_logger()
        genai = self._configure()
        model = genai.GenerativeModel(self.model_name)

        full_prompt = prompt
        if system:
            full_prompt = f"System: {system}\n\nUser: {prompt}"

        log.debug("=" * 60)
        log.debug(f"[{datetime.now(timezone.utc).isoformat()}] LLM CALL — model={self.model_name}")
        log.debug(f"PROMPT (first 500 chars): {full_prompt[:500]}")

        t0 = time.time()
        try:
            response = await model.generate_content_async(full_prompt)
            text = response.text
        except Exception as e:
            try:
                response = model.generate_content(full_prompt)
                text = response.text
            except Exception as e2:
                raise RuntimeError(f"Gemini generation failed: {e2}") from e

        elapsed = time.time() - t0
        log.debug(f"RESPONSE (first 500 chars): {text[:500]}")
        log.debug(f"Elapsed: {elapsed:.2f}s")
        return text


# ── Anthropic (OPTIONAL — no key required by default) ─────────────────────────

class AnthropicLLMClient(BaseLLMClient):
    """Claude via Anthropic SDK.

    OPTIONAL — not used by default.
    Requires 'anthropic' package and ANTHROPIC_API_KEY environment variable.
    """

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not set; cannot call Claude.")
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        log = _get_logger()
        client = self._get_client()
        kwargs: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        log.debug("=" * 60)
        log.debug(f"[{datetime.now(timezone.utc).isoformat()}] LLM CALL — model={self.model} (Anthropic)")
        log.debug(f"SYSTEM (first 500 chars): {(system or '')[:500]}")
        log.debug(f"PROMPT (first 500 chars): {prompt[:500]}")

        t0 = time.time()
        msg = await client.messages.create(**kwargs)
        elapsed = time.time() - t0

        if not msg.content or not getattr(msg.content[0], "text", None):
            return ""
        text = msg.content[0].text
        log.debug(f"RESPONSE (first 500 chars): {text[:500]}")
        log.debug(f"Elapsed: {elapsed:.2f}s  Tokens: {msg.usage.output_tokens}")
        return text


# ── Factory ───────────────────────────────────────────────────────────────────

def get_default_llm_client() -> BaseLLMClient:
    """Return the default LLM client (Gemini). Falls back gracefully if key missing."""
    return GeminiLLMClient()
