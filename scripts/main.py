import sys
import os
import subprocess
from pathlib import Path

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.logger import logger
from engine.runner import EngineRunner


def main():
    """Entry point for the Wellfound Job Application Engine"""
    logger.info("=" * 60)
    logger.info("Wellfound Job Application Engine")
    logger.info("=" * 60)

    print("\nAvailable Actions:")
    print("1. Run Wellfound Engine (Discover Jobs)")
    print("2. Initialize Database")
    print("3. Run Wellfound Engine & Ingest to API")
    print("q. Quit")

    choice = input("\nSelect an option: ").strip().lower()

    if choice == "1":
        runner = EngineRunner()
        runner.run(site_filter="Wellfound")
    elif choice == "2":
        subprocess.run([sys.executable, str(ROOT / "scripts" / "init_db.py")], cwd=str(ROOT))
    elif choice == "3":
        runner = EngineRunner()
        runner.run(site_filter="Wellfound")
        subprocess.run([sys.executable, str(ROOT / "scripts" / "ingest_to_api.py")], cwd=str(ROOT))
    elif choice == "q":
        sys.exit(0)
    else:
        logger.error("Invalid selection")

if __name__ == "__main__":
    main()
