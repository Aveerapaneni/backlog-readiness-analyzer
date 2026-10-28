"""Per-ticket-type readiness rules.

check(ticket, cfg) returns (gaps, advisories):
  gaps        -> required content that is missing; these decide the tier.
  advisories  -> things to review (sizing, parent link, severity...); they never change the tier.
"""
import re

from .config import Config, POINTED_TYPES

PLACEHOLDERS = {"tbd", "todo", "see above", "as discussed", "n/a", "na", "-", "same as before"}
CODE_FILE = re.compile(r"[\w/\-.]+\.(py|js|ts|tsx|go|java|yaml|yml|sql|rb|kt)\b")


def words(text):
    return len((text or "").split())


def is_blank(text):
    return not (text or "").strip()


def is_placeholder(text):
    return (text or "").strip().lower().rstrip(".") in PLACEHOLDERS


def is_thin(text, cfg: Config):
    """Blank, a placeholder, or a single line shorter than cfg.thin_words."""
    t = (text or "").strip()
    return is_blank(t) or is_placeholder(t) or ("\n" not in t and words(t) < cfg.thin_words)


def thin_reason(text):
    if is_blank(text):
        return "Description is blank"
    if is_placeholder(text):
        return "Description is a placeholder"
    return "Description is a one-liner"


def _acceptance_testable(ac):
    if is_blank(ac) or is_placeholder(ac) or words(ac) < 8:
        return False
    given_then = re.search(r"\bgiven\b.*\bthen\b", ac, re.I | re.S)
    lines = [ln for ln in ac.splitlines() if ln.strip()]
    return bool(given_then) or len(lines) >= 2


def check(t, cfg: Config):
    gaps, adv = [], []
    ty = t["type"]
    desc = t.get("description") or ""
    ac = t.get("acceptance_criteria") or ""
    dl = desc.lower()
    thin = is_thin(desc, cfg)

    if ty == "Story":
        if thin:
            gaps.append(thin_reason(desc))
        else:
            has_as = "as a" in dl or "as an" in dl
            if not (has_as and "i want" in dl):
                gaps.append("Not in user-story format (As a / I want / so that)")
            elif "so that" not in dl:
                gaps.append("Story is missing the 'so that' value statement")
        if is_blank(ac):
            gaps.append("Acceptance criteria blank")
        elif not _acceptance_testable(ac):
            gaps.append("Acceptance criteria not testable")

    elif ty == "Bug":
        if thin:
            gaps.append(thin_reason(desc))
        else:
            if not (re.search(r"steps to reproduce|repro", dl) or re.search(r"^\s*1\.", desc, re.M)):
                gaps.append("No steps to reproduce")
            if "current behavio" not in dl:
                gaps.append("No current behavior")
            if "expected" not in dl:
                gaps.append("No expected result")
        if not t.get("severity"):
            adv.append("No severity / business impact")

    elif ty == "Tech Debt":
        if thin:
            gaps.append(thin_reason(desc))
        else:
            if not CODE_FILE.search(desc):
                gaps.append("No code file or component named")
            if not ("problem" in dl or "change" in dl):
                gaps.append("Problem / needed change not described")
            if "why it matters" not in dl and "risk" not in dl:
                adv.append("No 'why it matters' (risk or cost of leaving it)")

    elif ty == "Research":
        if thin:
            gaps.append(thin_reason(desc))
        elif "definition of done" not in dl and "dod" not in dl:
            gaps.append("No Definition of Done")

    elif ty == "Spike":
        if thin:
            gaps.append(thin_reason(desc))
        if not t.get("assignee"):
            gaps.append("No assignee")
        if not t.get("start_date"):
            gaps.append("No start date")
        if not thin and "time-box" not in dl and "timebox" not in dl:
            adv.append("No time-box")

    else:  # Task
        if thin:
            gaps.append(thin_reason(desc))

    # Dependencies
    if t.get("blocked_by"):
        gaps.append(f"Blocked by {t['blocked_by']}")  # cleared in analyze() once the blocker is Done
    elif re.search(r"depends on|waiting on|blocked by", dl):
        adv.append("Mentions a dependency but no blocking link")

    # Sizing and structure (advisory only: unpointed cards may be awaiting refinement)
    pts = t.get("story_points")
    if ty in POINTED_TYPES:
        if pts is None:
            adv.append("Unpointed (fine if awaiting refinement)")
        elif pts >= cfg.oversize_points:
            adv.append(f"SPLIT? {pts} pts - consider splitting this card")
    if not t.get("parent"):
        adv.append("No epic / parent link")

    return gaps, adv, thin


def is_blocker_gap(gap):
    return gap.startswith("Blocked by ")


def tier_for(gaps, thin):
    """Ready: no gaps. Almost ready: exactly one. Not ready: two or more, a thin description,
    or an open blocker (a blocked ticket stays Not ready until its blocker is unblocked)."""
    if thin or len(gaps) >= 2 or any(is_blocker_gap(g) for g in gaps):
        return "Not ready"
    return "Almost ready" if len(gaps) == 1 else "Ready"
