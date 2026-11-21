# Default Start List Rules

These are the rules the skill and `scripts/build_start_list.py` apply by default, for every start list. For WRE races set `"wre": true`: the Elite categories then follow the IOF intervals (see `rules-iof.md`); everything else stays as below. For IOF championships or events abroad, ask the organizer which rules apply: the options listed here can switch off the recommended minimums and the widening.

## The Rules

1. **Start load.** The total start window must stay contained: 4-6 starters per minute **per physical start**, never more than 8. Events with separate starts (start 1, start 2, ...) have that throughput on each of them.
   - The organizer chooses the pace: finish early (`"pace": "compact"`, default: about 5.5 starters per minute per start on average) or spread the starts (`"pace": "spread"`: about 4 per minute and at least 30% longer, the extra room goes into wider intervals). With 3 or more separate starts both targets are one lower (4.5 and 3). A maximum window (`window_minutes`) always wins over the pace.
   - The organizer can raise the limit up to 8 (`"max_load": 8`) to shorten a long grid (e.g. a large sprint). Short peaks up to 8 are acceptable only with a fixed `window_minutes`; an automatic window grows a little instead.
   - Each start ramps up gradually: 1 starter in the first minute, 2 in the second, 4 in the third, then normal pace, so the start crew can settle in (`ramp_up`).
2. **Intervals.**
   - Normal interval: 1 minute in sprint, 2 in middle and long (`interval_minutes` overrides it).
   - **Recommended minimum** (a strong recommendation, not a hard limit): master categories (35+: M35, W35, M40 ... W75 and above) at least **2 minutes in sprint and 3 in the other races**; in **long** races **every category** at least **3 minutes**. It is given up, back to the normal interval and for that category only, only when there are too many entries (see "Too Many Entries" below).
   - **Wider intervals by default:** every category gets the widest constant interval the window allows, up to 7 minutes (4 in sprint and for sensitive categories, see rule 8), unless the organizer says otherwise (`"widen_intervals": false`, or `max_interval`). Smaller categories naturally get the widest gaps. Widening never makes the total window longer.
   - **Fixed intervals:** Elite and Junior categories (Junior = up to 20 years included: M10, M 13/14 ... W 19/20) stay at **1 minute in sprint**. In **WRE** races the Elite categories follow the IOF rules in every race: sprint 1, middle 2, long 3. An explicit `categories.<name>.interval` is exact and never changed.
   - The interval is **constant within each category**; it can differ between categories.
3. **Different courses for all categories.** Course setters are asked to give every category its own course. Courses arrive already made: this only means more distinct courses and first controls to check.
4. **Seeding by strength groups** using a ranking (Coppa Italia, lista base/ranking list, WRE, or another list the organizer names):
   - Default: about **three strength groups** (weakest/unranked first, strongest last), shuffled within each group.
   - **Elite categories:** three groups are too coarse (the strongest athlete must not start 51st out of 75). Shuffle in **blocks of 5 or 10** from the end of the category, so the strongest runners stay in the final block. Elite categories are filled according to the lista base when entries are many (FISO RTF).
   - Unranked athletes count as weakest and fall in the first group.
   - Report the seed and use a different seed per stage in multi-day events.
5. **No same-club athletes one after the other** in the same category, except in very small categories (fewer than 4 athletes) or when one club has more than half of the category. In random categories the order is repaired with random swaps, so no club is favoured for the first or last positions. In seeded categories this is first attempted inside each strength group/block; if that is not enough, an athlete may move to the **adjacent** group/block (never further): a small seeding change is preferred to two same-club athletes in a row.
6. **Vacants:** 2 per grid category, 1 in small categories (fewer than 10 athletes), at the end of the category.
7. **First-control collisions** (same start, same first control, same minute) are **never accepted without the organizer's approval**. Starters from different starts going to the same first control run different legs: not a collision.
8. **Sensitive categories start at the beginning** of the grid whenever possible: the youngest (up to 14 years included: M10, W12, M 13/14) and the supermasters (70 and over: M70, W75, M80...). Elite categories never are. It never makes the grid longer: when a shared first control or the load does not allow it, a sensitive category starts later and the report says so. It comes before widening: an interval is not widened if that would make a sensitive category start later, and sensitive categories themselves are widened to at most 4 minutes between starters, so the whole category also finishes early.
9. **Grid criteria of the national regulation** (FISO RTF 6.10.2, foot orienteering):
   - the same interval between consecutive starters inside each category;
   - categories sharing a course may start alternately, still keeping their interval;
   - categories starting at the same time must have different first controls;
   - vacant positions at the head or at the tail of the grid, not in the middle.

   If not all criteria can be respected, the Technical Delegate (DT) decides with the race director. The grid is prepared by the race director with the DT's collaboration/approval.

## How The Script Applies Them

1. **Window.** `window_minutes` if given; otherwise it is computed: long enough for the longest category at its minimum interval, for the busiest first control (one starter per minute per first control and start) and for the pace (`target_load` starters per minute on average at the busiest start). Several category orders are tried (`placement_attempts`, default 30), each category placed in turn where it fits best; if none fits, a local search (`repair_moves`, `repair_restarts`) moves the categories involved in a conflict one at a time, each to the offset and interval (its minimum up to +2, within its limit) that leaves the fewest overloaded minutes and first-control collisions, with minutes that stay in conflict weighing more and more, first with the sensitive categories held in the first quarter of the grid. If that fails too, the automatic window grows in 3% steps and is then refined with a binary search. At 5 Days of Italy 2025 (850-900 athletes on one start) it reached the target pace in three stages where the category-by-category placement needed 6-20 minutes more.
2. **Too few first controls.** A grid without collisions is searched up to an acceptable length (`max_window_stretch`, default +25% over what entries and load need, at least +20 minutes; up to 15% beyond the busiest first control when that is still realistic, i.e. within `first_control_realistic` = +50%, at least +30 minutes). If there is none, or a fixed `window_minutes` cannot be met without collisions, the script **stops** and prints the busiest first control, the minimum length of a collision-free grid and how many collisions the fewest-collision grid would have. Tell the organizer and let them decide: more first controls (ask the course setter), more starts, a longer window, or approve the collisions (`"allow_first_control_collision": true`). With the approval the script still prefers a collision-free grid; when it has to accept collisions it uses the fewest it finds and the report warns and lists every one of them. Example: Begun Cup 2025 middle day 1 (628 athletes; 209 starters, vacants included, on the busiest first control): a collision-free grid needs at least 208 minutes; with the approval 157 minutes and 51 collisions (real grid: 161 minutes, 168 collisions).
3. **Too many entries: the recommended minimum is given up** (thresholds found empirically on past Italian races, app.liveresults.it):
   - **Large categories:** a category with 50 or more athletes (`large_category`) whose span at the recommended minimum alone would make the grid more than `compact_min_saving` (10) minutes longer than the rest needs (or would not fit a fixed `window_minutes`) gets the normal interval, with a WARNING (alternatives: split it over two starts, or set `categories.<name>.min_interval` to the recommended value and accept a longer grid). Example: 5 Days of Italy 2024 stage 1, M55 with 63 athletes: 192 minutes at 3 minutes vs about 150 needed by the rest of the grid; M50, M60 and M65 (56-62 athletes) likewise, W50 (52 athletes) would save only 9 minutes and keeps 3.
   - **A few overflowing categories:** when the automatic grid has to grow beyond what entries and load need, the script finds which categories do not fit. If only a few do (`compact_max_categories`, default 3) and they are held at a recommended minimum, they alone go back to the normal interval when that makes the grid more than `compact_min_saving` (10) minutes shorter; for a smaller saving the larger interval is kept. The report says which categories and how to undo it. If many categories overflow, or the overflow comes from how several categories share first controls, the longer grid is kept and the report explains why. Examples: 5 Days of Italy 2024 stage 1, M45 at 2 minutes: 162 instead of 176 minutes; Venezia in notturna 2026, W35 and W45 at 2 minutes would give 114 instead of 124 minutes, only 10 minutes less: they keep 3 minutes.
4. **Widening.** Every category starts at its minimum interval. Then, one minute at a time, the category with the smallest interval is widened (ties: the larger category first) and all categories are placed again (on a grid found by the local search, that category alone); the change is kept only if everything still fits the window, no more minutes go over `max_load` and no first-control collision appears. This shares the available room fairly instead of giving it to whichever category is placed first.
5. **Shared first controls need compatible intervals.** Two intervals are compatible when they share a factor (2 and 4, 3 and 6), not when they do not: 2 and 3 collide every other start, so while a 2-minute category is starting a 3-minute one cannot start on that control. When the grid does not fit, the script first raises odd intervals to the next even one (3 → 4, between the 2-minute categories), then tries giving the group its largest interval, then the largest rounded up to even (2 and 3 → 4: four categories fill the four minutes of each cycle), and only then lengthens the window; the report says which categories were changed and why. Example: Finali Coppa Italia 2026 middle, M Elite and W Elite raised from 2 to 3 minutes to share their first controls with 3-minute master categories.
6. **Same-club separation** as in rule 5: random categories are repaired by random local search (no greedy "largest club first" order); seeded categories swap inside their group/block, then move to the adjacent one only for the cases left (`club_move_to_neighbour_group`; the report counts moved athletes). Same-club separation has priority over varying neighbours between races.
7. **Sensitive categories** (rule 8; `categories.<name>.sensitive` overrides the detection, `sensitive_early: false` switches the rule off): the category orders tried first place them before the others, and every minute their first start is delayed costs in the placement (`sensitive_weight`). Once the window is fixed, every order is tried and the one that starts them earliest is kept (with no more minutes over `max_load` and no more collisions); widening steps that would delay them are rejected. The report lists their first-start minutes, with a NOTE for those that could not start in the first quarter of the grid. Examples: 5 Days of Italy 2024 stage 1, all 8 sensitive categories start within the first 3 minutes (without the rule: up to minute 130); Finali Coppa Italia 2026 middle, within minute 38 (without: 110); Venezia in notturna 2026, W 13/14 still starts at minute 67, because its first control is shared by 103 athletes in a 114-minute grid.
8. **Seeding.** Ranked categories (those with `rank_mode`, `invert_ranking`, `random_block` or `random_groups` in their config) use `random_block` or `random_groups` if given; otherwise Elite categories (the same detection as for intervals: `M Elite`, `WE`, `M21E`, or `categories.<name>.elite`) get blocks of `elite_random_block` (5), all other ranked categories `default_random_groups` (3) strength groups.

Example:

```json
{
  "race_type": "middle",
  "first_start": "10:00:00",
  "random_seed": 20270412,
  "stage": 1,
  "categories": {
    "M Elite": {"rank_mode": "points", "invert_ranking": true, "random_block": 5},
    "W Elite": {"rank_mode": "points", "invert_ranking": true, "random_block": 5},
    "M20": {"rank_mode": "points", "invert_ranking": true},
    "W20": {"rank_mode": "points", "invert_ranking": true}
  }
}
```

## Tested On Past Races

The full benchmark on every 2025-2026 LiveResults race (with an independent validator and the exact optimum) is in `tests/start-list/results-2025-2026.md` of the plugin repository. In short: 98 grids, all valid; where the shortest possible window is proven (81 races) the script finds it in 74 and is never more than 3 minutes longer; in the 17 largest races, where it is not proven, the script is at most 1 minute above the shortest grid its pace allows (5.5 starters a minute on average) and at most 9 minutes above the shortest grid known (which loads every minute up to 6); the 21 races where it stops to ask for first-control collisions really have no collision-free grid of acceptable length. A selection, recomputed with the current script on LiveResults data (app.liveresults.it): every grid category with the course and first control published for it, the start of its class, default vacants, no rankings (all categories random), automatic window, compact pace, `random_seed` 2027. "Real" is the published grid from its first to its last regular start (single changes more than 10 minutes away from the grid excluded); collisions are same start, same first control, same minute.

| Race | Grid athletes | Starts | Script | Real grid |
|---|---|---|---|---|
| Toscana Orienteering Classic 2026, day 2 (middle) | 129 | 1 | 37 min (51 with `spread`) | 54 min |
| Venezia in notturna 2026 | 467 | 1 | 124 min, no collisions, masters at 3 minutes (114 at 2 minutes: saving not above 10) | 113 min, 5 collisions |
| Eridano 2026, Coppa Italia middle | 577 | 1 | 129 min, no collisions | 131 min, 4 collisions |
| Finali Coppa Italia 2026, middle | 618 | 2 | 132 min, no collisions | 141 min, 5 collisions |
| Finali Coppa Italia 2026, sprint | 685 | 1 | 136 min, no collisions | 153 min, 2 collisions |
| Begun Cup 2025, middle day 3 | 385 | 1 | 80 min, no collisions | 104 min, 120 collisions |
| Begun Cup 2025, middle day 1 | 628 | 1 | stops: needs approval; then 157 min, 51 collisions | 161 min, 168 collisions |
| 5 Days of Italy 2024, stage 1 | 1102 | 3 | 162 min, no collisions | 128 min, 8 collisions |

- **Distinct first controls shorten the grid.** Finali Coppa Italia 2026 middle had 8 first controls for 618 athletes (128 starters on the busiest): 132 minutes. With a different first control per category, as course setters are asked, the same race fits in 115 minutes with wider intervals. If the window comes out too long, check first how many starters share the busiest first control (reported as a lower bound) and ask the course setter for more distinct first controls before shortening intervals.

## Weekends And Multi-Day Events: Vary The Neighbours

When there are two races in a weekend or a multi-day event, the start lists should not pair the same runners again: two athletes who started one after the other in a previous race should not be consecutive again in the same category. This gives variety (different people to meet or follow in the forest).

With the script, build the races in order and pass the earlier proposals with `previous_start_lists` (e.g. `["day1.csv"]` for day 2, `["day1.csv", "day2.csv"]` for day 3). Use stable `id` values across races. The script swaps athletes only inside their shuffle scope (whole category for random categories, the same strength group or elite block for seeded ones), so the seeding is preserved, and keeps club separation as far as possible. Categories in fixed ranking order are not changed. Very small categories (e.g. 3 athletes) may make a repeat unavoidable: the report gives the number of repeated pairs per category.

## Questions To Ask The Organizer

- Is the race a WRE (Elite at the IOF intervals)?
- Which start (lane/corridor) each category uses, when there is more than one.
- Pace: finish early (`compact`) or spread the starts (`spread`); or a maximum total window (`window_minutes`).
- Load limit: 6 per minute per start, or up to 8 to shorten a long grid.
- Whether to widen intervals (default yes, up to 7 minutes, 4 in sprint) or keep some categories fixed.
- Which ranking to use for seeding (Coppa Italia, lista base, WRE, other) and for which categories; Elite blocks of 5 or 10.
- Free-start categories and vacants.
- Sensitive categories to start at the beginning: by default the youngest up to 14 and the 70 and over; others to add or remove?
- For weekends/multi-day events: the start lists of the previous races, so neighbours can be varied.
- When the script stops on first-control collisions: more first controls, more starts, a longer window, or approve the collisions.

## In Oribos

Oribos stores the interval per category (`<Intervallo>` on each `<categoria>`, see `read-file-og4`), so different intervals for masters and other categories can be carried over when the organizer enters the approved grid.
