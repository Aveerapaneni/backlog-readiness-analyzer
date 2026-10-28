# Shared mock data contract

All portfolio projects (Sprint Planning, RAID Log, RAID-Sprint Bridge, Sprint Confidence Gap, Resource Capacity,
Backlog Readiness) should read the same teams, ids and card fields so new projects can be built on one dataset.

## Teams (identical everywhere)

The source of truth is `pm-portfolio-mock-data/teams.json` (unchanged from your earlier projects): `team_id`, `team_name`, `velocity`,
`product_owner`, `engineers`, `active_sprint_id`. Spike assignees in the backlog are drawn from each team's `engineers`.
RAID owners in the earlier RAID log (Marcus Cho, Priya Nair, Dana Lee) are the product owners listed there.

| team_id | Team (custom field) | Card prefix | Velocity | Features |
|---|---|---|---|---|
| team_alpha | Team Alpha | ALPHA | 32 | FEAT-01 Account Settings & SSO, FEAT-02 Payment Reliability |
| team_bravo | Team Bravo | BRAVO | 24 | see features.json |
| team_charlie | Team Charlie | CHAR | 18 | see features.json |

## Shared files (in `pm-portfolio-mock-data`, not in this project)

| File | Contents |
|---|---|
| `teams.json` | 3 teams: id, name, velocity, product owner, engineers, active sprint. Unchanged from the Sprint Confidence Gap Analyzer |
| `features.json` | FEAT-01..FEAT-04 with owner and linked cards. Copied unchanged from the same place |
| `cards.json` | `{"sprints", "cards"}`: the 10 sprint cards from your earlier projects, unchanged, plus 100 backlog tickets (`status: "backlog"`), all with the new `team` field |

Sprint card fields (unchanged): `card_id`, `team_id`, `sprint_id`, `title`, `priority`, `story_points`, `status`
(done / in_progress), `linked_pr_id`, `linked_risk_ids`, `feature_id`. Backlog cards use the same fields with
`sprint_id: null`, and add `issue_type`, `rank`, `severity`, `blocked_by`, `created`, `updated`, `description`,
`acceptance_criteria`, `assignee`, `start_date`. Rebuild with `python3 scripts/build_shared_data.py`.

Not included: the five extra cards in sprint-planning-automator (ALPHA-205/206, BRAVO-105, CHAR-303/304), which use
statuses sprint_ready / backlog and have no descriptions. Backlog titles avoid duplicating any of them.

**Two versions of teams.json exist today.** `sprint-confidence-gap-analyzer` has 2 engineers per team;
`resource-capacity-analyzer` has larger rosters plus a `scrum_master`. Pick one as the source of truth.

## The Team custom field

Every card or ticket carries both `team_id` (stable key) and `team` (display name, the JIRA custom field called **Team**).
Rule: `team` must equal the name of the `team_id` in `teams.json`. Grouping always uses `team_id`; reports display `team`.

## Card id ranges (no overlap between projects)

| Range | Used by |
|---|---|
| ALPHA-201..204, BRAVO-102..104, CHAR-301 | sprint cards in the earlier projects (current sprint) |
| ALPHA-301..334, BRAVO-401..433, CHAR-501..533 | backlog tickets (this project) |

A ticket's `blocked_by` may point at any id in these ranges. Blockers in another team's backlog make a ticket Not ready until Done.

## Adding Team to an old project

```
python3 scripts/add_team_field.py path/to/data/cards.json            # dry run
python3 scripts/add_team_field.py path/to/data/cards.json --write    # save
```

It adds `team_id` and `team` from the id prefix and leaves every other field alone. Run it on cards.json in each old
project, then copy `data/mock_backlog.json` in as the backlog.
