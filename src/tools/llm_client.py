"""
LLM client for Intelligence Layer agents (Librarian, Strategist).
Uses Anthropic Claude; set ANTHROPIC_API_KEY in environment.
"""
import os
from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMClient(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        """Return model completion for the given prompt and optional system message."""
        pass


class AnthropicLLMClient(BaseLLMClient):
    """Claude via Anthropic SDK. Requires anthropic package and ANTHROPIC_API_KEY."""

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
        client = self._get_client()
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        msg = await client.messages.create(**kwargs)
        if not msg.content or not getattr(msg.content[0], "text", None):
            return ""
        return msg.content[0].text


class GeminiLLMClient(BaseLLMClient):
    """Google Gemini via Generative AI SDK. Requires GEMINI_API_KEY."""

    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        self.model_name = model_name
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")

        if not self._api_key:
             # Try to read from .env if running locally without properly loaded env vars
             # (Fallback, though run_workflow.py usually loads dotenv)
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
        genai = self._configure()
        model = genai.GenerativeModel(self.model_name)
        
        # Combine system prompt if provided (Gemini supports system instruction in newer models, 
        # but simple concatenation or chat history is safer for broad compatibility)
        # However, 1.5 Pro/Flash supports system_instruction argument in constructor.
        # But we are initializing model here. Let's try to use it if creating a new model instance.
        
        # Actually, let's just use generate_content for now.
        full_prompt = prompt
        if system:
             # Prepend system prompt for simplicity
             full_prompt = f"System: {system}\n\nUser: {prompt}"
        
        try:
             # Run in executor to be async-compatible if the library is sync
             # Google's library has async methods but they might not be fully standard awaitables in all versions
             # Let's assume standard usage:
             response = await model.generate_content_async(full_prompt)
             return response.text
        except Exception as e:
             # Fallback to sync if async fails or not available
             try:
                 response = model.generate_content(full_prompt)
                 return response.text
             except Exception as e2:
                 raise RuntimeError(f"Gemini generation failed: {e2}") from e
