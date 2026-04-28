from pathlib import Path

import_block = (
    "try:\n"
    "    from src.dashboard.config import API_BASE_URL\n"
    "except ImportError:\n"
    '    API_BASE_URL = "http://localhost:8000"\n'
)
marker = "from src.dashboard.autonomous_chat import render_autonomous_agent_widget\n"
pages_dir = Path("src/dashboard/pages")
targets = [
    "2_Vault_Explorer.py",
    "6_Optimization_Lab.py",
    "8_Situational_Analysis.py",
    "9_Technical_Analysis.py",
    "3_No_Code_Builder.py",
]
for fname in targets:
    fpath = pages_dir / fname
    src = fpath.read_text(encoding="utf-8")
    if "API_BASE_URL" in src:
        print(f"SKIP (has it): {fname}")
        continue
    if marker in src:
        fpath.write_text(src.replace(marker, marker + import_block, 1), encoding="utf-8")
        print(f"FIXED: {fname}")
    else:
        print(f"WARN marker not found: {fname}")
