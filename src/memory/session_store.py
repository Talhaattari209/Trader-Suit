"""
Session store: optional JSONL transcript per agent/session (OpenClaw-style).
Stored under ~/.alpha-factory/agents/<agent_id>/sessions/ or in-memory only.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

_BASE_DIR = Path(os.environ.get("ALPHA_FACTORY_HOME", os.path.expanduser("~/.alpha-factory")))


def _sessions_dir(agent_id: str) -> Path:
    return _BASE_DIR / "agents" / agent_id / "sessions"


def append_transcript(agent_id: str, session_id: str, role: str, content: str, meta: Optional[Dict[str, Any]] = None) -> None:
    """Append one line (JSONL) to the session transcript. Creates dirs if needed."""
    path = _sessions_dir(agent_id) / f"{session_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"role": role, "content": content[:5000], **(meta or {})}, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def read_transcript(agent_id: str, session_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """Read last limit lines from session transcript. Returns list of dicts."""
    path = _sessions_dir(agent_id) / f"{session_id}.jsonl"
    if not path.exists():
        return []
    lines = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return lines[-limit:] if limit else lines


def list_sessions(agent_id: str) -> List[str]:
    """List session_id (stem of .jsonl files) for the agent."""
    d = _sessions_dir(agent_id)
    if not d.exists():
        return []
    return [f.stem for f in d.glob("*.jsonl")]
