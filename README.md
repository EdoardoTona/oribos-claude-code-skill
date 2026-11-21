# Oribos Claude Code Plugin

A Claude Code plugin that adds knowledge of the [Oribos](https://oribos.it) OG4/OG3 file format — orienteering competition management software mostly used in Italy.

When you're working with `.og4` or `.og3` files, Claude automatically loads the skill and knows:

- How to read and edit OG4/OG3 files
- Time encoding conventions (relative vs. absolute times, dot-separated split format)
- Special race types: relay (Staffetta), Score-O/Rogaining, MultiDays, One Man Relay

## Installation

### 1. Add the marketplace

```shell
/plugin marketplace add EdoardoTona/oribos-claude-code-skill
```

### 2. Install the plugin

```shell
/plugin install oribos@oribos
```

That's it. Claude will now automatically load the OG4/OG3 reference when you work with Oribos files.

## Skills

The plugin provides two skills, invoked automatically by Claude when relevant (not slash commands — no manual invocation needed).

### `read-file-og4`

Reads and edits OG4/OG3 files.

#### Supporting files

| File             | Contents                                                                        |
| ---------------- | ------------------------------------------------------------------------------- |
| `og4-base.md`    | Archive structure, core XML files (Progetto, Gara, Categorie, Percorsi, Atleti) |
| `og4-special.md` | Relay (Staffetta), Score-O, MultiDays, One Man Relay                            |
| `og4-fields.md`  | Full abbreviated field code table + G1–G16 start grid parameters                |

### `orienteering-start-list`

Builds start list proposals as reviewable CSV files plus a report (it never writes event files): start load per physical start, intervals (masters and long races at least 3 minutes, wider intervals when the window allows it, IOF intervals for Elite in WRE races), first-control collisions (only with the organizer's approval), sensitive categories (youngest and 70+) at the beginning, seeding by strength groups, same-club separation, vacants and varied neighbours across multi-day races.

| File                           | Contents                                                     |
| ------------------------------ | ------------------------------------------------------------ |
| `references/baseline-rules.md` | Default rules, how the script applies them, past-race tests  |
| `references/rules-iof.md`      | IOF start rules compared with the defaults (WRE)             |
| `references/input-schema.md`   | Athletes CSV, config JSON options, output CSV                |
| `scripts/build_start_list.py`  | Proposal generator (CSV + report)                            |

Checks for the start-list script (independent validator, exact CP-SAT optimum, benchmark on LiveResults.it races) are in [`tests/start-list`](tests/start-list/README.md).
