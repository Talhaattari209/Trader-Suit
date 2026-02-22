"""
Run an edge workflow by type (statistical, pattern_based, volume_based, etc.).

Usage (from project root):
  set US30_CSV_PATH=path/to/us30.csv
  python run_edges.py statistical
  python run_edges.py pattern_based
  python run_edges.py --list
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.edges import run_edge_by_type, EDGE_REGISTRY


def main():
    parser = argparse.ArgumentParser(description="Run edge workflow by type")
    parser.add_argument("edge_type", nargs="?", default=None, help="Edge type (e.g. statistical, pattern_based)")
    parser.add_argument("--list", action="store_true", help="List available edge types")
    parser.add_argument("--csv", default=None, help="US30 CSV path (default: US30_CSV_PATH env)")
    args = parser.parse_args()

    if args.list:
        for info in EDGE_REGISTRY:
            print(f"  {info.edge_type}: {info.workflow_module or 'N/A'}")
        return 0

    edge_type = args.edge_type
    if not edge_type:
        print("Provide edge_type or use --list")
        return 1
    csv_path = args.csv or os.environ.get("US30_CSV_PATH")
    approved, metrics = run_edge_by_type(edge_type.strip().lower(), csv_path=csv_path)
    print("Approved:", approved)
    print("Metrics:", metrics)
    return 0 if approved else 1


if __name__ == "__main__":
    sys.exit(main())
