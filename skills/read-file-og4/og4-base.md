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
  <ContGare>150</ContGare>         <!-- Next-ID counter / high-water mark for race IDs (like the Cont* fields in Gara.xml) -->
  <MostraErroreCopia>False</MostraErroreCopia>  <!-- UI flag: show copy-error warning -->
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
| `TipoGara` | Race type: `Normale`, `Staffetta`, `Score`, `Trail` (Trail-O, see og4-special.md) |
| `TipoGriglia` | Start list type: `Nessuna`, `Griglia`, `Lancio` |
| `TipoTempoPartenza` | How start time is determined (see below) |
| `TipoTempoFine` | How finish time is determined: `SportIdent`, `ManualeCrono` |
| `T3` | First start time (HH:MM:SS, absolute clock time) |
| `T4` | First start time from SportIdent |
| `TempoMassimo` | Time limit (HH:MM:SS). Default `03:00:00` |
| `OneManRelay` | `True` if one-man relay format |
| `GrigliaSalvata` | `True` if start grid has been generated |
| `ContAtleti` | Next athlete `M1` allocator. Must be greater than every athlete `M1`; update it when adding athletes to avoid future ID conflicts. |
| `ContCategorie` | Next category `M1` allocator. Must be greater than every category `M1`; update it when adding categories. |
| `ContPercorsi` | Next course `M1` allocator. Must be greater than every course `M1`; update it when adding courses. |
| `ContStaffette` | Next relay-team `M1` allocator (Staffetta only). Must be greater than every team `M1`; update it when adding teams. |
| `PercorsiSportIdent` | Paths to `.ord` SportIdent files. Each `<c f="..." v="N" />` entry: `f`=file path (Windows, informational), `v`=file format version |
| `ricevute` | Issued payment receipts. Each `<ricevuta>`: `Numero` (receipt no.), `Tipo` (`Societa`/...), `Id`, `N3` (payer name), `N1` (nationality), `Q1` (amount), `Annullata` (cancelled flag). Empty `<ricevute />` when none |
| `puntiradio` | Radio control definitions: `<p n="54" d="54" />` (n=control code, d=label) |
| `Sistema` | Timing system: `SportIdent`, `Nessuno` |
| `TipoPunteggio` | Points system: `Nessuno`, `Formula`, `TTFormula`, `GSS`, `Fisso`, `TourTrev` |
| `IntervalloPercorsi` | Interval between courses in minutes |
| `RichiediNomeScarico` | `True` = always prompt for name/bib on every SI card download (useful for school events where the same cards are reused by different athletes across races) Default is  `False`, set only if the user request for it |
| `RichiediNomeSoloNoleggio` | `True` = prompt only when downloading rented cards |

The `Cont*` fields are next-ID counters/high-water marks, not record counts. For each entity type, the matching counter in `Gara.xml` must always be greater than `max(M1)` in the corresponding XML file. When adding a record, assign `M1 = Cont*`, then increment that counter. Do not lower an existing counter to `max(M1)+1`; if the counter is not updated, Oribos may later reuse an existing internal ID and create conflicts. Old files can already violate this invariant (e.g. a 2013 file with `ContAtleti` < `max(M1)`); before adding records to such a file, first raise the counter above `max(M1)`.

### Other Gara.xml fields seen in real files

| Field | Description |
|---|---|
| `LiveEvent` | Live-publishing event ID (numeric) |
| `FSLivePassword` | Encrypted password for live publishing |
| `ImportaDecimi` | `True` = import tenths of a second from SI readouts |
| `StazioniNonFunzionanti` | List of control codes marked as out of order (punches there are excused) |
| `PercorsoIscrizioni` | Local path to the entries folder (informational, machine-specific) |
| `Noleggi` (capital N) | Serialization artifact (`Oribos.Engine.Dati.DatiNoleggio[]`) — ignore; the real data is in lowercase `noleggi` |
| `TrailMode`, `TempoTrailMAX`, `PenalitaTrailERR` | Trail-O settings (see og4-special.md) |

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

### Vacant / `{Libero}` start slots

Reserved empty start slots are stored as athlete records in `Atleti.xml`, not as separate grid objects. The distinguishing flag is `<V1>True</V1>` (`Vacante`); the name convention is `Cognome={Libero}` with empty `N3`, but do not rely on the name alone.

Vacant records still need a unique `M1` allocated from `ContAtleti`, a category (`C1`), and the grid fields used by the event (commonly `T3` for the reserved start time and `P9` for the category grid position). They usually contain minimal/fake identity data such as `C3=0`, `S3=Senza Società`, empty `P2`, empty punch/split lists, and no SI card. Normal athletes usually omit `V1`; absence means not vacant.

When assigning a last-minute real athlete to a reserved slot, reuse the vacant record's `M1` and grid time, replace the fake identity fields, and remove `<V1>True</V1>`/`{Libero}` so Oribos no longer treats it as a vacant slot.

### Time encoding

All internal times (athlete T3, T1, T7, TempoSplit) are **relative to the race first start time** (Gara.xml `T3`). Example: if race T3=09:00:00 and an athlete's absolute start is 09:32:00, the athlete's T3 is stored as `00:32:00`. Absolute wall-clock times (T2, T4) are stored separately.

---

## Categorie.xml — Categories

```xml
<categorie>
  <categoria>
    <M1>1</M1>                  <!-- Internal ID; allocate from Gara.xml ContCategorie -->
    <N3>M21E</N3>               <!-- Full name -->
    <NomeBreve>M21E</NomeBreve> <!-- Short name -->
    <P2>Nero</P2>               <!-- Associated course name/ID -->
    <Q1>15</Q1>                 <!-- Entry fee -->
    <Ora>1</Ora>                <!-- First-start HOURS offset for this category (often omitted = 0) -->
    <Min>2</Min>                <!-- First-start MINUTES offset for this category (often omitted = 0) -->
    <Intervallo>2</Intervallo>  <!-- Start interval between athletes, in MINUTES -->
    <VacantiFine>1</VacantiFine> <!-- Vacant (empty) start slots appended at end of category -->
    <Classifica>True</Classifica>
    <PartenzaLibera>True</PartenzaLibera>  <!-- Punching start if True -->
    <Sesso>M</Sesso>            <!-- M or F (absent = unisex) -->
    <EtaMin>35</EtaMin>         <!-- Minimum age for the category (master classes: M35, M40, ...) -->
    <EtaMax>18</EtaMax>         <!-- Maximum age for the category (youth classes: M18, M16, ...) -->
    <Agonista>True</Agonista>   <!-- Competitive (non-recreational) category -->
    <ListaBase>WRE M</ListaBase> <!-- Base seeding list used to order the start grid (e.g. world ranking); only on elite classes -->
    <Ludico>True</Ludico>       <!-- Present and True = recreational category -->
    <Frazionisti>3</Frazionisti> <!-- Number of relay legs (Staffetta only) -->
    <Punti>                     <!-- Points awarded by finishing position -->
      <p>25</p><p>20</p>...
    </Punti>
  </categoria>
</categorie>
```

`P2` is the course name/ID. In staffette and one-man-relay, the course is set per-athlete instead.

### Additional category fields seen in real files

| Field | Description |
|---|---|
| `Partenza` | Start point number assigned to the category when the event uses multiple physical starts (absent = first/default start) |
| `PosGriglia` | Category position/order used when generating the start grid |
| `OffsetPartenza` | Category start offset as `HH:MM:SS` (observed on individual-start categories inside relay events; elsewhere the offset is `Ora`/`Min`) |
| `TempoLancio` | Mass-start (lancio) time for the category, relative to race `T3` (relay/`Lancio` races) |
| `Percorsi` | List of course names available to the category. For relay categories it lists every leg+fork variant (e.g. `M 13_1AA`, `M 13_2BC`, ...); for normal categories it usually repeats the single course |
| `Femminile` | Legacy female flag (rare; prefer `Sesso`) |
| `alert` | Per-category alert configuration (`<times/>`, `<codes/>`), used for announcer/radio alerts |
| `MaxTrail` | Trail-O: maximum stations for the category (see og4-special.md) |

### Start interval and first start time

- **Start interval** between consecutive athletes in a category is stored per-category as `<Intervallo>` (in **minutes**). This is the field Oribos actually writes; the `G6`/`G7`/`G8` grid codes (see og4-fields.md) are UI-side grid-generation parameters and may be absent from a saved file.
- **First start time per category** is stored as the **offset** `<Ora>` (hours) + `<Min>` (minutes), relative to the race-level `Gara.xml` `T3`. Either tag is omitted when zero (so a category with no `<Ora>`/`<Min>` starts at the race `T3`). Example: race `T3`=10:00:00 with `<Ora>1</Ora><Min>2</Min>` → that category's first start is **11:02:00**.
- The **absolute first start of the whole race** is `Gara.xml` `T3`. All athlete `T3`/`T9` times are relative to it.

> Note: the category's configured first start (`Ora`/`Min`) is the *intended* slot. The first **actual** athlete may start later if the leading grid slots are vacant/unassigned, so don't assume `min(athlete T9) == Ora*60+Min`. Read `Ora`/`Min` for the planned first start; derive from the grid only for the realised one.

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
    <M1>1</M1>                  <!-- Internal ID; allocate from Gara.xml ContPercorsi -->
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
    <TempoLimite>00:30:00</TempoLimite>  <!-- Per-course time limit (the operative limit for Score-O) -->
    <Penalita>10</Penalita>     <!-- Points deducted per minute over time limit -->
  </percorso>
</percorsi>
```

Rare/legacy course fields seen in old files: `MinPartenza` (numeric, semantics unconfirmed), `Pettorali` (list of bib numbers, observed in old relay files — apparently the first bib of each leg block; unconfirmed), `PuntiTrail` (Trail-O stations, see og4-special.md).

**Important:** The last entry in `SequenzaPunti` is the last **control** before the finish chute, not the finish line itself (typically code 100 or 200). The race time `T7` includes the run-in from that last control to the actual finish — commonly 10-60 seconds (median ~20-35 s across real events), occasionally a few minutes on long run-ins. Split times in `TempoSplit` cover up to the last control punch only; `T7 - lastSplit = run-in time`.

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
    <M1>15</M1>               <!-- Internal ID; allocate from Gara.xml ContAtleti; MUST be unique -->
    <P3>15</P3>               <!-- Bib number — should be unique within the race (see note below) -->
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
    <Note>see split times</Note>   <!-- Free-text manual note (operator-entered; vs auto NoteAuto) -->
    <BatteryDate1>22-10-26</BatteryDate1>  <!-- SI-card battery date (YY-MM-DD), read from chip on download -->
    <BatteryVolt1>2.98</BatteryVolt1>      <!-- SI-card battery voltage (Volts), read from chip on download -->

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

### Other athlete fields seen in real files

| Field | Description |
|---|---|
| `ModGriglia` | Athlete's start-time request used by grid generation: `Presto` (early) / `Tardi` (late) |
| `SiCard2` | Second SI card number (athlete carrying two chips) |
| `SiCardOld`, `SiCard2Old` | Previous SI card numbers after a chip change |
| `TempoCheck` | Check-station punch time |
| `GPS` | GPS tracker number assigned to the athlete |
| `Telefono` | Phone number |
| `RFID` | RFID tag number (0 = none) |
| `Fotofinish` | Photo-finish reference (numeric) |
| `BatteryDate2`, `BatteryVolt2` | Battery info of the second SI card |
| `Iscrizioni` | MultiDays: list of stage numbers the athlete is entered in (see og4-special.md) |
| `StaffettaLancio` | Relay: `True` when the leg started in the mass launch (restart) instead of chase start |
| `Trail` | Trail-O answers (see og4-special.md) |
| `SoloFinish`, `ImportFinish` | Finish-only timing / imported finish flags (semantics unconfirmed) |
| `G1` | GSS individual flag (school events) |

### P3 — Bib number uniqueness

The bib number `P3` should be **unique within a race**. Oribos does not enforce this at the file level — duplicates can exist for virtual/scratch entries or vacant slots — but real classified athletes are expected to have distinct bibs, and SI-card download/lookup by bib relies on it. When adding or editing athletes, assign each a bib not already used by another classified athlete in the same `Gara*/Atleti.xml`. (Note: `P3` differs from the internal ID `M1`, which **must** be unique; `P3` is the human-facing race number.)

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
- **Include `Gara1/AtletiMD.xml`** even for single-day (empty `<atleti></atleti>`). (When *reading*, note that very old `.og3` files — 2012-2013 — may lack `AtletiMD.xml` entirely.)
- ZIP paths: no leading slash, no top-level folder prefix (`Progetto.xml`, not `EVENT/Progetto.xml`).

### XML encoding

All XML files: **UTF-8 BOM** (`\xef\xbb\xbf`) + `standalone="yes"` + **tab** indentation.

### Gara.xml — required fields beyond the documented ones

All these must be present or Oribos may crash/misbehave:

`Uid` (any GUID), `FileModificato`, `QuotaIscrizione`, `CostoUguale`, `GriglieImpostate`, `Intervallo`, `RigaSportIdent`, `TempoSfasamentoPartenza` (00:00:00), `SfasamentoPositivo`, `T4` (= T3 initially), `UtilizzoTempoStartSportIdent`, `NumeroGiorno`, `OneManRelay`, `Valuta` (€), `Valuta2` (CHF), `AbilitaValuta2`, `CambioValuta`, `LinkBunner` (http://www.bostek.it), `ContPettorali`, `IntervalloPercorsi`, `NumeroRicevute`, `PercorsoCrono`, `UsaPuntoFinish`, `PuntoFinish` (200), `UsaUltimoPuntoFinish`, `UsaPuntoStart`, `PuntoStart` (200), `UsaPrimoPuntoStart`, `noleggi` (4 disabled slots), `statocrono`, `statomod`, `liveconfig` (with `RocEventId`=0, `RocUrl`).

### Categorie.xml — required scoring fields

Even with `TipoPunteggio=Nessuno`, each category needs: `PuntiPrimo` (100), `PuntiAltri` (1), `PuntiCategoria` (0), `Punti` (60 `<p>` entries: 25,20,18,17,16,...,2,1 — 20 values — then 40 more `1`s; real files consistently have 60 entries).

### Percorsi.xml — extra rules

- Include `<Kmsf>` = Lunghezza/1000 + Dislivello/100 (km-effort; all real files match this formula). `<N4>` = count of `<SequenzaPunti>` entries.
- IOF XML import: **exclude CrossingPoint and Finish** from `<SequenzaPunti>`.
- `<LanterneObbligatorie>` and `<PuntiScore>` must have exactly N4 entries.

### Atleti.xml — minimum fields for new athletes

Beyond the fields documented above, ensure:
- Use `M1 = Gara.xml ContAtleti`, then increment `ContAtleti`. `ContAtleti` must remain greater than `max(M1)`; otherwise later Oribos inserts may reuse an existing internal ID and create conflicts.
- `S2=PAR` (waiting for start), `T3=00:00:00` for punching-start races.
- `P1=True` when `Q1=0` (free = already paid). Omit `<Sesso>` entirely (not `<Sesso />`) when unknown.
- `TempoScarico=01/01/0001 00:00:00` for undownloaded chips.
- Include empty `<CodicePunto />`, `<TempoSplit />`, and `<Noleggi>` with 4 False entries.
