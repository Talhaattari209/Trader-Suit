"""
Strategist Agent: Algorithmic Trader / Python Developer.
Reads RESEARCH_PLAN_*.md from Plans/, uses US30Loader for data context,
and produces executable strategy_<name>.py in src/models/drafts/ implementing BaseStrategy.
"""
import os
from pathlib import Path
from typing import Any, Dict, List

from .base_agent import BaseAgent
from ..data.us30_loader import US30Loader
from ..tools.llm_client import BaseLLMClient, AnthropicLLMClient, GeminiLLMClient


SYSTEM_STRATEGIST = """You are an Algorithmic Trader and Python Developer. Your task is to turn a Research Plan into a concrete, executable Python strategy that implements the BaseStrategy interface.

You must output only valid Python code for a single file. The class must:
1. Inherit from BaseStrategy (from src.models.base_strategy import BaseStrategy).
2. Implement entry(self, state: Dict[str, Any]) -> bool
3. Implement exit(self, state: Dict[str, Any]) -> bool
4. Implement risk(self, state: Dict[str, Any]) -> float

The `state` dict will contain at least: Open, High, Low, Close, Volume (floats for the current bar). You may add indicators in __init__ or cache them.

Output ONLY the Python code: no markdown fences, no explanation. Start with the import and class definition."""

PROMPT_STRATEGIST = """Research Plan to implement as a trading strategy:

---
{plan_content}
---

Data context (US30 OHLCV): columns available per bar are Open, High, Low, Close, Volume. Index is Timestamp (datetime).
Data shape: {rows} rows.

Generate a single Python file that defines a class implementing BaseStrategy. Use a descriptive class name (e.g. MeanReversionUS30). The file should be importable and the class instantiable. No backtest runner—only the strategy class. Output only code."""


class StrategistAgent(BaseAgent):
    """
    Monitors Plans/ for new RESEARCH_PLAN_*.md; uses LLM with US30 data context
    to generate strategy_<name>.py in drafts/ implementing BaseStrategy.
    """

    def __init__(
        self,
        vault_path: str,
        drafts_dir: str | Path | None = None,
        us30_csv_path: str | None = None,
        llm_client: BaseLLMClient | None = None,
    ):
        super().__init__("StrategistAgent")
        self.vault_path = Path(vault_path)
        self.plans_dir = self.vault_path / "Plans"
        self.logs_dir = self.vault_path / "Logs"
        self.drafts_dir = Path(drafts_dir) if drafts_dir else Path(__file__).resolve().parent.parent / "models" / "drafts"
        self.us30_csv_path = us30_csv_path or os.environ.get("US30_CSV_PATH", "")
        
        if llm_client:
            self.llm = llm_client
        else:
            # Auto-detect client
            if os.environ.get("ANTHROPIC_API_KEY"):
                self.llm = AnthropicLLMClient()
            elif os.environ.get("GEMINI_API_KEY"):
                self.llm = GeminiLLMClient()
            else:
                self.logger.warning("No API key found (Anthropic or Gemini). Strategist will fail.")
                self.llm = AnthropicLLMClient() # Default to Anthropic to let it error out if tried
        
        self._processed_log = self.logs_dir / "strategist_processed.log"

    def _load_processed(self) -> set:
        if self._processed_log.exists():
            return set(line.strip() for line in self._processed_log.read_text().splitlines() if line.strip())
        return set()

    def _mark_processed(self, path: Path):
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        with open(self._processed_log, "a", encoding="utf-8") as f:
            f.write(f"{path.name}\n")
        self.processed.add(path.name)

    async def perceive(self, input_data: Any) -> Any:
        """
        Scan Plans/ for RESEARCH_PLAN_*.md not yet processed.
        Returns list of {"path": Path, "content": str}.
        """
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.processed = self._load_processed()
        items = []
        for f in self.plans_dir.glob("RESEARCH_PLAN_*.md"):
            if not f.is_file() or f.name in self.processed:
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                items.append({"path": f, "content": content})
            except Exception as e:
                self.log_action("perceive", f"Skip {f.name}: {e}")
        self.log_action("perceive", f"Found {len(items)} new plan(s)")
        return items

    def _get_data_context(self) -> str:
        """Return data shape / context for prompt; avoid failing if no CSV."""
        if not self.us30_csv_path or not Path(self.us30_csv_path).exists():
            return "No US30 CSV loaded; assume standard OHLCV columns and arbitrary row count."
        try:
            loader = US30Loader(self.us30_csv_path)
            df = loader.load_clean_data()
            return f"{len(df)} rows"
        except Exception as e:
            return f"Load error: {e}; assume standard OHLCV."

    async def reason(self, state: Any) -> Dict[str, Any]:
        """
        For each plan, get data context and call LLM to generate strategy code.
        Returns {"drafts": [{"name": str, "code": str, "source_path": Path}], "items": state}.
        """
        if not state:
            return {"drafts": [], "items": state}
        data_context = self._get_data_context()
        drafts = []
        for item in state:
            path, content = item["path"], item["content"]
            name = path.stem.replace("RESEARCH_PLAN_", "").strip()
            prompt = PROMPT_STRATEGIST.format(plan_content=content[:8000], rows=data_context)
            try:
                code = await self.llm.complete(prompt, system=SYSTEM_STRATEGIST)
                # Strip markdown code blocks if present
                if "```python" in code:
                    code = code.split("```python", 1)[-1].split("```", 1)[0].strip()
                elif "```" in code:
                    code = code.split("```", 1)[-1].split("```", 1)[0].strip()
                drafts.append({"name": name, "code": code, "source_path": path})
            except Exception as e:
                self.log_action("reason", f"LLM failed for {path.name}: {e}")
        return {"drafts": drafts, "items": state}

    async def act(self, plan: Dict[str, Any]) -> bool:
        """Write each strategy_<name>.py to drafts/ and mark plans as processed."""
        drafts_list = plan.get("drafts") or []
        items = plan.get("items") or []
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        for d in drafts_list:
            name = d.get("name", "unknown").replace(" ", "_")
            code = d.get("code", "")
            out_path = self.drafts_dir / f"strategy_{name}.py"
            # Ensure correct import path from drafts (sibling of models)
            if "from src.models.base_strategy" not in code and "BaseStrategy" in code:
                code = "from src.models.base_strategy import BaseStrategy\n\n" + code
            out_path.write_text(code, encoding="utf-8")
            self.log_action("act", f"Wrote {out_path.name}")
        for item in items:
            self._mark_processed(item["path"])
        return True
