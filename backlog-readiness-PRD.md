# Backlog Readiness Analyzer: Product Requirements Document

Status: v1 built and tested against mock data. Author: Program Manager. Last updated: 2026-10-28 (decisions on open questions applied).

## 1. Summary

Sprint planning only works when the cards at the top of the backlog are ready to pull. In practice a
backlog accumulates one-line descriptions, stories with no acceptance criteria, bugs with no steps to
reproduce, tech debt with no file named, and tickets nobody has touched in six months. Nobody sees the
size of the problem until sprint planning, when it costs the whole team time.

The Backlog Readiness Analyzer reads a backlog export for a program, checks every ticket against a rule
set that depends on its type, and reports how healthy each team's backlog is: what share is ready, what is
not and exactly why, how much ready work sits at the top, and how many sprints of runway that gives. Run
weekly, it also shows whether refinement is working, by comparing each run with the last.

It is the fifth project in the TPM automation portfolio and the first that works on the *quality of the
backlog itself*. It sits upstream of the Sprint Planning Automator, which only backfills from the Sprint
Ready pile and assumes that pile is healthy.

## 2. Problem

Observed on a three-team program:

- Product Owners cannot tell at a glance which tickets are ready and which are not, so planning meetings
  turn into live refinement.
- "Ready" means different things to different people. A ticket with a title and a story point is called
  ready by one team and rejected by another.
- Old tickets pile up. Cards created more than six months ago are rarely re-read, and often describe a
  world that has changed.
- Nothing measures refinement progress, so the effort is invisible to leadership.

## 3. Goals and non-goals

### Goals

1. Score every backlog ticket as **Ready**, **Almost ready** (exactly one gap) or **Not ready**, with a
   plain-English reason for every gap.
2. Apply different required content by ticket type: user story, bug, tech debt, research, spike, task.
3. Report per team and for the whole program: ready share, tickets to fix, tickets 6+ months old, ready
   share of the top of the backlog, and runway in sprints.
4. Show which ticket types are weakest on which team (team by type matrix).
5. Keep a dated snapshot of every run and report what changed since the previous run, so improvement is
   visible week over week.
6. Run on mock data with no network, no API key and no paid dependency, like the earlier projects.

### Non-goals (v1)

- No live JIRA integration. v1 reads a JSON export. A connector is v2 (Section 13).
- No judgment of *content quality* by an LLM. v1 checks that required content is present and shaped
  correctly (for example, a story has "so that"), not that it is well written.
- No writing back to JIRA. The tool reports; people decide.
- No estimation. Missing story points never make a ticket not ready.

## 4. Users

| User | Needs |
|---|---|
| Program Manager (primary) | Program-wide health, trend, which team and ticket type to coach |
| Product Owner (per team) | The exact list of their tickets to fix, in rank order, with the reason for each |
| Engineering lead | Whether the top of the backlog is safe to pull, and runway |
| Leadership | One number per team and its direction |

## 5. Data

### 5.1 Input

One JSON file per run: `{ "meta": {...}, "tickets": [...] }`.

`meta`: `as_of` (ISO date the analysis is evaluated on), `teams` (`team_id` to `name` and `velocity` in
points per sprint), `note`.

Each ticket:

| Field | Notes |
|---|---|
| `key`, `team_id`, `team` | Card id (for example `ALPHA-304`), stable team key (`team_alpha`), and the **Team** custom field (`Team Alpha`). `team` must match the team name for `team_id`; grouping uses `team_id`. Same fields in every portfolio project (see `DATA_CONTRACT.md`). |
| `type` | `Story`, `Bug`, `Tech Debt`, `Research`, `Spike`, `Task` |
| `summary`, `description` | Free text |
| `acceptance_criteria` | A custom field in JIRA, kept separate from `description` |
| `rank` | Position in the team's backlog; 1 is the top |
| `story_points` | Optional |
| `parent` | Epic or feature link, optional |
| `severity` | Optional, used on bugs |
| `blocked_by` | Key of the blocking ticket, optional |
| `assignee`, `start_date` | Used on spikes |
| `priority`, `created`, `updated`, `status` | `created` and `updated` drive age and staleness |

### 5.2 Mock data

`data/mock_backlog.json` has 100 tickets across Team Alpha (34), Team Bravo (33) and Team Charlie (33), with
all six ticket types. Team names, card prefixes, velocities (32, 24, 18) and features follow the earlier
portfolio projects, so card ids stay consistent across the series. Quality is deliberately mixed, with
planted gaps: blank and one-line descriptions, stories with no acceptance criteria or no "so that", bugs
missing expected results, tech debt with no file, spikes with no assignee, cross-team blockers, one
near-duplicate pair, and about a third of tickets older than six months. It is generated by
`scripts/generate_mock_backlog.py` with a fixed seed, so it is reproducible.

`data/mock_backlog_week1.json` and `mock_backlog_week2.json` are **simulated** refinement weeks (Section 9,
US-9), clearly labeled as such, used only to demonstrate and test the comparison.

## 6. Readiness rules

A *gap* is required content that is missing. Gaps decide the tier. *Flags to review* are advisory and never
change the tier.

| Type | Required (a missing item is a gap) | Flag to review (advisory) |
|---|---|---|
| User story | Description in "As a / I want / so that" form. Acceptance criteria that can be tested: Given / When / Then, or at least two checkable lines, at least 8 words | No points, oversize, no parent |
| Bug | Steps to reproduce; current behavior; expected result | No severity or business impact |
| Tech debt | Problem and needed change described; a code file or component named | No "why it matters" (risk or cost of leaving it) |
| Research | What is to be researched; a Definition of Done | n/a |
| Spike | Description; assignee; start date | No time-box |
| Task | A description that is more than a one-liner | n/a |
| All types | A description that is not blank, a placeholder ("TBD", "See above", "As discussed") or a single line under 10 words. No open blocker: a ticket blocked by another ticket is **Not ready** until the blocker is Done | Dependency mentioned in text but no link; possible duplicate; no update in 90 days; no epic or parent |

### Tiers

- **Ready**: no gaps.
- **Almost ready**: exactly one gap.
- **Not ready**: two or more gaps, a blank / placeholder / one-line description, or an open blocker (a ticket blocked by another team's ticket stays Not ready until that ticket is unblocked, that is Done).

Story points are optional. Cards waiting for refinement are legitimately unpointed, so a missing estimate is
only a flag. A pointed ticket at or above the oversize limit (default 8) gets a prominent **"consider splitting"** warning (in the terminal report, workbook and dashboard), on
the basis that sizing is settled after engineers refine the card. It is a warning only and never changes the tier.

## 7. Metrics

- **Ready %**: Ready tickets divided by total, per team and for the program. Almost ready % and Not ready %
  are reported alongside.
- **6+ months old**: created 182 or more days before `as_of`. Reported with how many of those are not Ready.
  Age tiers (<3 months, 3-6, 6-12, >12) are available per ticket. Days since last update is tracked
  separately.
- **Top of backlog readiness**: ready share of the next two sprints of work, taken in rank order until the
  points reach two times team velocity. Unpointed tickets count as 3 points for this slicing only. The top
  of the backlog matters far more than the tail.
- **Runway**: points on fully Ready, pointed tickets divided by team velocity, in sprints. Ready tickets with no
  points are not counted. Almost ready tickets are never counted.
- **Next-sprint candidates**: Almost ready, unblocked tickets (count and points). They belong in the next sprint
  or the backlog once their one gap is closed.
- **Blocked**: count of tickets with an open blocker.
- **Readiness by type**: Ready % for each team and ticket type.
- **Common gaps**: the most frequent gap reasons per team.
- **Possible duplicates**: ticket pairs whose summaries overlap by 70% or more (token Jaccard).

All thresholds live in `config.py` and can be overridden on the command line.

## 8. Outputs

1. **Terminal report** (`python3 cli.py run ...`): program line, one block per team, duplicates, and with
   `--list` every ticket that is not Ready with its reasons.
2. **Dated snapshot** (`--snapshot-dir`): full result saved as `YYYY-MM-DD.json`.
3. **Change report**: when an earlier snapshot exists, what moved since then.
4. **Trend** (`cli.py trend`): ready share per run, program and team.
5. **Dashboard** (companion, built from the same JSON): program tiles, team cards, team by type matrix,
   filterable ticket list, trend, and the scoring rules.
6. **Workbook** (companion): Summary, Tickets, By Type, Common Gaps and Rules tabs, with formulas over the
   ticket rows.

## 9. User stories

**US-1. Load a backlog export.**
As a Program Manager, I point the tool at a JSON export so that all three teams are analyzed together.
- Accepts the schema in Section 5.1.
- A missing file or missing required key prints one clear message and exits with status 1, never a stack trace.
- `--as-of` overrides the evaluation date.

**US-2. Score tickets by type.**
As a Product Owner, I see each ticket scored against the rules for its type so that "ready" means the same
thing on every team.
- Every ticket gets exactly one tier.
- Rules match Section 6, including the thin-description override.
- Each gap is a plain-English reason (for example "No steps to reproduce").

**US-3. Spot blank, one-line and placeholder descriptions.**
As a Product Owner, I want thin descriptions called out so they are fixed first.
- Blank, placeholder and one-line (under 10 words, single line) descriptions are each named distinctly.
- A thin description always makes the ticket Not ready.

**US-4. Flag tickets that are 6+ months old.**
As a Program Manager, I want old tickets marked so they can be re-validated or closed.
- Marked when created 182+ days before `as_of`; the report states how many are not fully ready.
- Days since last update is separate; 90+ days adds a "Untouched" flag.

**US-5. Report team health.**
As a Program Manager, I want, per team, the count and percent Ready, Almost ready and Not ready.
- Team totals sum to the program total.
- Percentages are rounded to one decimal.

**US-6. Top of backlog and runway.**
As an engineering lead, I want to know whether the next two sprints of work are ready and how many sprints
of ready work exist.
- Slice is rank order up to 2 x velocity points; runway uses only pointed Ready tickets.
- A team with zero velocity reports no runway rather than dividing by zero.

**US-7. Readiness by ticket type.**
As a Program Manager, I want a team by type view so that coaching targets the weak spot.
- A cell is Ready % for that team and type; the count behind it is available.

**US-8. Advisory flags.**
As a Product Owner, I want sizing, structure and dependency flags that do not block readiness.
- Unpointed, oversize (default 8+ points), no parent, bug with no severity, tech debt with no "why it
  matters", spike with no time-box, dependency mentioned without a link, possible duplicate.
- None of these changes a tier.

**US-9. Snapshot and compare.**
As a Program Manager, I want each run saved and compared with the previous one so that I can show
refinement progress.
- Snapshot is saved as `YYYY-MM-DD.json`; re-running the same date overwrites it.
- Change report lists tickets that moved up or down a tier, newly Ready tickets, gaps closed, new and
  removed tickets, newly 6+ months old tickets, and the change in ready share and runway per team.
- The first run is reported as a baseline.
- The simulated weekly data lets this be demonstrated and tested without real JIRA.

**US-10. Trend.**
As leadership, I want the ready share over time so that the direction is clear.
- `cli.py trend` prints one row per saved snapshot, program and team.

**US-11. Tickets-to-fix list.**
As a Product Owner, I want my not-Ready tickets in rank order with reasons.
- `--list` prints Not ready first, then Almost ready, by team and rank, with the 6+ months mark.

**US-12. Configurable thresholds.**
As a Program Manager, I want the thresholds adjustable so the rules fit our team agreements.
- One-liner words, oversize points, stale days, untouched days and top-of-backlog sprints are CLI flags with
  documented defaults.

## 10. Edge cases

- Empty backlog for a team: team reports zero tickets and no percentages, no crash.
- Ticket with a type outside the six known types: treated like a Task (needs a real description).
- Missing optional fields (points, parent, severity): never an error.
- Acceptance criteria stored inside the description instead of the custom field: v1 reads the custom field
  only; documented in Section 13 as a mapping option.
- Two tickets with the same key: not detected in v1; JIRA keys are unique by construction.
- `updated` before `created`: age uses `created`; days since update would be inflated. Out of scope for v1.
- Snapshot directory missing: created on first save.
- Re-running the same `as_of`: snapshot is replaced, comparison uses the previous earlier date.
- Blockers: a gap on the blocked ticket, reported as "Blocked by <key>", that forces Not ready. The gap clears when the blocker's `status` is Done, Closed, Resolved or Released. A blocker missing from the file is treated as open.

## 11. Non-functional requirements

- Full 3-team, 100-ticket analysis completes in well under a second (measured at about 0.01 s).
- Standard library only; Python 3.9+. `pytest` for tests.
- Deterministic: same input and `as_of` give the same output.
- No network access, no API key, no cost.
- Thresholds are configuration, not code constants buried in rules.

## 12. Design decisions

1. **Gaps decide the tier; flags never do.** Mixing "content missing" with "worth a look" made scores hard to
   explain. Keeping them apart means every Not ready ticket has a concrete to-do.
2. **Almost ready is its own tier.** One-gap tickets are the cheapest wins, so they are separated from tickets
   that need real work.
3. **Points are optional.** Unpointed cards are normal before refinement. Oversize is advisory because
   engineers size after refinement.
4. **Top of backlog and runway are first-class.** A healthy tail does not rescue a thin top, and the top is
   what sprint planning pulls from.
5. **Presence and shape, not prose quality.** Cheap, explainable and consistent. LLM quality scoring is a v2
   option that must not replace the deterministic gate.
6. **Snapshots are plain JSON files.** Easy to diff, commit or load into the dashboard without a database.
7. **Mock data is reproducible, simulated weeks are labeled.** Demo data is never presented as real.

## 13. v2 and out of scope

- Live JIRA through the Atlassian connector instead of a JSON export, with field mapping for the acceptance
  criteria custom field and for team (project, component or label).
- Scheduled weekly run that posts the change report to the team channel.
- Optional LLM pass that judges *quality* of descriptions and acceptance criteria, shown as a separate score.
- Write-back: comment on a Not ready ticket listing its gaps, or label it.
- Auto-detect acceptance criteria written inside the description.
- Per-person view (tickets to fix by assignee or Product Owner).
- Link to the Sprint Planning Automator so only Ready tickets enter the Sprint Ready pile.

## 14. Success measures

- Ready share of the top two sprints of work reaches 90% before each planning session.
- Program ready share rises week over week for four consecutive runs.
- Tickets 6+ months old that are not Ready drop to zero, by closing or refining.
- Planning meetings spend less time on live refinement (tracked by the Program Manager).

## 15. Decisions on earlier open questions (2026-10-28)

1. **Runway** counts fully Ready tickets only. Almost ready tickets belong in the next sprint or the backlog, and are reported as next-sprint candidates.
2. **8-point cards** get an advisory "consider splitting" warning so the team can decide whether to split. It never changes readiness.
3. **A ticket blocked by another team's ticket is Not ready** until that ticket is unblocked.
4. **Team** is a custom field on every ticket (`team`, with stable `team_id`), shared by all portfolio projects. `scripts/add_team_field.py` stamps it onto old projects' cards, and `DATA_CONTRACT.md` defines the shared fields.

Shared data (added after the decisions): `teams.json`, `features.json`, `cards.json` (the 10 earlier sprint cards plus the 100 backlog tickets, one schema with the Team field), `risks.json` and `prs.json`, kept in the common `pm-portfolio-mock-data` folder rather than in this project. See `DATA_CONTRACT.md`.

The sprint cards in the shared `cards.json` are your originals from the Sprint Confidence Gap Analyzer, with the new `team` field added.
