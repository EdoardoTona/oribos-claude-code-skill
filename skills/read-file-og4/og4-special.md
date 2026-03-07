# Oribos OG4/OG3 — Special Race Types

Supplement to `og4-base.md`. Load this file for: relay (Staffetta), Score-O/Rogaining, MultiDays, One Man Relay.

---

## Staffetta (relay)

`TipoGara=Staffetta`. Teams are stored in `Staffette.xml` (present only for relay races).

### Staffette.xml

```xml
<staffette>
  <sta>
    <M1>761</M1>                        <!-- Team internal ID -->
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

Each athlete in `Atleti.xml` has:
- `F1` = leg number (Frazione), 1-based
- `P2` = course name + fork code (e.g. `M E_BBCAB`)
- `C1` = category name
- `T3` absent or 00:00:00 for legs 2+ (chase start, time carried from previous leg)

The number of legs per team is defined by `<Frazionisti>` in the category.

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
- `UtilizzoTempoLimite=True`, `Penalita=N`: N points deducted per minute over `TempoMassimo`.

### Athlete result (Atleti.xml)

- `PuntoPunzonato`: list of True/False, one per control in `SequenzaPunti`. True = athlete visited that control.
- `P7` (PuntiTotali): final score = sum of `PuntiScore` for visited controls − time penalty.
  - Time penalty = `Penalita × minutes_over_limit` (rounded down to whole minutes).
  - `P7` can be negative if heavily over time.
- `CodicePunto` and `TempoSplit` are **not used** in Score-O.
- `T3` absent = athlete starts at race first start (00:00:00 relative).
- `T7` = elapsed race time from start to finish punch.

### Ranking

Highest `P7` wins. Tiebreak: lower `T7` (faster time).

---

## MultiDays

`Progetto.xml` has `<Tipo>MultiDays</Tipo>`.

### Structure

- `Gara0/` — overall (multi-day) classification. `IdGara=0`. Contains master athlete list and overall results.
- `Gara1/`…`GaraN/` — individual stages. `IdGara=1,2,…`.

### Gara0

- `Atleti.xml`: master list with full personal data (name, club, category, SI card, etc.) for all athletes in the overall classification.
- `AtletiMD.xml`: empty at this level.
- `Gara.xml`: overall event settings (date range, scoring formula, etc.).

### GaraN (each stage)

- `AtletiMD.xml`: result data for athletes in the overall classification. Each entry links to the master record via `MyAtletaId`:

```xml
<atleti>
  <atleta>
    <MyAtletaId>2781</MyAtletaId>  <!-- Links to M1 in Gara0/Atleti.xml -->
    <M1>1352</M1>                   <!-- Stage-local ID (unique within this stage) -->
    <S2>CLA</S2>
    <T3>00:20:00</T3>
    <T1>00:56:29</T1>
    <T7>00:36:29</T7>
    <!-- Same result fields as Atleti.xml, but no personal data -->
  </atleta>
</atleti>
```

- `Atleti.xml`: full athlete records for walk-in entries (DIRECT, Esordienti, etc.) who are **not** in the overall classification. These athletes do not appear in `Gara0/Atleti.xml`.

### Overall classification data flow

To reconstruct a stage result for an overall-classification athlete:
1. Get personal data from `Gara0/Atleti.xml` where `M1 = MyAtletaId`.
2. Get stage result from `GaraN/AtletiMD.xml`.

To get all athletes in a stage (including walk-ins):
- Overall athletes: `GaraN/AtletiMD.xml`
- Walk-in athletes: `GaraN/Atleti.xml`
