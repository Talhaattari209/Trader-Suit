"""
Librarian Agent: Senior Quantitative Researcher.
Ingests raw information from Needs_Action and produces RESEARCH_PLAN_<Topic>.md in Plans/.
Uses LLM (Claude) to extract Alpha Signals, Timeframe/Asset Class, and Risk Factors.
"""
import os
from pathlib import Path
from typing import Any, Dict, List

from .base_agent import BaseAgent
from ..tools.llm_client import BaseLLMClient, AnthropicLLMClient, GeminiLLMClient


SYSTEM_LIBRARIAN = """You are a Senior Quantitative Researcher. Your task is to read raw research or data ingestion notices and produce a structured Trading Hypothesis / Research Plan.

Extract and output in a clear, structured way:
1. **Alpha Signals**: What edge or signal is suggested (e.g. mean reversion, breakout, sentiment)?
2. **Timeframe / Asset Class**: e.g. M5 US30, daily FX, etc.
3. **Risk Factors**: What could invalidate the hypothesis or increase risk?

Also suggest a short topic slug (a few words, no spaces, for use in a filename) and a one-line title."""

PROMPT_TEMPLATE = """Analyze the following content from our research/data pipeline and produce a Research Plan.

Content:
---
{content}
---

If the content includes "EDGE_TYPE: <name>", include a "## Edge Type" section with that value.

Output your analysis in the following format (use these exact headers):

## Topic
<short slug and title>

## Edge Type
<edge_type if present: statistical, pattern_based, volume_based, market_structure, tokenized_assets, geopolitical, prediction_event, ai_enhanced>

## Alpha Signals
<bullet or paragraph>

## Timeframe / Asset Class
<e.g. M5 US30, Daily indices>

## Risk Factors
<bullet list>

## Summary
<one short paragraph>"""


class LibrarianAgent(BaseAgent):
    """
    Reads research tasks from Needs_Action/, researches them (currently via LLM knowledge),
    and produces a Research Plan in Plans/.
    """

    def __init__(
        self,
        vault_path: str,
        llm_client: BaseLLMClient | None = None,
    ):
        super().__init__("LibrarianAgent")
        self.vault_path = Path(vault_path)
        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.plans_dir = self.vault_path / "Plans"
        self.logs_dir = self.vault_path / "Logs"

        if llm_client:
            self.llm = llm_client
        else:
            if os.environ.get("ANTHROPIC_API_KEY"):
                self.llm = AnthropicLLMClient()
            elif os.environ.get("GEMINI_API_KEY"):
                self.llm = GeminiLLMClient()
            else:
                 self.logger.warning("No API key found. Librarian will default to AnthropicLLMClient, which may fail.")
                 self.llm = AnthropicLLMClient()
        self._processed_log = self.logs_dir / "librarian_processed.log"

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
        Scan Needs_Action for .md (and optionally other) files not yet processed.
        Returns list of {"path": Path, "content": str}.
        """
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)
        self.processed = self._load_processed()
        items = []
        for f in self.needs_action_dir.iterdir():
            if not f.is_file() or f.name in self.processed:
                continue
            if f.suffix.lower() == ".md":
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    items.append({"path": f, "content": content})
                except Exception as e:
                    self.log_action("perceive", f"Skip {f.name}: {e}")
        self.log_action("perceive", f"Found {len(items)} new item(s) in Needs_Action")
        return items

    async def reason(self, state: Any) -> Dict[str, Any]:
        """
        For each item, call LLM to extract Alpha Signals, Timeframe/Asset Class, Risk Factors.
        Returns {"plans": [{"topic_slug": str, "plan_md": str, "source_path": Path}], "items": state}.
        """
        if not state:
            return {"plans": [], "items": state}
        plans = []
        for item in state:
            path, content = item["path"], item["content"]
            # Parse EDGE_TYPE from input so we can inject into plan
            edge_type = ""
            for line in content.splitlines():
                if line.strip().upper().startswith("EDGE_TYPE:"):
                    edge_type = line.split(":", 1)[1].strip()
                    break
            prompt = PROMPT_TEMPLATE.format(content=content[:12000])
            try:
                raw = await self.llm.complete(prompt, system=SYSTEM_LIBRARIAN)
                if edge_type and "## Edge Type" not in raw:
                    raw = "## Edge Type\n" + edge_type + "\n\n" + raw
                # Parse topic slug: first line after "## Topic" or filename fallback
                topic_slug = "unknown"
                seen_topic = False
                for line in raw.splitlines():
                    if line.strip().lower().startswith("## topic"):
                        seen_topic = True
                        continue
                    if seen_topic and line.strip() and not line.strip().startswith("#"):
                        s = line.strip()
                        topic_slug = "".join(c if c.isalnum() or c in "_-" else "_" for c in s)[:40] or "unknown"
                        break
                if topic_slug == "unknown":
                    topic_slug = path.stem.replace(" ", "_").replace("-", "_")[:40]
                plans.append({
                    "topic_slug": topic_slug,
                    "plan_md": raw,
                    "source_path": path,
                })
            except Exception as e:
                self.log_action("reason", f"LLM failed for {path.name}: {e}")
        return {"plans": plans, "items": state}

    async def act(self, plan: Dict[str, Any]) -> bool:
        """
        Write each RESEARCH_PLAN_<Topic>.md to Plans/ and mark source files as processed.
        """
        plans_list = plan.get("plans") or []
        items = plan.get("items") or []
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        for p in plans_list:
            slug = p.get("topic_slug", "unknown")
            plan_md = p.get("plan_md", "")
            out_path = self.plans_dir / f"RESEARCH_PLAN_{slug}.md"
            out_path.write_text(plan_md, encoding="utf-8")
            self.log_action("act", f"Wrote {out_path.name}")
        for item in items:
            self._mark_processed(item["path"])
        return True
