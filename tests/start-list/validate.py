#!/usr/bin/env python3
"""Independent checker for proposals of skills/orienteering-start-list/scripts/build_start_list.py.

It does not import the script: the rules are re-implemented from references/baseline-rules.md, so a bug in the
script is not repeated here. It covers the default rules (no per-category overrides except `vacants`,
`interval`, `min_interval`, `sensitive`, `elite`, `junior`, `master` and ranked categories).

    python3 validate.py athletes.csv config.json proposal.csv report.txt

Exit code 1 when a rule is broken. As a module: validate(...) returns a dict with errors, notes and lower bounds.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict

AGE = re.compile(r"^\s*[MWDHF]\s*-?\s*(\d{1,2})(?!\d)", re.I)
MASTER = re.compile(r"^\s*[MWDHF]\s*-?\s*(\d{2})\b", re.I)
ELITE = re.compile(r"[eé]lite|^\s*[MWDHF]\s*-?\s*(?:21\s*-?\s*)?E\b", re.I)


class Rules:
    """Category classification and interval limits, as documented in baseline-rules.md."""

    def __init__(self, config: dict):
        self.config = config
        self.kind = str(config.get("race_type", "middle")).lower()
        self.cats = config.get("categories", {})

    def flag(self, category: str, key: str, default: bool) -> bool:
        return bool(self.cats.get(category, {}).get(key, default))

    def age(self, category: str) -> int | None:
        match = AGE.match(category)
        return int(match.group(1)) if match else None

    def elite(self, c: str) -> bool:
        return self.flag(c, "elite", bool(ELITE.search(c)))

    def junior(self, c: str) -> bool:
        a = self.age(c)
        return self.flag(c, "junior", a is not None and a <= int(self.config.get("junior_max_age", 20)) and not self.elite(c))

    def master(self, c: str) -> bool:
        match = MASTER.match(c)
        default = bool(match) and int(match.group(1)) >= int(self.config.get("master_min_age", 35))
        return self.flag(c, "master", default)

    def sensitive(self, c: str) -> bool:
        a = self.age(c)
        default = (
            bool(self.config.get("sensitive_early", True)) and a is not None and not self.elite(c)
            and (a <= int(self.config.get("sensitive_young_max_age", 14)) or a >= int(self.config.get("sensitive_old_min_age", 70)))
        )
        return self.flag(c, "sensitive", default)

    def normal(self) -> int:
        return int(self.config.get("interval_minutes", 1 if self.kind == "sprint" else 2))

    def fixed(self, c: str) -> int | None:
        cfg = self.cats.get(c, {})
        if "interval" in cfg:
            return int(cfg["interval"])
        if "max_interval" in cfg:
            return None
        if self.config.get("wre") and self.elite(c):
            return {"sprint": 1, "long": int(self.config.get("wre_long_interval", 3))}.get(self.kind, 2)
        if self.kind == "sprint" and (self.elite(c) or self.junior(c)):
            return 1
        return None

    def recommended(self, c: str) -> int:
        values = [0]
        if self.master(c):
            values.append(int(self.config.get("master_min_interval_sprint", 2)) if self.kind == "sprint"
                          else int(self.config.get("master_min_interval", 3)))
        if self.kind == "long":
            values.append(int(self.config.get("long_min_interval", 3)))
        return max(values)

    def minimum(self, c: str, relaxed: bool) -> int:
        """Smallest interval allowed: fixed value, categories.<name>.min_interval, recommended minimum
        (or the normal interval when the report says it was given up)."""
        fixed = self.fixed(c)
        if fixed is not None:
            return fixed
        cfg = self.cats.get(c, {})
        if "min_interval" in cfg:
            return max(self.normal(), int(cfg["min_interval"]))
        return self.normal() if relaxed else max(self.normal(), self.recommended(c))

    def maximum(self, c: str) -> int:
        fixed = self.fixed(c)
        if fixed is not None:
            return fixed
        cap = 4 if self.kind == "sprint" else 7
        if self.sensitive(c):
            cap = min(cap, int(self.config.get("sensitive_max_interval", 4)))
        return cap

    def vacants(self, c: str, athletes: int) -> int:
        cfg = self.cats.get(c, {})
        if "vacants" in cfg:
            return int(cfg["vacants"] or 0)
        count = int(self.config.get("default_vacants", 2) or 0)
        if athletes < int(self.config.get("small_category_size", 10)):
            count = min(count, int(self.config.get("small_category_vacants", 1)))
        return count


def relaxed_categories(report: str) -> set[str]:
    """Categories the report says were given the normal interval instead of the recommended minimum."""
    relaxed = set(re.findall(r"WARNING: (.+?) has \d+ athletes", report))
    for line in re.findall(r"normal interval instead of the recommended minimum: (.+?)\. To keep", report):
        relaxed |= {part.rsplit(" ", 2)[0] for part in line.split(", ")}
    return relaxed


def validate(athletes_path: str, config_path: str, out_path: str, report_path: str) -> dict:
    config = json.load(open(config_path, encoding="utf-8"))
    report = open(report_path, encoding="utf-8").read()
    athletes = list(csv.DictReader(open(athletes_path, encoding="utf-8-sig")))
    rows = list(csv.DictReader(open(out_path, encoding="utf-8")))
    rules = Rules(config)
    errors: list[str] = []
    notes: list[str] = []
    free_cats = {c.strip() for c in config.get("free_categories", [])} | {c.strip() for c, v in rules.cats.items() if v.get("free_start")}

    # Every athlete exactly once, same category and club.
    out_ids = Counter(r["athlete_id"] for r in rows if r["row_type"] != "vacant")
    by_id = {a["id"]: a for a in athletes}
    for a in athletes:
        if out_ids[a["id"]] != 1:
            errors.append(f"athlete {a['id']} appears {out_ids[a['id']]} times")
    for r in rows:
        a = by_id.get(r["athlete_id"])
        if r["row_type"] != "vacant" and a is None:
            errors.append(f"unknown athlete {r['athlete_id']}")
        elif a and (a["category"].strip() != r["category"] or a["club"].strip() != r["club"]):
            errors.append(f"athlete {r['athlete_id']} changed category or club")

    # Free rows without a time, grid rows with a consistent time.
    parts = (list(map(int, str(config.get("first_start", "10:00:00")).split(":"))) + [0])[:3]
    for r in rows:
        if r["category"] in free_cats:
            if r["row_type"] != "free" or r["minute"]:
                errors.append(f"free-start category with a time: {r['category']} {r['athlete_id']}")
            continue
        if not r["minute"]:
            errors.append(f"grid row without a time: {r['category']} {r['athlete_id']}")
            continue
        total = parts[0] * 60 + parts[1] + int(r["minute"])
        if r["absolute_time"] != f"{total // 60:02}:{total % 60:02}:{parts[2]:02}":
            errors.append(f"absolute time does not match the minute: {r['athlete_id']}")

    grid = [r for r in rows if r["row_type"] in ("assigned", "vacant") and r["minute"]]
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in grid:
        by_cat[r["category"]].append(r)
    relaxed = relaxed_categories(report)
    aligned = {c for c in by_cat if re.search(rf"^- {re.escape(c)}: .*interval raised from", report, re.M)}
    window = int(re.search(r"Target window: (\d+)", report).group(1))

    # Per category: positions, constant interval, vacants, interval limits.
    for c, rs in by_cat.items():
        rs.sort(key=lambda r: int(r["category_position"]))
        if [int(r["category_position"]) for r in rs] != list(range(1, len(rs) + 1)):
            errors.append(f"{c}: category positions are not 1..n")
        minutes = [int(r["minute"]) for r in rs]
        gaps = {b - a for a, b in zip(minutes, minutes[1:])}
        if len(gaps) > 1 or (gaps and min(gaps) <= 0):
            errors.append(f"{c}: interval not constant {sorted(gaps)}")
            continue
        n = sum(1 for r in rs if r["row_type"] == "assigned")
        vacant_positions = [i for i, r in enumerate(rs) if r["row_type"] == "vacant"]
        if len(vacant_positions) != rules.vacants(c, n):
            errors.append(f"{c}: {len(vacant_positions)} vacants, expected {rules.vacants(c, n)}")
        position = str(rules.cats.get(c, {}).get("vacant_position", config.get("vacant_position", "end"))).lower()
        expected = list(range(len(vacant_positions))) if position == "start" else \
            list(range(len(rs) - len(vacant_positions), len(rs)))
        if vacant_positions and vacant_positions != expected:
            errors.append(f"{c}: vacants not at the {position}")
        if not gaps:
            continue
        d = gaps.pop()
        fixed = rules.fixed(c)
        if fixed is not None:
            if d != fixed:
                errors.append(f"{c}: interval {d}, expected the fixed {fixed}")
            continue
        low = rules.minimum(c, c in relaxed)
        if d < low:
            errors.append(f"{c}: interval {d} below the minimum {low} without a warning")
        high = max(rules.maximum(c), low)
        if d > high:
            (notes if c in aligned else errors).append(
                f"{c}: interval {d} above the limit {high}" + (" (raised for first-control compatibility)" if c in aligned else "")
            )

    # Load per start and minute, ramp-up, window.
    load = Counter((r["start"], int(r["minute"])) for r in grid)
    max_load = min(int(config.get("max_load", 6)), 8)
    automatic = str(config.get("window_minutes", "auto")).lower() == "auto"
    ramp = config.get("ramp_up", [1, 2, 4])
    for (lane, minute), count in sorted(load.items()):
        if count > 8:
            errors.append(f"start {lane} minute {minute}: {count} starters, more than 8")
        elif automatic and count > max_load:
            errors.append(f"start {lane} minute {minute}: {count} starters, more than max_load {max_load}")
        if minute < len(ramp) and count > ramp[minute]:
            errors.append(f"start {lane} minute {minute}: {count} starters, ramp-up allows {ramp[minute]}")
    if grid and max(int(r["minute"]) for r in grid) > window:
        errors.append(f"last start after the target window {window}")

    # First-control collisions: only with approval, and as many as the report says.
    legs = Counter((r["start"], r["first_control"], int(r["minute"])) for r in grid if r["first_control"])
    collisions = sum(v - 1 for v in legs.values() if v > 1)
    reported = int(re.search(r"First-control collisions: (\d+)", report).group(1))
    if collisions and not config.get("allow_first_control_collision"):
        errors.append(f"{collisions} first-control collisions without approval")
    if collisions != reported:
        errors.append(f"{collisions} first-control collisions, the report says {reported}")

    # Same-club neighbours: random categories must reach the fewest possible.
    ranked = {c for c, v in rules.cats.items() if any(k in v for k in ("rank_mode", "invert_ranking", "random_block", "random_groups"))}
    for c, rs in by_cat.items():
        people = [r for r in rs if r["row_type"] == "assigned"]
        if len(people) < int(config.get("club_separation_min_entries", 4)) or c in ranked:
            continue
        same = sum(1 for a, b in zip(people, people[1:]) if a["club"] and a["club"] == b["club"])
        clubs = Counter(r["club"] for r in people if r["club"])
        fewest = max(0, 2 * max(clubs.values(), default=0) - len(people) - 1)
        if same > fewest:
            errors.append(f"{c}: {same} same-club neighbours, {fewest} possible")

    # Sensitive categories starting after the first quarter must be reported.
    note = re.search(r"NOTE: these sensitive categories.*", report)
    for c, rs in by_cat.items():
        if rules.sensitive(c) and min(int(r["minute"]) for r in rs) > window // 4 and (not note or c not in note.group(0)):
            errors.append(f"{c}: sensitive category starts late and is not reported")

    # Lower bounds: no grid can be shorter than any of these.
    first_leg = Counter((r["start"], r["first_control"]) for r in grid if r["first_control"])
    lanes = Counter(r["start"] for r in grid)
    bounds = {
        "first_control": (max(first_leg.values()) - 1) if first_leg else 0,
        "load": max((-(-v // max_load) for v in lanes.values()), default=1) - 1,
        "longest_category": max(((len(rs) - 1) * rules.minimum(c, c in relaxed) for c, rs in by_cat.items()), default=0),
    }
    if config.get("allow_first_control_collision"):
        bounds["first_control"] = 0  # collisions approved: not a bound
    return {"window": window, "errors": errors, "notes": notes, "bounds": bounds,
            "lower_bound": max(bounds.values()), "collisions": collisions}


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    result = validate(*sys.argv[1:5])
    status = "OK" if not result["errors"] else "ERRORS"
    print(f"{status}: window {result['window']} min, lower bound {result['lower_bound']} min {result['bounds']}, "
          f"{len(result['errors'])} errors")
    for line in result["errors"][:30]:
        print("  -", line)
    for line in result["notes"][:10]:
        print("  ·", line)
    sys.exit(1 if result["errors"] else 0)


if __name__ == "__main__":
    main()
