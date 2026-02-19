import os
import time
import logging
from pathlib import Path
from abc import ABC, abstractmethod
import shutil
from datetime import datetime
import json

from .base_watcher import BaseWatcher

# Optional: set USE_CONNECTOR_FETCH=1 and BROKER_TYPE=alpaca|mt5 to also ingest from broker API
USE_CONNECTOR_FETCH_ENV = "USE_CONNECTOR_FETCH"
CONNECTOR_SYMBOL_ENV = "CONNECTOR_SYMBOL"
CONNECTOR_TIMEFRAME_ENV = "CONNECTOR_TIMEFRAME"
CONNECTOR_COUNT_ENV = "CONNECTOR_COUNT"


class DataIngestionWatcher(BaseWatcher):
    def __init__(self, vault_path: str, data_source_path: str, check_interval: int = 60, use_connector_fetch: bool | None = None):
        super().__init__(vault_path, check_interval)
        self.data_source_path = Path(data_source_path)
        self.processed_files = self._load_processed_files() # To prevent reprocessing
        # When True, also fetch OHLCV from ConnectorFactory (BROKER_TYPE) and create DATA_connector_*.md
        self.use_connector_fetch = use_connector_fetch if use_connector_fetch is not None else (os.environ.get(USE_CONNECTOR_FETCH_ENV, "").strip().lower() in ("1", "true", "yes"))

    def _load_processed_files(self) -> set:
        processed_log = self.vault_path / 'Logs' / 'data_processed.log'
        if processed_log.exists():
            return set(processed_log.read_text().splitlines())
        return set()

    def _save_processed_file(self, filename: str):
        processed_log = self.vault_path / 'Logs' / 'data_processed.log'
        with open(processed_log, 'a') as f:
            f.write(f'{filename}\n')
        self.processed_files.add(filename)

    def check_for_updates(self) -> list:
        new_items = []
        for item in self.data_source_path.iterdir():
            if item.is_file() and item.name not in self.processed_files:
                # For now, only process CSV and JSON files for market data
                if item.suffix.lower() in ['.csv', '.json']:
                    new_items.append(item)
        # Optional: fetch from broker connector and create a virtual "new" data file
        if self.use_connector_fetch and os.environ.get("BROKER_TYPE"):
            connector_item = self._fetch_from_connector()
            if connector_item:
                new_items.append(connector_item)
        return new_items

    def _fetch_from_connector(self) -> Path | None:
        """If USE_CONNECTOR_FETCH and BROKER_TYPE are set, fetch OHLCV from connector and create DATA_connector_*.md. Returns path to action file or None."""
        try:
            from ..connectors import get_connector
            connector = get_connector()
            connector.connect()
            symbol = os.environ.get(CONNECTOR_SYMBOL_ENV, "US30")
            timeframe = os.environ.get(CONNECTOR_TIMEFRAME_ENV, "1h")
            count = int(os.environ.get(CONNECTOR_COUNT_ENV, "500"))
            df = connector.get_ohlcv(symbol, timeframe, count)
            if df is None or df.empty:
                return None
            # Write CSV to Research_Data and create action file
            date_str = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"connector_{symbol}_{timeframe}_{date_str}.csv"
            dest = self.vault_path / "Research_Data" / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(dest)
            action_path = self.create_action_file(dest)
            self._save_processed_file(filename)
            return action_path
        except Exception as e:
            self.logger.warning("Connector fetch skipped: %s", e)
            return None

    def create_action_file(self, item: Path) -> Path:
        # Copy the file to Research_Data (or a specific Market_Data folder if created later) for Claude to access
        destination_path = self.vault_path / 'Research_Data' / item.name # Assuming Research_Data can hold raw data
        shutil.copy2(item, destination_path)

        # Create a markdown file in Needs_Action for Claude Code processing
        filename_without_suffix = item.stem
        action_filepath = self.needs_action / f'DATA_{filename_without_suffix}.md'
        content = f"""---
type: market_data_ingestion
original_filename: {item.name}
file_path: {destination_path.relative_to(self.vault_path)}
received_at: {datetime.now().isoformat()}
status: new
---

## New Market Data: {item.name}

New market data has been ingested. Please process this data for analysis and potential alpha generation.

[Link to file in vault: [[Research_Data/{item.name}]]]
"""
        action_filepath.write_text(content)
        self.logger.info(f'Created data ingestion action file: {action_filepath}')
        self._save_processed_file(item.name)
        return action_filepath

# Example usage (for testing, not part of the deployed watcher)
if __name__ == "__main__":
    # In a real scenario, these would be configured via environment variables or a config file
    VAULT_PATH = "AI_Employee_Vault"
    DATA_SOURCE_PATH = "AI_Employee_Vault/Needs_Action/DataSource" # Simulate an input folder for data

    # Ensure directories exist for the example
    Path(VAULT_PATH).mkdir(exist_ok=True)
    (Path(VAULT_PATH) / 'Needs_Action').mkdir(exist_ok=True)
    (Path(VAULT_PATH) / 'Logs').mkdir(exist_ok=True)
    (Path(VAULT_PATH) / 'Research_Data').mkdir(exist_ok=True)
    Path(DATA_SOURCE_PATH).mkdir(exist_ok=True)

    # Create a dummy data file for testing
    dummy_csv_file = Path(DATA_SOURCE_PATH) / "sample_market_data.csv"
    if not dummy_csv_file.exists():
        dummy_csv_file.write_text("Date,Open,High,Low,Close,Volume\n2023-01-01,100,105,98,103,1000\n2023-01-02,103,107,101,106,1200")

    watcher = DataIngestionWatcher(VAULT_PATH, DATA_SOURCE_PATH, check_interval=5) # Check every 5 seconds for testing
    logging.basicConfig(level=logging.INFO)
    try:
        watcher.run()
    except KeyboardInterrupt:
        logging.info("DataIngestionWatcher stopped.")
