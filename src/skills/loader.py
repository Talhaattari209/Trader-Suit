"""
Skill loader: three-tier resolution (workspace > managed > bundled).
Returns markdown text for the given agent for injection into agent context.
Non-breaking: if no skill file found, returns empty string.
"""
from pathlib import Path
from typing import Optional

# Canonical agent names that map to skill dirs
AGENT_SKILL_DIRS = (
    "watchers",
    "librarian",
    "strategist",
    "killer",
    "risk_architect",
    "execution_manager",
    "reporter",
)
SKILL_FILENAME = "SKILL.md"


def load_skill_for_agent(
    agent_name: str,
    workspace_root: Optional[str | Path] = None,
) -> str:
    """
    Load SKILL.md for the given agent from highest-priority tier that has it.

    Tier order:
      1. workspace: ./skills/<agent>/SKILL.md or <workspace_root>/skills/<agent>/SKILL.md
      2. managed:   ~/.alpha-factory/skills/<agent>/SKILL.md
      3. bundled:   src/skills/<agent>/SKILL.md (relative to workspace or cwd)

    agent_name: e.g. "librarian", "strategist", "killer", "risk_architect", "reporter",
                "watchers", "execution_manager". Normalized to lowercase.

    Returns:
        Content of SKILL.md or empty string if not found.
    """
    agent = agent_name.strip().lower().replace(" ", "_")
    if agent == "librarianagent":
        agent = "librarian"
    elif agent == "strategistagent":
        agent = "strategist"
    elif agent == "killeragent":
        agent = "killer"
    elif agent == "riskarchitectagent" or agent == "risk_architect_agent":
        agent = "risk_architect"
    elif agent == "reporteragent":
        agent = "reporter"

    root = Path(workspace_root) if workspace_root else Path.cwd()

    # Tier 1: workspace skills/
    ws_skills = root / "skills" / agent / SKILL_FILENAME
    if ws_skills.exists() and ws_skills.is_file():
        return _read_file(ws_skills)

    # Tier 2: managed ~/.alpha-factory/skills/
    home = Path.home()
    managed = home / ".alpha-factory" / "skills" / agent / SKILL_FILENAME
    if managed.exists() and managed.is_file():
        return _read_file(managed)

    # Tier 3: bundled src/skills/<agent>/SKILL.md
    # Resolve src from root (project root may be parent of src)
    for base in (root, root.parent):
        bundled = base / "src" / "skills" / agent / SKILL_FILENAME
        if bundled.exists() and bundled.is_file():
            return _read_file(bundled)
    # If we're running from repo root, src/skills/ might be under cwd
    bundled_cwd = Path.cwd() / "src" / "skills" / agent / SKILL_FILENAME
    if bundled_cwd.exists() and bundled_cwd.is_file():
        return _read_file(bundled_cwd)

    return ""


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
