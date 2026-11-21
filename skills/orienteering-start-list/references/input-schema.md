# Input Schema For Generic Start Lists

Use this reference when adapting arbitrary race exports to `scripts/build_start_list.py`.

## Athletes CSV

Required columns:

- `id`: stable athlete identifier for this proposal.
- `last_name`
- `first_name`
- `club`
- `category`

Recommended columns:

- `bib`
- `course`
- `first_control`
- `rank_position`: numeric ranking where lower is better, such as WRE position.
- `rank_points`: numeric points where higher is better.
- `request`: free text shown in reports.
- `request_kind`: `early`, `late`, `exact`, or empty.
- `request_minute`: minute offset from first start for `exact`, or target minute for `early`/`late`.
- `request_weight`: numeric soft-constraint weight; use higher values for childcare/transport/organizer-approved needs.
- `start`: physical start (lane/corridor) of the athlete's category, e.g. `1`, `2`. Load limits (`max_load`, `peak_load`, `ramp_up`) apply to each start separately. Can also be set per category in the config (`categories.<name>.start`). In Oribos/LiveResults data each class has a start number.

If `course` or `first_control` is missing, provide it through category/course config.

## Config JSON

Minimal example:

```json
{
  "first_start": "10:00:00",
  "race_type": "middle",
  "window_minutes": 90,
  "max_load": 6,
  "peak_load": 8,
  "allow_first_control_collision": false,
  "free_categories": ["Beginners", "M 10", "W 10", "M 12", "W 12", "Direct"],
  "default_vacants": 2,
  "vacant_position": "end",
  "randomize_unseeded": true,
  "stage": 1,
  "categories": {
    "M ELITE": {
      "course": "Course 1",
      "interval": 2,
      "rank_mode": "position",
      "invert_ranking": true,
      "random_block": 5,
      "vacants": 2,
      "vacant_position": "end"
    }
  },
  "courses": {
    "Course 1": {"first_control": "36"}
  },
  "separate_pairs": [
    {"left": "123", "right": "456", "minutes": 30, "weight": 10}
  ],
  "near_pairs": [
    {"left": "789", "right": "790", "minutes": 10, "weight": 4}
  ],
  "random_seed": 20260612
}
```

## Defaults

- `race_type=sprint` gives interval 1.
- `race_type=middle` gives interval 2.
- `race_type=long` gives interval 3 by default; real long events often use 2 (same as middle) — confirm with the organizer.
- `default_vacants=2` for grid categories.
- `vacant_position=end`.
- `max_load=6`; `peak_load=8` (or `max_load` when `max_load` > 8).
- `allow_first_control_collision=false` — when `true`, same-minute first-control collisions become a heavy penalty instead of a hard failure (only set on explicit organizer approval).
- Missing ranks are treated as zero points/unranked.
- `randomize_unseeded=true` means categories without ranking/random-block policy are genuinely shuffled with `random_seed` before any club-separation heuristic. Use different `stage` values or different seeds for multi-day races.
- In multi-day work, compare common-athlete orders across stages and reject repeated full orders or repeated final blocks unless the organizer explicitly requested identical grids.
- The script works in whole minutes. For 30-second start intervals, treat one slot as 30 seconds and convert times when exporting.

## Ruleset Options

- `ruleset`: empty (generic) or `fiso-2027` for Italian events from 2027 (see `fiso-2027.md`).
- `master_min_age` (default 35), `master_min_interval_sprint` (default 2), `master_min_interval` (default 3): used by `fiso-2027`.
- `categories.<name>.master`: force master detection on/off for non-standard category names.
- `categories.<name>.min_interval`: minimum interval for one category (works with any ruleset).
- `window_minutes`: maximum total window. Omit it (or use `"auto"`) to compute a contained window from the longest category at minimum interval, the busiest first control and `target_load` starters per minute on average at the busiest start (default 6 for sprint, 5 otherwise). In automatic mode no minute may exceed `max_load` on any start (`auto_over_max_minutes`, default 0): the window grows a little instead.
- `ramp_up` (default `[1, 2, 4]`): maximum starters per start in the first minutes of the window, so the start can settle in; `[]` disables it.
- `placement_attempts` (default 30): category orders tried when placing; the first is largest-category-first, then busiest-first-control-first, longest-span-first and seeded variations.
- `max_interval` (global or per category) and `master_max_interval`: upper limit for widening. Intervals are widened one minute at a time, smallest first, while every category still fits the window without new minutes over `max_load` or new first-control collisions. With `fiso-2027` in non-sprint races, every category defaults to `fiso_max_interval` (7).
- `separate_clubs` (global or per category): defaults to `true` for categories with a random component (full shuffle, `random_groups`, `random_block`); swaps stay inside the shuffle scope. On a fixed-order ranked category, `true` uses the legacy greedy separation, which can break the ranking order. `club_separation_min_entries` (default 4): smaller categories are not separated. `club_move_to_neighbour_group` (default true): when swaps inside a group/block cannot separate same-club athletes, allow moving them to the adjacent group/block.
- `small_category_size` (default 10) and `small_category_vacants` (default 1): categories with fewer athletes get this many vacants instead of `default_vacants` (unless the category sets `vacants`).
- `previous_start_lists`: list of proposal CSVs from earlier races of the same weekend/multi-day event (paths relative to the config file). Athletes who were consecutive there are kept apart, swapping only inside each category's shuffle scope. Requires stable `id` values across races. Disable with `avoid_repeated_pairs: false` (global or per category).
- `random_groups` (global or per category): shuffle a ranked category within N contiguous strength groups. `random_block` takes precedence when both are set. With `fiso-2027`, ranked categories default to `elite_random_block` (5) when the name contains "Elite" and `default_random_groups` (3) otherwise.

## Output CSV

The script writes:

- `row_type`: `assigned`, `free`, or `vacant`.
- `relative_time`
- `absolute_time`
- `minute`
- `category_position`
- `bib`
- `last_name`
- `first_name`
- `club`
- `category`
- `course`
- `first_control`
- `athlete_id`
- `vacant`
- `request`
- `start`

Downstream integrations can add event-software-specific IDs later.
