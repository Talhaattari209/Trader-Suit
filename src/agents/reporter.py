"""
Reporter Agent: "Monday Morning Briefing".
Analyzes Logs/ and Accounting/ data; generates weekly Markdown report in AI_Employee_Vault/Reports/.
Content: P&L summary, strategy approvals/rejections stats, market regime analysis.
Paradigms Task 1: graveyard summaries with journaled failure insights, alpha decay trends (when DATABASE_URL set).
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Any, Dict, List

from .base_agent import BaseAgent


class ReporterAgent(BaseAgent):
    """
    Scans Logs/ (Risk_Audit_*.md, etc.) and Accounting/ (P&L CSVs/JSONs if present);
    produces a weekly briefing in Reports/.
    """

    def __init__(
        self,
        vault_path: str,
        *,
        bootstrap_context: str | None = None,
        skill_context: str | None = None,
    ):
        super().__init__("Reporter")
        self.vault_path = Path(vault_path)
        self.logs_dir = self.vault_path / "Logs"
        self.accounting_dir = self.vault_path / "Accounting"
        self.reports_dir = self.vault_path / "Reports"

    async def perceive(self, input_data: Any) -> Any:
        """
        Gather Logs (risk audits) and Accounting (P&L) data.
        Returns {"audits": [...], "accounting": [...]}.
        """
        audits = []
        if self.logs_dir.exists():
            for f in sorted(self.logs_dir.glob("Risk_Audit_*.md")):
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    audits.append({"path": f.name, "text": text})
                except Exception as e:
                    self.log_action("perceive", f"Skip {f.name}: {e}")

        accounting = []
        if self.accounting_dir.exists():
            for f in self.accounting_dir.iterdir():
                if not f.is_file():
                    continue
                try:
                    if f.suffix.lower() == ".csv":
                        import csv
                        rows = list(csv.DictReader(f.open(encoding="utf-8", errors="replace")))
                        accounting.append({"path": f.name, "type": "csv", "rows": rows})
                    elif f.suffix.lower() == ".json":
                        import json
                        data = json.loads(f.read_text(encoding="utf-8", errors="replace"))
                        accounting.append({"path": f.name, "type": "json", "data": data})
                except Exception as e:
                    self.log_action("perceive", f"Skip accounting {f.name}: {e}")

        self.log_action("perceive", f"Found {len(audits)} audit(s), {len(accounting)} accounting file(s)")
        return {"audits": audits, "accounting": accounting}

    def _parse_audit_decision(self, text: str) -> Dict[str, Any]:
        d = {"decision": None, "prob_of_ruin": None, "timestamp": None}
        if "decision:" in text:
            m = re.search(r"decision:\s*(\w+)", text, re.I)
            if m:
                d["decision"] = m.group(1).strip()
        if "prob_of_ruin:" in text:
            m = re.search(r"prob_of_ruin:\s*([\d.]+)", text)
            if m:
                try:
                    d["prob_of_ruin"] = float(m.group(1))
                except ValueError:
                    pass
        if "timestamp:" in text:
            m = re.search(r"timestamp:\s*([^\n]+)", text)
            if m:
                d["timestamp"] = m.group(1).strip()
        return d

    async def reason(self, state: Any) -> Dict[str, Any]:
        """
        Aggregate: approval/rejection counts, P&L summary from accounting, regime note.
        """
        if not state:
            return {"report_sections": {}, "audits": [], "accounting": []}

        audits = state.get("audits") or []
        accounting = state.get("accounting") or []

        decisions = []
        for a in audits:
            parsed = self._parse_audit_decision(a["text"])
            parsed["path"] = a["path"]
            decisions.append(parsed)

        approved = sum(1 for d in decisions if d.get("decision") == "APPROVE")
        rejected = sum(1 for d in decisions if d.get("decision") == "REJECT")
        flagged = sum(1 for d in decisions if d.get("decision") == "FLAG")

        # P&L summary from accounting
        pnl_summary = "No accounting data available."
        total_pnl = None
        if accounting:
            totals = []
            for acc in accounting:
                if acc.get("type") == "csv" and acc.get("rows"):
                    rows = acc["rows"]
                    for row in rows:
                        for k, v in row.items():
                            if k and v and ("pnl" in k.lower() or "profit" in k.lower() or "return" in k.lower()):
                                try:
                                    totals.append(float(str(v).replace(",", "")))
                                except ValueError:
                                    pass
                elif acc.get("type") == "json":
                    data = acc.get("data")
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if "pnl" in k.lower() or "profit" in k.lower():
                                try:
                                    totals.append(float(v))
                                except (TypeError, ValueError):
                                    pass
            if totals:
                total_pnl = sum(totals)
                pnl_summary = f"Total P&L (from accounting files): {total_pnl:,.2f}"

        # Regime note: from latest audit regime section if present
        regime_note = "No regime stress detail in logs."
        if audits:
            last = audits[-1]["text"]
            if "Regime Stress" in last or "prob_of_ruin" in last:
                regime_note = "Regime stress tests (2020_crash, 2022_bear, 2023_chop) are included in recent Risk Audits."

        # Paradigms Task 1: graveyard and alpha decay (optional, when DATABASE_URL set)
        graveyard_entries = []
        alpha_decay_trends = {}
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            try:
                from src.db.db_handler import DBHandler
                db = DBHandler(db_url)
                await db.connect()
                try:
                    graveyard_entries = await db.fetch_graveyard_entries(limit=50)
                    for e in graveyard_entries:
                        ctx = e.get("context") or {}
                        mode = ctx.get("failure_mode") or "other"
                        alpha_decay_trends[mode] = alpha_decay_trends.get(mode, 0) + 1
                finally:
                    await db.close()
            except Exception as ex:
                self.log_action("reason", f"Graveyard fetch skip: {ex}")

        return {
            "report_sections": {
                "approvals_rejections": {
                    "approved": approved,
                    "rejected": rejected,
                    "flagged": flagged,
                    "total": len(decisions),
                },
                "pnl_summary": pnl_summary,
                "total_pnl": total_pnl,
                "regime_analysis": regime_note,
            },
            "graveyard_entries": graveyard_entries,
            "alpha_decay_trends": alpha_decay_trends,
            "decisions": decisions,
            "audits": audits,
            "accounting": accounting,
        }

    async def act(self, plan: Dict[str, Any]) -> bool:
        """Write weekly briefing Markdown to Reports/."""
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        sections = plan.get("report_sections") or {}
        stats = sections.get("approvals_rejections") or {}
        week_end = datetime.now()
        week_start = week_end - timedelta(days=7)
        fname = f"Monday_Briefing_{week_end.strftime('%Y-%m-%d')}.md"
        path = self.reports_dir / fname

        graveyard_entries = plan.get("graveyard_entries") or []
        alpha_decay_trends = plan.get("alpha_decay_trends") or {}
        graveyard_section = "No graveyard data (DATABASE_URL not set or empty)."
        if graveyard_entries:
            lines = []
            for e in graveyard_entries[:15]:
                ctx = e.get("context") or {}
                mode = ctx.get("failure_mode", "other")
                desc = (ctx.get("description") or e.get("hypothesis", ""))[:200]
                lines.append(f"- **{mode}**: {desc}...")
            graveyard_section = "\n".join(lines) + (f"\n\n_({len(graveyard_entries)} total entries)_" if len(graveyard_entries) > 15 else "")
        decay_section = "No failure mode breakdown (no graveyard data)."
        if alpha_decay_trends:
            decay_section = " | ".join(f"{k}: {v}" for k, v in sorted(alpha_decay_trends.items()))

        body = f"""---
type: weekly_briefing
week_start: {week_start.date().isoformat()}
week_end: {week_end.date().isoformat()}
generated_at: {datetime.now().isoformat()}
---

# Monday Morning Briefing — {week_end.strftime('%Y-%m-%d')}

## P&L Summary

{sections.get('pnl_summary', 'N/A')}

## Strategy Approvals / Rejections

| Decision | Count |
|----------|-------|
| APPROVE  | {stats.get('approved', 0)} |
| REJECT   | {stats.get('rejected', 0)} |
| FLAG     | {stats.get('flagged', 0)} |
| **Total** | {stats.get('total', 0)} |

## Market Regime Analysis

{sections.get('regime_analysis', 'N/A')}

## Strategy Graveyard & Failure Journals

{graveyard_section}

## Alpha Decay Trends (by failure_mode)

{decay_section}

## Notes

- Review FLAG strategies for overfitting before promoting to Done.
- Move REJECT strategies to Strategy_Graveyard.
- Use Telegram `/failure_report` to query graveyard journals.
"""
        path.write_text(body, encoding="utf-8")
        self.log_action("act", f"Wrote {path.name}")
        return True
