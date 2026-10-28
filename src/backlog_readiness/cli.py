"""Command line entry point.

  python3 cli.py run data/mock_backlog.json [--as-of YYYY-MM-DD] [--snapshot-dir snapshots] [--list] [--json out.json]
  python3 cli.py trend --snapshot-dir snapshots
"""
import argparse
import json
import sys

from .loader import load
from .analyze import analyze
from .config import Config
from .history import compare, latest_before, save_snapshot, trend
from .report import render


def _config(args):
    d = Config()
    return Config(thin_words=args.thin_words or d.thin_words, oversize_points=args.oversize_points or d.oversize_points,
                  stale_days=args.stale_days or d.stale_days, untouched_days=args.untouched_days or d.untouched_days,
                  dup_similarity=d.dup_similarity, top_sprints=args.top_sprints or d.top_sprints,
                  unpointed_for_slicing=d.unpointed_for_slicing)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="backlog-readiness", description="Score backlog tickets for sprint readiness.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="analyze a backlog export")
    run.add_argument("input", help="backlog JSON (see data/mock_backlog.json for the shape)")
    run.add_argument("--as-of", help="evaluate as of this date (default: the file's meta.as_of)")
    run.add_argument("--snapshot-dir", help="save a dated snapshot here and compare with the previous one")
    run.add_argument("--list", action="store_true", help="list every ticket that is not Ready")
    run.add_argument("--json", help="also write the full result to this file")
    for flag, helptext in [("thin-words", "one-liner threshold, in words"), ("oversize-points", "split-candidate points"),
                           ("stale-days", "days before a ticket counts as 6+ months old"),
                           ("untouched-days", "days without an update"), ("top-sprints", "sprints that make up the top of the backlog")]:
        run.add_argument("--" + flag, type=int, help=helptext)

    tr = sub.add_parser("trend", help="print ready share across saved snapshots")
    tr.add_argument("--snapshot-dir", required=True)

    args = ap.parse_args(argv)
    if args.cmd == "trend":
        rows = trend(args.snapshot_dir)
        if not rows:
            print("No snapshots yet.")
            return 0
        print(f"{'as of':<12}{'program':>9}   per team")
        for r in rows:
            print(f"{r['as_of']:<12}{r['program_ready_pct']:>8}%   " + "  ".join(f"{k.replace('team_', '')} {v}%" for k, v in r["teams"].items()))
        return 0

    try:
        data = load(args.input)
        result = analyze(data, _config(args), as_of=args.as_of)
    except (OSError, KeyError, ValueError) as exc:
        print(f"Could not analyze {args.input}: {exc}", file=sys.stderr)
        return 1

    change = None
    if args.snapshot_dir:
        prev = latest_before(args.snapshot_dir, result["as_of"])
        change = compare(prev, result) if prev else None
        path = save_snapshot(result, args.snapshot_dir)
    print(render(result, change, args.list))
    if args.snapshot_dir:
        print(f"\nSnapshot saved to {path}" + ("" if change else " (first run: baseline, nothing to compare yet)"))
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(result, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
