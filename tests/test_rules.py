"""Rule checks per ticket type. Each test is worked by hand from the PRD (Section 6)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from backlog_readiness.config import Config
from backlog_readiness.rules import check, is_thin, tier_for

CFG = Config()


def ticket(ty, **kw):
    base = dict(key="X-1", type=ty, description="", acceptance_criteria="", story_points=None, parent="FEAT-01",
                severity=None, blocked_by=None, assignee=None, start_date=None)
    base.update(kw)
    return base


GOOD_STORY = "As a user, I want to save a card, so that checkout is faster."
GOOD_AC = "- Given I am signed in, when I save a card, then it appears in my wallet.\n- Given a bad number, when I save, then I see an error."


def tier(t):
    gaps, _adv, thin = check(t, CFG)
    return tier_for(gaps, thin), gaps


def test_story_complete_is_ready():
    assert tier(ticket("Story", description=GOOD_STORY, acceptance_criteria=GOOD_AC)) == ("Ready", [])


def test_story_missing_ac_is_almost_ready():
    t, gaps = tier(ticket("Story", description=GOOD_STORY))
    assert t == "Almost ready" and gaps == ["Acceptance criteria blank"]


def test_story_missing_so_that():
    t, gaps = tier(ticket("Story", description="As a returning user, I want to save a new payment card to my wallet.", acceptance_criteria=GOOD_AC))
    assert gaps == ["Story is missing the 'so that' value statement"]


def test_story_weak_ac_not_testable():
    _t, gaps = tier(ticket("Story", description=GOOD_STORY, acceptance_criteria="Works as expected"))
    assert gaps == ["Acceptance criteria not testable"]


def test_story_format_and_ac_missing_is_not_ready():
    t, gaps = tier(ticket("Story", description="Save a card for users and more."))
    assert t == "Not ready" and len(gaps) == 2


def test_bug_needs_steps_current_expected():
    full = "Steps to reproduce:\n1. Open the page.\nCurrent behavior: crash.\nExpected result: no crash."
    assert tier(ticket("Bug", description=full))[0] == "Ready"
    t, gaps = tier(ticket("Bug", description="Steps to reproduce:\n1. Open the page.\nCurrent behavior: crash."))
    assert gaps == ["No expected result"] and t == "Almost ready"


def test_bug_missing_severity_is_only_advisory():
    full = "Steps to reproduce:\n1. Open.\nCurrent behavior: crash.\nExpected result: ok."
    gaps, adv, _ = check(ticket("Bug", description=full), CFG)
    assert gaps == [] and "No severity / business impact" in adv


def test_tech_debt_needs_file():
    d = "Problem: the module is brittle.\nChange needed: split it up and add tests for the public interface."
    t, gaps = tier(ticket("Tech Debt", description=d))
    assert gaps == ["No code file or component named"]
    assert tier(ticket("Tech Debt", description=d + "\nFiles: payments/retry_service.py"))[0] == "Ready"


def test_research_needs_dod():
    d = "Question to research: compare SMS vendors on cost and deliverability for the PO."
    assert tier(ticket("Research", description=d))[1] == ["No Definition of Done"]
    assert tier(ticket("Research", description=d + "\nDefinition of Done: findings doc reviewed."))[0] == "Ready"


def test_spike_needs_assignee_and_start_date():
    d = "Question: SAML vs OIDC - which fits?\nTime-box: 3 days.\nOutput: short write-up."
    t, gaps = tier(ticket("Spike", description=d))
    assert t == "Not ready" and set(gaps) == {"No assignee", "No start date"}
    assert tier(ticket("Spike", description=d, assignee="Priya N.", start_date="2026-11-02"))[0] == "Ready"


def test_task_one_liner_is_not_ready():
    assert tier(ticket("Task", description="Update"))[0] == "Not ready"
    assert tier(ticket("Task", description="Update the runbook, confirm with the on-call team and note completion in the ticket."))[0] == "Ready"


def test_placeholders_and_blank_are_thin():
    for text in ["", "TBD", "see above", "Do it"]:
        assert is_thin(text, CFG)
    assert not is_thin("A longer description that clearly has more than ten words in a single line here.", CFG)


def test_blocked_ticket_is_not_ready():
    t, gaps = tier(ticket("Task", description="Update the runbook, confirm with the on-call team and note completion.", blocked_by="BRAVO-410"))
    assert t == "Not ready" and gaps == ["Blocked by BRAVO-410"]


def test_oversize_and_unpointed_are_advisory():
    d = "Problem: x is slow.\nChange needed: cache it.\nFiles: api/cache.py\nWhy it matters: cost."
    _g, adv, _ = check(ticket("Tech Debt", description=d, story_points=13), CFG)
    assert any("SPLIT? 13 pts" in a for a in adv)
    _g, adv, _ = check(ticket("Tech Debt", description=d), CFG)
    assert any(a.startswith("Unpointed") for a in adv)


def test_add_team_field_script(tmp_path):
    import json, subprocess
    f = tmp_path / "cards.json"
    f.write_text(json.dumps([{"card_id": "ALPHA-202"}, {"card_id": "CHAR-301"}, {"card_id": "ZZZ-1"}]))
    out = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..", "scripts", "add_team_field.py"), str(f), "--write"], capture_output=True, text=True)
    cards = json.loads(f.read_text())
    assert cards[0]["team"] == "Team Alpha" and cards[1]["team_id"] == "team_charlie" and "team" not in cards[2]
    assert "1 with no team found: ZZZ-1" in out.stdout
