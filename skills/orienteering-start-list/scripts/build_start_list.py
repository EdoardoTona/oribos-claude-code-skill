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
    start_lane: str = "1"


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
                    start_lane=start_lane_for(config, row, category),
                )
            )
    return entries


def start_lane_for(config: dict, row: dict[str, str], category: str) -> str:
    """Physical start (lane/corridor) of the category: categories.<name>.start, the athletes CSV
    `start` column, or "1". Load limits apply to each start separately."""
    cfg = category_config(config, category)
    if "start" in cfg:
        return str(cfg["start"]).strip() or "1"
    return value(row, "start") or "1"


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
        stats: dict = {}
        neighbour_groups = bool(cfg.get("club_move_to_neighbour_group", config.get("club_move_to_neighbour_group", True)))
        ordered = improve_order(ordered, segments, forbidden, club_separation, seed + 7919)
        same_club_left = club_separation and any(
            left.club and left.club == right.club for left, right in zip(ordered, ordered[1:])
        )
        if same_club_left and neighbour_groups and len(set(segments)) > 1:
            # Second phase, only for what the group-internal search could not solve: allow moving an
            # athlete to the adjacent strength group/block. Positions are re-anchored to the original
            # groups so nobody drifts more than one group away.
            original = {entry.athlete_id: segments[index] for index, entry in enumerate(ordered)}
            ordered = improve_order(
                ordered, segments, forbidden, club_separation, seed + 104729,
                neighbour_groups=True, stats=stats, home=original,
            )
        config.setdefault("_moved", {})[category] = stats.get("moved", 0)
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
    neighbour_groups: bool = False,
    stats: dict | None = None,
    home: dict[str, int] | None = None,
) -> list[Entry]:
    """Local search: swap athletes inside their shuffle segment (so seeding is preserved) to avoid
    (a) same-club neighbours and (b) neighbours who were consecutive in a previous race.
    With neighbour_groups, an athlete may also move to the adjacent strength group/block when that
    is the only way to separate same-club neighbours (each moved athlete costs less than one
    same-club neighbour, more than nothing)."""
    if len(order) < 3:
        return order
    rng = random.Random(seed)
    result = order[:]
    home = home or {entry.athlete_id: segments[index] for index, entry in enumerate(order)}
    reach = 1 if neighbour_groups else 0

    def bad_link(left: Entry, right: Entry) -> bool:
        if frozenset((left.athlete_id, right.athlete_id)) in forbidden:
            return True
        return club_separation and bool(left.club) and left.club == right.club

    def cost(items: list[Entry]) -> int:
        # Same-club neighbours weigh more than repeated pairs: fairness first, variety second.
        total = 0
        for left, right in zip(items, items[1:]):
            if club_separation and left.club and left.club == right.club:
                total += 50  # always worse than moving a few athletes to the adjacent group
            if frozenset((left.athlete_id, right.athlete_id)) in forbidden:
                total += 1
        if reach:
            total += sum(1 for index, entry in enumerate(items) if segments[index] != home[entry.athlete_id])
        return total

    current = cost(result)
    members: dict[int, list[int]] = defaultdict(list)
    for index, segment in enumerate(segments):
        for near in range(segment - reach, segment + reach + 1):
            members[near].append(index)
    best, best_cost = result[:], current
    steps = 500 * len(result)
    for step in range(steps):
        if best_cost == 0:
            break
        bad = [index for index in range(len(result) - 1) if bad_link(result[index], result[index + 1])]
        if not bad:
            break
        index = rng.choice(bad) + rng.randint(0, 1)
        partners = [
            other
            for other in members[segments[index]]
            if other != index
            and abs(segments[other] - home[result[index].athlete_id]) <= reach
            and abs(segments[index] - home[result[other].athlete_id]) <= reach
        ]
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
    if reach and len(best) <= 14 and any(
        left.club and left.club == right.club for left, right in zip(best, best[1:])
    ):
        # Small category: the local search can get stuck when several athletes must move at once.
        # Exhaustive search for an order with no same-club neighbours, own group first (fewest moves).
        exact = exact_club_order(best, segments, home, reach)
        if exact is not None and cost(exact) < cost(best):
            best = exact
    if stats is not None:
        stats["moved"] = sum(1 for index, entry in enumerate(best) if segments[index] != home[entry.athlete_id])
    return best


def exact_club_order(
    order: list[Entry], segments: list[int], home: dict[str, int], reach: int, limit: float = 1.0
) -> list[Entry] | None:
    """Depth-first search for an order without same-club neighbours where every athlete stays within
    `reach` groups of its home group; tries athletes of the position's own group first."""
    import time

    n = len(order)
    deadline = time.time() + limit
    used = [False] * n
    result: list[Entry] = []

    def rec(pos: int) -> bool:
        if time.time() > deadline:
            return False
        if pos == n:
            return True
        prev = result[-1].club if result else None
        candidates = sorted(
            (i for i in range(n) if not used[i] and abs(segments[pos] - home[order[i].athlete_id]) <= reach),
            key=lambda i: (home[order[i].athlete_id] != segments[pos], i),
        )
        seen = set()
        for i in candidates:
            entry = order[i]
            if entry.club and entry.club == prev:
                continue
            key = (entry.club, home[entry.athlete_id])
            if key in seen:
                continue
            seen.add(key)
            # nobody may be left behind beyond its reach
            if pos + 1 < n and any(
                not used[j] and j != i and home[order[j].athlete_id] + reach < segments[pos + 1] for j in range(n)
            ):
                continue
            used[i] = True
            result.append(entry)
            if rec(pos + 1):
                return True
            result.pop()
            used[i] = False
        return False

    return result[:] if rec(0) else None


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


def relax_large_masters(entries: list[Entry], config: dict) -> None:
    """FISO 2027 master minimum (3 minutes outside sprint) on a very large master category can make
    the whole grid far longer than entries and load need (e.g. 65 athletes x 3 min = 192 minutes).
    For such categories propose 2 minutes instead, only for that category, and report it."""
    if ruleset(config) != FISO_2027 or race_type(config) == "sprint":
        return
    grid = [entry for entry in entries if entry.row_type == "assigned"]
    per_category = Counter(entry.category for entry in grid)
    per_lane = Counter(entry.start_lane for entry in grid)
    target = target_for(len(per_lane), config)
    load_window = math.ceil(max(per_lane.values(), default=0) / max(1.0, target)) - 1
    large = int(config.get("master_large_category", 50))
    for category, count in per_category.items():
        cfg = category_config(config, category)
        if not is_master(config, category) or count < large or "interval" in cfg or "min_interval" in cfg:
            continue
        slots = count + int(config.get("default_vacants", 2) or 0)
        if (slots - 1) * min_interval_for(config, category) > load_window:
            config.setdefault("categories", {}).setdefault(category, {})["min_interval"] = 2
            config.setdefault("_relaxed_masters", {})[category] = (count, (slots - 1) * 3, load_window)


def build_category_slots(entries: list[Entry], config: dict) -> dict[str, list[Slot]]:
    by_category: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        if entry.row_type == "assigned":
            by_category[entry.category].append(entry)

    slots_by_category: dict[str, list[Slot]] = {}
    for category, category_entries in by_category.items():
        ordered = order_category(category_entries, config, category)
        cfg = category_config(config, category)
        if "vacants" in cfg:
            vacant_count = int(cfg["vacants"] or 0)
        else:
            vacant_count = int(config.get("default_vacants", 2) or 0)
            # Small categories: one vacant is enough (but always at least one).
            if len(ordered) < int(config.get("small_category_size", 10)):
                vacant_count = min(vacant_count, int(config.get("small_category_vacants", 1)))
        vacant_position = str(cfg.get("vacant_position", config.get("vacant_position", "end"))).lower()
        course = ordered[0].course if ordered else str(cfg.get("course", ""))
        first_control = ordered[0].first_control if ordered else first_control_for(config, {"category": category}, course)
        vacants = [vacant_entry(category, course, first_control, idx + 1) for idx in range(vacant_count)]
        for vacant in vacants:
            vacant.start_lane = ordered[0].start_lane if ordered else str(cfg.get("start", "1"))
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


def leg_key(entry: Entry) -> str:
    """First leg = start + first control. Two starters from different starts heading to the same first
    control run different legs and do not follow each other, so only the same start + first control
    in the same minute counts as a collision."""
    return f"{entry.start_lane}|{entry.first_control}" if entry.first_control else ""


class Board:
    """Start load and first controls per minute of the categories placed so far."""

    def __init__(self) -> None:
        self.load: Counter[tuple[str, int]] = Counter()  # (start lane, minute) -> starters
        self.first: dict[int, Counter[str]] = defaultdict(Counter)

    def add(self, slots: list[Slot]) -> None:
        for slot in slots:
            assert slot.minute is not None
            self.load[(slot.entry.start_lane, slot.minute)] += 1
            if slot.entry.first_control:
                self.first[slot.minute][leg_key(slot.entry)] += 1


def offset_score(
    board: Board,
    slots: list[Slot],
    offset: int,
    interval: int,
    max_load: int,
    peak_load: int,
    allow_collision: bool,
    ramp: tuple[int, ...] = (),
) -> float:
    score = 0.0
    squares = 0
    for index, slot in enumerate(slots):
        minute = offset + index * interval
        load = board.load[(slot.entry.start_lane, minute)] + 1
        if load > peak_load or (minute < len(ramp) and load > ramp[minute]):
            return math.inf
        if load > max_load:
            score += (load - max_load) * 100
        control = leg_key(slot.entry)
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
    pack: float = 0.0,
    ramp: tuple[int, ...] = (),
) -> tuple[list[Slot] | None, float]:
    span = (len(slots) - 1) * interval if slots else 0
    best_score = math.inf
    best_offset: int | None = None
    for offset in range(0, max(0, window - span) + 1):
        # pack > 0 favours the earliest valid offset, so categories sharing a busy first control
        # interleave without leaving holes on it (first fit) instead of spreading the load.
        score = offset_score(board, slots, offset, interval, max_load, peak_load, allow_collision, ramp) + pack * offset
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
    packed: frozenset[str] = frozenset(),
    ramp: tuple[int, ...] = (),
) -> Placement:
    board = Board()
    placed: list[Slot] = []
    for category in order:
        candidate, score = best_placement(
            board, slots_by_category[category], intervals[category], window, max_load, peak_load, allow_collision,
            pack=1.0 if category in packed else 0.0, ramp=ramp,
        )
        if candidate is None or math.isinf(score):
            return Placement(placed, category, 0, 0)
        board.add(candidate)
        placed.extend(candidate)
    over_max = sum(1 for value in board.load.values() if value > max_load)
    collisions = sum(count - 1 for counter in board.first.values() for count in counter.values() if count > 1)
    return Placement(placed, None, over_max, collisions)


def first_control_bound(slots_by_category: dict[str, list[Slot]]) -> int:
    """At most one starter per first control per minute: the busiest first control needs this many minutes."""
    counts = Counter(
        leg_key(slot.entry) for slots in slots_by_category.values() for slot in slots if slot.entry.first_control
    )
    return max(counts.values(), default=1) - 1


PACES = {"compact": 0.5, "spread": 2.0}


def target_for(lanes: int, config: dict) -> float:
    """Average starters per minute per start used to size an automatic window.
    pace "compact" (default): finish early, max_load - 0.5 (5.5 with the usual 6);
    pace "spread": spread the starts more, max_load - 2 (about 4).
    With 3 or more separate starts, which are harder to manage, one less."""
    if "target_load" in config:
        return float(config["target_load"])
    pace = str(config.get("pace", "compact")).lower()
    if pace not in PACES:
        raise RuntimeError(f"Unknown pace {pace!r}: use one of {', '.join(PACES)}")
    max_load = float(config.get("max_load", 6))
    many = lanes >= int(config.get("many_starts", 3))
    return max(1.0, max_load - PACES[pace] - (1.0 if many else 0.0))


def target_load(slots_by_category: dict[str, list[Slot]], config: dict) -> float:
    lanes = {slot.entry.start_lane for slots in slots_by_category.values() for slot in slots}
    return target_for(len(lanes), config)


def auto_window(slots_by_category: dict[str, list[Slot]], config: dict, include_first_controls: bool = True) -> int:
    """Contained start window: long enough for the longest category at its minimum interval, for the
    busiest first control and for the target average load per start."""
    per_lane = Counter(slot.entry.start_lane for slots in slots_by_category.values() for slot in slots)
    total = max(per_lane.values(), default=0)  # the busiest start sets the pace
    target = target_load(slots_by_category, config)
    longest = max(((len(slots) - 1) * interval_for(config, category) for category, slots in slots_by_category.items()), default=0)
    # Several long categories cannot all start in the first minutes while the start ramps up.
    longest += len(config.get("ramp_up", [1, 2, 4]))
    bound = 0
    if include_first_controls and not config.get("allow_first_control_collision"):
        bound = first_control_bound(slots_by_category)
    window = max(longest, bound, math.ceil(total / target) - 1)
    if str(config.get("pace", "compact")).lower() == "spread" and "target_load" not in config:
        # Spread: at least `spread_factor` (default +30%) longer than the compact window, so that small
        # races (whose length is set by the longest category / first control, not by load) spread too.
        compact = auto_window(slots_by_category, {**config, "pace": "compact"}, include_first_controls)
        window = max(window, math.ceil(compact * float(config.get("spread_factor", 1.3))))
    return window


def candidate_orders(slots_by_category: dict[str, list[Slot]], intervals: dict[str, int], seed: int, attempts: int) -> list[list[str]]:
    """Category placement orders to try. The first one (largest category first) is the historical order;
    the others put categories on the busiest first controls / with the longest span first, then
    seeded random variations of that."""
    names = sorted(slots_by_category)
    size = {c: len(slots_by_category[c]) for c in names}
    span = {c: (size[c] - 1) * intervals[c] for c in names}
    first = {c: (leg_key(slots_by_category[c][0].entry) if slots_by_category[c] else "") for c in names}
    pressure = Counter()
    for c in names:
        pressure[first[c]] += size[c]
    orders = [
        sorted(names, key=lambda c: (-size[c], c)),
        # Grouped by first control (busiest first), shortest interval first inside the group, so that
        # categories sharing a first control interleave (two at 2 min fill every minute, three at 3 min...).
        sorted(names, key=lambda c: (-pressure[first[c]], first[c], intervals[c], -size[c], c)),
        sorted(names, key=lambda c: (-pressure[first[c]], -span[c], c)),
        sorted(names, key=lambda c: (-span[c], -size[c], c)),
    ]
    rng = random.Random(seed)
    while len(orders) < attempts:
        noise = {c: rng.random() for c in names}
        orders.append(sorted(names, key=lambda c: (-pressure[first[c]] * (0.5 + noise[c]), -span[c], c)))
    unique: list[list[str]] = []
    for order in orders:
        if order not in unique:
            unique.append(order)
    return unique


def assign_times(slots_by_category: dict[str, list[Slot]], config: dict) -> list[Slot]:
    raw_window = config.get("window_minutes", "auto")
    automatic = str(raw_window).lower() == "auto"
    window = auto_window(slots_by_category, config) if automatic else int(raw_window)
    max_load = int(config.get("max_load", 6))
    peak_load = int(config.get("peak_load", max(8, max_load)))
    allow_collision = bool(config.get("allow_first_control_collision", False))
    intervals = {category: interval_for(config, category) for category in slots_by_category}
    attempts = int(config.get("placement_attempts", 30))
    ramp = tuple(int(value) for value in config.get("ramp_up", [1, 2, 4]))
    orders = candidate_orders(slots_by_category, intervals, int(config.get("random_seed", 1)), attempts)

    fc_count = Counter(
        leg_key(slot.entry) for slots in slots_by_category.values() for slot in slots if slot.entry.first_control
    )

    def busy(window: int) -> frozenset[str]:
        # Categories whose first control is used in more than 60% of the window's minutes.
        return frozenset(
            category
            for category, slots in slots_by_category.items()
            if slots and fc_count[leg_key(slots[0].entry)] > 0.6 * (window + 1)
        )

    mode = {"packed": frozenset()}

    def place(order: list[str], window: int, packed: frozenset[str] | None = None) -> Placement:
        packed = mode["packed"] if packed is None else packed
        return place_all(order, slots_by_category, intervals, window, max_load, peak_load, allow_collision, packed, ramp)

    def first_fit(window: int, preferred: list[str] | None = None) -> tuple[list[str], Placement] | None:
        tried = [preferred] if preferred else []
        everything = frozenset(slots_by_category)
        modes = [mode["packed"]] + [m for m in (frozenset(), busy(window), everything) if m != mode["packed"]]
        for packed in modes:
            for order in tried + [o for o in orders if o != preferred]:
                result = place(order, window, packed)
                if not result.failed:
                    mode["packed"] = packed
                    return order, result
        return None

    # 1. Minimum intervals must fit, trying several category orders. An automatic window grows
    #    (3% steps) until they do; a fixed window that cannot work reports the window that would.
    base_intervals = dict(intervals)
    groups: dict[str, list[str]] = defaultdict(list)
    for category, slots in slots_by_category.items():
        if slots and slots[0].entry.first_control:
            groups[leg_key(slots[0].entry)].append(category)

    def harmonized(window: int, mode: str) -> dict[str, int]:
        """Make intervals of categories sharing a start + first control compatible. Two categories never
        collide when their intervals share a factor (2 and 4, 3 and 6), while 2 and 3 collide every other
        start. mode "even": raise odd intervals to the next even one (3 -> 4) so they fit between the
        2-minute categories; mode "max": give everyone the group's largest interval."""
        result = dict(base_intervals)
        for members in groups.values():
            values = {base_intervals[c] for c in members}
            if len(values) < 2 or all(math.gcd(a, b) > 1 for a in values for b in values):
                continue
            for c in members:
                if mode == "even":
                    target = base_intervals[c] + (base_intervals[c] % 2)
                else:
                    target = max(values)
                if (len(slots_by_category[c]) - 1) * target <= window:
                    result[c] = target
        return result

    # With an automatic window, minutes above max_load (peaks up to peak_load) are only accepted up to
    # `auto_over_max_minutes` (default 0): a slightly longer window is better than a sustained 7-8 per minute.
    over_allowed = int(config.get("auto_over_max_minutes", 0)) if automatic else None

    def acceptable(found: tuple[list[str], Placement] | None) -> bool:
        return found is not None and (over_allowed is None or found[1].over_max <= over_allowed)

    def fit_window(window: int) -> tuple[list[str], Placement] | None:
        intervals.update(base_intervals)
        found = first_fit(window)
        if found is not None and not acceptable(found):
            found = None
        for mode in ("even", "max"):
            if found is not None:
                break
            aligned = harmonized(window, mode)
            if aligned != base_intervals:
                intervals.update(aligned)
                found = first_fit(window)
                if found is not None and not acceptable(found):
                    found = None
                if found is None:
                    intervals.update(base_intervals)
                else:
                    config["_aligned"] = {
                        c: (base_intervals[c], aligned[c], sorted(m for m in groups[leg_key(slots_by_category[c][0].entry)] if m != c))
                        for c in aligned if aligned[c] != base_intervals[c]
                    }
        return found

    # Acceptable length: what entries, load and the longest category need, ignoring first controls.
    # Too few distinct first controls must not make the grid unrealistically long: beyond
    # `max_window_stretch` (default +25%) the script accepts the fewest possible first-control
    # collisions instead, and warns.
    fc_bound = first_control_bound(slots_by_category)
    if automatic:
        acceptable_window = auto_window(slots_by_category, config, include_first_controls=False)
        # Percentages alone are too tight for small races: allow at least +20 minutes of search margin.
        limit = max(
            math.ceil(acceptable_window * float(config.get("max_window_stretch", 1.25))),
            acceptable_window + int(config.get("min_window_margin", 20)),
        )
        # A first-control bound is realistic if it is not far beyond what the whole event would need
        # through a single start (separate starts shorten the window, but not a shared first control).
        all_slots = sum(len(slots) for slots in slots_by_category.values())
        single_start = max(acceptable_window, math.ceil(all_slots / target_load(slots_by_category, config)) - 1)
        realistic = max(
            single_start * float(config.get("first_control_realistic", 1.5)),
            single_start + int(config.get("first_control_margin", 30)),
        )
        if fc_bound <= realistic:
            # The busiest first control is still realistic: prefer a slightly longer grid without collisions.
            limit = max(limit, math.ceil(fc_bound * 1.15))
    else:
        limit = window
    fallback = None

    def grow(start: int, stop: int) -> tuple[int, tuple[list[str], Placement] | None]:
        needed, found = start, None
        while found is None and needed < stop:
            needed = min(stop, math.ceil(needed * 1.03) + 1)
            found = fit_window(needed)
        return needed, found

    found = None if (automatic and window > limit and not allow_collision) else fit_window(window)
    if found is None and automatic and window <= limit:
        window, found = grow(window, limit)
    if found is None and not allow_collision:
        # First-control fallback: same acceptable window, fewest collisions.
        allow_collision = True
        window = limit
        found = fit_window(window)
        if found is None and automatic:
            window, found = grow(window, 24 * 60)
        if found is not None:
            fallback = {"bound": fc_bound, "window": window}
    if found is None:
        needed, hint_found = grow(window, 24 * 60)
        hint = f" about {needed} minutes would be needed" if hint_found else ""
        raise RuntimeError(
            f"Cannot place all categories in window_minutes={window};{hint} — increase the window, "
            "the load limit or the start lanes, or reduce intervals/vacants."
        )
    order, result = found

    # 2. Widen intervals inside the same window ("water filling"): repeatedly give +1 minute to the
    #    category with the smallest interval, keeping the change only if every category still fits,
    #    no minute gets more over max_load and no first-control collision is added.
    caps = {}
    for category in intervals:
        gaps = max(1, len(slots_by_category[category]) - 1)
        caps[category] = max(intervals[category], min(max_interval_for(config, category), window // gaps))
    frozen = {category for category in intervals if intervals[category] >= caps[category]}
    while len(frozen) < len(intervals):
        category = min(
            (c for c in intervals if c not in frozen),
            key=lambda c: (intervals[c], -len(slots_by_category[c]), c),
        )
        intervals[category] += 1
        trial = place(order, window)
        if trial.failed:
            # The current order may simply not suit the new intervals: try the others once.
            alternative = first_fit(window, order)
            if alternative is not None:
                order, trial = alternative
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
    config["_target_load"] = target_load(slots_by_category, config)
    if fallback is not None:
        fallback["collisions"] = result.collisions
        config["_fc_fallback"] = fallback
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
        "start": entry.start_lane,
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
        "start",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def report(rows: list[dict[str, str]], config: dict) -> str:
    assigned = [row for row in rows if row["row_type"] in {"assigned", "vacant"}]
    free = [row for row in rows if row["row_type"] == "free"]
    load = Counter(int(row["minute"]) for row in assigned if row["minute"])
    lane_load = Counter((row.get("start") or "1", int(row["minute"])) for row in assigned if row["minute"])
    lanes = sorted({lane for lane, _ in lane_load})
    first_counts = defaultdict(Counter)
    for row in assigned:
        if row["first_control"]:
            first_counts[int(row["minute"])][(row.get("start") or "1", row["first_control"])] += 1
    collisions = [
        (minute, f"{first} (start {lane})", count)
        for minute, counter in first_counts.items()
        for (lane, first), count in counter.items()
        if count > 1
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
                f"Starts (lanes): {', '.join(lanes)}",
                f"Peak load per start: {max(lane_load.values())}",
                f"Minutes over max_load={config.get('max_load', 6)} (per start): "
                f"{sum(1 for value in lane_load.values() if value > int(config.get('max_load', 6)))}",
                f"Ramp-up at the beginning: {config.get('ramp_up', [1, 2, 4])} max per start in the first minutes",
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
    if config.get("_window_auto"):
        lines.append(
            f"Target average load per start for the automatic window: {config.get('_target_load')} "
            f"(pace: {config.get('pace', 'compact')})"
        )
    fallback = config.get("_fc_fallback")
    if fallback:
        lines.extend(
            [
                "",
                f"WARNING: too few distinct first controls for this window. {len(collisions)} first-control "
                f"collisions were accepted (the fewest found) to keep the grid at {fallback['window']} minutes.",
                f"         A grid with no collisions would need at least {fallback['bound']} minutes "
                "(busiest first control), which is not realistic.",
                "         Options: more distinct first controls (ask the course setter), more separate starts, "
                "a longer window, or accept the collisions listed below.",
                "",
            ]
        )
    lines.extend(
        [
            f"First-control collisions: {len(collisions)}",
            "",
            "Load by minute" + (" (per start: " + " / ".join(lanes) + ")" if len(lanes) > 1 else "") + ":",
        ]
    )
    for minute in sorted(load):
        detail = " (" + " / ".join(str(lane_load[(lane, minute)]) for lane in lanes) + ")" if len(lanes) > 1 else ""
        lines.append(f"- {minute}: {load[minute]}{detail}")
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
        moved = config.get("_moved", {}).get(category, 0)
        if moved:
            notes.append(f"{moved} athletes moved to a neighbouring strength group/block to separate clubs")
        if not config.get("_club_separation", {}).get(category, True):
            notes.append("club separation off")
        repeated = config.get("_repeated_pairs", {}).get(category)
        if config.get("_previous_pairs") and repeated is not None:
            notes.append(f"{repeated} consecutive pairs repeated from previous races")
        if minimum and base < minimum:
            notes.append(f"raised from {base} to ruleset minimum {minimum}")
        aligned = config.get("_aligned", {}).get(category)
        if aligned:
            notes.append(
                f"interval raised from {aligned[0]} to {aligned[1]} to match the categories sharing its start and first "
                f"control ({', '.join(aligned[2])}): 2 and 3 minutes on the same first control collide every other start"
            )
        elif interval > max(base, minimum):
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
                "load target 4-6 per minute per start, never above 8.",
            ]
        )
        peak = Counter(
            (row.get("start") or "1", int(row["minute"])) for rows_ in by_category.values() for row in rows_ if row["minute"]
        )
        if peak and max(peak.values()) > 8:
            warnings.append(f"WARNING: peak load {max(peak.values())} exceeds the FISO limit of 8 per minute per start.")
    for category, (count, span, load_window) in sorted(config.get("_relaxed_masters", {}).items()):
        warnings.append(
            f"WARNING: {category} has {count} athletes: at the FISO master minimum of 3 minutes it alone would take "
            f"{span} minutes, while entries and load need about {load_window}. Proposed minimum 2 minutes for this "
            "category only; alternatives: split it over two starts, or accept a longer grid (set categories."
            f"{category}.min_interval to 3)."
        )
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
        config["max_load"] = min(int(config.get("max_load", 6)), 8)
        config["peak_load"] = min(int(config.get("peak_load", 8)), 8)
    entries = load_entries(args.athletes, config)
    relax_large_masters(entries, config)
    slots_by_category = build_category_slots(entries, config)
    assigned_slots = assign_times(slots_by_category, config)
    rows = build_rows(entries, assigned_slots, config)
    write_csv(args.out, rows)
    args.report.write_text(report(rows, config), encoding="utf-8")
    print(f"rows={len(rows)} out={args.out} report={args.report}")


if __name__ == "__main__":
    main()
