"""Generate a mock 100-ticket JIRA backlog for 3 teams (Alpha, Bravo, Charlie).

Deterministic (seeded). Content quality is deliberately mixed so the readiness
analyzer has real gaps to catch.

  python3 scripts/generate_mock_backlog.py data/mock_backlog.json
"""
import json
import os, random, sys
from datetime import date, timedelta

AS_OF = date(2026, 10, 28)
rnd = random.Random(42)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from backlog_readiness.paths import SHARED as SHARED_DIR  # noqa: E402

SHARED = {t["team_id"]: t for t in json.load(open(os.path.join(SHARED_DIR, "teams.json")))["teams"]}

# Features are limited to the four in the earlier projects' features.json (FEAT-01..04).
# Per-team backlog settings that live only in this project; names, velocity, people and sprint come from the
# shared teams.json (pm-portfolio-mock-data) so every portfolio project agrees.
_LOCAL = {
    "team_alpha": dict(prefix="ALPHA", start=301, persona="account holder", features=["FEAT-01", "FEAT-02"]),
    "team_bravo": dict(prefix="BRAVO", start=401, persona="app user", features=["FEAT-03", "FEAT-03"]),
    "team_charlie": dict(prefix="CHAR", start=501, persona="business analyst", features=["FEAT-04", "FEAT-04"]),
}
TEAMS = {
    tid: dict(name=SHARED[tid]["team_name"], velocity=SHARED[tid]["velocity"],
              product_owner=SHARED[tid]["product_owner"], engineers=SHARED[tid]["engineers"],
              active_sprint_id=SHARED[tid]["active_sprint_id"],
              people=SHARED[tid]["engineers"] * 2,  # four slots keeps the random stream identical to earlier runs
              **loc)
    for tid, loc in _LOCAL.items()
}

T = {
 "team_alpha": {
  "Story": ["Save multiple payment methods", "Update billing address", "Download monthly invoices as PDF",
            "Enroll in two-factor authentication", "Request account deletion", "Manage notification preferences panel",
            "Change email with verification", "Show session timeout warning", "Link Google account for login",
            "Remind users of saved card expiry", "Show payment retry status banner", "Choose dark mode in settings",
            "Choose language preference", "Export personal data"],
  "Bug": ["Card form accepts expired dates", "Profile photo upload fails above 5MB", "Billing address saves blank ZIP",
          "Duplicate invoice emails sent", "Logout does not clear session on mobile web",
          "Payment retry double-charges on timeout", "Settings page flickers on tab switch"],
  "Tech Debt": [("Refactor PaymentRetryService retry loop", "payments/retry_service.py"),
                ("Remove deprecated v1 settings API", "api/v1/settings_controller.py"),
                ("Replace homegrown date utils with library", "utils/date_helpers.js"),
                ("Split AccountSettingsForm component", "src/components/AccountSettingsForm.tsx"),
                ("Migrate session store to Redis client v4", "auth/session_store.py")],
  "Research": ["Evaluate SSO providers for enterprise tenants", "Assess PCI scope impact of tokenized card storage"],
  "Spike": ["Spike: SAML vs OIDC for SSO", "Spike: Idempotency keys for payment retries", "Spike: Offline-capable settings cache"],
  "Task": ["Update SSO onboarding runbook", "Rotate payment gateway sandbox credentials", "Archive legacy settings feature flags"]},
 "team_bravo": {
  "Story": ["Show SMS delivery status to senders", "Set quiet hours", "Receive notification digest email",
            "See push notification opt-in prompt", "Set per-channel delivery preferences", "View notification history",
            "Snooze notifications for 1 hour", "Edit templates as admin", "Alert admins on delivery failures",
            "Localize notification templates", "Add webhook notification channel", "Mark all notifications as read",
            "Rate-limit notification bursts"],
  "Bug": ["Notification worker restarts under load", "Repeated push alerts after app reconnect",
          "Email notifications arrive out of order", "Unread badge count wrong after dismiss",
          "Scheduled notifications off by one day across timezones", "SMS fails for numbers with extension",
          "Template placeholder renders raw braces"],
  "Tech Debt": [("Replace polling with event stream in dispatcher", "notifications/dispatcher.go"),
                ("Consolidate three template renderers", "notifications/render/renderer.go"),
                ("Remove unused queue consumer groups", "infra/queues/consumers.yaml"),
                ("Upgrade Kafka client to 3.x", "notifications/kafka_client.go"),
                ("Add structured logging to delivery workers", "workers/delivery_worker.go")],
  "Research": ["Compare SMS vendors for cost and deliverability", "Investigate notification fatigue metrics"],
  "Spike": ["Spike: WebSocket vs SSE for in-app notifications", "Spike: Batching strategy for digest emails",
            "Spike: Dead-letter queue replay tooling"],
  "Task": ["Document on-call runbook for notification outages", "Provision staging SMS sandbox",
           "Clean up stale notification templates"]},
 "team_charlie": {
  "Story": ["Add data freshness banner to dashboard", "Filter reports by date range", "Export report to Excel workbook",
            "Save report views", "Schedule report emails", "Drill down from summary tiles",
            "Compare two periods side by side", "Restrict report access by role", "Show dashboard loading skeleton states",
            "Annotate charts", "Favorite reports", "Share report via link", "Export report as Excel file"],
  "Bug": ["Dashboard totals mismatch pipeline output", "CSV export truncates at 10k rows", "Filter resets on page refresh",
          "Chart tooltip shows wrong currency", "Scheduled report sent twice", "Timeout on reports over 1 year range"],
  "Tech Debt": [("Replace legacy ETL cron jobs with orchestrator DAGs", "pipelines/legacy_etl.py"),
                ("Remove duplicated aggregation SQL", "sql/aggregations/daily_rollup.sql"),
                ("Add typed schema for pipeline events", "pipelines/events/schema.py"),
                ("Split ReportBuilder monolith", "src/reports/ReportBuilder.tsx"),
                ("Add cache layer for dashboard queries", "api/dashboard_queries.py"),
                ("Delete unused chart library wrappers", "src/charts/legacy/wrappers.ts")],
  "Research": ["Evaluate columnar store options for reporting", "Review data retention requirements for report history"],
  "Spike": ["Spike: Incremental refresh for large datasets", "Spike: Pre-aggregation tables vs live queries",
            "Spike: Embed BI tool in dashboard"],
  "Task": ["Update data dictionary for new pipeline tables", "Request access to Data Platform API sandbox",
           "Archive old dashboard screenshots"]},
}

BENEFITS = ["I can complete this without contacting support", "I save time on repetitive work",
            "I trust the data I am looking at", "I stay in control of my information",
            "the team can act on it faster", "I avoid mistakes that cost money"]


def lower_first(s):
    return s[0].lower() + s[1:]


def build_fields(ttype, topic, team, good, defect, i, file_path=None):
    f = dict(description="", acceptance_criteria="", assignee=None, start_date=None)
    low = lower_first(topic)
    persona = team["persona"]
    if ttype == "Story":
        f["description"] = f"As a {persona}, I want to {low}, so that {BENEFITS[i % len(BENEFITS)]}."
        f["acceptance_criteria"] = (
            f"- Given I am signed in, when I {low}, then the change is saved and a confirmation is shown.\n"
            f"- Given invalid input, when I submit, then an inline error explains how to fix it.\n"
            f"- Given I lack permission, when I try, then the action is blocked with a clear message.")
        if not good:
            if defect == "no_ac": f["acceptance_criteria"] = ""
            elif defect == "weak_ac": f["acceptance_criteria"] = rnd.choice(["Works as expected", "Should be easy to use", "TBD"])
            elif defect == "bad_format": f["description"] = f"{topic} for users."
            elif defect == "blank": f["description"] = ""
            elif defect == "both": f["acceptance_criteria"] = ""; f["description"] = f"{topic}."
    elif ttype == "Bug":
        f["description"] = (f"Steps to reproduce:\n1. Sign in as a standard user.\n2. Go to the affected screen.\n"
                            f"3. Perform the action related to: {low}.\n\n"
                            f"Current behavior: {topic}; the user sees an incorrect or failed result.\n"
                            f"Expected result: The action completes correctly with no error and consistent data.\n"
                            f"Environment: Production v4.{10 + i % 5}, Chrome 126 / iOS 17.")
        if not good:
            if defect == "one_liner": f["description"] = rnd.choice(["Fails sometimes", "Broken on prod, please look", "Doesn't work"])
            elif defect == "no_steps": f["description"] = f"Current behavior: {topic}.\nExpected result: Works correctly."
            elif defect == "no_expected": f["description"] = f"Steps to reproduce:\n1. Open the screen.\n2. Trigger the action.\nCurrent behavior: {topic}."
            elif defect == "blank": f["description"] = ""
    elif ttype == "Tech Debt":
        f["description"] = (f"Problem: {topic} has grown brittle and slows delivery of related features.\n"
                            f"Change needed: Rework the module, remove dead paths and add tests around the public interface.\n"
                            f"Files: {file_path}\nWhy it matters: Reduces incident risk and shortens review and onboarding time.")
        if not good:
            if defect == "no_file": f["description"] = f"Problem: {topic} is messy.\nChange needed: Clean it up and add tests so future changes are safer to make."
            elif defect == "one_liner": f["description"] = rnd.choice(["Clean up code", "Refactor this", "Needs cleanup"])
            elif defect == "blank": f["description"] = ""
    elif ttype == "Research":
        f["description"] = (f"Question to research: {topic}. Compare options, constraints and cost; summarize trade-offs for the PO.\n"
                            f"Definition of Done: A 1-2 page findings doc reviewed with the team and a recommendation recorded in the ticket.")
        if not good:
            if defect == "no_dod": f["description"] = f"Question to research: {topic}. Compare options, constraints and cost."
            elif defect == "one_liner": f["description"] = rnd.choice(["Look into this", "Research options"])
            elif defect == "blank": f["description"] = ""
    elif ttype == "Spike":
        f["description"] = (f"Question: {topic.replace('Spike: ', '')} - which approach fits our constraints?\n"
                            f"Time-box: {2 + i % 3} days.\nOutput: Short write-up and a throwaway prototype if useful.")
        f["assignee"] = rnd.choice(team["people"])
        f["start_date"] = (AS_OF + timedelta(days=rnd.randint(-10, 20))).isoformat()
        if not good:
            if defect == "no_assignee": f["assignee"] = None
            elif defect == "no_start": f["start_date"] = None
            elif defect == "no_timebox": f["description"] = f"Question: {topic.replace('Spike: ', '')} - which approach fits our constraints?\nOutput: Short write-up."
            elif defect == "one_liner": f["description"] = "Investigate"
            elif defect == "blank": f["description"] = ""
    else:
        f["description"] = f"{topic}. Update the owning doc or config, confirm with the affected team, and note completion in the ticket."
        if not good:
            if defect == "one_liner": f["description"] = rnd.choice(["Do it", "Update", "Same as before"])
            elif defect == "blank": f["description"] = ""
    return f


DEFECTS = {
    "Story": ["no_ac", "weak_ac", "bad_format", "blank", "both", "no_ac"],
    "Bug": ["one_liner", "no_steps", "no_expected", "blank", "no_expected"],
    "Tech Debt": ["no_file", "one_liner", "blank", "no_file"],
    "Research": ["no_dod", "one_liner", "blank"],
    "Spike": ["no_assignee", "no_start", "no_timebox", "one_liner", "no_assignee"],
    "Task": ["one_liner", "blank", "one_liner"],
}

PLANTED_BLOCKERS = {
    # open: another team's backlog ticket
    "ALPHA-304": "CHAR-506", "BRAVO-405": "ALPHA-305", "CHAR-503": "BRAVO-406", "CHAR-509": "ALPHA-311",
    # open: card in another team's active sprint
    "ALPHA-310": "BRAVO-102", "BRAVO-411": "CHAR-301", "CHAR-513": "ALPHA-204",
    # cleared: blocker already done
    "ALPHA-314": "CHAR-302", "BRAVO-412": "ALPHA-203", "CHAR-514": "BRAVO-101",
}


def generate():
    global rnd
    rnd = random.Random(42)
    tickets = []
    for tid, team in TEAMS.items():
        rows = []
        for ttype, topics in T[tid].items():
            for topic in topics:
                if isinstance(topic, tuple): topic, fp = topic
                else: fp = None
                rows.append((ttype, topic, fp))
        rnd.shuffle(rows)
        for rank, (ttype, topic, fp) in enumerate(rows, 1):
            p_good = 0.75 if rank <= 8 else 0.55 if rank <= 18 else 0.25
            good = rnd.random() < p_good
            defect = rnd.choice(DEFECTS[ttype]) if not good else None
            i = len(tickets)
            f = build_fields(ttype, topic, team, good, defect, i, fp)
            if rnd.random() < 0.30:
                created = date(2026, 4, 28) - timedelta(days=rnd.randint(5, 150))
            else:
                created = AS_OF - timedelta(days=rnd.randint(5, 175))
            updated = created + timedelta(days=rnd.randint(0, (AS_OF - created).days))
            pointable = ttype in ("Story", "Bug", "Tech Debt")
            points = rnd.choice([2, 3, 5, 5, 8, 8, 13]) if pointable and rnd.random() < 0.82 else None
            parent = rnd.choice(team["features"]) if rnd.random() > 0.12 else None
            severity = None
            if ttype == "Bug":
                severity = rnd.choice(["Critical", "Major", "Major", "Minor"]) if rnd.random() > 0.15 else None
            blocked_by = None
            if rnd.random() < 0.06 and ttype != "Task":
                other = rnd.choice([k for k in TEAMS if k != tid])
                blocked_by = f"{TEAMS[other]['prefix']}-{TEAMS[other]['start'] + rnd.randint(0, 20)}"
            if rnd.random() < 0.10 and blocked_by is None and ttype in ("Story", "Tech Debt") and f["description"]:
                f["description"] += "\nNote: depends on the Platform team delivering the shared API first."
            tickets.append(dict(
                key=f"{team['prefix']}-{team['start'] + rank - 1}", team_id=tid, team=team["name"],
                type=ttype, summary=topic, status="Backlog", rank=rank,
                priority=rnd.choice(["High", "Medium", "Medium", "Low"]),
                story_points=points, parent=parent, severity=severity, blocked_by=blocked_by,
                created=created.isoformat(), updated=updated.isoformat(), **f))

    # Planted dependencies, hand-picked so the mock data shows every case: blocked by another team's backlog ticket,
    # by a card in another team's active sprint, and by a card that is already done (blocker cleared).
    for key, blocker in PLANTED_BLOCKERS.items():
        next(t for t in tickets if t["key"] == key)["blocked_by"] = blocker
    sprint_cards = json.load(open(os.path.join(SHARED_DIR, "cards.json")))["cards"]
    external_status = {c["card_id"]: c["status"] for c in sprint_cards if c["status"] != "backlog"}

    meta = dict(as_of=AS_OF.isoformat(), external_status=external_status,
            teams={k: dict(name=v["name"], velocity=v["velocity"], product_owner=v["product_owner"], engineers=v["engineers"], active_sprint_id=v["active_sprint_id"]) for k, v in TEAMS.items()},
            note="Mock data. Teams, card prefixes, velocities and features follow the earlier portfolio projects.")
    return dict(meta=meta, tickets=tickets)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "mock_backlog.json"
    data = generate()
    with open(out, "w") as fh:
        json.dump(data, fh, indent=1)
    print(len(data["tickets"]), "tickets written to", out)
