# Oribos OG4/OG3 — Special Race Types & Oris Print Settings

Supplement to `og4-base.md`. Load this file for: relay (Staffetta), Score-O/Rogaining, MultiDays, One Man Relay, Trail-O (TempO/PreO), or Oris print configuration.

---

## Staffetta (relay)

`TipoGara=Staffetta`. Teams are stored in `Staffette.xml` (present only for relay races).

### Staffette.xml

```xml
<staffette>
  <sta>
    <M1>761</M1>                        <!-- Team internal ID; allocate from Gara.xml ContStaffette -->
    <N3>G.S. MONTE GINER A.S.D. A</N3>  <!-- Team name -->
    <P3>67</P3>                         <!-- Team bib number -->
    <T7>03:09:13</T7>                   <!-- Total team time -->
    <S2>CLA</S2>                        <!-- Team status (same codes as athlete) -->
    <P4>2</P4>                          <!-- Team position -->
    <PuntiScore>0</PuntiScore>
    <I1>True</I1>
    <Atleti>                            <!-- M1 IDs of team athletes, in leg order -->
      <p>1811</p>
      <p>1812</p>
      <p>1813</p>
    </Atleti>
  </sta>
</staffette>
```

`ContStaffette` in `Gara.xml` is the next team `M1` allocator, not the team count. It must remain greater than `max(M1)` in `Staffette.xml`; assign the current `ContStaffette` to a new team and increment it to avoid future ID conflicts.

Each athlete in `Atleti.xml` has:
- `F1` = leg number (Frazione), 1-based
- `P2` = course name + fork code (e.g. `M E_BBCAB`)
- `C1` = category name
- `T3` absent or 00:00:00 for legs 2+ (chase start, time carried from previous leg)
- `StaffettaLancio=True` when the leg started in a mass launch (restart for late legs) instead of the chase start

The number of legs per team is defined by `<Frazionisti>` in the category.

Relay-specific category fields:
- `<TempoLancio>`: mass-start (launch) time of the category, relative to race `T3` (different categories can be launched at different times, e.g. `00:03:00`).
- `<Percorsi>`: list of every leg+fork course variant available to the category (e.g. `M 13_1AA` ... `M 13_3CC`). For non-relay categories in the same event it usually repeats the single course name.
- `<OffsetPartenza>`: start offset (`HH:MM:SS`) observed on individual-start categories hosted inside a relay event.

### Fork codes

The `P2` field contains the course name optionally followed by `_` and fork letters:

```
M E_BBCAB
     ^^^^^ one letter per fork point in the course
```

- Each letter = which variant (A, B, C…) the athlete runs at that fork point.
- Between fork points there may be shared controls visited by all athletes.
- Some course software uses A/B/C for every fork; others use A/B/C for fork 1, D/E/F for fork 2, etc. Both are valid.
- A numeric prefix (e.g. `1AAAA`) means the course is for that leg number only.
- Assignment rule: across all legs of a team, every variant must appear exactly once at each fork point. Oribos enforces and assigns this automatically.

### Start type

`TipoGriglia=Lancio` (mass start): all teams start simultaneously. Leg 2+ athletes start when their team's previous leg finishes (chase start — not encoded separately, implicit from leg 1 finish time).

---

## One Man Relay (OMR)

`OneManRelay=True` in `Gara.xml`. Structurally identical to a standard `Normale` race:
- Individual athletes, individual results.
- Course assigned **per athlete** (not per category) — `P2` is set on the athlete record, category `P2` is typically empty.
- `TipoGriglia=Lancio`: mass start, all athletes in a category depart simultaneously.
- Fork codes apply the same way as in relay.
- The "laps" or "butterfly loops" are embedded in the single course definition; each athlete gets exactly one course.

---

## Score-O / Rogaining (`TipoGara=Score`)

Athletes visit any subset of controls in any order within a time limit.

### Course (Percorsi.xml)

- `SequenzaPunti`: all available controls (order not meaningful for athletes, but defines the index used in `PuntoPunzonato`).
- `PuntiScore`: points value for each control, parallel to `SequenzaPunti`.
- `LanterneObbligatorie`: True = this control is mandatory.
- `UtilizzoTempoLimite=True`, `TempoLimite=HH:MM:SS`, `Penalita=N`: N points deducted per minute over the **course-level** `TempoLimite` (e.g. `00:30:00`); the race-level `TempoMassimo` is the fallback when no course limit is set.

### Athlete result (Atleti.xml)

- `PuntoPunzonato`: list of True/False, one per control in `SequenzaPunti`. True = athlete visited that control.
- `P7` (PuntiTotali): final score = sum of `PuntiScore` for visited controls − time penalty.
  - Time penalty = `Penalita × minutes_over_limit` (rounded down to whole minutes; limit = course `TempoLimite`, else `TempoMassimo`).
  - `P7` can be negative if heavily over time.
- `CodicePunto` and `TempoSplit` are **not used** in Score-O.
- `T3` absent = athlete starts at race first start (00:00:00 relative).
- `T7` = elapsed race time from start to finish punch.

### Ranking

Highest `P7` wins. Tiebreak: lower `T7` (faster time).

---

## Trail-O (TempO / PreO)

`TipoGara=Trail` with `TrailMode` in `Gara.xml` (observed: `TempO`). Athletes answer flag-identification questions at stations instead of (or in addition to) punching. Note: merged/overall Trail-O files may also appear as `TipoGara=Normale` with Trail data on the athletes.

### Gara.xml settings

| Field | Description |
|---|---|
| `TrailMode` | Trail-O discipline, e.g. `TempO` |
| `TempoTrailMAX` | Maximum answer time per station, in seconds (e.g. 30) |
| `PenalitaTrailERR` | Penalty seconds added per wrong answer (e.g. 30) |
| `TrailTempoLimiteStaffettaAtleta` | Per-athlete time limit in trail relay |

### Course stations (Percorsi.xml)

`<PuntiTrail>` holds one `<Punto>` per station:

```xml
<PuntiTrail>
  <Punto>
    <ATempo>True</ATempo>      <!-- timed station (TempO) -->
    <Corretto>ZZCBE</Corretto> <!-- correct answers, one letter per task; Z = "zero"/no flag -->
    <Range>AF</Range>          <!-- answer options span (A..F) -->
    <N3>T1</N3>                <!-- station name -->
  </Punto>
</PuntiTrail>
```

### Athlete answers (Atleti.xml)

`<Trail>` holds one `<p>` per station, parallel to `PuntiTrail`:

```xml
<Trail>
  <p><Tempo>370</Tempo><Risposta>AZEZB</Risposta></p>  <!-- Tempo in centiseconds (370 = 3.7 s); Risposta = given answers, one letter per task -->
  <p />                                                 <!-- empty = station not (yet) answered -->
</Trail>
```

`MaxTrail` on a category limits the number of stations counted for that category.

---

## MultiDays

`Progetto.xml` has `<Tipo>MultiDays</Tipo>`.

### Structure

- `Gara0/` — overall (multi-day) classification. `IdGara=0`. Contains master athlete list and overall results.
- `Gara1/`…`GaraN/` — individual stages. `IdGara=1,2,…`.

### Gara0

- `Atleti.xml`: master list with full personal data (name, club, category, SI card, etc.) for all athletes in the overall classification.
- `AtletiMD.xml`: empty at this level.
- `Gara.xml`: overall event settings (date range, scoring formula, etc.). Fields specific to the overall race (some only appear in `Gara0`):

| Field | Description |
|---|---|
| `DataGara` / `DataGaraFine` | Event start / end date (the multi-day span) |
| `DefaultClassifica` | Overall classification type. `ATempo` = sum of stage times (other point-based modes exist) |
| `GareScarto` | Number of worst stages to drop from the overall (drop-worst-N); `0` = count all stages |
| `TCPClientConfig` | Live-timing TCP reader frame template, e.g. `{CODE:2}{CARD:4}{HH:2}{MM:2}{SS:2}{D:1}` — token:width pairs describing how to parse each packet from the SI reader |
| `nolextra` | Extra rental slots, same structure as `noleggi` (`Q1`/`Abilita`/`Descrizione`) |

Every athlete in `Gara0/Atleti.xml` carries an `<Iscrizioni>` list with the stage numbers they are entered in (e.g. `<p>1</p><p>4</p>` = stages 1 and 4 only). Athletes entered in all stages have the full explicit list (`1,2,3,4,5`); a missing `<Iscrizioni>` is rare — do **not** assume it means "all stages".

Vacant start-slot records can also appear in `Gara0/Atleti.xml` with `V1=True` and `Cognome={Libero}`. Their `Iscrizioni` list identifies the stages where the placeholder is entered; use the `V1` flag, not the name alone, to recognize them.

### GaraN (each stage)

- `AtletiMD.xml`: result data for athletes in the overall classification. Each entry links to the master record via `MyAtletaId`:

```xml
<atleti>
  <atleta>
    <MyAtletaId>2781</MyAtletaId>  <!-- Links to M1 in Gara0/Atleti.xml -->
    <M1>1352</M1>                   <!-- Stage-local ID; allocate from this stage's Gara.xml ContAtleti -->
    <S2>CLA</S2>
    <T3>00:20:00</T3>
    <T1>00:56:29</T1>
    <T7>00:36:29</T7>
    <!-- Same result fields as Atleti.xml, but no personal data -->
  </atleta>
</atleti>
```

For `AtletiMD.xml`, the stage-local `M1` values use that stage's `Gara.xml` `ContAtleti` counter. Keep `ContAtleti` greater than `max(M1)` across the stage athlete/result records and increment it after adding records; stale counters can cause later ID conflicts.

- `Atleti.xml`: full athlete records for walk-in entries (DIRECT, Esordienti, etc.) who are **not** in the overall classification. These athletes do not appear in `Gara0/Atleti.xml`.

### Overall classification data flow

To reconstruct a stage result for an overall-classification athlete:
1. Get personal data from `Gara0/Atleti.xml` where `M1 = MyAtletaId`.
2. Get stage result from `GaraN/AtletiMD.xml`.

To get all athletes in a stage (including walk-ins):
- Overall athletes: `GaraN/AtletiMD.xml`
- Walk-in athletes: `GaraN/Atleti.xml`

---

## Oris/ — Print Layout Settings for Olympic Result Information System

The `Oris/` directory contains print and display configuration. Oribos creates it with defaults on first save, but it can be pre-populated to customize print output.

### Files

All files are stored in the `Oris/` directory inside the archive:

- `Oris.xml` — all print settings (single-line XML)
- `Logo.png` — event/organizer logo (top-left of printouts)
- `LogoSport.png` — sport federation logo (top-right)
- `LogoSponsor.png` — sponsor banner (bottom)

### Oris.xml structure

Root element `<prints>`, single-line format. Key fields:

| Field | Description |
|---|---|
| `PrintLogoOribos` | Show Oribos branding |
| `PrintOribos` | Show "Oribos" text |
| `PrintNameFile` | Print filename |
| `DrawRowsResult` | Draw alternating row backgrounds in results |
| `DrawRowsPodium` | Draw row backgrounds in podium view |
| `Footer` | Custom footer text |
| `Sport` | Sport name (e.g. "Orienteering") |
| `VictoryCeremony` | Victory ceremony title text |
| `StampaNonPartiti` | Print DNS athletes |
| `CategoriaTitolo` | Show category name as title |
| `StampaCategoriaTitolo` | Print category title |
| `Titolo` | Custom title override |
| `PrintTitle1` / `PrintTitle2` | Show title lines |

#### Logo/image positioning

Each logo (`logo`, `logosport`, `logosponsor`, `logovideo`, `medaglie`, `medaglied`, `medaglief`) has:

```xml
<logo>
  <ResImage>False</ResImage>        <!-- True = embedded resource, False = file in Oris/ -->
  <ImageName>Logo.png</ImageName>   <!-- filename or resource path -->
  <X>1</X><Y>1</Y>                 <!-- position (cm for print, px for video) -->
  <W>6.1</W><H>2.8</H>            <!-- size -->
</logo>
```

#### Color fields

Colors are stored as signed 32-bit integers (ARGB). Common values: `-13421773` (dark background), `-39424` (orange title), `-1` (white text).

```xml
<BackgroundColor>-13421773</BackgroundColor>
<TitleColor>-39424</TitleColor>
<RowColor1>-13092808</RowColor1>
<RowColor2>-12171706</RowColor2>
<TextColor>-1</TextColor>
<TextTitleColor>-1</TextTitleColor>
<TextTitleColor1>-1</TextTitleColor1>
<TextTitleColor2>-1</TextTitleColor2>
```
