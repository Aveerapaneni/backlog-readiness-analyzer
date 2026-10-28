"""Where the shared portfolio files live (teams.json, features.json, cards.json, ...).

They are kept in the common mock-data folder, not in this project: ../pm-portfolio-mock-data next to this
project's folder. Override with the BACKLOG_SHARED_DIR environment variable.
"""
import os

PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SHARED = os.environ.get("BACKLOG_SHARED_DIR") or os.path.abspath(os.path.join(PROJECT, "..", "pm-portfolio-mock-data"))
