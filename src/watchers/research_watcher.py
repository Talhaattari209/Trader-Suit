import time
import logging
from pathlib import Path
from abc import ABC, abstractmethod
import shutil
from datetime import datetime

# Assuming base_watcher.py is in the same directory
from .base_watcher import BaseWatcher

class ResearchWatcher(BaseWatcher):
    def __init__(self, vault_path: str, research_input_path: str, check_interval: int = 60):
        super().__init__(vault_path, check_interval)
        self.research_input_path = Path(research_input_path)
        self.processed_files = self._load_processed_files() # To prevent reprocessing

    def _load_processed_files(self) -> set:
        # Simple way to keep track of processed files, can be improved with a database
        processed_log = self.vault_path / 'Logs' / 'research_processed.log'
        if processed_log.exists():
            return set(processed_log.read_text().splitlines())
        return set()

    def _save_processed_file(self, filename: str):
        processed_log = self.vault_path / 'Logs' / 'research_processed.log'
        with open(processed_log, 'a') as f:
            f.write(f'{filename}\n')
        self.processed_files.add(filename)

    def check_for_updates(self) -> list:
        new_items = []
        for item in self.research_input_path.iterdir():
            if item.is_file() and item.name not in self.processed_files:
                # For now, only process markdown, text, and PDF files
                if item.suffix.lower() in ['.md', '.txt', '.pdf']:
                    new_items.append(item)
        return new_items

    def create_action_file(self, item: Path) -> Path:
        # Copy the file to Research_Data for Claude to access
        destination_path = self.vault_path / 'Research_Data' / item.name
        shutil.copy2(item, destination_path)

        # Create a markdown file in Needs_Action for Claude Code processing
        filename_without_suffix = item.stem
        action_filepath = self.needs_action / f'RESEARCH_{filename_without_suffix}.md'
        content = f"""---
type: research_input
original_filename: {item.name}
file_path: {destination_path.relative_to(self.vault_path)}
received_at: {datetime.now().isoformat()}
status: new
---

## Research Material: {item.name}

New research material has been ingested. Please analyze this document to extract core alpha hypotheses.

[Link to file in vault: [[Research_Data/{item.name}]]]
"""
        action_filepath.write_text(content)
        self.logger.info(f'Created research action file: {action_filepath}')
        self._save_processed_file(item.name)
        return action_filepath

# Example usage (for testing, not part of the deployed watcher)
if __name__ == "__main__":
    # In a real scenario, these would be configured via environment variables or a config file
    VAULT_PATH = "AI_Employee_Vault"
    RESEARCH_INPUT_PATH = "AI_Employee_Vault/Needs_Action/ResearchInput" # Simulate an input folder

    # Ensure directories exist for the example
    Path(VAULT_PATH).mkdir(exist_ok=True)
    (Path(VAULT_PATH) / 'Needs_Action').mkdir(exist_ok=True)
    (Path(VAULT_PATH) / 'Logs').mkdir(exist_ok=True)
    (Path(VAULT_PATH) / 'Research_Data').mkdir(exist_ok=True)
    Path(RESEARCH_INPUT_PATH).mkdir(exist_ok=True)

    # Create a dummy research file for testing
    dummy_file = Path(RESEARCH_INPUT_PATH) / "sample_research_paper.md"
    if not dummy_file.exists():
        dummy_file.write_text("# Sample Research\nThis is a sample research paper content.")

    watcher = ResearchWatcher(VAULT_PATH, RESEARCH_INPUT_PATH, check_interval=5) # Check every 5 seconds for testing
    logging.basicConfig(level=logging.INFO)
    try:
        watcher.run()
    except KeyboardInterrupt:
        logging.info("ResearchWatcher stopped.")
