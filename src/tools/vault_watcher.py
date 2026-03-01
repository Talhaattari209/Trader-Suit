"""
Vault watcher: monitor Obsidian_Vault/Needs_Action for new files (monitor_vault skill).
Runs under PM2; use watchdog if available, else polling. Non-blocking.
"""
import logging
import os
import time
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DIR = "Obsidian_Vault/Needs_Action"
DEFAULT_FILE_TYPES = (".pdf", ".csv", ".txt", ".md")
DEFAULT_POLL_INTERVAL = 10


class VaultWatcher:
    """
    Watches a directory for new files of given types and invokes a callback.
    Use start() in a PM2-managed process; callback can trigger Librarian ingestion.
    """

    def __init__(
        self,
        directory: str | Path = DEFAULT_DIR,
        file_types: tuple = DEFAULT_FILE_TYPES,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        on_new_file: Optional[Callable[[Path], None]] = None,
    ):
        self.directory = Path(directory)
        self.file_types = tuple(ft if ft.startswith(".") else f".{ft}" for ft in file_types)
        self.poll_interval = poll_interval
        self.on_new_file = on_new_file or (lambda p: logger.info("New file: %s", p))
        self._seen: set = set()
        self._running = False

    def _discover(self) -> List[Path]:
        if not self.directory.exists():
            return []
        return [f for f in self.directory.iterdir() if f.is_file() and f.suffix.lower() in self.file_types]

    def poll_once(self) -> int:
        """Check for new files, call on_new_file for each new one. Returns count of new files."""
        current = {f.resolve(): f for f in self._discover()}
        new = [p for k, p in current.items() if k not in self._seen]
        for path in new:
            self._seen.add(path.resolve())
            try:
                self.on_new_file(path)
            except Exception as e:
                logger.exception("on_new_file %s: %s", path, e)
        return len(new)

    def run(self) -> None:
        """Blocking run: poll every poll_interval seconds. Stop with Ctrl+C."""
        self.directory.mkdir(parents=True, exist_ok=True)
        self._seen = {f.resolve() for f in self._discover()}
        self._running = True
        logger.info("VaultWatcher started: %s", self.directory)
        while self._running:
            self.poll_once()
            time.sleep(self.poll_interval)

    def stop(self) -> None:
        self._running = False
