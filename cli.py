"""Entry point: python3 cli.py run data/mock_backlog.json"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from backlog_readiness.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
