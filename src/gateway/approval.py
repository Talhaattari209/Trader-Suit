"""
Lightweight approval gate: strategy promotion and execution (HITL).
File-based: strategies approved when moved to production; orders when file in Approved/.
"""
from pathlib import Path
from typing import Any, Dict, Optional


def can_approve_strategy(
    decision: str,
    reason: str = "",
    metrics: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    True if Killer decision allows strategy to be promoted to production.
    Does not check file system; callers move file to src/models/production/ when True.
    """
    if decision == "APPROVE":
        return True
    if decision == "FLAG":
        # Caller may still promote after manual review
        return False
    return False


def can_execute_order(
    signal: Dict[str, Any],
    approved_dir: Optional[str | Path] = None,
    require_approved_file: bool = True,
) -> bool:
    """
    True if order is allowed (e.g. file in Approved/ or require_approved_file=False for paper).
    approved_dir: e.g. Obsidian_Vault/Approved; check for a matching signal file or flag file.
    """
    if not require_approved_file:
        return True
    ad = Path(approved_dir) if approved_dir else Path("Obsidian_Vault/Approved")
    if not ad.exists():
        return False
    # Simple rule: if Approved/ contains any .md or .json indicating "go", allow
    for f in ad.iterdir():
        if f.is_file() and f.suffix.lower() in (".md", ".json", ".txt"):
            return True
    return False
