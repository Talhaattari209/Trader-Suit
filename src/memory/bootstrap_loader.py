"""
Bootstrap loader: read AGENTS.md, SOUL.md, TOOLS.md, IDENTITY.md, USER.md
from workspace root or vault and return a single context string (or dict) for agent injection.
Non-breaking: if files are missing, returns empty string / empty dict.
"""
from pathlib import Path
from typing import Dict, Optional


BOOTSTRAP_FILES = ("AGENTS.md", "SOUL.md", "TOOLS.md", "IDENTITY.md", "USER.md")


def load_bootstrap(
    workspace_root: Optional[str | Path] = None,
    vault_path: Optional[str | Path] = None,
    as_dict: bool = False,
) -> str | Dict[str, str]:
    """
    Load bootstrap markdown files from workspace root (or vault_path) and return
    concatenated context string, or dict of filename -> content.

    Priority: workspace_root if set and exists, else vault_path, else current working directory.
    Missing files are skipped (no error). Empty content if none found.

    Args:
        workspace_root: Project/workspace root (e.g. repo root).
        vault_path: Fallback path (e.g. Obsidian_Vault).
        as_dict: If True, return dict of {filename: content}; else return single string.

    Returns:
        Concatenated markdown string with "## <filename>" sections, or dict if as_dict=True.
    """
    root = _resolve_root(workspace_root, vault_path)
    result: Dict[str, str] = {}
    for name in BOOTSTRAP_FILES:
        path = root / name
        if path.exists() and path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    result[name] = text
            except Exception:
                pass

    if as_dict:
        return result

    if not result:
        return ""

    parts = []
    for name in BOOTSTRAP_FILES:
        if name in result:
            parts.append(f"## {name}\n\n{result[name]}")
    return "\n\n---\n\n".join(parts)


def _resolve_root(
    workspace_root: Optional[str | Path] = None,
    vault_path: Optional[str | Path] = None,
) -> Path:
    if workspace_root is not None:
        p = Path(workspace_root)
        if p.exists():
            return p
    if vault_path is not None:
        p = Path(vault_path)
        if p.exists():
            return p
    return Path.cwd()
