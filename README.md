# Oribos Claude Code Plugin

A Claude Code plugin that adds knowledge of the [Oribos](https://oribos.it) OG4/OG3 file format — orienteering competition management software by Edoardo Tona.

## What it does

When you're working with `.og4` or `.og3` files, Claude automatically loads the skill and knows:

- How to open OG4/OG3 files (ZIP archives containing XML)
- The structure of all XML files inside: `Progetto.xml`, `Gara.xml`, `Categorie.xml`, `Percorsi.xml`, `Atleti.xml`, `Staffette.xml`
- All abbreviated field codes (`M1`, `N3`, `T7`, `S2`, etc.) and their meanings
- Time encoding conventions (relative vs. absolute times, dot-separated split format)
- Special race types: relay (Staffetta), Score-O/Rogaining, MultiDays, One Man Relay

## Installation

```shell
/plugin install oribos@<marketplace>
```

## Skill

The plugin provides one skill: `read-file-og4`, invoked automatically by Claude when relevant (not available as a slash command).

### Supporting files

| File             | Contents                                                                        |
| ---------------- | ------------------------------------------------------------------------------- |
| `og4-base.md`    | Archive structure, core XML files (Progetto, Gara, Categorie, Percorsi, Atleti) |
| `og4-special.md` | Relay (Staffetta), Score-O, MultiDays, One Man Relay                            |
| `og4-fields.md`  | Full abbreviated field code table + G1–G16 start grid parameters                |

