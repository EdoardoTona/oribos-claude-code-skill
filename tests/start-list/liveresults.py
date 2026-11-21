"""LiveResults.it (app.liveresults.it) races as test cases for build_start_list.py: list, download (cached),
classify (which races make sense for a start-list benchmark) and convert to the script's inputs."""
from __future__ import annotations

import csv
import json
import re
import statistics
import urllib.request
from collections import Counter
from pathlib import Path

API = "https://app.liveresults.it"
MIN_GRID_ATHLETES = 30


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def list_races(years: list[str]) -> list[dict]:
    """All races of the events held in the given years (newest first)."""
    races, offset = [], 0
    while True:
        events = json.loads(fetch(f"{API}/api/events?limit=100&offset={offset}"))
        if not events:
            break
        for event in events:
            if event["from"][:4] in years:
                for race in event["races"]:
                    races.append({
                        "id": f"{event['slug']}__{race['slug']}", "event": event["name"], "event_slug": event["slug"],
                        "race": race.get("name") or race["slug"], "date": (race.get("start") or event["from"])[:10],
                        "url": API + race.get("url", f"/data/{event['slug']}/{race['slug']}.json"),
                    })
        if min(e["from"][:4] for e in events) < min(years):
            break
        offset += 100
    return races


def load(race: dict, cache: Path) -> dict | None:
    """Race data from the cache, downloaded when missing; None when LiveResults has no data for it."""
    path = cache / "races" / f"{race['id']}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_bytes(fetch(race["url"]))
        except Exception:  # noqa: BLE001 - unpublished race: keep a marker
            path.write_bytes(b"")
    try:
        return json.loads(path.read_bytes().decode("utf-8-sig"))
    except ValueError:
        return None


def is_free(cls: dict) -> bool:
    return bool(cls.get("freestart")) or bool(cls.get("ludica"))  # promotional (ludica) classes have no grid


def classify(race: dict, data: dict | None) -> tuple[str | None, str]:
    """(race_type, "") for a race to benchmark, or (None, reason) for one to leave out."""
    name = f"{race['event']} {race['race']}".lower()
    if data is None:
        return None, "no data published"
    info = data.get("race", {})
    if info.get("type") == "Staffetta" or info.get("gridmode") == "Lancio" or re.search(r"relay|staffett|štafet", name):
        return None, "relay / mass start"
    if str(info.get("onemanrelay")).lower() == "true" or re.search(r"knock ?out final|ko final", name):
        return None, "knock-out finals (heats)"
    if re.search(r"mtbo|mtb-o|ski-?o|trail-?o|\bwinter\b", name):
        return None, "not foot orienteering (MTBO, ski-O, trail-O)"
    if re.search(r"labirint|maze|model|training|promozional|scuol|studentesc", name):
        return None, "promotional / model / training"
    if info.get("type") not in (None, "Normale"):
        return None, f"race type {info.get('type')}"
    classes = {c["name"]: c for c in data.get("classes", [])}
    grid = [x for x in data.get("competitors", []) if x.get("class") in classes and not is_free(classes[x["class"]])]
    if len(grid) < MIN_GRID_ATHLETES:
        return None, f"fewer than {MIN_GRID_ATHLETES} athletes on the grid"
    # Race type from the race name, else from the event name when it names a single type.
    patterns = {"sprint": r"sprint|knock ?out|\bko\b", "long": r"\blong\b|\blunga\b", "middle": r"middle|\bmedia\b"}
    for text in (race["race"].lower(), race["event"].lower()):
        found = [kind for kind, pattern in patterns.items() if re.search(pattern, text)]
        if len(found) == 1:
            return found[0], ""
    # No name hint: the intervals actually used tell sprint (1 minute) from the others; long by course length.
    gaps = []
    by_class: dict[str, list[int]] = {}
    for x in grid:
        if x.get("start"):
            by_class.setdefault(x["class"], []).append(x["start"] // 60)
    for minutes in by_class.values():
        minutes.sort()
        steps = [b - a for a, b in zip(minutes, minutes[1:]) if b > a]
        if steps:
            gaps.append(Counter(steps).most_common(1)[0][0])
    if gaps and statistics.median(gaps) <= 1:
        return "sprint", ""
    longest = max((c.get("length") or 0 for c in data.get("courses", [])), default=0)
    return ("long" if longest >= 9500 else "middle"), ""


def convert(data: dict, race_type: str, out_dir: Path, seed: int = 2027) -> dict:
    """Write athletes.csv and config.json for the script; return the real grid's figures."""
    out_dir.mkdir(parents=True, exist_ok=True)
    classes = {c["name"]: c for c in data["classes"]}
    courses = {c["name"]: c for c in data.get("courses", [])}

    def first_control(course: str) -> str:
        controls = courses.get(course, {}).get("controls", [])
        return str(controls[0]["code"]) if controls else ""

    rows, real, seen = [], [], set()
    for x in data["competitors"]:
        cls = classes.get(x.get("class"))
        if cls is None:
            continue
        course = x.get("courses") or (cls["courses"][0] if cls.get("courses") else "")
        lane = str(cls.get("start", 1))
        athlete_id = str(x["id"]) if x.get("id") and str(x["id"]) not in seen else f"row-{len(rows) + 1}"
        seen.add(athlete_id)
        rows.append({
            "id": athlete_id, "last_name": x.get("surname") or "", "first_name": x.get("name") or "",
            "club": f"{x.get('clubCountry', '')}-{x.get('clubId', '')}", "category": x["class"],
            "course": course, "first_control": first_control(course), "start": lane,
        })
        if not is_free(cls) and x.get("start"):
            real.append((x["start"] // 60, lane, first_control(course)))
    with (out_dir / "athletes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    config = {"race_type": race_type, "random_seed": seed, "first_start": "10:00:00",
              "free_categories": sorted(n for n, c in classes.items() if is_free(c))}
    (out_dir / "config.json").write_text(json.dumps(config, indent=1), encoding="utf-8")

    figures = {"grid_athletes": sum(1 for r in rows if r["category"] not in config["free_categories"]),
               "starts": len({r["start"] for r in rows if r["category"] not in config["free_categories"]})}
    if real:
        # The published grid: the largest block of starts without gaps over 10 minutes (late changes excluded).
        minutes = sorted(m for m, _, _ in real)
        blocks, current = [], [minutes[0]]
        for m in minutes[1:]:
            if m - current[-1] > 10:
                blocks.append(current)
                current = []
            current.append(m)
        blocks.append(current)
        main = max(blocks, key=len)
        inside = [r for r in real if main[0] <= r[0] <= main[-1]]
        figures["real_window"] = main[-1] - main[0]
        figures["real_collisions"] = sum(n - 1 for n in Counter(r for r in inside if r[2]).values() if n > 1)
    return figures
