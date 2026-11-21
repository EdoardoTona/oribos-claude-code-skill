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
        result["exact"] = solve(str(work / "athletes.csv"), str(work / "config.json"), horizon=result["stop_length"], seconds=seconds)
    return result


def gap_text(r: dict) -> str:
    exact = r.get("exact", {})
    if r.get("outcome") == "grid":
        if "best" not in exact:
            return "-"
        gap = r["window"] - exact["best"]
        return f"{gap}" if exact["status"] == "optimal" else f"≤{r['window'] - exact['lower_bound']}"
    return ""


def write_report(results: list[dict], out: Path, years: list[str], seconds: float) -> None:
    included = [r for r in results if "excluded" not in r]
    excluded = [r for r in results if "excluded" in r]
    grids = [r for r in included if r.get("outcome") == "grid"]
    optimal = [r for r in grids if r.get("exact", {}).get("status") == "optimal"]
    gaps = [r["window"] - r["exact"]["best"] for r in optimal]
    stops = [r for r in included if r.get("outcome", "").startswith("stop: collisions")]
    lines = [
        f"# Start-list benchmark: LiveResults.it races {', '.join(years)}",
        "",
        "Generated by `tests/start-list/benchmark.py`: each race's published entries (categories, clubs, courses, first "
        "controls, starts) run through `build_start_list.py` with the default rules (automatic window, compact pace, no "
        "rankings, `random_seed` 2027), checked by `validate.py` and compared with the exact shortest window from "
        f"`exact_window.py` (CP-SAT, {seconds:.0f} s per race). Minutes are window lengths (last minute of the grid).",
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
            f"median {sorted(gaps)[len(gaps) // 2]} min longer, at most {max(gaps)} min "
            f"({max((r['window'] - r['exact']['best']) / max(1, r['exact']['best']) for r in optimal):.0%})."
        )
    lines += ["", "## Races", "",
              "| Date | Event | Race | Type | Grid athletes | Starts | Script | Exact optimum | Gap | Real grid | Valid | Time (s) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(included, key=lambda r: (r["date"], r["id"])):
        exact = r.get("exact", {})
        if r.get("outcome") == "grid":
            script = f"{r['window']}"
            best = (f"{exact['best']}" if exact.get("status") == "optimal" else
                    f"{exact.get('lower_bound', '?')}-{exact.get('best', '?')}" if "best" in exact else exact.get("status", "-"))
        elif r.get("outcome", "").startswith("stop: collisions"):
            script = f"stop at {r.get('stop_length')} ({r.get('collisions_if_approved')} collisions if approved)"
            best = ("no collision-free grid" if exact.get("status") == "infeasible" else
                    f"collision-free {exact['best']}" if "best" in exact else exact.get("status", "-"))
        else:
            script, best = r.get("outcome", "-"), "-"
        real = f"{r.get('real_window', '-')} ({r.get('real_collisions', '-')} coll.)"
        valid = "" if r.get("outcome") != "grid" else ("yes" if r.get("valid") else "NO")
        lines.append(f"| {r['date']} | {r['event']} | {r['race']} | {r.get('race_type', '')} | {r.get('grid_athletes', '')} | "
                     f"{r.get('starts', '')} | {script} | {best} | {gap_text(r)} | {real} | {valid} | {r.get('seconds', '')} |")
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
