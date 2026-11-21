# Start-list checks

Tools to make sure `skills/orienteering-start-list/scripts/build_start_list.py` breaks no rule and to measure how
far its grids are from the best possible one. They are not part of the skill; Python 3.10+.

| File | What it does |
|---|---|
| `validate.py` | Independent validator: re-implements the rules of `references/baseline-rules.md` (without importing the script) and checks a proposal against them. |
| `exact_window.py` | Exact shortest window with OR-Tools CP-SAT (`pip install ortools`), with the same hard rules as the script. |
| `liveresults.py` | Lists, downloads (cached), classifies and converts LiveResults.it races into the script's inputs. |
| `benchmark.py` | Runs everything on the real races of the chosen years and writes a Markdown report. |
| `results-2025-2026.md` | Latest benchmark on the 2025-2026 LiveResults races. |

## Validator

```bash
python3 tests/start-list/validate.py athletes.csv config.json proposal.csv report.txt
```

Checks, for every proposal:

- every athlete exactly once, in the right category and club; free-start categories without a time; times consistent with the first start;
- per category: positions 1..n, one constant interval, the expected vacants at the end (or the start);
- intervals: fixed ones (Elite/Junior in sprint, WRE Elite, `categories.<name>.interval`), at least the recommended minimum (masters, long races) unless the report warns that it was given up, at most the limit (7, 4 in sprint and for sensitive categories) unless the report says it was raised for first-control compatibility;
- load: never more than 8 per start and minute, never more than `max_load` with an automatic window, the ramp-up in the first minutes, nothing after the window;
- first-control collisions: none without `allow_first_control_collision`, and as many as the report says;
- same-club neighbours in random categories: no more than the fewest possible;
- sensitive categories starting after the first quarter are reported.

It also prints simple lower bounds for the window (busiest first control, load at `max_load`, longest category at its minimum interval). Exit code 1 when a rule is broken.

## Exact shortest window

```bash
pip install ortools
python3 tests/start-list/exact_window.py athletes.csv config.json --report report.txt --seconds 60
python3 tests/start-list/exact_window.py athletes.csv config.json --horizon 157   # e.g. where the script stopped
```

Same categories, vacants, starts and first controls as the script; each category takes a constant interval from its minimum to its minimum + 2 (fixed intervals stay fixed); no two starters of the same start on the same first control in the same minute; at most `max_load` per start and minute; the ramp-up. It minimises the window only: sensitive categories, clubs and widening are not modelled. "optimal" means proven; "feasible" gives the best grid found and a proven lower bound within the time limit; "infeasible" means no grid of that length exists (with `--horizon`, it confirms a stop of the script).

## Benchmark on LiveResults.it

```bash
pip install ortools
python3 tests/start-list/benchmark.py --years 2025 2026 --cache ~/.cache/startlist-bench --out tests/start-list/results-2025-2026.md
```

Races left out: relays and mass starts, knock-out finals (heats), MTBO, ski-O and trail-O, promotional/model/training races (maze, school...), races without published data or with fewer than 30 athletes on the grid. Promotional (`ludica`) and free-start classes are free-start categories. The race type comes from the race or event name, else from the intervals actually used (1 minute = sprint) and the course length (long from 9.5 km). Every race runs with the default rules: international championships too, which in reality follow the IOF rules. The cache keeps downloads and per-race results, so an interrupted run resumes (`--force` recomputes).
