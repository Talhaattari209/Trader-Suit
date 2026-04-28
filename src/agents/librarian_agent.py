"""
Librarian Agent: Senior Quantitative Researcher.
Ingests raw information from Needs_Action and produces RESEARCH_PLAN_<Topic>.md in Plans/.
Uses LLM (Claude) to extract Alpha Signals, Timeframe/Asset Class, and Risk Factors.
"""
import os
from pathlib import Path
from typing import Any, Dict, List

from .base_agent import BaseAgent
from ..tools.llm_client import BaseLLMClient, GeminiLLMClient, get_default_llm_client


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
        *,
        bootstrap_context: str | None = None,
        skill_context: str | None = None,
    ):
        super().__init__("LibrarianAgent")
        self.vault_path = Path(vault_path)
        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.plans_dir = self.vault_path / "Plans"
        self.logs_dir = self.vault_path / "Logs"
        self._bootstrap_context = bootstrap_context or ""
        self._skill_context = skill_context or ""

        if llm_client:
            self.llm = llm_client
        else:
            self.llm = get_default_llm_client()  # Gemini by default
        self._processed_log = self.logs_dir / "librarian_processed.log"

        # FilesystemStore for alpha persistence and similarity checks
        try:
            from src.persistence.filesystem_store import FilesystemStore
            self._store = FilesystemStore()
        except Exception:
            self._store = None

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
        Also runs similarity check via FilesystemStore and embeds report in plan.
        Returns {"plans": [{"topic_slug": str, "plan_md": str, "source_path": Path}], "items": state}.
        """
        if not state:
            return {"plans": [], "items": state}
        plans = []
        for item in state:
            path, content = item["path"], item["content"]
            edge_type = ""
            for line in content.splitlines():
                if line.strip().upper().startswith("EDGE_TYPE:"):
                    edge_type = line.split(":", 1)[1].strip()
                    break

            # ── Similarity check via FilesystemStore ──────────────────────────
            similarity_section = ""
            if self._store:
                try:
                    similar = self._store.find_similar_alphas(content[:500], top_k=3)
                    if similar:
                        lines = ["## Similarity Analysis\n"]
                        for s in similar:
                            score = s.get("similarity_score", 0)
                            hyp   = s.get("hypothesis", "")[:80]
                            aid   = s.get("alpha_id", "?")
                            pl    = s.get("price_levels", {})
                            day_h = pl.get("session_levels", {}).get("day", {}).get("high", "—")
                            lines.append(
                                f"- **{aid}** (score: {score:.2f}): {hyp}\n"
                                f"  - Day High: {day_h}\n"
                            )
                        if similar[0].get("similarity_score", 0) > 0.7:
                            lines.append(
                                "\n> **Recommendation:** High similarity detected. "
                                "Consider merging with existing alpha or confirming novelty."
                            )
                        similarity_section = "\n".join(lines) + "\n\n"
                except Exception as e:
                    self.log_action("reason", f"Similarity check failed: {e}")

            prompt = PROMPT_TEMPLATE.format(content=content[:12000])
            system = SYSTEM_LIBRARIAN
            if self._bootstrap_context or self._skill_context:
                extra = []
                if self._bootstrap_context:
                    extra.append(self._bootstrap_context)
                if self._skill_context:
                    extra.append("## Agent skills\n\n" + self._skill_context)
                system = "\n\n".join(extra) + "\n\n---\n\n" + system
            try:
                raw = await self.llm.complete(prompt, system=system)
                if edge_type and "## Edge Type" not in raw:
                    raw = "## Edge Type\n" + edge_type + "\n\n" + raw
                # Prepend similarity section
                if similarity_section:
                    raw = similarity_section + raw

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
        Also saves alpha record to DataStore/alphas.json and advances workflow state.
        """
        plans_list = plan.get("plans") or []
        items = plan.get("items") or []
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        for p in plans_list:
            slug     = p.get("topic_slug", "unknown")
            plan_md  = p.get("plan_md", "")
            out_path = self.plans_dir / f"RESEARCH_PLAN_{slug}.md"
            out_path.write_text(plan_md, encoding="utf-8")
            self.log_action("act", f"Wrote {out_path.name}")

            # ── Save alpha to DataStore ───────────────────────────────────────
            if self._store:
                try:
                    alpha_id = self._store.save_alpha({
                        "hypothesis": slug,
                        "edge_type": "unknown",
                        "regime_tags": [],
                        "plan_path": str(out_path),
                        "status": "draft",
                    })
                    self._store.advance_workflow_step("librarian_done", {
                        "alpha_id": alpha_id,
                        "plan_path": str(out_path),
                    })
                    self.log_action("act", f"Saved alpha {alpha_id} to DataStore")
                except Exception as e:
                    self.log_action("act", f"DataStore save failed: {e}")

        for item in items:
            self._mark_processed(item["path"])
        return True
