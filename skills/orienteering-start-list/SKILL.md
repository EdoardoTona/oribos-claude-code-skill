---
name: orienteering-start-list
description: Create fair orienteering start list proposals as CSV files from athlete, category, ranking, request, and course-first-control data. Use when calculating start grids for sprint, middle, long, WRE, national-list, club, or recreational orienteering races; balance start intervals, first-control conflicts, start load, vacants, free-start categories, ranking inversion/randomization, club separation, and soft timing requests. This skill does not write back to Oribos or other event files; it prepares reviewable CSV/report outputs.
---

# Orienteering Start Lists

## Core Workflow

1. Gather the race facts before calculating:
   - Race type: sprint, middle, long, or custom interval.
   - WRE: if the race is a WRE, set `"wre": true` (the Elite categories keep the IOF intervals; see `references/rules-iof.md`). For IOF championships or events abroad, ask which rules apply.
   - Previous races of the same weekend/multi-day event: their proposal CSVs, to avoid repeating consecutive pairs.
   - Pace: ask whether the organizer prefers to finish early (`"pace": "compact"`, default, about 5.5 starters per minute per start) or to spread the starts more (`"pace": "spread"`, about 4 per minute and at least 30% longer, with wider intervals). A maximum window (`window_minutes`) always wins over the pace.
   - First start time and desired total window. Scale the window with entries: 80-90 minutes is reasonable for a few hundred middle-distance runners; 800 runners may need 150-220 minutes or multiple start lanes.
   - Start interval: the script chooses it (see Default Rules below): normal 1 minute in sprint, 2 in middle; at least 3 for masters outside sprint and for every category in long races; wider when the window allows it. Ask whether the organizer wants some categories fixed instead. Oribos also supports 30-second intervals.
   - Maximum start load per minute, per physical start: 4-6 normally, 6 as the usual maximum, short peaks up to 8, never more than 8; more requires more physical start lanes/corridors. Ask which start each category uses when there is more than one.
   - Course for each category and the first control for each course. Importing courses into event software is not required, but first controls are essential for avoiding conflicts.
   - Free-start categories. Always ask; common examples are Beginners, M/W10, M/W12, Direct.
   - Sensitive categories, which start at the beginning of the grid: by default the youngest (up to 14 included) and the supermasters (70 and over). Ask whether to add or remove any.
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
   - No two runners from the same start with the same first control start at the same minute. Collisions are never accepted without the organizer's explicit approval (`allow_first_control_collision`); when the script stops on them, explain the options and ask. Always tell the organizer how many collisions a proposal has.
   - Interval is constant within each category/course group unless custom rules say otherwise.
   - Vacants appear only where requested/allowed, normally at the category end (Oribos itself only places vacants at the end of a category; use other placements only on explicit request).
   - Free-start categories are clearly marked and normally have no assigned time.
   - Ranking order is deterministic unless random block seeding was requested.
   - Any requested randomization uses a reported seed and a real shuffle within the requested scope. Do not call a club-balanced or bib-sorted deterministic order "random".
   - In multi-day events, no category should have the same start order in two stages unless the organizer explicitly asks for identical grids or a fixed ranking order makes it unavoidable; report any repeated full order or repeated tail block.
   - Report start load per minute, peak load, window, request satisfaction, club-consecutive issues, and first-control collisions.

## Default Rules

Read `references/baseline-rules.md` before building a proposal. In short:

- Load: contained window, 4-6 starters per minute per physical start, never more than 8 (separate starts each have that throughput; read each category's start from the event data). Pace `compact` (default, about 5.5 per minute per start) or `spread` (about 4, at least 30% longer, wider intervals); one lower with 3 or more starts. The organizer may raise `max_load` up to 8 to shorten a long grid. Each start ramps up gradually (1, 2, 4, then normal pace).
- Intervals: masters (35+) at least 2 minutes in sprint and 3 in other races; in long races every category at least 3. These minimums are a strong recommendation, given up (back to the normal interval, that category only) only with too many entries: categories of 50+ athletes, or up to 3 categories that would make the grid more than 10 minutes longer. The report warns every time.
- Every category gets the widest constant interval the window allows (up to 7 minutes, 4 in sprint and for sensitive categories), unless the organizer says otherwise; the total window does not grow for it. Elite and Junior (up to 20 included) stay at 1 minute in sprint; in WRE races (`"wre": true`) the Elite categories keep the IOF intervals (sprint 1, middle 2, long 3).
- Categories sharing a start and first control need compatible intervals (2 and 4 yes, 2 and 3 no); different starts to the same first control are different legs and never collide.
- Sensitive categories (youngest up to 14 included, 70 and over) start at the beginning of the grid whenever possible, before widening, and are widened to at most 4 minutes so they also finish early; never at the cost of a longer grid. The report lists their first starts and notes the ones that had to start later.
- First-control collisions need the organizer's approval. Too few distinct first controls: the script stops, reports the busiest first control and the fewest collisions found; the organizer decides (more first controls, more starts, longer window, or approve the collisions).
- Ranked categories (Coppa Italia, lista base, WRE): randomize within about 3 strength groups; Elite categories within blocks of 5 or 10 so the strongest stay at the end.
- No same-club athletes one after the other, except in very small categories; random categories are repaired with random swaps (no club favoured at the start or end), seeded ones within the strength group/block, otherwise moving an athlete to the adjacent group/block.
- Vacants: 2 per grid category, 1 in small categories (fewer than 10 athletes).
- Grid criteria from FISO RTF 6.10.2: constant interval inside each category, categories sharing a course may alternate, categories starting together need different first controls, vacants only at the head or tail; if not all can be met the Technical Delegate decides. IOF rules and the comparison with the defaults are in `references/rules-iof.md`.
- Every category may have its own course: more distinct first controls to check, nothing else changes for the start list.

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
2. First-control conflicts: no same start and first control at the same minute without the organizer's approval.
3. Fixed race rules: interval, free-start categories, seeded category requirements.
4. Strong timing requests: childcare, transport, organiser-approved exact needs.
5. Category window and total race window.
6. Sensitive categories (youngest up to 14, 70 and over) at the beginning of the grid.
7. Separate same-club runners within category when possible (inside the shuffle scope for seeded categories; skipped for categories with fewer than 4 athletes).
8. Soft early/late preferences, wider intervals and aesthetic balance.

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
- The bundled script works in whole minutes. For 30-second intervals, treat one slot as 30 seconds (halve the time unit) and convert times when writing the final CSV; every minute-based option must then be expressed in slots too: intervals, their minimums/maximums and windows doubled, loads per minute (`max_load`, `peak_load`, `ramp_up`) halved.
