# Start Interval And Start List Rules: IOF And FISO

Read this when the organizer asks which rules apply, or when choosing between the default (wide) intervals and `interval_policy: "iof"`. Sources checked in November 2026:

- IOF Competition Rules for IOF Foot Orienteering Events, valid from 1 July 2024 (v1.12).
- FISO Regolamento Tecnico Federale (RTF), approved 14/11/2015, updated 02/11/2021; chapter 6 is foot orienteering (CO). The 2/2/3-minute table in chapter 7 is for MTB-O, not CO.
- FISO Consiglio Federale n. 283, 12/09/2025, resolution DF 53/2025 (experimental for 2026 only).
- FISO 2027 guidelines as reported by the organizer (no published document found yet).

## Start Intervals

| Categories | Race | IOF | FISO | Script default (`fiso-2027`) | Script `interval_policy: "iof"` |
|---|---|---|---|---|---|
| Elite | Sprint | 1 (12.17); WOC 1 or 1.5 (12.18) | not specified for CO | **1, fixed** | 1, fixed |
| Elite | Middle | 2 (12.17); WOC qualification 3, final 2 (12.18) | not specified | 2, widened when possible (max 7) | **2, fixed** |
| Elite | Long | 2 or 3 (12.17); WOC 3 (12.18) | not specified | 3, widened (max 7) | **3, fixed** |
| Junior (up to 20 included) | Sprint | 1 (12.17); EYOC 1 | not specified | **1, fixed** | 1, fixed |
| Junior | Middle | 2 (JWOC 12.19; 1.5 above 180 per class) | not specified | 2, widened (max 7) | **2, fixed** |
| Junior | Long | 2 (JWOC 12.19); EYOC 2 | not specified | 3, widened (max 7) | **2, fixed** |
| Master 35+ | Sprint | WMOC 1 (12.23) | 2026 experimental: MW50+ at least 2; 2027: 35+ at least 2 | at least 2, widened (max 4) | same as default |
| Master 35+ | Middle / Long | WMOC qualification 1, Middle A-final 2, other Middle finals 1, Long finals 2; longer allowed with few competitors if the start period stays within 80 min (160 for Middle A / Long) (12.23) | 2027: at least 3, wider welcome | at least 3, widened (max 7); 2 for master categories of 50+ whose 3-minute span would be unrealistic | same as default |
| Other (A, B, Open, Direct...) | Sprint | 1 | not specified | 1, widened (max 4) | same as default |
| Other | Middle / Long | 2 / 2-3 | not specified | 2 / 3, widened (max 7) | same as default |

Notes:
- The IOF rules apply to IOF events (WOC, JWOC, WMOC, World Cup, regional championships, WRE). For Italian events FISO sets only the grid criteria below; the minutes come from the 2027 guidelines and the organizer.
- A fixed 1-minute category takes every minute on its first control: categories sharing that start and first control cannot interleave with it and run before or after it, which can lengthen the grid (Coppa Italia 2026 sprint final: 160 instead of 148 minutes).
- The script works in whole minutes: the IOF 1.5-minute options are not available (see the 30-second note in SKILL.md).

## Start List (Grid) Criteria

FISO RTF 6.10.2 (CO) — the grid must respect:
- the same interval between consecutive starters inside each category;
- categories sharing a course may start alternately, still keeping their interval;
- categories starting at the same time must have different first controls;
- vacant positions at the head or at the tail of the grid, not in the middle.
If not all criteria can be respected, the Technical Delegate (DT) decides with the race director. The grid is prepared by the race director with the DT's collaboration/approval.

FISO RTF: Elite categories are filled according to the Lista Base when entries are many.

IOF:
- 12.2 the starting order must be approved by the IOF Event Adviser; the draw may be by hand or computer.
- 12.4 all correctly entered competitors are drawn, even if not yet arrived; entries without names are not.
- 12.5 / 12.6 WOC/World Cup: draw in starting groups based on ranking, random inside each group, best group last; JWOC: random in three starting groups (early, middle, late).
- 12.7 competitors from the same federation must not start consecutively; if drawn so, the next competitor drawn is inserted between them (for merit order, the draw starts with the best competitor).
- 12.11 finals after qualification: reverse order of the qualification placings, best last.
- Regional championships appendices (e.g. NAOC): ranked competitors start last; for subsequent races the ranking order is randomized in sub-groups of 15.

## How The Script Maps These Rules

- Same-club separation follows the spirit of IOF 12.7 (same federation) at club level; seeded categories keep their strength group/block, moving to the adjacent one only when needed.
- Elite blocks of 5 (or 10) and 3 strength groups follow the IOF starting-group idea and the FISO 2027 guidelines.
- First-control collisions follow RTF 6.10.2 ("different first controls for categories starting at the same time"), counted per start.
- Vacants: the script puts them at the end by default (Oribos only does that); RTF also allows the head (`vacant_position: "start"`).
- When criteria cannot all be met (too few first controls, very large master categories) the script still produces a grid and warns: the DT decides, as RTF 6.10.2 says.
