# Backlog Readiness Analyzer

Scores every backlog ticket for sprint readiness (Ready / Almost ready / Not ready), per team and for the program,
and tracks improvement week to week. Rules, metrics and decisions are in `backlog-readiness-PRD.md`.

## How to run it (what to do when the user asks to "run the backlog readiness analysis")
1. Work from this folder. Python 3 standard library only, no install needed.
2. Run: `python3 cli.py run ../pm-portfolio-mock-data/cards.json --list --snapshot-dir snapshots --as-of <today YYYY-MM-DD>`
   - Shared data (teams, cards, features) lives in `../pm-portfolio-mock-data`, not in this project.
   - Always pass `--as-of` with today's date for real runs; the file's own date is a mock date.
   - The run saves a dated snapshot in `snapshots/` and prints what changed since the previous run.
3. Summarize for the user: ready % per team, top-of-backlog readiness, runway, blocked tickets, 8+ point split
   warnings, tickets 6+ months old, what changed since last run, and the tickets to fix first (Not ready, then Almost ready).
4. Trend over all runs: `python3 cli.py trend --snapshot-dir snapshots`.
5. Dashboard page: `python3 scripts/build_dashboard.py --as-of <today>` writes `dashboard/index.html` (self-contained, open in a browser). Rebuild it after every run. It matches the shared Claude dashboard: program tiles, team cards, readiness by type, tickets to fix with filters, dependencies, trend.
6. Tests: `python3 -m pytest -q` (35 tests; needs pytest).

## Rules to remember
- Gaps decide the tier; advisories (no points, 8+ pts split warning, no epic, no severity...) never do.
- Ready = no gaps. Almost ready = one gap. Not ready = two or more, a thin description, or an open blocker.
- A ticket blocked by another ticket (usually another team's) is Not ready until the blocker is Done.
- Runway counts fully Ready tickets only. Almost ready tickets are next-sprint candidates.
- `team` is a custom field on every card; grouping uses `team_id`.
- `data/mock_backlog*.json` are mock data; weeks 1 and 2 are SIMULATED. Delete `snapshots/` before the first real run.

## Do not
- Edit files in `../pm-portfolio-mock-data` without asking (other projects copy from it).
- Commit or push without being asked.
