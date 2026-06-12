#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Entry:
    row_type: str
    athlete_id: str
    bib: str
    last_name: str
    first_name: str
    club: str
    category: str
    course: str
    first_control: str
    rank_position: int | None
    rank_points: float
    request: str
    request_kind: str
    request_minute: int | None
    request_weight: float
    source_row: dict[str, str]


@dataclass
class Slot:
    entry: Entry
    category_position: int
    minute: int | None = None


def value(row: dict[str, str], key: str, default: str = "") -> str:
    return (row.get(key) or default).strip()


def as_int(raw: str, default: int | None = None) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


def as_float(raw: str, default: float = 0.0) -> float:
    raw = (raw or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def parse_time(raw: str) -> tuple[int, int, int]:
    parts = [int(part) for part in raw.split(":")]
    if len(parts) == 2:
        return parts[0], parts[1], 0
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    raise ValueError(f"Bad time: {raw!r}")


def relative_time(minute: int | None) -> str:
    if minute is None:
        return ""
    return f"{minute // 60:02}:{minute % 60:02}:00"


def absolute_time(first_start: str, minute: int | None) -> str:
    if minute is None:
        return ""
    hh, mm, ss = parse_time(first_start)
    total = hh * 60 + mm + minute
    return f"{total // 60:02}:{total % 60:02}:{ss:02}"


def interval_for(config: dict, category: str) -> int:
    category_config = config.get("categories", {}).get(category, {})
    if "interval" in category_config:
        return int(category_config["interval"])
    if "interval_minutes" in config:
        return int(config["interval_minutes"])
    race_type = str(config.get("race_type", "middle")).lower()
    if race_type == "sprint":
        return 1
    if race_type == "long":
        return 3
    return 2


def category_config(config: dict, category: str) -> dict:
    return config.get("categories", {}).get(category, {})


def is_free_category(config: dict, category: str) -> bool:
    if category in set(config.get("free_categories", [])):
        return True
    return bool(category_config(config, category).get("free_start", False))


def category_course(config: dict, row: dict[str, str]) -> str:
    category = value(row, "category")
    return value(row, "course") or str(category_config(config, category).get("course", ""))


def first_control_for(config: dict, row: dict[str, str], course: str) -> str:
    if value(row, "first_control"):
        return value(row, "first_control")
    course_data = config.get("courses", {}).get(course, {})
    if isinstance(course_data, dict):
        return str(course_data.get("first_control", "")).strip()
    return ""


def load_entries(athletes_path: Path, config: dict) -> list[Entry]:
    entries: list[Entry] = []
    with athletes_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            category = value(row, "category")
            if not category:
                raise RuntimeError(f"Row {index}: missing category")
            course = category_course(config, row)
            first_control = first_control_for(config, row, course)
            entries.append(
                Entry(
                    row_type="free" if is_free_category(config, category) else "assigned",
                    athlete_id=value(row, "id") or str(index),
                    bib=value(row, "bib"),
                    last_name=value(row, "last_name"),
                    first_name=value(row, "first_name"),
                    club=value(row, "club"),
                    category=category,
                    course=course,
                    first_control=first_control,
                    rank_position=as_int(value(row, "rank_position")),
                    rank_points=as_float(value(row, "rank_points")),
                    request=value(row, "request"),
                    request_kind=value(row, "request_kind").lower(),
                    request_minute=as_int(value(row, "request_minute")),
                    request_weight=as_float(value(row, "request_weight"), 1.0),
                    source_row=row,
                )
            )
    return entries


def strength_key(entry: Entry, mode: str) -> tuple[float, str, str, str]:
    if mode == "points":
        strength = entry.rank_points
    else:
        # Position ranking: lower is stronger. Missing rank behaves as weakest.
        strength = -float(entry.rank_position) if entry.rank_position is not None else -999999.0
    return strength, entry.last_name, entry.first_name, entry.athlete_id


def randomize_blocks(order: list[Entry], block_size: int, seed: int) -> list[Entry]:
    if block_size <= 1:
        return order
    rng = random.Random(seed)
    result = order[:]
    # Full blocks are anchored at the strong end (last starters); a partial block falls on the weak end.
    stop = len(result)
    while stop > 0:
        start = max(0, stop - block_size)
        block = result[start:stop]
        rng.shuffle(block)
        result[start:stop] = block
        stop = start
    return result


def separate_clubs(order: list[Entry]) -> list[Entry]:
    groups: dict[str, list[Entry]] = defaultdict(list)
    for entry in order:
        groups[entry.club].append(entry)
    result: list[Entry] = []
    last_club = ""
    while groups:
        choices = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
        chosen = None
        for club, entries in choices:
            if club != last_club or len(choices) == 1:
                chosen = club
                break
        assert chosen is not None
        result.append(groups[chosen].pop(0))
        last_club = chosen
        if not groups[chosen]:
            del groups[chosen]
    return result


def order_category(entries: list[Entry], config: dict, category: str) -> list[Entry]:
    cfg = category_config(config, category)
    rank_mode = str(cfg.get("rank_mode", config.get("rank_mode", "position"))).lower()
    invert = bool(cfg.get("invert_ranking", config.get("invert_ranking", False)))
    block_size = int(cfg.get("random_block", config.get("random_block", 0)) or 0)
    seed = int(config.get("random_seed", 1)) + sum(ord(ch) for ch in category)

    # strength_key sorts weakest/unranked first, strongest last — already the inverted-ranking start order.
    ordered = sorted(entries, key=lambda entry: strength_key(entry, rank_mode))
    if not invert:
        ordered.reverse()

    if block_size:
        ordered = randomize_blocks(ordered, block_size, seed)

    has_seed_policy = any(key in cfg for key in ("rank_mode", "invert_ranking", "random_block"))
    separate_default = not has_seed_policy
    if bool(cfg.get("separate_clubs", config.get("separate_clubs", separate_default))):
        ordered = separate_clubs(ordered)
    return ordered


def vacant_entry(category: str, course: str, first_control: str, index: int) -> Entry:
    return Entry(
        row_type="vacant",
        athlete_id=f"VACANT-{category}-{index}",
        bib="",
        last_name="{Libero}",
        first_name="",
        club="",
        category=category,
        course=course,
        first_control=first_control,
        rank_position=None,
        rank_points=0.0,
        request="",
        request_kind="",
        request_minute=None,
        request_weight=0.0,
        source_row={},
    )


def build_category_slots(entries: list[Entry], config: dict) -> dict[str, list[Slot]]:
    by_category: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        if entry.row_type == "assigned":
            by_category[entry.category].append(entry)

    slots_by_category: dict[str, list[Slot]] = {}
    for category, category_entries in by_category.items():
        ordered = order_category(category_entries, config, category)
        cfg = category_config(config, category)
        vacant_count = int(cfg.get("vacants", config.get("default_vacants", 2)) or 0)
        vacant_position = str(cfg.get("vacant_position", config.get("vacant_position", "end"))).lower()
        course = ordered[0].course if ordered else str(cfg.get("course", ""))
        first_control = ordered[0].first_control if ordered else first_control_for(config, {"category": category}, course)
        vacants = [vacant_entry(category, course, first_control, idx + 1) for idx in range(vacant_count)]
        if vacant_position == "start":
            ordered = vacants + ordered
        elif vacant_position == "none":
            pass
        else:
            ordered = ordered + vacants
        slots_by_category[category] = [
            Slot(entry=entry, category_position=index) for index, entry in enumerate(ordered, start=1)
        ]
    return slots_by_category


def request_penalty(slots: list[Slot]) -> float:
    penalty = 0.0
    for slot in slots:
        entry = slot.entry
        if slot.minute is None or entry.request_minute is None:
            continue
        weight = entry.request_weight or 1.0
        if entry.request_kind == "early":
            penalty += max(0, slot.minute - entry.request_minute) * weight
        elif entry.request_kind == "late":
            penalty += max(0, entry.request_minute - slot.minute) * weight
        elif entry.request_kind == "exact":
            penalty += abs(slot.minute - entry.request_minute) * weight * 2
    return penalty


def relation_penalty(all_slots: list[Slot], config: dict) -> float:
    by_id = {slot.entry.athlete_id: slot for slot in all_slots if slot.minute is not None}
    penalty = 0.0
    for relation in config.get("separate_pairs", []):
        left = by_id.get(str(relation.get("left", "")))
        right = by_id.get(str(relation.get("right", "")))
        if not left or not right:
            continue
        wanted = int(relation.get("minutes", 0))
        weight = float(relation.get("weight", 1))
        penalty += max(0, wanted - abs(left.minute - right.minute)) * weight
    for relation in config.get("near_pairs", []):
        left = by_id.get(str(relation.get("left", "")))
        right = by_id.get(str(relation.get("right", "")))
        if not left or not right:
            continue
        wanted = int(relation.get("minutes", 0))
        weight = float(relation.get("weight", 1))
        penalty += max(0, abs(left.minute - right.minute) - wanted) * weight
    return penalty


def evaluate(
    placed: list[Slot],
    candidate: list[Slot],
    max_load: int,
    peak_load: int,
    allow_collision: bool = False,
) -> float:
    score = 0.0
    load = Counter(slot.minute for slot in placed if slot.minute is not None)
    first = defaultdict(Counter)
    for slot in placed:
        if slot.minute is not None:
            first[slot.minute][slot.entry.first_control] += 1
    for slot in candidate:
        assert slot.minute is not None
        load[slot.minute] += 1
        if load[slot.minute] > peak_load:
            return math.inf
        if load[slot.minute] > max_load:
            score += (load[slot.minute] - max_load) * 100
        first[slot.minute][slot.entry.first_control] += 1
        if slot.entry.first_control and first[slot.minute][slot.entry.first_control] > 1:
            if not allow_collision:
                return math.inf
            score += 1000
    score += sum(value * value for value in load.values()) * 0.1
    score += request_penalty(candidate)
    return score


def assign_times(slots_by_category: dict[str, list[Slot]], config: dict) -> list[Slot]:
    window = int(config.get("window_minutes", 90))
    max_load = int(config.get("max_load", 6))
    peak_load = int(config.get("peak_load", max(8, max_load)))
    allow_collision = bool(config.get("allow_first_control_collision", False))
    placed: list[Slot] = []
    categories = sorted(
        slots_by_category,
        key=lambda category: (-len(slots_by_category[category]), category),
    )
    for category in categories:
        slots = slots_by_category[category]
        interval = interval_for(config, category)
        span = (len(slots) - 1) * interval if slots else 0
        latest_offset = max(0, window - span)
        best_score = math.inf
        best_candidate: list[Slot] | None = None
        for offset in range(0, latest_offset + 1):
            candidate = [
                Slot(entry=slot.entry, category_position=slot.category_position, minute=offset + index * interval)
                for index, slot in enumerate(slots)
            ]
            score = evaluate(placed, candidate, max_load, peak_load, allow_collision)
            if score < best_score:
                best_score = score
                best_candidate = candidate
        if best_candidate is None or math.isinf(best_score):
            raise RuntimeError(
                f"Cannot place category {category!r}; increase window, load limit, interval, or start lanes."
            )
        placed.extend(best_candidate)
    placed.sort(key=lambda slot: (slot.minute if slot.minute is not None else -1, slot.entry.category, slot.category_position))
    return placed


def build_rows(entries: list[Entry], assigned_slots: list[Slot], config: dict) -> list[dict[str, str]]:
    first_start = str(config.get("first_start", "10:00:00"))
    free_entries = [entry for entry in entries if entry.row_type == "free"]
    rows: list[dict[str, str]] = []
    for entry in sorted(free_entries, key=lambda item: (item.category, item.club, item.last_name, item.first_name)):
        rows.append(row_for(Slot(entry=entry, category_position=0, minute=None), first_start))
    for slot in assigned_slots:
        rows.append(row_for(slot, first_start))
    return rows


def row_for(slot: Slot, first_start: str) -> dict[str, str]:
    entry = slot.entry
    return {
        "row_type": entry.row_type,
        "relative_time": relative_time(slot.minute),
        "absolute_time": absolute_time(first_start, slot.minute),
        "minute": "" if slot.minute is None else str(slot.minute),
        "category_position": "" if slot.category_position == 0 else str(slot.category_position),
        "bib": entry.bib,
        "last_name": entry.last_name,
        "first_name": entry.first_name,
        "club": entry.club,
        "category": entry.category,
        "course": entry.course,
        "first_control": entry.first_control,
        "athlete_id": entry.athlete_id,
        "vacant": "True" if entry.row_type == "vacant" else "",
        "request": entry.request,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "row_type",
        "relative_time",
        "absolute_time",
        "minute",
        "category_position",
        "bib",
        "last_name",
        "first_name",
        "club",
        "category",
        "course",
        "first_control",
        "athlete_id",
        "vacant",
        "request",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def report(rows: list[dict[str, str]], config: dict) -> str:
    assigned = [row for row in rows if row["row_type"] in {"assigned", "vacant"}]
    free = [row for row in rows if row["row_type"] == "free"]
    load = Counter(int(row["minute"]) for row in assigned if row["minute"])
    first_counts = defaultdict(Counter)
    for row in assigned:
        first_counts[int(row["minute"])][row["first_control"]] += 1
    collisions = [
        (minute, first, count)
        for minute, counter in first_counts.items()
        for first, count in counter.items()
        if first and count > 1
    ]
    lines = [
        "Orienteering start list proposal",
        "",
        f"Rows: {len(rows)}",
        f"Assigned rows incl. vacants: {len(assigned)}",
        f"Free-start rows: {len(free)}",
        f"Vacants: {sum(1 for row in rows if row['row_type'] == 'vacant')}",
    ]
    if load:
        lines.extend(
            [
                f"Window: {min(load)}-{max(load)} minutes",
                f"Peak load: {max(load.values())}",
                f"Minutes over max_load={config.get('max_load', 6)}: "
                f"{sum(1 for value in load.values() if value > int(config.get('max_load', 6)))}",
            ]
        )
        window_target = int(config.get("window_minutes", 90))
        if max(load) > window_target:
            lines.append(
                f"WARNING: last start at minute {max(load)} exceeds window_minutes={window_target}; "
                "increase the window, load limit, or start lanes."
            )
    lines.extend(
        [
            f"First-control collisions: {len(collisions)}",
            "",
            "Load by minute:",
        ]
    )
    for minute in sorted(load):
        lines.append(f"- {minute}: {load[minute]}")
    if collisions:
        lines.extend(["", "Collisions:"])
        for minute, first, count in collisions:
            lines.append(f"- minute {minute}, first control {first}: {count}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--athletes", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    entries = load_entries(args.athletes, config)
    slots_by_category = build_category_slots(entries, config)
    assigned_slots = assign_times(slots_by_category, config)
    rows = build_rows(entries, assigned_slots, config)
    write_csv(args.out, rows)
    args.report.write_text(report(rows, config), encoding="utf-8")
    print(f"rows={len(rows)} out={args.out} report={args.report}")


if __name__ == "__main__":
    main()
