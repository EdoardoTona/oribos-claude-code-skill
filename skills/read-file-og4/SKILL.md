---
name: read-file-og4
description: Reference for Oribos OG4/OG3 orienteering competition management files. Use when working with .og4 or .og3 files, reading or parsing race data, understanding the XML structure, or working with Oribos results.
user-invocable: false
---

`.og4` and `.og3` files are ZIP archives containing XML. Unzip to a temp directory, then parse the XML files inside. The extension is the only difference between og3 and og4 — the internal format is identical.

When Oribos has a file open it creates a `.lock` file alongside it.

## File reference

Always read [og4-base.md](og4-base.md) first — it covers the archive structure, all core XML files (Progetto.xml, Gara.xml, Categorie.xml, Percorsi.xml, Atleti.xml), field descriptions, and time encoding.

Also read [og4-special.md](og4-special.md) if:
- The race is a relay: `TipoGara=Staffetta`
- The race is Score-O/Rogaining: `TipoGara=Score`
- The project is MultiDays: `Progetto.xml` has `<Tipo>MultiDays</Tipo>`
- One Man Relay: `OneManRelay=True` in `Gara.xml`

Read [og4-fields.md](og4-fields.md) when you need the full mapping of abbreviated XML field codes (M1, N3, T7, etc.) or the G1–G16 start grid parameters.
