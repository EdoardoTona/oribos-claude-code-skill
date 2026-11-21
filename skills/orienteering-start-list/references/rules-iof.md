# IOF Start Rules Compared With The Defaults

Read this when the organizer asks which rules apply, for WRE races (`"wre": true`), or for IOF events. The default rules are in `baseline-rules.md`. Source checked in November 2026: IOF Competition Rules for IOF Foot Orienteering Events, valid from 1 July 2024 (v1.12).

## Start Intervals (minutes)

The IOF rules define fixed intervals per race type. The default practice widens them when the window allows it; in WRE races the Elite categories keep the IOF intervals.

| Categories | Race | IOF | Default | WRE race (`wre: true`) |
|---|---|---|---|---|
| Elite | Sprint | 1 (12.17); WOC 1 or 1.5 (12.18) | **1, fixed** | 1, fixed |
| Elite | Middle | 2 (12.17); WOC qualification 3, final 2 (12.18) | 2, widened when possible (max 7) | **2, fixed** |
| Elite | Long | 2 or 3 (12.17); WOC 3 (12.18) | 3, widened (max 7) | **3, fixed** |
| Junior (up to 20 included) | Sprint | 1 (12.17); EYOC 1 | **1, fixed** | 1, fixed |
| Junior | Middle | 2 (JWOC 12.19; 1.5 above 180 per class) | 2, widened (max 7) | as default |
| Junior | Long | 2 (JWOC 12.19); EYOC 2 | 3, widened (max 7) | as default |
| Master 35+ | Sprint | WMOC 1 (12.23) | at least 2 (recommended), widened (max 4) | as default |
| Master 35+ | Middle / Long | WMOC qualification 1, Middle A-final 2, other Middle finals 1, Long finals 2; longer allowed with few competitors if the start period stays within 80 min (160 for Middle A / Long) (12.23) | at least 3 (recommended), widened (max 7); the normal interval (2) when there are too many entries | as default |
| Other (A, B, Open, Direct...) | Sprint | 1 | 1, widened (max 4) | as default |
| Other | Middle | 2 | 2, widened (max 7) | as default |
| Other | Long | 2-3 | 3 (recommended), widened (max 7); 2 when there are too many entries | as default |

Notes:
- The IOF rules apply to IOF events (WOC, JWOC, WMOC, World Cup, regional championships, WRE). In WRE races the defaults apply to every category except the Elite ones.
- A fixed 1-minute category takes every minute on its first control: categories sharing that start and first control cannot interleave with it and run before or after it, which can lengthen the grid (Finali Coppa Italia 2026 sprint: 155 instead of 148 minutes).
- The script works in whole minutes: the IOF 1.5-minute options are not available (see the 30-second note in SKILL.md).

## Start Order (Draw)

- 12.2 the starting order must be approved by the IOF Event Adviser; the draw may be by hand or computer.
- 12.4 all correctly entered competitors are drawn, even if not yet arrived; entries without names are not.
- 12.5 / 12.6 WOC/World Cup: draw in starting groups based on ranking, random inside each group, best group last; JWOC: random in three starting groups (early, middle, late).
- 12.7 competitors from the same federation must not start consecutively; if drawn so, the next competitor drawn is inserted between them (for merit order, the draw starts with the best competitor).
- 12.11 finals after qualification: reverse order of the qualification placings, best last.
- Regional championships appendices (e.g. NAOC): ranked competitors start last; for subsequent races the ranking order is randomized in sub-groups of 15.

## How The Script Maps These Rules

- Same-club separation follows the spirit of IOF 12.7 (same federation) at club level; seeded categories keep their strength group/block, moving to the adjacent one only when needed.
- Elite blocks of 5 (or 10) and 3 strength groups follow the IOF starting-group idea.
- First-control collisions follow the national grid criteria (FISO RTF 6.10.2, "different first controls for categories starting at the same time"), counted per start, and are accepted only with the organizer's approval.
- Vacants: the script puts them at the end by default (Oribos only does that); the national regulation also allows the head (`vacant_position: "start"`).
- When the criteria cannot all be met the script stops or warns and the Technical Delegate decides, as FISO RTF 6.10.2 says.
