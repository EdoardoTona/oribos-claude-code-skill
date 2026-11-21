#!/usr/bin/env python3
"""Shortest possible start window, computed exactly with OR-Tools CP-SAT (pip install ortools), to measure how
far build_start_list.py is from the optimum.

The model has the same hard rules as the script, built from the athletes and the config (not from the proposal):
the same grid categories and vacants, each category on its start and first control, a constant interval
between its minimum and minimum + 2 (fixed intervals stay fixed), no two starters of the same start on the same
first control in the same minute, at most max_load starters per start and minute, the ramp-up. Secondary goals
(sensitive categories, clubs, widening) are not modelled: only the length is compared.

    python3 exact_window.py athletes.csv config.json [--report report.txt] [--horizon N] [--seconds 60]

With --report the categories that gave up their recommended minimum are read from it and the script's window
is the upper limit; without it, --horizon is the upper limit (e.g. the length at which the script stopped) and
--relaxed lists the categories at the normal interval (the script prints them when it stops; default: 50+
athletes). Prints one JSON line.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import Rules, relaxed_categories  # noqa: E402


def grid_categories(athletes_path: str, rules: Rules) -> dict[str, dict]:
    config = rules.config
    free = {c.strip() for c in config.get("free_categories", [])} | {c.strip() for c, v in rules.cats.items() if v.get("free_start")}
    courses = config.get("courses", {})
    cats: dict[str, dict] = {}
    for row in csv.DictReader(open(athletes_path, encoding="utf-8-sig")):
        c = row["category"].strip()
        if c in free:
            continue
        cfg = rules.cats.get(c, {})
        course = row.get("course") or cfg.get("course", "")
        fc = (row.get("first_control") or "").strip() or str(courses.get(course, {}).get("first_control", ""))
        lane = str(cfg.get("start", "")).strip() or (row.get("start") or "").strip() or "1"
        entry = cats.setdefault(c, {"athletes": 0, "lane": lane, "first_control": fc})
        entry["athletes"] += 1
    for c, entry in cats.items():
        entry["slots"] = entry["athletes"] + rules.vacants(c, entry["athletes"])
    return cats


def solve(athletes_path: str, config_path: str, report_path: str | None = None, horizon: int | None = None,
          seconds: float = 60, workers: int = 4, relaxed: set[str] | None = None) -> dict:
    from ortools.sat.python import cp_model

    config = json.load(open(config_path, encoding="utf-8"))
    rules = Rules(config)
    cats = grid_categories(athletes_path, rules)
    large = int(config.get("large_category", 50))
    if report_path:
        report = open(report_path, encoding="utf-8").read()
        relaxed = relaxed_categories(report)
        script_window = int(re.search(r"Target window: (\d+)", report).group(1))
        horizon = horizon or script_window
    else:
        relaxed = relaxed if relaxed is not None else {c for c, e in cats.items() if e["athletes"] >= large}
        script_window = None
    if horizon is None:
        raise SystemExit("--report or --horizon is needed")
    max_load = min(int(config.get("max_load", 6)), 8)
    ramp = list(config.get("ramp_up", [1, 2, 4]))

    model = cp_model.CpModel()
    W = model.NewIntVar(0, horizon, "W")
    by_leg, by_lane = defaultdict(list), defaultdict(list)
    for c, e in cats.items():
        low = rules.minimum(c, c in relaxed)
        options = [low] if rules.fixed(c) is not None else list(range(low, max(low, min(rules.maximum(c), low + 2)) + 1))
        offset = model.NewIntVar(0, horizon, f"o[{c}]")
        picks = []
        for d in options:
            pick = model.NewBoolVar(f"d[{c}]={d}")
            picks.append(pick)
            model.Add(offset + (e["slots"] - 1) * d <= W).OnlyEnforceIf(pick)
            for k in range(e["slots"]):
                slot = model.NewOptionalFixedSizeIntervalVar(offset + k * d, 1, pick, f"s[{c}][{d}][{k}]")
                if e["first_control"]:
                    by_leg[(e["lane"], e["first_control"])].append(slot)
                by_lane[e["lane"]].append(slot)
        model.AddExactlyOne(picks)
    for slots in by_leg.values():
        model.AddNoOverlap(slots)
    for lane, slots in by_lane.items():
        demands = [1] * len(slots)
        for minute, limit in enumerate(ramp):  # capacity not available while the start ramps up
            if limit < max_load:
                slots = slots + [model.NewFixedSizeIntervalVar(minute, 1, f"ramp[{lane}][{minute}]")]
                demands = demands + [max_load - limit]
        model.AddCumulative(slots, demands, max_load)
    model.Minimize(W)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_workers = workers
    started = time.time()
    status = solver.Solve(model)
    result = {
        "script_window": script_window, "horizon": horizon, "slots": sum(e["slots"] for e in cats.values()),
        "seconds": round(time.time() - started, 1),
        "status": {cp_model.OPTIMAL: "optimal", cp_model.FEASIBLE: "feasible", cp_model.INFEASIBLE: "infeasible"}.get(
            status, solver.StatusName(status).lower()),
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result["best"] = int(solver.Value(W))
        result["lower_bound"] = int(solver.BestObjectiveBound())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("athletes")
    parser.add_argument("config")
    parser.add_argument("--report")
    parser.add_argument("--horizon", type=int)
    parser.add_argument("--relaxed", nargs="*", help="categories at the normal interval (default without --report: 50+ athletes)")
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    relaxed = set(args.relaxed) if args.relaxed is not None else None
    print(json.dumps(solve(args.athletes, args.config, args.report, args.horizon, args.seconds, args.workers, relaxed)))


if __name__ == "__main__":
    main()
