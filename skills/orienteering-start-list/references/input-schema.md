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
- The script works in whole minutes. For 30-second start intervals, treat one slot as 30 seconds and convert times when exporting.

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

Downstream integrations can add event-software-specific IDs later.
