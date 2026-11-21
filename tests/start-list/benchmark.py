#!/usr/bin/env python3
"""Benchmark build_start_list.py on real races from LiveResults.it.

For every sensible race of the given years (individual foot-orienteering races with a start grid: no relays,
mass starts, knock-out finals, MTBO, promotional/model/training races, or grids under 30 athletes):
  1. convert the published entries (categories, clubs, courses, first controls, starts) to the script's inputs;
  2. run the script with the default rules (automatic window, compact pace, no rankings);
  3. check the proposal with the independent validator (validate.py);
  4. compute the exact shortest window with CP-SAT (exact_window.py, needs `pip install ortools`); when the script
     stops on first-control collisions, check whether a collision-free grid of that length exists after all.

    python3 benchmark.py --years 2025 2026 --cache ~/.cache/startlist-bench --out results-2025-2026.md

Results are cached per race in --cache, so an interrupted run resumes where it stopped (--force recomputes).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent.parent / "skills" / "orienteering-start-list" / "scripts" / "build_start_list.py"
sys.path.insert(0, str(HERE))
import liveresults  # noqa: E402
from exact_window import pace_floor  # noqa: E402
from validate import validate  # noqa: E402


def run_script(work: Path, timeout: int) -> dict:
    started = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--athletes", str(work / "athletes.csv"), "--config", str(work / "config.json"),
             "--out", str(work / "proposal.csv"), "--report", str(work / "report.txt")],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"outcome": "timeout", "seconds": timeout}
    result = {"seconds": round(time.time() - started, 1)}
    if proc.returncode == 0:
        report = (work / "report.txt").read_text(encoding="utf-8")
        result["outcome"] = "grid"
        result["window"] = int(re.search(r"Target window: (\d+)", report).group(1))
        result["warnings"] = len(re.findall(r"^WARNING", report, re.M))
    elif "ERROR: No grid without first-control collisions" in proc.stderr + proc.stdout:
        text = proc.stderr + proc.stdout
        result["outcome"] = "stop: collisions need approval"
        length = re.search(r"acceptable length \((\d+) minutes\)", text)
        result["stop_length"] = int(length.group(1)) if length else None
        result["collisions_if_approved"] = int(re.search(r"with about (\d+) first-control", text).group(1))
        relaxed = re.search(r"Already at the normal interval because of their size: (.+)\.", text)
        result["relaxed"] = relaxed.group(1).split(", ") if relaxed else []
    elif "ERROR:" in proc.stderr + proc.stdout:
        result["outcome"] = "stop: " + re.search(r"ERROR: ([^.]*)", proc.stderr + proc.stdout).group(1)[:80]
    else:
        result["outcome"] = "crash"
        result["error"] = (proc.stderr or proc.stdout)[-1500:]
    return result


def stage_script(args: tuple) -> dict:
    race, cache, timeout = args
    data = liveresults.load(race, cache)
    race_type, reason = liveresults.classify(race, data)
    result = dict(race)
    if race_type is None:
        result["excluded"] = reason
        return result
    work = cache / "work" / race["id"]
    result["race_type"] = race_type
    result.update(liveresults.convert(data, race_type, work))
    result["pace_floor"] = pace_floor(str(work / "athletes.csv"), str(work / "config.json"))
    result.update(run_script(work, timeout))
    if result["outcome"] == "grid":
        check = validate(str(work / "athletes.csv"), str(work / "config.json"), str(work / "proposal.csv"), str(work / "report.txt"))
        result["valid"] = not check["errors"]
        result["errors"] = check["errors"][:10]
        result["simple_lower_bound"] = check["lower_bound"]
    return result


def stage_exact(result: dict, cache: Path, seconds: float) -> dict:
    from exact_window import solve

    work = cache / "work" / result["id"]
    if result.get("outcome") == "grid":
        result["exact"] = solve(str(work / "athletes.csv"), str(work / "config.json"), str(work / "report.txt"), seconds=seconds)
    elif result.get("stop_length"):
        result["exact"] = solve(str(work / "athletes.csv"), str(work / "config.json"), horizon=result["stop_length"],
                                seconds=seconds, relaxed=set(result.get("relaxed", [])))
    return result


def lower_bound(r: dict) -> int:
    """Best proven lower bound: CP-SAT's, or the validator's simple ones (busiest first control, load, longest
    category), which CP-SAT does not always reach within its time limit."""
    return max(r.get("exact", {}).get("lower_bound", 0), r.get("simple_lower_bound", 0))


def proven(r: dict) -> bool:
    exact = r.get("exact", {})
    return r.get("outcome") == "grid" and "best" in exact and (exact["status"] == "optimal" or exact["best"] <= lower_bound(r))


def gap_text(r: dict) -> str:
    exact = r.get("exact", {})
    if r.get("outcome") == "grid":
        if "best" not in exact:
            return "-"
        gap = r["window"] - exact["best"]
        return f"{gap}" if proven(r) else f"{gap}-{r['window'] - lower_bound(r)}"
    return ""


def write_report(results: list[dict], out: Path, years: list[str], seconds: float) -> None:
    included = [r for r in results if "excluded" not in r]
    excluded = [r for r in results if "excluded" in r]
    grids = [r for r in included if r.get("outcome") == "grid"]
    optimal = [r for r in grids if proven(r)]
    gaps = [r["window"] - r["exact"]["best"] for r in optimal]
    stops = [r for r in included if r.get("outcome", "").startswith("stop: collisions")]
    lines = [
        f"# Start-list benchmark: LiveResults.it races {', '.join(years)}",
        "",
        "Generated by `tests/start-list/benchmark.py`: each race's published entries (categories, clubs, courses, first "
        "controls, starts) run through `build_start_list.py` with the default rules (automatic window, compact pace, no "
        "rankings, `random_seed` 2027), checked by `validate.py` and compared with the exact shortest window from "
        f"`exact_window.py` (CP-SAT, {seconds:.0f} s per race, up to 180 s for the largest). Minutes are window lengths "
        "(last minute of the grid). An optimum is proven by CP-SAT or when it equals a simple lower bound (busiest first "
        "control, load, longest category); otherwise the Exact column gives the proven range. The exact model may load "
        "every minute up to `max_load` (6), while the script's automatic window keeps the pace at 5.5 starters a minute "
        "on average (4.5 with 3 or more starts): Pace floor is the shortest window that pace allows, so a gap down to it "
        "is by design.",
        "",
        "## Summary",
        "",
        f"- Races found: {len(results)}; benchmarked: {len(included)}; left out: {len(excluded)} (list at the end).",
        f"- Proposals: {len(grids)}; valid for the independent validator: {sum(1 for r in grids if r.get('valid'))}; "
        f"crashes or timeouts: {sum(1 for r in included if r.get('outcome') in ('crash', 'timeout'))}.",
        f"- Stopped asking to approve first-control collisions: {len(stops)} (confirmed by the exact model: "
        f"{sum(1 for r in stops if r.get('exact', {}).get('status') == 'infeasible')}; a collision-free grid exists after all: "
        f"{sum(1 for r in stops if 'best' in r.get('exact', {}))}).",
    ]
    if gaps:
        lines.append(
            f"- Window vs proven optimum ({len(optimal)} races): optimal in {sum(1 for g in gaps if g == 0)}, "
            f"within 3 min in {sum(1 for g in gaps if g <= 3)}, "
            f"median {sorted(gaps)[len(gaps) // 2]} min longer, at most {max(gaps)} min "
            f"({max((r['window'] - r['exact']['best']) / max(1, r['exact']['best']) for r in optimal):.0%})."
        )
        beyond = [r["window"] - max(r["exact"]["best"], r.get("pace_floor", 0)) for r in optimal]
        lines.append(
            f"- Beyond what the pace requires (the larger of optimum and pace floor), same races: none in "
            f"{sum(1 for g in beyond if g <= 0)}, within 3 min in {sum(1 for g in beyond if g <= 3)}, at most {max(beyond)} min."
        )
    unproven = [r for r in grids if "best" in r.get("exact", {}) and not proven(r)]
    if unproven:
        found = sorted(r["window"] - r["exact"]["best"] for r in unproven)
        worst = max(unproven, key=lambda r: r["window"] - r["exact"]["best"])
        lines.append(
            f"- Optimum not proven within the time limit ({len(unproven)} races, mostly the largest): the exact model found "
            f"a grid shorter than the script's by a median of {found[len(found) // 2]} min, at most {found[-1]} min "
            f"({worst['event']} {worst['race']}: {worst['window']} vs {worst['exact']['best']}); the true gap is at "
            "least that, at most the upper end of the Gap column."
        )
    lines += ["", "## Races", "",
              "| Date | Event | Race | Type | Grid athletes | Starts | Script | Exact optimum | Gap | Pace floor | Real grid | Valid | Time (s) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(included, key=lambda r: (r["date"], r["id"])):
        exact = r.get("exact", {})
        if r.get("outcome") == "grid":
            script = f"{r['window']}"
            best = (f"{exact['best']}" if proven(r) else
                    f"{lower_bound(r)}-{exact['best']}" if "best" in exact else exact.get("status", "-"))
        elif r.get("outcome", "").startswith("stop: collisions"):
            script = f"stop at {r.get('stop_length')} ({r.get('collisions_if_approved')} collisions if approved)"
            best = ("no collision-free grid" if exact.get("status") == "infeasible" else
                    f"collision-free {exact['best']}" if "best" in exact else exact.get("status", "-"))
        else:
            script, best = r.get("outcome", "-"), "-"
        real = f"{r.get('real_window', '-')} ({r.get('real_collisions', '-')} coll.)"
        valid = "" if r.get("outcome") != "grid" else ("yes" if r.get("valid") else "NO")
        lines.append(f"| {r['date']} | {r['event']} | {r['race']} | {r.get('race_type', '')} | {r.get('grid_athletes', '')} | "
                     f"{r.get('starts', '')} | {script} | {best} | {gap_text(r)} | {r.get('pace_floor', '')} | {real} | {valid} | "
                     f"{r.get('seconds', '')} |")
    problems = [r for r in included if r.get("errors") or r.get("outcome") in ("crash", "timeout")]
    if problems:
        lines += ["", "## Problems", ""]
        for r in problems:
            lines.append(f"- {r['id']}: {r.get('outcome')}; " + "; ".join(r.get("errors", [])[:5]) + (r.get("error", "")[-300:]))
    lines += ["", "## Left out", "", "| Date | Event | Race | Reason |", "|---|---|---|---|"]
    for r in sorted(excluded, key=lambda r: (r["date"], r["id"])):
        lines.append(f"| {r['date']} | {r['event']} | {r['race']} | {r['excluded']} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", nargs="+", default=["2025", "2026"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=3, help="script runs in parallel")
    parser.add_argument("--timeout", type=int, default=900, help="seconds per script run")
    parser.add_argument("--exact-seconds", type=float, default=60, help="CP-SAT time limit per race (0 = skip)")
    parser.add_argument("--only", nargs="*", help="race ids to run (event__race)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    results_dir = args.cache / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    races = liveresults.list_races(args.years)
    if args.only:
        races = [r for r in races if r["id"] in set(args.only)]
    todo = [r for r in races if args.force or not (results_dir / f"{r['id']}.json").exists()]
    print(f"{len(races)} races, {len(todo)} to run", flush=True)
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for result in pool.map(stage_script, [(r, args.cache, args.timeout) for r in todo]):
            (results_dir / f"{result['id']}.json").write_text(json.dumps(result), encoding="utf-8")
            print(f"script {result['id']}: {result.get('excluded') or result.get('outcome')}", flush=True)
    if args.exact_seconds > 0:
        for race in races:
            path = results_dir / f"{race['id']}.json"
            result = json.loads(path.read_text(encoding="utf-8"))
            if "excluded" in result or ("exact" in result and not args.force):
                continue
            result = stage_exact(result, args.cache, args.exact_seconds)
            path.write_text(json.dumps(result), encoding="utf-8")
            print(f"exact {race['id']}: {result.get('exact')}", flush=True)
    results = [json.loads((results_dir / f"{r['id']}.json").read_text(encoding="utf-8")) for r in races]
    write_report(results, args.out, args.years, args.exact_seconds)
    print(f"written {args.out}")


if __name__ == "__main__":
    main()
