# Backlog Readiness Analyzer

Scores every ticket in a program's backlog for sprint readiness, tells each team exactly what to fix, and
shows whether refinement is working from one week to the next.

Full requirements: [`backlog-readiness-PRD.md`](backlog-readiness-PRD.md).

## Live dashboard

**[Open the backlog readiness dashboard](https://raw.githack.com/Aveerapaneni/backlog-readiness-analyzer/main/dashboard/index.html)**

Shows the latest pushed run of `dashboard/index.html`; it can take a few minutes to refresh after a push.
Once GitHub Pages is enabled (Settings > Pages > Deploy from branch `main`, `/ (root)`), it is also at
https://aveerapaneni.github.io/backlog-readiness-analyzer/dashboard/.

## The problem

Sprint planning assumes the top of the backlog is ready. It usually is not: one-line descriptions, stories
with no acceptance criteria, bugs with no steps to reproduce, tech debt with no file named, and tickets nobody
has touched in six months. The cost shows up in the planning meeting, when the whole team refines live.

This tool reads a backlog export, checks each ticket against rules for its type, and reports how healthy each
team's backlog is and why. It sits upstream of the Sprint Planning Automator, which backfills only from the
Sprint Ready pile and assumes that pile is healthy.

## What it does

For every ticket, by type:

| Type | Must have |
|---|---|
| User story | "As a / I want / so that" description; testable acceptance criteria |
| Bug | Steps to reproduce, current behavior, expected result |
| Tech debt | Problem and needed change; the code file or component |
| Research | What to research; a Definition of Done |
| Spike | Description, assignee, start date |
| Task | A real description, not a one-liner |

Every ticket lands in one tier: **Ready** (no gaps), **Almost ready** (one gap) or **Not ready** (two or more
gaps, or a blank, placeholder or one-line description). A ticket blocked by another ticket (typically another team's) is **Not ready until the blocker is Done**. Runway counts Ready tickets only; Almost ready tickets are shown as next-sprint candidates.

Per team and for the program it reports ready share, tickets 6+ months old, ready share of the top two
sprints of work, runway in sprints, readiness by ticket type, and the most common gaps. Advisory flags (no
points, 8+ point cards (a prominent "consider splitting" warning), no epic, bug with no severity, possible duplicate, untouched for 90 days)
are shown but never change a tier, because unpointed cards are normal before refinement.

## Running it

Python 3.9+, standard library only. No API key, no network.

```
# Analyze a backlog export
python3 cli.py run ../pm-portfolio-mock-data/cards.json   # shared portfolio data; data/mock_backlog.json also works

# List every ticket that is not Ready, with reasons
python3 cli.py run data/mock_backlog.json --list

# Save a dated snapshot and compare with the previous one
python3 cli.py run data/mock_backlog.json --snapshot-dir snapshots

# Ready share across all saved snapshots
python3 cli.py trend --snapshot-dir snapshots
```

Thresholds are flags (`--thin-words`, `--oversize-points`, `--stale-days`, `--untouched-days`,
`--top-sprints`); see `python3 cli.py run --help`. Defaults are documented in `src/backlog_readiness/config.py`.

## Dashboard page

`python3 scripts/build_dashboard.py` writes `dashboard/index.html`, a self-contained page (no server or network) with program tiles, team cards, readiness by type, filterable tickets to fix, dependencies and trend. Open it in a browser; rebuild after each run.

## Tracking teams as they add detail

Run it on the same cadence as backlog refinement, for example every Monday. Each run saves
`snapshots/YYYY-MM-DD.json` and prints what changed since the previous run: tickets that moved up a tier, newly
Ready tickets, gaps closed, new tickets, tickets that just turned six months old, and the change in ready share
and runway per team.

`examples/` shows this on three runs. The two later weeks are **simulated** by
`scripts/simulate_refinement.py` (each Product Owner fixes the four highest-ranked not-Ready tickets and two
thin intake tickets are added), because there is no real JIRA behind the mock data.

| Run | Program ready | Alpha | Bravo | Charlie |
|---|---|---|---|---|
| 2026-10-28 (baseline: 37 Ready / 20 Almost / 43 Not ready) | 37.0% | 35.3% | 39.4% | 36.4% |
| 2026-11-04 (simulated) | 46.2% | 44.4% | 48.6% | 45.7% |
| 2026-11-11 (simulated) | 54.5% | 52.6% | 56.8% | 54.1% |

Real numbers will not climb this smoothly. The table shows the comparison working, not a forecast.

## Data

The mock data plants 16 cross-team dependencies so every case shows up: 13 open blockers (10 on another team's backlog ticket, 3 on a card in another team's active sprint) and 3 cleared because the blocking card is already Done.

Input is one JSON file: `meta` (`as_of`, team names and velocities) and a `tickets` list. The schema is in PRD
Section 5.1. `data/mock_backlog.json` is 100 tickets across Team Alpha, Bravo and Charlie with planted gaps,
generated reproducibly by `scripts/generate_mock_backlog.py`. Card prefixes, team names and velocities match the
earlier portfolio projects.

To use a real JIRA export, map your fields to the schema (acceptance criteria and **Team** are each read from their own custom field) and point `run` at the file. A live connector is v2.

## Project structure

```
backlog-readiness-analyzer/
├── cli.py                          # entry point
├── backlog-readiness-PRD.md        # requirements, rules, user stories, edge cases
├── data/
│   ├── mock_backlog.json           # 100 mock tickets, 3 teams (baseline)
│   └── mock_backlog_week1/2.json   # SIMULATED later weeks, for the comparison demo
├── src/backlog_readiness/
│   ├── config.py                   # every threshold, with defaults
│   ├── rules.py                    # per-type readiness rules and tier logic
│   ├── analyze.py                  # scoring, team/program roll-ups, duplicates, top of backlog, runway
│   ├── history.py                  # snapshots, run-to-run comparison, trend
│   ├── report.py                   # terminal report
│   └── cli.py                      # argument parsing
├── scripts/
│   ├── generate_mock_backlog.py    # reproducible mock data
│   ├── add_team_field.py           # stamps team_id + Team onto an old project's cards.json
│   └── simulate_refinement.py      # demo-only refinement weeks
├── DATA_CONTRACT.md                # shared teams, ids and the Team field (copy also in pm-portfolio-mock-data)
├── examples/                       # sample run output and demo snapshots
└── tests/
```

## Tests

```
python3 -m pip install pytest
python3 -m pytest -q
```

35 tests cover every ticket type's rules (including the boundary cases: one gap vs two, advisory vs required,
placeholders, blocked tickets), roll-up consistency against the mock data, duplicate detection, runway and
top-of-backlog, snapshots and comparison, empty teams and zero velocity, and end-to-end CLI runs including a
clean error on bad input.

## Design notes

- **Gaps decide the tier; flags never do.** Every Not ready ticket has a concrete to-do.
- **Almost ready is its own tier**, because one-gap tickets are the cheapest wins.
- **Points are optional.** Oversize is advisory because engineers size after refinement.
- **Top of backlog and runway** matter more than the overall percentage; a healthy tail does not rescue a thin top.
- **Presence and shape, not prose quality.** Cheap, explainable, consistent.

## Related projects

- **Sprint Planning Automator**: backfills a sprint from the Sprint Ready pile; this tool tells you whether that pile is healthy.
- **RAID Log Automator**, **Sprint Confidence Gap Analyzer**, **Resource Capacity Analyzer**: same card ids and teams.

## v2 (out of scope for now)

- Live JIRA through the Atlassian connector, with field mapping
- Scheduled weekly run that posts the change report to the team channel
- Optional LLM pass that scores the quality of descriptions, shown separately from the readiness gate
- Write-back: comment or label Not ready tickets with their gaps
- Feed only Ready tickets into the Sprint Planning Automator

## Shared data lives elsewhere

`teams.json`, `features.json`, `cards.json`, `risks.json` and `prs.json` are kept in the common folder `../pm-portfolio-mock-data`, not in this project. Only the backlog-specific files stay here (`data/mock_backlog*.json`, `examples/`). Override the location with `BACKLOG_SHARED_DIR`. After regenerating the mock backlog, run `python3 scripts/build_shared_data.py` to refresh the backlog cards in the shared `cards.json`.
