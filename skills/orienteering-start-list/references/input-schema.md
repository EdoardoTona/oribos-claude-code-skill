# Input Schema For Generic Start Lists

Use this reference when adapting arbitrary race exports to `scripts/build_start_list.py`.

## Athletes CSV

Required columns:

- `id`: stable athlete identifier, unique (the script stops on duplicates) and the same across the races of a multi-day event.
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

- `race_type`: `sprint`, `middle` (default) or `long`. Normal interval: sprint 1, middle 2, long 2 (`interval_minutes` overrides it); recommended minimums on top of it (see below), so long races use 3 for every category where possible.
- `default_vacants=2` for grid categories, 1 in small categories.
- `vacant_position=end`.
- `max_load=6` (may be raised up to 8); `peak_load=8`. Nothing above 8 per minute per start is ever allowed.
- `allow_first_control_collision=false`: first-control collisions are never accepted; when no collision-free grid of acceptable length exists the script stops and explains the options. Set it to `true` only after the organizer approved the collisions: a collision-free grid is still preferred, the fewest collisions found are used only as a last resort, and the report warns and lists each of them.
- Missing ranks are treated as zero points/unranked.
- `randomize_unseeded=true` means categories without ranking/random-block policy are genuinely shuffled with `random_seed`; same-club neighbours are then removed with random swaps (no club is favoured for the first or last positions). Use different `stage` values or different seeds for multi-day races.
- In multi-day work, compare common-athlete orders across stages and reject repeated full orders or repeated final blocks unless the organizer explicitly requested identical grids.
- The script works in whole minutes. For 30-second start intervals, treat one slot as 30 seconds and convert times when exporting; every option in minutes must then be given in slots too: intervals, minimums, `max_interval` and windows doubled, loads per minute (`max_load`, `peak_load`, `ramp_up`) halved.

## Rule Options

All rules in `baseline-rules.md` apply by default; these options change them.

- `wre`: `true` for WRE races: Elite categories at the IOF intervals in every race (sprint 1, middle 2, long `wre_long_interval` = 3), never widened.
- Elite detection (one rule for intervals, WRE and seeding blocks): the word "Elite" in the name, or `ME`/`WE`/`M21E`-style short names; override with `categories.<name>.elite`. Junior: age classes up to `junior_max_age` (20) included, e.g. `M10`, `M 13/14`, `W 19/20`; override with `categories.<name>.junior`. Elite and Junior are fixed at 1 minute in sprint.
- Master detection: `M35`, `W 40`, `D45`, `H-50`... with age ≥ `master_min_age` (35); override with `categories.<name>.master`.
- Recommended minimums: `master_min_interval_sprint` (2), `master_min_interval` (3, other races), `long_min_interval` (3, every category in long races). `categories.<name>.min_interval` replaces the minimum for one category.
- Sensitive categories (start at the beginning when possible, before widening): age classes up to `sensitive_young_max_age` (14) included and from `sensitive_old_min_age` (70) included, Elite excluded; override with `categories.<name>.sensitive`, switch off with `sensitive_early: false`. `sensitive_weight` (3): placement cost per minute of delay of their first start. `sensitive_max_interval` (4): widening limit for sensitive categories (a per-category `max_interval` wins).
- `categories.<name>.interval`: exact interval for one category: no minimum, no widening, never changed by the script.
- `pace`: `compact` (default: finish early, `max_load` − 0.5 per start on average) or `spread` (spread the starts: `max_load` − 2 per start and at least `spread_factor` = 1.3 times the compact window, so small races spread too; the extra room goes into wider intervals). With `many_starts` (3) or more starts the target is one lower. `target_load` overrides both.
- `window_minutes`: maximum total window. Omit it (or use `"auto"`) to compute a contained window from the longest category at its minimum interval, the busiest first control and `target_load` starters per minute on average at the busiest start. In automatic mode no minute may exceed `max_load` on any start (`auto_over_max_minutes`, default 0): the window grows a little instead. A fixed window shorter than a single category at its minimum interval stops the script, naming the category and the options.
- `widen_intervals` (global or per category, default `true`): give every category the widest constant interval the window allows. Upper limits: `categories.<name>.max_interval`, `master_max_interval` (masters), `max_interval` (global), otherwise 7 minutes (`sprint_max_interval` = 4 in sprint); sensitive categories at most `sensitive_max_interval` (4). Intervals are widened one minute at a time, smallest first, while every category still fits the window without new minutes over `max_load` or new first-control collisions.
- Too many entries: `large_category` (50), `compact_max_categories` (3) and `compact_min_saving` (10 minutes). A category of 50+ athletes whose span at the recommended minimum would make the grid more than 10 minutes longer than the rest needs (or not fit a fixed window) gets the normal interval; when only up to 3 categories overflow the automatic window and they are held at a recommended minimum, they get the normal interval if the grid becomes more than 10 minutes shorter. Both are reported with a WARNING.
- First-control collisions are counted per start: the same first control used from different starts is not a collision.
- `max_window_stretch` (default 1.25, at least `min_window_margin` = 20 minutes) and `first_control_realistic` (default 1.5, at least `first_control_margin` = 30 minutes): how much longer than entries and load need the automatic window may grow to avoid first-control collisions before the script stops (or, with `allow_first_control_collision`, accepts the fewest collisions).
- `ramp_up` (default `[1, 2, 4]`): maximum starters per start in the first minutes of the window, so the start can settle in; `[]` disables it.
- `placement_attempts` (default 30): category orders tried when placing; the first is largest-category-first, then busiest-first-control-first, longest-span-first and seeded variations.
- `separate_clubs` (global or per category): defaults to `true` for categories with a random component (full shuffle, `random_groups`, `random_block`); swaps stay inside the shuffle scope. On a fixed-order ranked category, `true` uses the legacy greedy separation, which can break the ranking order. `club_separation_min_entries` (default 4): smaller categories are not separated. `club_move_to_neighbour_group` (default true): when swaps inside a group/block cannot separate same-club athletes, allow moving them to the adjacent group/block.
- `small_category_size` (default 10) and `small_category_vacants` (default 1): categories with fewer athletes get this many vacants instead of `default_vacants` (unless the category sets `vacants`).
- `previous_start_lists`: list of proposal CSVs from earlier races of the same weekend/multi-day event (paths relative to the config file). Athletes who were consecutive there are kept apart, swapping only inside each category's shuffle scope. Requires stable `id` values across races. Disable with `avoid_repeated_pairs: false` (global or per category).
- `random_groups` (global or per category): shuffle a ranked category within N contiguous strength groups. `random_block` takes precedence when both are set. Ranked categories default to `elite_random_block` (5) for Elite categories and `default_random_groups` (3) otherwise.

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
