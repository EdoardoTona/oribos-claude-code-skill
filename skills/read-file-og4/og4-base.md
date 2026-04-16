# Oribos OG4/OG3 — Base Format

## Archive Structure

```
MyEvent.og4
├── Progetto.xml          # Project metadata (event type, list of races)
├── Immagini/             # Images (logos, bitmaps) — created by Oribos on first save
├── Oris/                 # Print layout settings (see og4-special.md for format)
│   ├── Oris.xml          # Print/display settings (colors, logos, titles)
│   ├── Logo.png / LogoSport.png / LogoSponsor.png
├── Gara1/                # First (or only) race
│   ├── Gara.xml          # Race settings
│   ├── Atleti.xml        # Athletes + results
│   ├── AtletiMD.xml      # Required even for single-day (empty <atleti></atleti>)
│   ├── Categorie.xml     # Categories
│   ├── Percorsi.xml      # Courses
│   └── Staffette.xml     # Relay teams (only for TipoGara=Staffetta)
├── Gara2/ ...            # Additional races (MultiDays only)
└── Gara0/                # MultiDays only: overall classification (IdGara=0)
```

---

## Progetto.xml

```xml
<progetto>
  <tipo>0</tipo>              <!-- 0=SingleDay, 1=MultiDays -->
  <Tipo>SingleDay</Tipo>      <!-- SingleDay | MultiDays -->
  <Versione>4.0.0</Versione>
  <gare>
    <gara>
      <IdGara>1</IdGara>
      <DescrizioneGara>Stage 1</DescrizioneGara>
      <DataGara>07/02/2024 00:00:00</DataGara>
      <StatoGara>GaraChiusa</StatoGara>
      <Uid>...</Uid>
    </gara>
    ...
  </gare>
</progetto>
```

For MultiDays, `Gara0` is the overall classification (IdGara=0); individual stages are Gara1, Gara2, etc.

---

## Gara.xml — Race Settings

Key fields:

| Field | Description |
|---|---|
| `IdGara` | Race ID (0 = overall MD classification) |
| `DescrizioneGara` | Race name |
| `S3` | Organising club |
| `Luogo` | Location |
| `DataGara` | Date (MM/DD/YYYY HH:MM:SS) |
| `StatoGara` | Race state (see below) |
| `TipoGara` | Race type: `Normale`, `Staffetta`, `Score` |
| `TipoGriglia` | Start list type: `Nessuna`, `Griglia`, `Lancio` |
| `TipoTempoPartenza` | How start time is determined (see below) |
| `TipoTempoFine` | How finish time is determined: `SportIdent`, `ManualeCrono` |
| `T3` | First start time (HH:MM:SS, absolute clock time) |
| `T4` | First start time from SportIdent |
| `TempoMassimo` | Time limit (HH:MM:SS). Default `03:00:00` |
| `OneManRelay` | `True` if one-man relay format |
| `GrigliaSalvata` | `True` if start grid has been generated |
| `ContAtleti` | Total athlete count |
| `ContCategorie` | Total category count |
| `ContPercorsi` | Total course count |
| `ContStaffette` | Relay team count (Staffetta only) |
| `PercorsiSportIdent` | Paths to `.ord` SportIdent files (Windows paths, informational) |
| `puntiradio` | Radio control definitions: `<p n="54" d="54" />` (n=control code, d=label) |
| `Sistema` | Timing system: `SportIdent`, `Nessuno` |
| `TipoPunteggio` | Points system: `Nessuno`, `Formula`, `TTFormula`, `GSS` |
| `IntervalloPercorsi` | Interval between courses in minutes |
| `RichiediNomeScarico` | `True` = always prompt for name/bib on every SI card download (useful for school events where the same cards are reused by different athletes across races) Default is  `False`, set only if the user request for it |
| `RichiediNomeSoloNoleggio` | `True` = prompt only when downloading rented cards |

### SiCardNoleggio — Rental SI card pool

`<SiCardNoleggio>` in `Gara.xml` lists all SI card numbers available for rental. Each entry is a `<p>` element containing the card number. When an athlete's `S1` (SI card) matches one of these numbers, Oribos treats it as a rented card.

```xml
<SiCardNoleggio>
  <p>205625</p>
  <p>337709</p>
  <p>425711</p>
  ...
</SiCardNoleggio>
```

### noleggi — Rental slot definitions

`<noleggi>` in `Gara.xml` defines up to 4 rental slots. Each `<noleggio>` has:

| Field | Description |
|---|---|
| `Q1` | Rental fee |
| `Abilita` | `True` / `False` — whether this rental slot is active |
| `Descrizione` | Label for this rental type (e.g. "Si-card") |

```xml
<noleggi>
  <noleggio>
    <Q1>0</Q1>
    <Abilita>False</Abilita>
    <Descrizione>Si-card</Descrizione>
  </noleggio>
  <!-- up to 4 slots -->
</noleggi>
```

The per-athlete `<Noleggi>` field (in `Atleti.xml`) has one `<p>True/False</p>` flag for each of these 4 slots, indicating which rentals apply to that athlete.

### StatoGara values

| Value | Meaning |
|---|---|
| `AtletiInseriti` | Athletes entered, start grid not yet generated |
| `Griglie` | Start grid generated (also called "PreGara") |
| `PreGaraChiuso` | Start grid locked, no more changes |
| `Partenza` | Race in progress |
| `GaraChiusa` | Race closed, results final |

### TipoTempoPartenza values

| Value | Meaning |
|---|---|
| `Sportident` | Start time read from SportIdent START control (punching start) |
| `SportidentGriglia` | Clock-based start from grid, validated with SportIdent |
| `Griglia` | Clock-based start from grid (no SportIdent start validation) |

### Pre-computed start grid

When generating a start grid externally (not via Oribos UI), set these fields consistently:

**Gara.xml:**
```xml
<TipoGriglia>Griglia</TipoGriglia>
<TipoTempoPartenza>Griglia</TipoTempoPartenza>   <!-- or SportidentGriglia if SI start unit used -->
<GrigliaSalvata>True</GrigliaSalvata>
<StatoGara>Griglie</StatoGara>
```

**Each athlete in Atleti.xml** must have all three grid fields populated:
```xml
<T3>00:32:00</T3>   <!-- start time relative to race T3 -->
<T9>00:32:00</T9>   <!-- grid-assigned time — set equal to T3 -->
<P9>7</P9>          <!-- 1-based position within the athlete's category -->
```

- `T3` and `T9` are always equal when the grid is pre-computed (they diverge only if an athlete is manually moved after grid generation).
- `P9` is the athlete's rank within their own category grid (1 = first starter of that category), not a global slot number.
- Multiple athletes from **different categories** may share the same `T3` (simultaneous start slots). This is valid — Oribos handles concurrent starters across categories.
- `StatoGara` in **both** `Progetto.xml` and `Gara.xml` must be updated to `Griglie`.

### Time encoding

All internal times (athlete T3, T1, T7, TempoSplit) are **relative to the race first start time** (Gara.xml `T3`). Example: if race T3=09:00:00 and an athlete's absolute start is 09:32:00, the athlete's T3 is stored as `00:32:00`. Absolute wall-clock times (T2, T4) are stored separately.

---

## Categorie.xml — Categories

```xml
<categorie>
  <categoria>
    <M1>1</M1>                  <!-- Internal ID -->
    <N3>M21E</N3>               <!-- Full name -->
    <NomeBreve>M21E</NomeBreve> <!-- Short name -->
    <P2>Nero</P2>               <!-- Associated course name/ID -->
    <Q1>15</Q1>                 <!-- Entry fee -->
    <Classifica>True</Classifica>
    <PartenzaLibera>True</PartenzaLibera>  <!-- Punching start if True -->
    <Sesso>M</Sesso>            <!-- M or F (absent = unisex) -->
    <Ludico>True</Ludico>       <!-- Present and True = recreational category -->
    <Frazionisti>3</Frazionisti> <!-- Number of relay legs (Staffetta only) -->
    <Punti>                     <!-- Points awarded by finishing position -->
      <p>25</p><p>20</p>...
    </Punti>
  </categoria>
</categorie>
```

`P2` is the course name/ID. In staffette and one-man-relay, the course is set per-athlete instead.

### Accorpate (merged categories for results publishing)

Defined in `Gara.xml`. Used to publish combined M+W results for the same course. Presentation only — does not affect scoring or timing.

```xml
<accorpate>
  <accorpata>
    <N3>Nero</N3>
    <NomeBreve>NERO</NomeBreve>
    <StampaClassifica>True</StampaClassifica>
    <Categorie>
      <p>Nero M</p>
      <p>Nero W</p>
    </Categorie>
  </accorpata>
</accorpate>
```

---

## Percorsi.xml — Courses

```xml
<percorsi>
  <percorso>
    <M1>1</M1>
    <N3>Nero</N3>               <!-- Course name — also acts as ID, matches P2 in category/athlete -->
    <Lunghezza>5240</Lunghezza> <!-- Distance in metres -->
    <Dislivello>0</Dislivello>  <!-- Climb in metres -->
    <Kmsf>5.24</Kmsf>           <!-- Km effort (km + climb/100) -->
    <N4>29</N4>                 <!-- Number of controls -->
    <MaxIscrizioni>80</MaxIscrizioni>
    <SequenzaPunti>             <!-- Control codes in order (NEVER 0 — must be actual codes) -->
      <p>35</p><p>34</p>...<p>100</p>
    </SequenzaPunti>
    <LanterneObbligatorie>      <!-- Parallel to SequenzaPunti: False for normal races -->
      <p>False</p>...
    </LanterneObbligatorie>
    <PuntiScore>                <!-- Parallel to SequenzaPunti: 0 for normal races, points for Score-O -->
      <p>0</p><p>0</p>...
    </PuntiScore>
    <!-- Score-O only: -->
    <UtilizzoTempoLimite>True</UtilizzoTempoLimite>
    <Penalita>10</Penalita>     <!-- Points deducted per minute over time limit -->
  </percorso>
</percorsi>
```

**Important:** The last entry in `SequenzaPunti` is the last **control** before the finish chute, not the finish line itself (typically code 100 or 200). The race time `T7` includes the run-in from that last control to the actual finish — typically 13–24 seconds. Split times in `TempoSplit` cover up to the last control punch only; `T7 - lastSplit = run-in time`.

### Populating SequenzaPunti from IOF XML 3.0

Each `<Course>` in the IOF file contains `<CourseControl>` elements. To build `<SequenzaPunti>`:
1. Iterate `<CourseControl>` elements in order.
2. Include only those with `type="Control"` — skip `type="Start"`, `type="Finish"`, and `type="CrossingPoint"`.
3. Use the `<Control>` child text as the `<p>` value (this is the control code, e.g. `32`, `100`).

A control code may appear more than once (butterfly loops). `<SequenzaPunti>` must list every visit.

In staffette and one-man-relay, a separate course is created per athlete.

---

## Atleti.xml — Athletes

```xml
<atleti>
  <atleta>
    <!-- Identity -->
    <M1>15</M1>               <!-- Internal ID — MUST be unique across the file, never duplicated -->
    <P3>15</P3>               <!-- Bib number (may be duplicated for virtual/scratch entries) -->
    <N3>Mario</N3>            <!-- First name -->
    <Cognome>Rossi</Cognome>  <!-- Last name -->
    <D1>03/28/1981 00:00:00</D1>  <!-- Date of birth (MM/DD/YYYY) -->
    <T8>VE4990</T8>           <!-- Membership card / tessera (may be duplicated) -->
    <S1>205958</S1>           <!-- SI card number (may be duplicated — e.g. reused school cards) -->
    <C3>34</C3>               <!-- Society internal ID -->
    <S3>CLUB NAME</S3>        <!-- Society/club name -->
    <N1>ITA</N1>              <!-- Nationality (IOC 3-letter code) -->
    <N2>ITA</N2>              <!-- Society nationality -->
    <WRE>32449</WRE>          <!-- World Ranking Entry ID (international events) -->
    <Sesso>M</Sesso>          <!-- M or F -->
    <Agonista>False</Agonista>

    <!-- Category and course -->
    <C1>M21E</C1>             <!-- Category name -->
    <P2>Nero</P2>             <!-- Course name (+ fork code suffix for relay/OMR, e.g. Nero_BBCAB) -->

    <!-- Status -->
    <S2>CLA</S2>              <!-- Result status (see table below) -->

    <!-- Times — relative to race first start (Gara.xml T3): -->
    <T3>00:32:00</T3>         <!-- Athlete start time, relative (TempoPartenza) -->
    <T9>00:32:00</T9>         <!-- Athlete start time from grid (TempoPartenzaGriglia) -->
    <T1>01:10:14</T1>         <!-- Finish time, relative (TempoArrivo) -->
    <T7>00:38:14</T7>         <!-- Race time = T1 - T3 (TempoTotale) -->

    <!-- Times — absolute wall-clock (SportIdent): -->
    <T4>09:32:00</T4>         <!-- Absolute start (TempoPartenzaSportIdent) -->
    <T2>10:10:14</T2>         <!-- Absolute finish (TempoArrivoSportIdent) -->

    <!-- Results -->
    <N4>19</N4>               <!-- Number of controls punched -->
    <P4>7</P4>                <!-- Position in category -->
    <P9>9</P9>                <!-- Position in start grid -->
    <P5>54.22</P5>            <!-- Points earned -->
    <P6>54.22</P6>            <!-- Society points -->
    <P7>70</P7>               <!-- Total score points (Score-O only) -->
    <F1>1</F1>                <!-- Relay leg number (Staffetta only) -->

    <!-- Payment -->
    <Q1>15</Q1>               <!-- Entry fee amount -->
    <P1>True</P1>             <!-- Paid -->

    <!-- SI card processing -->
    <S4>True</S4>             <!-- SI card data downloaded -->
    <S6>True</S6>             <!-- SI card data analysed -->
    <I1>True</I1>             <!-- Imported from IOF -->
    <TempoScarico>01/25/2026 11:08:35</TempoScarico>  <!-- SI download timestamp -->
    <NoteAuto>Manca 83</NoteAuto>  <!-- Auto-generated note (e.g. missing control) -->

    <!-- Control punches (standard orienteering): -->
    <CodicePunto>             <!-- Control codes as actually punched, in order -->
      <p>39</p><p>41</p>...<p>100</p>
    </CodicePunto>
    <TempoSplit>              <!-- Cumulative split times from athlete's start, format HH.MM.SS (dots) -->
      <p>00.01.19</p><p>00.03.26</p>...
    </TempoSplit>

    <!-- Score-O only (instead of CodicePunto/TempoSplit): -->
    <PuntoPunzonato>          <!-- True/False parallel to course SequenzaPunti -->
      <p>True</p><p>False</p>...
    </PuntoPunzonato>

    <!-- Radio splits (live timing): -->
    <Radio>                   <!-- Absolute wall-clock times at radio controls -->
      <p id="54" t="14.29.55" />
    </Radio>

    <!-- SI card rental: -->
    <Noleggi>                 <!-- One flag per rental slot (up to 4) -->
      <p>True</p><p>False</p><p>False</p><p>False</p>
    </Noleggi>
  </atleta>
</atleti>
```

### S2 — Status values

| File value | Italian standard | Meaning |
|---|---|---|
| `CLA` | — | Classified / valid result |
| `NPA` | `NP` | Did not start |
| `RIT` | `RI` | Retired |
| `MAN` | `PM` | Missing punch |
| `FTM` | `FT` | Over time limit |
| `ERR` | `PE` | Wrong punch |
| `SQU` | `SQ` | Disqualified |
| `GAR` | - | Started (during the race) |
| `PAR` | - | Waiting for start (just entered) |
| `DIS` | - | Missing |

### Time formats summary

| Field | Format | Reference |
|---|---|---|
| T3, T1, T7 (athlete) | `HH:MM:SS` | Relative to race first start |
| T2, T4 | `HH:MM:SS` or `HH:MM:SS.fffffff` | Absolute wall-clock |
| TempoSplit | `HH.MM.SS` (dots) | Cumulative from athlete's own start |
| Radio `t` attribute | `HH.MM.SS` (dots) | Absolute wall-clock |
| Dates (D1, DataGara, TempoScarico) | `MM/DD/YYYY HH:MM:SS` | — |

---

## Creating an OG4 file from scratch

Rules to produce a file Oribos opens without errors. Violations cause silent failures or `Riferimento a un oggetto non impostato su un'istanza di oggetto`.

### Archive rules

- **`Oris/` directory is optional** — Oribos creates it with defaults on first save. You can include it to pre-configure print settings (see og4-special.md). If included, all required fields in `Oris.xml` must be present or `Oribos.Prints.IOC.Load` throws NullReferenceException.
- **Include `Gara1/AtletiMD.xml`** even for single-day (empty `<atleti></atleti>`).
- ZIP paths: no leading slash, no top-level folder prefix (`Progetto.xml`, not `EVENT/Progetto.xml`).

### XML encoding

All XML files: **UTF-8 BOM** (`\xef\xbb\xbf`) + `standalone="yes"` + **tab** indentation.

### Gara.xml — required fields beyond the documented ones

All these must be present or Oribos may crash/misbehave:

`Uid` (any GUID), `FileModificato`, `QuotaIscrizione`, `CostoUguale`, `GriglieImpostate`, `Intervallo`, `RigaSportIdent`, `TempoSfasamentoPartenza` (00:00:00), `SfasamentoPositivo`, `T4` (= T3 initially), `UtilizzoTempoStartSportIdent`, `NumeroGiorno`, `OneManRelay`, `Valuta` (€), `Valuta2` (CHF), `AbilitaValuta2`, `CambioValuta`, `LinkBunner` (http://www.bostek.it), `ContPettorali`, `IntervalloPercorsi`, `NumeroRicevute`, `PercorsoCrono`, `UsaPuntoFinish`, `PuntoFinish` (200), `UsaUltimoPuntoFinish`, `UsaPuntoStart`, `PuntoStart` (200), `UsaPrimoPuntoStart`, `noleggi` (4 disabled slots), `statocrono`, `statomod`, `liveconfig` (with `RocEventId`=0, `RocUrl`).

### Categorie.xml — required scoring fields

Even with `TipoPunteggio=Nessuno`, each category needs: `PuntiPrimo` (100), `PuntiAltri` (1), `PuntiCategoria` (0), `Punti` (50 `<p>` entries: 25,20,18,17..1 then 30x1).

### Percorsi.xml — extra rules

- Include `<Kmsf>` (= Lunghezza/1000.0). `<N4>` = count of `<SequenzaPunti>` entries.
- IOF XML import: **exclude CrossingPoint and Finish** from `<SequenzaPunti>`.
- `<LanterneObbligatorie>` and `<PuntiScore>` must have exactly N4 entries.

### Atleti.xml — minimum fields for new athletes

Beyond the fields documented above, ensure:
- `S2=PAR` (waiting for start), `T3=00:00:00` for punching-start races.
- `P1=True` when `Q1=0` (free = already paid). Omit `<Sesso>` entirely (not `<Sesso />`) when unknown.
- `TempoScarico=01/01/0001 00:00:00` for undownloaded chips.
- Include empty `<CodicePunto />`, `<TempoSplit />`, and `<Noleggi>` with 4 False entries.
