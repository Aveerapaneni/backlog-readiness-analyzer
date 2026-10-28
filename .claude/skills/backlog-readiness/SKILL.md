---
name: backlog-readiness
description: Run the weekly backlog readiness analysis for the three teams and report ready %, top-of-backlog, runway, blockers, split warnings, tickets to fix and what changed since last run. Use when the user asks to run, refresh or review backlog readiness.
---

Follow the "How to run it" steps in CLAUDE.md in this folder. Run the analysis with today's date as `--as-of`,
save the snapshot, then give the user a short summary: one line per team, the biggest movers since last run, the
blocked tickets, and the five most important tickets to fix. Offer to export the tickets to fix as a list per team.
