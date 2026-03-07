# Oribos — Field Code Reference

Supplement to `og4-base.md`. Load this file when you need the full mapping of abbreviated XML field names, or when working with start grid parameters.

---

## Abbreviated Field Names (legendaAtletixml.json)

All abbreviated codes used in Oribos XML files:

| Code  | Full name                        | Description                            |
| ----- | -------------------------------- | -------------------------------------- |
| `A1`  | AltrePenalita                    | Other penalties                        |
| `C1`  | Categoria                        | Category name                          |
| `C2`  | CodicePunto                      | Control code (punched)                 |
| `C3`  | CodiceSocieta                    | Society internal ID                    |
| `D1`  | Data                             | Date of birth                          |
| `F1`  | Frazione                         | Relay leg number                       |
| `G1`  | GSSIndividuale                   | GSS individual flag                    |
| `G2`  | GriglieStessiVacanti             | Grid: same vacant slots                |
| `G3`  | GriglieVacanti                   | Grid: vacant slots                     |
| `G4`  | GriglieVacantiFine               | Grid: vacant slots at end              |
| `G5`  | GriglieAggiungiVacantiAuto       | Grid: auto-add vacant slots            |
| `G6`  | GriglieStessoIntervallo          | Grid: same interval for all            |
| `G7`  | GriglieIntervallo                | Grid: interval (minutes)               |
| `G8`  | Griglie30Sec                     | Grid: 30-second interval               |
| `G9`  | GriglieCalcolaPartenzaPercorsi   | Grid: calculate starts per course      |
| `G10` | GrigliePercorsiPariDispari       | Grid: even/odd courses alternation     |
| `G11` | GrigliePercorsiMinuti            | Grid: minutes per course               |
| `G12` | GriglieOrdineAutomaticoCategorie | Grid: automatic category order         |
| `G13` | GriglieUsaListaBase              | Grid: use base entry list              |
| `G14` | GriglieListaBaseOrdineinverso    | Grid: reverse base list order          |
| `G15` | GriglieSeparaAtletiSoc           | Grid: separate athletes from same club |
| `G16` | GriglieNonSeparare               | Grid: do not separate                  |
| `I1`  | ImportIOF                        | Imported from IOF XML                  |
| `I2`  | ImportOOL                        | Imported from OOL                      |
| `M1`  | MyId                             | Internal ID (unique, never duplicated) |
| `M2`  | Maschio                          | Male flag                              |
| `N1`  | Nazione                          | Nationality (athlete, IOC code)        |
| `N2`  | NazioneSocieta                   | Nationality (society)                  |
| `N3`  | Nome                             | Name / description                     |
| `N4`  | NumeroPunti                      | Number of controls                     |
| `P1`  | Pagato                           | Paid                                   |
| `P2`  | Percorso                         | Course name                            |
| `P3`  | Pettorale                        | Bib number                             |
| `P4`  | Posizione                        | Finishing position                     |
| `P5`  | Punti                            | Points earned                          |
| `P6`  | PuntiSocieta                     | Society points                         |
| `P7`  | PuntiTotali                      | Total score points (Score-O)           |
| `P8`  | PuntoPunzonato                   | Control punched flag (Score-O)         |
| `P9`  | PosizioneGriglia                 | Start grid position                    |
| `Q1`  | Quota                            | Entry fee                              |
| `Q2`  | QuotaManuale                     | Manual fee override                    |
| `S1`  | SiCard                           | SI card number                         |
| `S2`  | Situazione                       | Status (CLA/NPA/RIT/MAN/FTM/ERR/SQ)    |
| `S3`  | Societa                          | Society/club name                      |
| `S4`  | SportIdentCaricato               | SI card data downloaded                |
| `S5`  | SportIdentControllo              | SI card control check                  |
| `S6`  | SportIdentAnalizzato             | SI card data analysed                  |
| `S7`  | SubJudice                        | Under jury review                      |
| `T1`  | TempoArrivo                      | Finish time (relative to first start)  |
| `T2`  | TempoArrivoSportIdent            | Finish time (absolute wall-clock)      |
| `T3`  | TempoPartenza                    | Start time (relative to first start)   |
| `T4`  | TempoPartenzaSportIdent          | Start time (absolute wall-clock)       |
| `T5`  | TempoSplit                       | Split times                            |
| `T6`  | TempoSprintFinale                | Sprint final time                      |
| `T7`  | TempoTotale                      | Race time (T1 − T3)                    |
| `T8`  | Tessera                          | Membership card number                 |
| `T9`  | TempoPartenzaGriglia             | Grid-assigned start time               |
| `T10` | TempoAttraversamenti             | Passage times                          |
| `T11` | TempoPenalita                    | Penalty time                           |
| `T12` | TempoAbbuono                     | Time bonus                             |
| `V1`  | Vacante                          | Vacant start slot                      |

---

## Start Grid Parameters (G-codes)

The G-codes appear as XML elements on category records and control how Oribos generates the start grid:

| Code  | Full name                        | Meaning                                                 |
| ----- | -------------------------------- | ------------------------------------------------------- |
| `G2`  | GriglieStessiVacanti             | Keep the same vacant slot pattern across categories     |
| `G3`  | GriglieVacanti                   | Number of vacant slots between athlete groups           |
| `G4`  | GriglieVacantiFine               | Number of vacant slots at the end of the category       |
| `G5`  | GriglieAggiungiVacantiAuto       | Auto-add vacant slots                                   |
| `G6`  | GriglieStessoIntervallo          | Use the same start interval for this category as others |
| `G7`  | GriglieIntervallo                | Start interval for this category (minutes)              |
| `G8`  | Griglie30Sec                     | Use 30-second start interval                            |
| `G9`  | GriglieCalcolaPartenzaPercorsi   | Calculate start times based on course                   |
| `G10` | GrigliePercorsiPariDispari       | Alternate even/odd courses in grid                      |
| `G11` | GrigliePercorsiMinuti            | Minutes allocated per course in grid                    |
| `G12` | GriglieOrdineAutomaticoCategorie | Automatic category ordering in grid                     |
| `G13` | GriglieUsaListaBase              | Use the base entry list order for seeding               |
| `G14` | GriglieListaBaseOrdineinverso    | Reverse the base list order                             |
| `G15` | GriglieSeparaAtletiSoc           | Separate athletes from the same club                    |
| `G16` | GriglieNonSeparare               | Do not apply club separation                            |
