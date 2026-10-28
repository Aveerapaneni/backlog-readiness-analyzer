"""Roll-ups, duplicates, snapshots and run-to-run comparison, checked against the bundled mock data."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from backlog_readiness.analyze import analyze, find_duplicates
from backlog_readiness.config import Config, TYPES
from backlog_readiness.paths import SHARED
from backlog_readiness.history import compare, latest_before, list_snapshots, load_snapshot, save_snapshot, trend

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")


def load(name):
    with open(os.path.join(DATA, name)) as fh:
        return json.load(fh)


def test_baseline_totals_match_the_documented_run():
    r = analyze(load("mock_backlog.json"))
    p = r["program"]
    assert (p["total"], p["Ready"], p["Almost ready"], p["Not ready"]) == (100, 37, 20, 43)
    assert p["ready_pct"] == 37.0 and p["stale_6m"] == 35 and p["stale_6m_not_ready"] == 22
    assert [t["Ready"] for t in r["teams"].values()] == [12, 13, 12]


def test_team_totals_add_up_to_program():
    r = analyze(load("mock_backlog.json"))
    for k in ("total", "Ready", "Almost ready", "Not ready", "stale_6m"):
        assert sum(t[k] for t in r["teams"].values()) == r["program"][k]


def test_every_ticket_gets_exactly_one_tier_and_ready_has_no_gaps():
    for t in analyze(load("mock_backlog.json"))["tickets"]:
        assert t["tier"] in ("Ready", "Almost ready", "Not ready")
        if t["tier"] == "Ready":
            assert t["gaps"] == []


def test_duplicate_detection_flags_the_planted_pair_only():
    r = analyze(load("mock_backlog.json"))
    assert r["program"]["duplicates"] == [("CHAR-511", "CHAR-516")]


def test_similar_but_different_stories_are_not_duplicates():
    tickets = [{"key": "A-1", "summary": "Add SMS notification channel"}, {"key": "A-2", "summary": "Add webhook notification channel"}]
    assert find_duplicates(tickets, 0.7) == {}


def test_stale_threshold_is_configurable():
    data = load("mock_backlog.json")
    assert analyze(data, Config(stale_days=365))["program"]["stale_6m"] < 35


def test_runway_uses_only_pointed_ready_work():
    r = analyze(load("mock_backlog.json"))["teams"]["team_alpha"]
    assert r["runway"]["sprints"] == round(r["runway"]["ready_points"] / r["velocity"], 1)


def test_compare_week_over_week():
    a, b = analyze(load("mock_backlog.json")), analyze(load("mock_backlog_week1.json"))
    c = compare(a, b)
    assert c["program_ready_pct_change"] > 0
    assert c["moved_down"] == [] and len(c["added"]) == 6 and c["removed"] == []
    assert all(old != "Ready" and new != old for _k, old, new in c["moved_up"])
    assert set(c["newly_ready"]) <= {k for k, _o, _n in c["moved_up"]}


def test_snapshots_round_trip_and_trend(tmp_path):
    a, b = analyze(load("mock_backlog.json")), analyze(load("mock_backlog_week1.json"))
    save_snapshot(a, str(tmp_path))
    assert latest_before(str(tmp_path), b["as_of"])["as_of"] == a["as_of"]
    assert latest_before(str(tmp_path), a["as_of"]) is None
    save_snapshot(b, str(tmp_path))
    assert [r["as_of"] for r in trend(str(tmp_path))] == [a["as_of"], b["as_of"]]


def test_cli_end_to_end(tmp_path):
    cmd = [sys.executable, os.path.join(ROOT, "cli.py"), "run", os.path.join(DATA, "mock_backlog.json"), "--snapshot-dir", str(tmp_path), "--list"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "Program: 37 Ready (37.0%)" in out.stdout and "first run" in out.stdout


def test_cli_reports_bad_input_cleanly(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    out = subprocess.run([sys.executable, os.path.join(ROOT, "cli.py"), "run", str(bad)], capture_output=True, text=True)
    assert out.returncode == 1 and "Could not analyze" in out.stderr and "Traceback" not in out.stderr


def test_empty_team_and_zero_velocity_do_not_crash():
    data = load("mock_backlog.json")
    data["meta"]["teams"]["team_bravo"]["velocity"] = 0
    data["tickets"] = [t for t in data["tickets"] if t["team_id"] != "team_charlie"]
    r = analyze(data)
    assert r["teams"]["team_charlie"]["total"] == 0 and r["teams"]["team_charlie"]["ready_pct"] is None
    assert r["teams"]["team_bravo"]["runway"]["sprints"] is None
    assert compare(r, r)["teams"]["team_charlie"]["ready_pct_change"] is None


def test_unknown_ticket_type_is_treated_like_a_task():
    data = load("mock_backlog.json")
    data["tickets"][0]["type"] = "Epic Idea"
    data["tickets"][0]["description"] = "TBD"
    assert analyze(data)["tickets"][0]["tier"] == "Not ready"


def test_every_ticket_has_a_team_field_matching_its_team_id():
    data = load("mock_backlog.json")
    names = {k: v["name"] for k, v in data["meta"]["teams"].items()}
    assert all(t["team"] == names[t["team_id"]] for t in data["tickets"])


def test_blocked_ticket_is_not_ready_until_blocker_is_done():
    desc = "Update the runbook, confirm with the on-call team and note completion in the ticket."
    base = dict(type="Task", status="Backlog", rank=1, story_points=None, parent="FEAT-01", severity=None,
                created="2026-10-01", updated="2026-10-01", acceptance_criteria="", assignee=None, start_date=None,
                summary="x", description=desc)
    a = dict(base, key="A-1", team_id="t1", team="T1", blocked_by="B-1")
    b = dict(base, key="B-1", team_id="t2", team="T2", blocked_by=None, summary="y y y", description=desc + " more")
    meta = {"as_of": "2026-10-28", "teams": {"t1": {"name": "T1", "velocity": 10}, "t2": {"name": "T2", "velocity": 10}}}
    r = {t["key"]: t for t in analyze({"meta": meta, "tickets": [a, b]})["tickets"]}
    assert r["A-1"]["tier"] == "Not ready" and r["A-1"]["blocked"] and r["B-1"]["tier"] == "Ready"
    b["status"] = "Done"
    r = {t["key"]: t for t in analyze({"meta": meta, "tickets": [a, b]})["tickets"]}
    assert r["A-1"]["tier"] == "Ready" and not r["A-1"]["blocked"]


def test_runway_counts_only_ready_and_next_sprint_candidates_are_almost_ready():
    r = analyze(load("mock_backlog.json"))
    for team in r["teams"].values():
        assert team["next_sprint_candidates"]["count"] <= team["Almost ready"]
    rows = [t for t in r["tickets"] if t["tier"] != "Ready"]
    assert all(t["tier"] != "Ready" for t in rows)


def test_split_warning_is_reported():
    r = analyze(load("mock_backlog.json"))
    assert r["split_at"] == 8 and r["program"]["split_candidates"] > 0


needs_shared = pytest.mark.skipif(not os.path.exists(os.path.join(SHARED, "cards.json")), reason="pm-portfolio-mock-data not found next to this project")


@needs_shared
def test_shared_cards_file_gives_the_same_result_as_the_backlog_file():
    a, b = analyze(load("mock_backlog.json")), analyze(__import__("backlog_readiness.loader", fromlist=["load"]).load(os.path.join(SHARED, "cards.json")))
    assert a["program"] == b["program"] and [t["tier"] for t in a["tickets"]] == [t["tier"] for t in b["tickets"]]


@needs_shared
def test_shared_files_are_consistent():
    def shared(name):
        with open(os.path.join(SHARED, name)) as fh:
            return json.load(fh)

    cards = shared("cards.json")["cards"]
    teams = {t["team_id"]: t["team_name"] for t in shared("teams.json")["teams"]}
    feats = {f["feature_id"] for f in shared("features.json")["features"]}
    assert feats == {"FEAT-01", "FEAT-02", "FEAT-03", "FEAT-04"}
    ids = [c["card_id"] for c in cards]
    assert len(ids) == len(set(ids)) == 110
    assert all(c["team"] == teams[c["team_id"]] and c["feature_id"] in feats | {None} for c in cards)
    assert all(c.get("blocked_by") in ids or not c.get("blocked_by") for c in cards)


def test_by_type_breakdown_sums_to_team_and_program_totals():
    r = analyze(load("mock_backlog.json"))
    for team in r["teams"].values():
        assert sum(v["total"] for v in team["by_type"].values()) == team["total"]
        for s in team["by_type"].values():
            assert s["Ready"] + s["Almost ready"] + s["Not ready"] == s["total"]
    assert set(r["program"]["by_type"]) == set(TYPES)
    assert sum(v["total"] for v in r["program"]["by_type"].values()) == r["program"]["total"]


def test_untouched_flag_set_at_90_days_since_update():
    desc = "Update the runbook, confirm with the on-call team and note completion in the ticket."
    base = dict(type="Task", status="Backlog", rank=1, story_points=None, parent="FEAT-01", severity=None,
                created="2026-01-01", acceptance_criteria="", assignee=None, start_date=None,
                team_id="t1", team="T1", blocked_by=None)
    fresh = dict(base, key="A-1", updated="2026-07-31", summary="x", description=desc)  # 89 days: not untouched
    stale = dict(base, key="A-2", updated="2026-07-30", summary="y y y", description=desc + " more")  # 90 days: untouched
    meta = {"as_of": "2026-10-28", "teams": {"t1": {"name": "T1", "velocity": 10}}}
    r = {t["key"]: t for t in analyze({"meta": meta, "tickets": [fresh, stale]})["tickets"]}
    assert r["A-1"]["untouched"] is False and not any("Untouched" in a for a in r["A-1"]["advisories"])
    assert r["A-2"]["untouched"] is True and "Untouched 90 days" in r["A-2"]["advisories"]
    assert r["A-2"]["tier"] == "Ready"  # advisory only, never changes the tier


def test_rerunning_same_as_of_overwrites_snapshot(tmp_path):
    a, b = analyze(load("mock_backlog.json")), analyze(load("mock_backlog_week1.json"))
    b["as_of"] = a["as_of"]  # simulate re-running the same day with refined data
    save_snapshot(a, str(tmp_path))
    save_snapshot(b, str(tmp_path))
    assert list_snapshots(str(tmp_path)) == [a["as_of"]]
    assert load_snapshot(str(tmp_path), a["as_of"])["program"]["Ready"] == b["program"]["Ready"]


def test_mock_data_covers_every_blocker_case():
    r = analyze(load("mock_backlog.json"))
    blocked = [t for t in r["tickets"] if t.get("blocker")]
    open_ = [t for t in blocked if t["blocker"]["open"]]
    cleared = [t for t in blocked if not t["blocker"]["open"]]
    assert (len(open_), len(cleared)) == (13, 3) and r["program"]["blocked"] == 13
    assert {t["blocker"]["status"] for t in blocked} == {"Backlog", "In progress", "Done"}
    assert all(t["tier"] == "Not ready" for t in open_)
    assert all(t["team"] != t["blocker"]["team"] for t in blocked)  # every planted blocker crosses teams
    assert all("Was blocked by" in " ".join(t["advisories"]) for t in cleared)
