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

## Skill

The plugin provides one skill: `read-file-og4`, invoked automatically by Claude when relevant (not a slash command — no manual invocation needed).

### Supporting files

| File             | Contents                                                                        |
| ---------------- | ------------------------------------------------------------------------------- |
| `og4-base.md`    | Archive structure, core XML files (Progetto, Gara, Categorie, Percorsi, Atleti) |
| `og4-special.md` | Relay (Staffetta), Score-O, MultiDays, One Man Relay                            |
| `og4-fields.md`  | Full abbreviated field code table + G1–G16 start grid parameters                |
