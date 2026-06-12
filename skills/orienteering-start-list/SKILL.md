---
name: orienteering-start-list
description: Create fair orienteering start list proposals as CSV files from athlete, category, ranking, request, and course-first-control data. Use when calculating start grids for sprint, middle, long, WRE, national-list, club, or recreational orienteering races; balance start intervals, first-control conflicts, start load, vacants, free-start categories, ranking inversion/randomization, club separation, and soft timing requests. This skill does not write back to Oribos or other event files; it prepares reviewable CSV/report outputs.
---

# Orienteering Start Lists

## Core Workflow

1. Gather the race facts before calculating:
   - Race type: sprint, middle, long, or custom interval.
   - First start time and desired total window. Scale the window with entries: 80-90 minutes is reasonable for a few hundred middle-distance runners; 800 runners may need 150-220 minutes or multiple start lanes.
   - Start interval: sprint usually 1 minute, middle usually 2 minutes, long 2 or 3 minutes (often the same as middle; confirm with the organizer). Oribos also supports 30-second intervals.
   - Maximum start load per minute: prefer fewer; 6 average/normal maximum is manageable, short peaks of 7-8 (occasionally 9 in large events) may be acceptable, higher usually requires more physical start lanes/corridors.
   - Course for each category and the first control for each course. Importing courses into event software is not required, but first controls are essential for avoiding conflicts.
   - Free-start categories. Always ask; common examples are Beginners, M/W10, M/W12, Direct.
   - Vacant policy. Ask case by case for free-start categories. For grid categories, default to 2 vacants unless told otherwise (real events use 1-3, with 2 the most common).
   - Ranking/list-base policy for elite or seeded classes: WRE, Italian list, national list, custom points/rank. Invert rankings by default when requested.
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
   - Report start load per minute, peak load, window, request satisfaction, club-consecutive issues, and first-control collisions.

## Seeding Rules

- Ranking inversion means weaker/unranked runners start earlier and stronger runners later.
- If the ranking source uses positions where `1` is best, sort by descending position for start order; missing rank behaves like zero points/unranked and starts among the weakest.
- If the ranking source uses points where higher is better, sort by ascending points for start order.
- If both position and points exist, position is normally primary.
- For multi-race weekends, seeded classes are randomized within strength blocks (commonly 5 or 10) to avoid identical grids across races while keeping the ranking ladder; do not fully shuffle a seeded class. Unseeded classes are commonly fully reshuffled each race.
- Put vacants at the end of the category unless the organizer explicitly asks otherwise; Oribos-generated grids always place them at the end.

## Constraint Priority

Use this priority unless the organizer changes it:

1. Safety/operation: manageable start load, no impossible physical start situation.
2. First-control conflicts: avoid same first control at the same minute.
3. Fixed race rules: interval, free-start categories, seeded category requirements.
4. Strong timing requests: childcare, transport, organiser-approved exact needs.
5. Category window and total race window.
6. Separate same-club runners within category when possible.
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
- Keep generated CSV/report filenames stable and stage/race-specific when there are multiple races.
- The bundled script works in whole minutes. For 30-second intervals, treat one slot as 30 seconds (halve the time unit) and convert times when writing the final CSV.
