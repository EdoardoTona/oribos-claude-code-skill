#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
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


FISO_2027 = "fiso-2027"
MASTER_PATTERN = re.compile(r"^\s*[MWDHF]\s*-?\s*(\d{2})\b", re.IGNORECASE)


def ruleset(config: dict) -> str:
    return str(config.get("ruleset", "")).strip().lower()


def race_type(config: dict) -> str:
    return str(config.get("race_type", "middle")).lower()


def is_master(config: dict, category: str) -> bool:
    """Master = age class 35+ (M35, W 40, D45, H-50...). Override with categories.<name>.master."""
    cfg = category_config(config, category)
    if "master" in cfg:
        return bool(cfg["master"])
    match = MASTER_PATTERN.match(category)
    return bool(match) and int(match.group(1)) >= int(config.get("master_min_age", 35))


def min_interval_for(config: dict, category: str) -> int:
    """Minimum interval imposed by the ruleset (0 = no minimum)."""
    cfg = category_config(config, category)
    if "min_interval" in cfg:
        return int(cfg["min_interval"])
    if ruleset(config) == FISO_2027 and is_master(config, category):
        if race_type(config) == "sprint":
            return int(config.get("master_min_interval_sprint", 2))
        return int(config.get("master_min_interval", 3))
    return 0


def base_interval_for(config: dict, category: str) -> int:
    cfg = category_config(config, category)
    if "interval" in cfg:
        return int(cfg["interval"])
    if "interval_minutes" in config:
        return int(config["interval_minutes"])
    if race_type(config) == "sprint":
        return 1
    if race_type(config) == "long":
        return 3
    return 2


def interval_for(config: dict, category: str) -> int:
    return max(base_interval_for(config, category), min_interval_for(config, category))


def max_interval_for(config: dict, category: str) -> int:
    """Largest interval worth trying when the window allows it (FISO 2027 encourages wider gaps)."""
    cfg = category_config(config, category)
    base = interval_for(config, category)
    if "max_interval" in cfg:
        return max(base, int(cfg["max_interval"]))
    if is_master(config, category) and "master_max_interval" in config:
        return max(base, int(config["master_max_interval"]))
    if "max_interval" in config:
        return max(base, int(config["max_interval"]))
    if ruleset(config) == FISO_2027 and race_type(config) != "sprint":
        # FISO 2027: in non-sprint races every category may get a wider (constant) interval, up to 7 minutes.
        return max(base, int(config.get("fiso_max_interval", 7)))
    return base


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


def randomize_groups(order: list[Entry], groups: int, seed: int) -> list[Entry]:
    """Split the weak->strong order into `groups` contiguous strength groups and shuffle inside each."""
    if groups <= 1 or len(order) <= 1:
        return order
    rng = random.Random(seed)
    result: list[Entry] = []
    size = len(order)
    for index in range(groups):
        start = round(index * size / groups)
        stop = round((index + 1) * size / groups)
        block = order[start:stop]
        rng.shuffle(block)
        result.extend(block)
    return result


def seeding_policy(config: dict, category: str) -> tuple[str, int]:
    """Return ("block", size), ("groups", count) or ("none", 0) for a ranked category."""
    cfg = category_config(config, category)
    if cfg.get("random_block"):
        return "block", int(cfg["random_block"])
    if cfg.get("random_groups"):
        return "groups", int(cfg["random_groups"])
    if "random_block" in cfg or "random_groups" in cfg:
        return "none", 0
    if config.get("random_block"):
        return "block", int(config["random_block"])
    if config.get("random_groups"):
        return "groups", int(config["random_groups"])
    if ruleset(config) == FISO_2027:
        # FISO 2027: elite classes shuffled in small blocks (5 or 10) so the strongest stay near the end;
        # other ranked classes shuffled within ~3 strength groups (Coppa Italia, lista base...).
        if "elite" in category.lower():
            return "block", int(config.get("elite_random_block", 5))
        return "groups", int(config.get("default_random_groups", 3))
    return "none", 0


def separate_clubs(order: list[Entry], preserve_input_ties: bool = False) -> list[Entry]:
    groups: dict[str, list[Entry]] = defaultdict(list)
    club_order: dict[str, int] = {}
    for index, entry in enumerate(order):
        groups[entry.club].append(entry)
        club_order.setdefault(entry.club, index)
    result: list[Entry] = []
    last_club = ""
    while groups:
        choices = sorted(
            groups.items(),
            key=lambda item: (-len(item[1]), club_order[item[0]] if preserve_input_ties else item[0]),
        )
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


def shuffle_entries(order: list[Entry], seed: int) -> list[Entry]:
    result = order[:]
    random.Random(seed).shuffle(result)
    return result


def order_category(entries: list[Entry], config: dict, category: str) -> list[Entry]:
    cfg = category_config(config, category)
    rank_mode = str(cfg.get("rank_mode", config.get("rank_mode", "position"))).lower()
    invert = bool(cfg.get("invert_ranking", config.get("invert_ranking", False)))
    stage_offset = int(config.get("stage", config.get("race_number", 0)) or 0) * 100000
    seed = int(config.get("random_seed", 1)) + stage_offset + sum(ord(ch) for ch in category)

    # strength_key sorts weakest/unranked first, strongest last — already the inverted-ranking start order.
    ordered = sorted(entries, key=lambda entry: strength_key(entry, rank_mode))
    if not invert:
        ordered.reverse()

    has_seed_policy = any(
        key in cfg for key in ("rank_mode", "invert_ranking", "random_block", "random_groups")
    )
    if has_seed_policy:
        policy, size = seeding_policy(config, category)
        if policy == "block":
            ordered = randomize_blocks(ordered, size, seed)
        elif policy == "groups":
            ordered = randomize_groups(ordered, size, seed)
    randomized_unseeded = False
    if not has_seed_policy and bool(cfg.get("randomize", config.get("randomize_unseeded", True))):
        ordered = shuffle_entries(ordered, seed)
        randomized_unseeded = True

    if has_seed_policy:
        policy, size = seeding_policy(config, category)
        segments = segment_ids(len(ordered), policy, size)
    elif randomized_unseeded:
        segments = [0] * len(ordered)
    else:
        segments = None  # fixed order: nothing may move

    # Same-club neighbours are avoided by default wherever the order is random (fully or inside
    # strength groups/blocks), except in very small categories where it is not meaningful.
    min_entries = int(cfg.get("club_separation_min_entries", config.get("club_separation_min_entries", 4)))
    club_separation = bool(cfg.get("separate_clubs", config.get("separate_clubs", segments is not None)))
    club_separation = club_separation and len(ordered) >= min_entries
    if club_separation and segments is None:
        # Explicit request on a fixed-order category: legacy greedy separation (may break the ranking order).
        ordered = separate_clubs(ordered)
    elif club_separation and randomized_unseeded:
        ordered = separate_clubs(ordered, preserve_input_ties=True)

    forbidden = config.get("_previous_pairs", set())
    if not bool(cfg.get("avoid_repeated_pairs", config.get("avoid_repeated_pairs", True))):
        forbidden = set()
    if segments is not None and (forbidden or club_separation):
        ordered = improve_order(ordered, segments, forbidden, club_separation, seed + 7919)
    config.setdefault("_repeated_pairs", {})[category] = sum(
        1 for left, right in zip(ordered, ordered[1:]) if frozenset((left.athlete_id, right.athlete_id)) in forbidden
    )
    config.setdefault("_club_separation", {})[category] = club_separation
    return ordered


def segment_ids(size: int, policy: str, value: int) -> list[int] | None:
    """Shuffle scope of each position: athletes may only be swapped inside the same segment."""
    if policy == "block" and value > 1:
        ids = [0] * size
        stop, segment = size, 0
        while stop > 0:
            start = max(0, stop - value)
            for index in range(start, stop):
                ids[index] = segment
            stop, segment = start, segment + 1
        return ids
    if policy == "groups" and value > 1:
        ids = [0] * size
        for group in range(value):
            for index in range(round(group * size / value), round((group + 1) * size / value)):
                ids[index] = group
        return ids
    return None


def improve_order(
    order: list[Entry],
    segments: list[int],
    forbidden: set[frozenset[str]],
    club_separation: bool,
    seed: int,
) -> list[Entry]:
    """Local search: swap athletes inside their shuffle segment (so seeding is preserved) to avoid
    (a) same-club neighbours and (b) neighbours who were consecutive in a previous race."""
    if len(order) < 3:
        return order
    rng = random.Random(seed)
    result = order[:]

    def bad_link(left: Entry, right: Entry) -> bool:
        if frozenset((left.athlete_id, right.athlete_id)) in forbidden:
            return True
        return club_separation and bool(left.club) and left.club == right.club

    def cost(items: list[Entry]) -> int:
        # Same-club neighbours weigh more than repeated pairs: fairness first, variety second.
        total = 0
        for left, right in zip(items, items[1:]):
            if club_separation and left.club and left.club == right.club:
                total += 3
            if frozenset((left.athlete_id, right.athlete_id)) in forbidden:
                total += 1
        return total

    current = cost(result)
    members: dict[int, list[int]] = defaultdict(list)
    for index, segment in enumerate(segments):
        members[segment].append(index)
    best, best_cost = result[:], current
    steps = 500 * len(result)
    for step in range(steps):
        if best_cost == 0:
            break
        bad = [index for index in range(len(result) - 1) if bad_link(result[index], result[index + 1])]
        if not bad:
            break
        index = rng.choice(bad) + rng.randint(0, 1)
        partners = [other for other in members[segments[index]] if other != index]
        if not partners:
            continue
        other = rng.choice(partners)
        result[index], result[other] = result[other], result[index]
        candidate = cost(result)
        # Accept improvements and sideways moves; occasionally accept a worse move to escape local minima.
        if candidate <= current or rng.random() < 0.1 * (1 - step / steps):
            current = candidate
            if current < best_cost:
                best, best_cost = result[:], current
        else:
            result[index], result[other] = result[other], result[index]
    return best


def load_previous_pairs(paths: list[str], base: Path) -> set[frozenset[str]]:
    """Consecutive athlete pairs (by athlete_id, vacants excluded) from earlier proposal CSVs."""
    pairs: set[frozenset[str]] = set()
    for raw in paths:
        path = Path(raw)
        if not path.is_absolute():
            path = base / path
        by_category: dict[str, list[tuple[int, str]]] = defaultdict(list)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("row_type") != "assigned" or not row.get("category_position"):
                    continue
                by_category[row["category"]].append((int(row["category_position"]), row["athlete_id"]))
        for rows in by_category.values():
            rows.sort()
            for (_, left), (_, right) in zip(rows, rows[1:]):
                pairs.add(frozenset((left, right)))
    return pairs


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


class Board:
    """Start load and first controls per minute of the categories placed so far."""

    def __init__(self) -> None:
        self.load: Counter[int] = Counter()
        self.first: dict[int, Counter[str]] = defaultdict(Counter)

    def add(self, slots: list[Slot]) -> None:
        for slot in slots:
            assert slot.minute is not None
            self.load[slot.minute] += 1
            if slot.entry.first_control:
                self.first[slot.minute][slot.entry.first_control] += 1


def offset_score(
    board: Board,
    slots: list[Slot],
    offset: int,
    interval: int,
    max_load: int,
    peak_load: int,
    allow_collision: bool,
) -> float:
    score = 0.0
    squares = 0
    for index, slot in enumerate(slots):
        minute = offset + index * interval
        load = board.load[minute] + 1
        if load > peak_load:
            return math.inf
        if load > max_load:
            score += (load - max_load) * 100
        control = slot.entry.first_control
        if control and board.first[minute][control] > 0:
            if not allow_collision:
                return math.inf
            score += 1000
        squares += 2 * load - 1  # increase of sum(load^2)
        entry = slot.entry
        if entry.request_minute is not None:
            weight = entry.request_weight or 1.0
            if entry.request_kind == "early":
                score += max(0, minute - entry.request_minute) * weight
            elif entry.request_kind == "late":
                score += max(0, entry.request_minute - minute) * weight
            elif entry.request_kind == "exact":
                score += abs(minute - entry.request_minute) * weight * 2
    return score + squares * 0.1


def best_placement(
    board: Board,
    slots: list[Slot],
    interval: int,
    window: int,
    max_load: int,
    peak_load: int,
    allow_collision: bool,
) -> tuple[list[Slot] | None, float]:
    span = (len(slots) - 1) * interval if slots else 0
    best_score = math.inf
    best_offset: int | None = None
    for offset in range(0, max(0, window - span) + 1):
        score = offset_score(board, slots, offset, interval, max_load, peak_load, allow_collision)
        if score < best_score:
            best_score, best_offset = score, offset
    if best_offset is None:
        return None, math.inf
    return [
        Slot(entry=slot.entry, category_position=slot.category_position, minute=best_offset + index * interval)
        for index, slot in enumerate(slots)
    ], best_score


@dataclass
class Placement:
    slots: list[Slot]
    failed: str | None
    over_max: int
    collisions: int


def place_all(
    order: list[str],
    slots_by_category: dict[str, list[Slot]],
    intervals: dict[str, int],
    window: int,
    max_load: int,
    peak_load: int,
    allow_collision: bool,
) -> Placement:
    board = Board()
    placed: list[Slot] = []
    for category in order:
        candidate, score = best_placement(
            board, slots_by_category[category], intervals[category], window, max_load, peak_load, allow_collision
        )
        if candidate is None or math.isinf(score):
            return Placement(placed, category, 0, 0)
        board.add(candidate)
        placed.extend(candidate)
    over_max = sum(1 for value in board.load.values() if value > max_load)
    collisions = sum(count - 1 for counter in board.first.values() for count in counter.values() if count > 1)
    return Placement(placed, None, over_max, collisions)


def auto_window(slots_by_category: dict[str, list[Slot]], config: dict) -> int:
    """Contained start window: long enough for the longest category at its minimum interval and for
    an average load of `target_load` starters per minute (default 5, the middle of FISO's 4-6)."""
    total = sum(len(slots) for slots in slots_by_category.values())
    target = float(config.get("target_load", 5))
    longest = max(((len(slots) - 1) * interval_for(config, category) for category, slots in slots_by_category.items()), default=0)
    return max(longest, math.ceil(total / target) - 1)


def assign_times(slots_by_category: dict[str, list[Slot]], config: dict) -> list[Slot]:
    raw_window = config.get("window_minutes", "auto")
    automatic = str(raw_window).lower() == "auto"
    window = auto_window(slots_by_category, config) if automatic else int(raw_window)
    max_load = int(config.get("max_load", 6))
    peak_load = int(config.get("peak_load", max(8, max_load)))
    allow_collision = bool(config.get("allow_first_control_collision", False))
    order = sorted(slots_by_category, key=lambda category: (-len(slots_by_category[category]), category))
    intervals = {category: interval_for(config, category) for category in order}

    # 1. Minimum intervals must fit. An automatic window grows (5% steps) until they do.
    result = place_all(order, slots_by_category, intervals, window, max_load, peak_load, allow_collision)
    while result.failed and automatic and window < 24 * 60:
        window = math.ceil(window * 1.05) + 1
        result = place_all(order, slots_by_category, intervals, window, max_load, peak_load, allow_collision)
    if result.failed:
        raise RuntimeError(
            f"Cannot place category {result.failed!r}; increase window, load limit, interval, or start lanes."
        )

    # 2. Widen intervals inside the same window ("water filling"): repeatedly give +1 minute to the
    #    category with the smallest interval, keeping the change only if every category still fits,
    #    no minute gets more over max_load and no first-control collision is added.
    caps = {}
    for category in order:
        gaps = max(1, len(slots_by_category[category]) - 1)
        caps[category] = max(intervals[category], min(max_interval_for(config, category), window // gaps))
    frozen = {category for category in order if intervals[category] >= caps[category]}
    while len(frozen) < len(order):
        category = min(
            (c for c in order if c not in frozen),
            key=lambda c: (intervals[c], -len(slots_by_category[c]), c),
        )
        intervals[category] += 1
        trial = place_all(order, slots_by_category, intervals, window, max_load, peak_load, allow_collision)
        if trial.failed or trial.over_max > result.over_max or trial.collisions > result.collisions:
            intervals[category] -= 1
            frozen.add(category)
            continue
        result = trial
        if intervals[category] >= caps[category]:
            frozen.add(category)

    config["_chosen_intervals"] = intervals
    config["_window"] = window
    config["_window_auto"] = automatic
    placed = result.slots
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
        f"Random seed: {config.get('random_seed', 1)}",
        f"Stage/race offset: {config.get('stage', config.get('race_number', 0))}",
        f"Randomize unseeded categories: {config.get('randomize_unseeded', True)}",
        f"Ruleset: {config.get('ruleset') or 'generic'}",
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
        window_target = int(config.get("_window", config.get("window_minutes", 90)))
        lines.append(
            f"Target window: {window_target} minutes"
            + (" (computed automatically)" if config.get("_window_auto") else " (window_minutes)")
        )
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
    lines.extend(category_report(rows, config))
    if collisions:
        lines.extend(["", "Collisions:"])
        for minute, first, count in collisions:
            lines.append(f"- minute {minute}, first control {first}: {count}")
    return "\n".join(lines) + "\n"


def category_report(rows: list[dict[str, str]], config: dict) -> list[str]:
    chosen = config.get("_chosen_intervals", {})
    by_category: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["row_type"] in {"assigned", "vacant"}:
            by_category[row["category"]].append(row)
    lines = ["", "Categories (interval, master, seeding):"]
    warnings: list[str] = []
    for category in sorted(by_category):
        cfg = category_config(config, category)
        cat_rows = by_category[category]
        minutes = [int(row["minute"]) for row in cat_rows if row["minute"]]
        interval = chosen.get(category, interval_for(config, category))
        base = base_interval_for(config, category)
        minimum = min_interval_for(config, category)
        master = is_master(config, category)
        has_seed_policy = any(
            key in cfg for key in ("rank_mode", "invert_ranking", "random_block", "random_groups")
        )
        if has_seed_policy:
            policy, size = seeding_policy(config, category)
            seeding = {"block": f"ranking, random blocks of {size}", "groups": f"ranking, {size} random strength groups"}.get(
                policy, "ranking, no randomization"
            )
        elif bool(cfg.get("randomize", config.get("randomize_unseeded", True))):
            seeding = "full random"
        else:
            seeding = "no ranking, not randomized"
        notes = []
        ordered_rows = sorted(
            (row for row in cat_rows if row["row_type"] == "assigned"), key=lambda row: int(row["category_position"])
        )
        same_club = sum(
            1 for left, right in zip(ordered_rows, ordered_rows[1:]) if left["club"] and left["club"] == right["club"]
        )
        if same_club:
            notes.append(f"{same_club} same-club neighbours")
        if not config.get("_club_separation", {}).get(category, True):
            notes.append("club separation off")
        repeated = config.get("_repeated_pairs", {}).get(category)
        if config.get("_previous_pairs") and repeated is not None:
            notes.append(f"{repeated} consecutive pairs repeated from previous races")
        if minimum and base < minimum:
            notes.append(f"raised from {base} to ruleset minimum {minimum}")
        if interval > max(base, minimum):
            notes.append("widened because the window allowed it")
        lines.append(
            f"- {category}: {len(cat_rows)} slots, interval {interval} min, "
            f"minutes {min(minutes) if minutes else '-'}-{max(minutes) if minutes else '-'}, "
            f"master={'yes' if master else 'no'}, seeding: {seeding}"
            + (f" ({'; '.join(notes)})" if notes else "")
        )
        if minimum and interval < minimum:
            warnings.append(f"WARNING: {category} interval {interval} is below the ruleset minimum {minimum}.")
    if ruleset(config) == FISO_2027:
        lines.extend(
            [
                "",
                "FISO 2027 checks: master (35+) minimum interval "
                f"{config.get('master_min_interval_sprint', 2)} min sprint / {config.get('master_min_interval', 3)} min other races; "
                "load target 4-6 per minute, never above 8.",
            ]
        )
        peak = Counter(int(row["minute"]) for rows_ in by_category.values() for row in rows_ if row["minute"])
        if peak and max(peak.values()) > 8:
            warnings.append(f"WARNING: peak load {max(peak.values())} exceeds the FISO limit of 8 per minute.")
    if warnings:
        lines.append("")
        lines.extend(warnings)
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--athletes", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    previous = config.get("previous_start_lists", [])
    if previous:
        config["_previous_pairs"] = load_previous_pairs(previous, args.config.parent)
    if ruleset(config) == FISO_2027:
        # FISO 2027 keeps the 6 normal / 8 absolute per-minute limits; never allow more than 8.
        config.setdefault("max_load", 6)
        config["peak_load"] = min(int(config.get("peak_load", 8)), 8)
    entries = load_entries(args.athletes, config)
    slots_by_category = build_category_slots(entries, config)
    assigned_slots = assign_times(slots_by_category, config)
    rows = build_rows(entries, assigned_slots, config)
    write_csv(args.out, rows)
    args.report.write_text(report(rows, config), encoding="utf-8")
    print(f"rows={len(rows)} out={args.out} report={args.report}")


if __name__ == "__main__":
    main()
