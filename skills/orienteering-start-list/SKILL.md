---
name: orienteering-start-list
description: Create fair orienteering start list proposals as CSV files from athlete, category, ranking, request, and course-first-control data. Use when calculating start grids for sprint, middle, long, WRE, national-list, club, or recreational orienteering races; balance start intervals, first-control conflicts, start load, vacants, free-start categories, ranking inversion/randomization, club separation, and soft timing requests. This skill does not write back to Oribos or other event files; it prepares reviewable CSV/report outputs.
---

# Orienteering Start Lists

## Core Workflow

1. Gather the race facts before calculating:
   - Race type: sprint, middle, long, or custom interval.
   - Country/ruleset: for Italian (FISO) events from 2027, read `references/fiso-2027.md` and set `"ruleset": "fiso-2027"` — masters 35+ need at least 2 minutes (sprint) / 3 minutes (other races), non-sprint categories are widened up to 7 minutes when the window allows, and ranked categories are randomized by strength groups.
   - Previous races of the same weekend/multi-day event: their proposal CSVs, to avoid repeating consecutive pairs.
   - First start time and desired total window. Scale the window with entries: 80-90 minutes is reasonable for a few hundred middle-distance runners; 800 runners may need 150-220 minutes or multiple start lanes.
   - Start interval: sprint usually 1 minute, middle usually 2 minutes, long 2 or 3 minutes (often the same as middle; confirm with the organizer). Oribos also supports 30-second intervals.
   - Maximum start load per minute, per physical start: prefer fewer; 6 average/normal maximum is manageable, short peaks of 7-8 (occasionally 9 in large events) may be acceptable, higher usually requires more physical start lanes/corridors. Ask which start each category uses when there is more than one.
   - Course for each category and the first control for each course. Importing courses into event software is not required, but first controls are essential for avoiding conflicts.
   - Free-start categories. Always ask; common examples are Beginners, M/W10, M/W12, Direct.
   - Vacant policy. Ask case by case for free-start categories. For grid categories, default to 2 vacants unless told otherwise (real events use 1-3, with 2 the most common); small categories (fewer than 10 athletes) get 1.
   - Ranking/list-base policy for elite or seeded classes: WRE, Italian list, national list, custom points/rank. Invert rankings by default when requested.
   - Multi-day policy: decide how each stage differs from the others. If the organizer says "random", use actual reproducible randomization, not a deterministic sort that only looks random.
   - Timing requests: early/late/exact, pairs to separate or keep close, family/childcare reasons that should increase weight.

2. Normalize inputs into tables:
   - Athletes: id, bib, name, club, category, course, optional SI/card, optional rank position/points.
   - Categories: category, course, free-start flag, interval override, vacant count, vacant placement.
   - Courses: course, first control.
   - Requests: athlete id/name, requested window or relation, weight/reason.

3. Build the proposal, not the final race file:
   - Produce a CSV first so the organizer can review.
   - Do not write `.og4`, `.oe`, Eventor, MeOS, or other event files from this skill.
   - Preserve enough columns to integrate later: athlete id, bib, name, club, category, course, first control, relative time, absolute time, category position, vacant flag, request notes.

4. Validate hard constraints before presenting:
   - No two runners with the same first control start at the same minute unless the organizer explicitly accepts it.
   - Interval is constant within each category/course group unless custom rules say otherwise.
   - Vacants appear only where requested/allowed, normally at the category end (Oribos itself only places vacants at the end of a category; use other placements only on explicit request).
   - Free-start categories are clearly marked and normally have no assigned time.
   - Ranking order is deterministic unless random block seeding was requested.
   - Any requested randomization uses a reported seed and a real shuffle within the requested scope. Do not call a club-balanced or bib-sorted deterministic order "random".
   - In multi-day events, no category should have the same start order in two stages unless the organizer explicitly asks for identical grids or a fixed ranking order makes it unavoidable; report any repeated full order or repeated tail block.
   - Report start load per minute, peak load, window, request satisfaction, club-consecutive issues, and first-control collisions.

## Italy (FISO) From 2027

Italian events from 2027 follow extra FISO guidelines; read `references/fiso-2027.md`. In short:

- Same limits as before: contained window, 4-6 starters per minute, never more than 8 — per physical start (separate starts each have that throughput; read each category's start from the event data). 5 or 6 per minute is fine for every race type; with 3 or more separate starts aim a bit lower (4-5 per start), but 6 with short peaks up to 8 is always acceptable when the window must stay within a maximum length. The organizer may raise the limit (up to 8) to shorten a long grid. Ramp up each start gradually (1, 2, 4, then normal pace) in every race.
- Too few distinct first controls must not produce an unrealistic grid: the script keeps an acceptable length, accepts the fewest first-control collisions and warns; tell the organizer and let them decide (more first controls, more starts, longer window, or accept).
- Master categories (35+): minimum interval 2 minutes in sprint, 3 minutes in other races.
- In non-sprint races every category gets the widest interval the window allows (4-7 minutes are fine), constant within the category; the total window does not grow. The script picks the intervals itself, sharing the room fairly between categories.
- No same-club athletes one after the other, except in very small categories; in seeded categories first within the same strength group/block, otherwise moving an athlete to the adjacent group/block.
- Vacants: 2 per grid category, 1 in small categories (fewer than 10 athletes).
- Ranked categories (Coppa Italia, lista base): randomize within about 3 strength groups; elite categories within blocks of 5 or 10 so the strongest stay at the end.
- Every category may have its own course: more distinct first controls to check, nothing else changes for the start list.

These rules are Italy-specific; do not apply them to other countries or IOF/WRE events unless asked.

## Seeding Rules

- Ranking inversion means weaker/unranked runners start earlier and stronger runners later.
- If the ranking source uses positions where `1` is best, sort by descending position for start order; missing rank behaves like zero points/unranked and starts among the weakest.
- If the ranking source uses points where higher is better, sort by ascending points for start order.
- If both position and points exist, position is normally primary.
- For multi-race weekends, seeded classes are randomized within strength blocks (commonly 5 or 10) to avoid identical grids across races while keeping the ranking ladder; do not fully shuffle a seeded class. Unseeded classes are commonly fully reshuffled each race.
- In weekends with two races and multi-day events, avoid repeating neighbours: two athletes who started consecutively in a previous race should not be consecutive again in the same category. Pass the previous proposals with `previous_start_lists`; the script swaps athletes only inside their shuffle scope and reports any unavoidable repeats.
- In multi-day events, use different seeds per stage/race and verify cross-stage uniqueness after building proposals. Compare each category's common athletes between stages; if the full order or the last meaningful block (for example the final 5 starters) repeats, reshuffle unless this was explicitly requested.
- Put vacants at the end of the category unless the organizer explicitly asks otherwise; Oribos-generated grids always place them at the end.

## Constraint Priority

Use this priority unless the organizer changes it:

1. Safety/operation: manageable start load, no impossible physical start situation.
2. First-control conflicts: avoid same first control at the same minute.
3. Fixed race rules: interval, free-start categories, seeded category requirements.
4. Strong timing requests: childcare, transport, organiser-approved exact needs.
5. Category window and total race window.
6. Separate same-club runners within category when possible (inside the shuffle scope for seeded categories; skipped for categories with fewer than 4 athletes).
7. Soft early/late preferences and aesthetic balance.

If the constraints do not fit, explain the tradeoff and adjust the window, load limit, intervals, or number of start lanes rather than silently breaking hard constraints.

## Script

Use `scripts/build_start_list.py` as a generic starting point when the input can be represented as CSV plus JSON config. It is intentionally format-neutral and writes only proposal files.

Example:

```bash
python3 scripts/build_start_list.py \
  --athletes athletes.csv \
  --config startlist_config.json \
  --out startlist_proposal.csv \
  --report startlist_report.txt
```

Read `references/input-schema.md` before using the script or adapting it to a specific event export.

## Practical Notes

- Keep free-start rows in the CSV, but mark them as `free` and leave relative/assigned times empty or `00:00:00` according to the organizer's review preference.
- A single runner can be placed outside the main block of their category when a strong timing request justifies it; report this explicitly.
- When using random seeding blocks, set and report a seed so the proposal is reproducible.
- When using randomness for unseeded categories, shuffle competitors with a seed before applying club-separation heuristics, and report the seed. Sorting by bib/name/club alone is not random.
- Keep generated CSV/report filenames stable and stage/race-specific when there are multiple races.
- The bundled script works in whole minutes. For 30-second intervals, treat one slot as 30 seconds (halve the time unit) and convert times when writing the final CSV.
