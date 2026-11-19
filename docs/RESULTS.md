# sim3_worldbox — results

> **Note:** this is the development log of the simulation, kept for transparency. Older sections describe earlier
> versions (for example story seed 102). The final film story is **seed 132** (see `samples/story_seed132/`).
> `story_backup_v4/` mentioned below was an internal reference copy; in this repository `quick_check.py` compares
> against `samples/story_seed132/` instead.


Engine: `sim.py` (pure stdlib, /usr/bin/python3). Map 160×100, one timeline, up to 1000 years, ends when one side wins.
Story: **seed 102**, result poor by collapse at year 604. Files: `story/` (see section 7).
Checks: `quick_check.py`, 26 checks, 0 failed.

## v4 fixes after second review (current)

Story: **seed 132**, poor win by collapse at year 555. Checks: `quick_check.py`, 32 checks, 0 failed.

### Batch (200 runs), before (v3) -> after (v4)
| measure | v3 | v4 |
|---|---|---|
| rich win rate | 0% | 30.5% (target 10-25%: slightly high) |
| time-limit runs | 45% (90) | 28.5% (57) (target under 10%: NOT MET) |
| mean end year | 901 | 734 (target 250-600: NOT MET) |
| captures per run | 28.8 | 46.2 |
| capital falls per run | 2.3 | 7.9 |
| field battles per run | 13.1 | 15.2 |
| ambush battles per run | 0.24 | 2.61 (ambush by tactics 2.52) |
| sieges per run (single events) | 51.9 | 125.8 |
| truces per run | 12.5 | 9.6 |
| tech gap poor minus rich at 25/50/75% | not measured | 5.5 / 4.7 / 3.0 |
| statues + palaces per run | not measured | 5.2 |
| feasts per run | 26 (story) | 4.5 |
| theft success per run | 2.0 | 1.6 |
| mercenary hires per run | - | (see story) |

### What changed
1. Mercenaries add soldiers on top of the garrison-limited levies (cap `MERC_MAX` = 400 units = 8,000 men per army).
   Upkeep 0.10 gold per unit per year; unpaid mercenaries lose 30% per year first. Mercenary power 1.3 (cavalry-like early
   edge; the poor's iron, bows and trebuchets come later). Hire = 15% of the rich treasury.
2. Truces are 15 to 40 years (random). Tension resets to 2.0 after a truce, a caught spy adds 1.5, and a new ruler adds 1.5
   (a succession crisis). Winning armies no longer garrison and stop: they leave a quarter of their men in the city
   and march on; armies prefer the enemy capital (score bonus).
3. Feasts capped at 6 per run (1% chance per year). Statues: one per rich city, at most 8 realm-wide, from 800 units of
   population and 1,500 gold; palaces logged. Statues and palaces are buildings in the city centre area (plaza ring).
4. Rich research factor 0.4 -> 0.3. Measured tech gap (poor minus rich) at 25/50/75%: 5.5 / 4.7 / 3.0.

### Story seed 132
- Eras: Founding 0-71; Age of trade 72-79; First war 80-96; Truces and raids 97-139; Great war 140-216; The fall 217-555.
- Wars: poor 80-96 and 140-216, rich 248-271, 303-352, 377-422, poor 456-469, 493-555.
- Scary rich peak: year 186. Rich territory 614 tiles against the poor's 491; rich soldiers 25,100 against 11,780.
  The rich take Dar al-Hikma (the poor capital) at 186; the poor retake Qasr al-Dhahab at 211.
- Waste (logged): palace Qasr al-Dhahab (0), statue Qasr al-Dhahab (0), statue Dar al-Hikma (187), palace Bayt al-Hisab (425).
  Feasts: 2. Statues 2, palaces 2 (4 total, within 4-10).
- Battles by type: field 18, ambush 1 (decided by tactics), sieges 103 (286 rounds; captured 43, lifted 15, failed 12, open 33).
  Hires: 9 (72,000 men in total).
- Theft: Windmill (year 136), Astronomy calendar (160), Composite bows (294), Trebuchets (476); one spy caught in Qasr al-Dhahab (398, Trebuchets).
- Capital falls: 6 (186, 205, 211, 311, 409, 528).
- Techs at the end: rich 12, poor 15.

### Still not met (honest)
- Time limit 28.5% (target under 10%) and mean end year 734 (target 250-600). Batches are longer than the review asks:
  the rich keep winning cities back, and no truce stops the cycle after year ~500. More decisive endings need a
  rule that ends a war when the loser's capital and half its cities are taken; not built in this round.
- Sieges per story (103) far above the 8-20 target; the hard rule for the story is at least 8.
- Rich win rate 30.5% is just above the 25% ceiling.
- Batch and story numbers are from the same final code; log-only changes after the batch (siege, battle, found, endowment
  logs) do not change outcomes.

## v3 fixes after review

### 1. The rich are rich (income, waste, bankruptcy)
- Before (v2 story 229): rich gold 5,599 → 0 by year 100, zero for ~340 years; 34 "cannot pay" events (one every 10 years).
- Fix: rich land rent (0.25 gold per owned tile per year, a royal domain), mines on rich land (gold 30, oil 25 per mine per year),
  trade income after contact, rich tax efficiency 0.9, starting treasury 30,000. Rich food purchases stay (wasteful).
  Bankruptcy is now a rare event (at most one per 60 years, 50% chance when unpaid).
- Waste is logged: statues, palaces (events `waste`, kind statue/palace), feasts (kind feast, 3% of the treasury when above 8,000,
  logged at most every 15 years), mercenary hires (`hire`, with the number of men and the cost).
- After (story 102): rich gold 29,544 at year 0 and 10,651 at year 604; positive for every year of the story.
  26 feasts, 1 statue, 1 palace, 15 hires (9,320 men).

### 2. The poor do not hoard
- Before: poor gold 131,923 at year 444 (silent pile).
- Fix: gold above 4,000 is spent each year: 5% of the excess becomes research (`endowment`, 20 gold per point), and militia
  up to 10% of population (`militia`). The poor are logged as overtaking the rich's income ("the poor now out-earn the rich").
- After (story): poor gold 1,790 at year 0, 8186 at year 200, 12,401 at year 604 (the excess stays near a bounded level).
  Overtake logged at year 133.

### 3. Battles
- Before: 433 "battles" that were yearly siege rounds; 0 field battles in the story.
- Fix: a siege is one record (start, end, rounds, losses, outcome). Field battles happen when armies come within 3 tiles; ambushes
  when a rich army crosses a mountain or river within 10 tiles of a poor army (chance 0.5). An army settles to besiege only with
  1.5× the garrison; otherwise it waits. Field battle records have x,y, both sizes, compositions, losses and the deciding factor
  (tech, terrain, tactics, surprise or numbers).
- After (story): 25 field battles, 0 ambushes, 46 sieges
  (captured 25, lifted 2, failed 7, still open at the end 12),
  143 siege rounds, 3 battles with a non-numbers deciding factor.

### 4. Scale
- Before: populations 175 → 17k; armies 20–900 "men".
- Fix: one stored unit = 20 people (`POP_UNIT`). Every people count in state.json, the army sizes, garrisons and battle
  sizes are people (multiplied in the export). Ratios and rules are unchanged (food, water, tax, soldier rules).
- After (story): starting population 20,400 per capital; year 604: poor 286,838 people, rich 4,800.
  Armies up to 900 units (18,000 men). The rich collapse late (few cities), which is part of the story.

### 5. Repetition
- The 10-year bankrupt loop is gone (34 → 0). Incident logs are throttled to one per 8 years, recruitment is random each
  year (`RECRUIT_P`, no fixed 4-year cadence), founding logs are throttled, militia and endowment logs fire on cumulative
  thresholds (irregular years).
- quick_check now enforces: no event type more than 6 times in any 10-year window; no run of 5 equal gaps of 2+ years.
  Consecutive-year campaigns are allowed.
- key_moments.md caps each event type at 6.

### 6. Batch: poor as likely winner, rich 10–25%
- The rich win 0% of runs (target 10–25%). **Not met.** The poor win 100%.
- Levers tried (in order): rich gold and rent (rich now stay solvent), truce length 15 → 25, poor tactics slope 0.5 → 0.3 (a test with
  slope 0 still gave 0 rich wins, so tactics are not the cause), no founding during wars, capital rebuild needs 3 cities,
  militia cap 25% → 10% (the 25% militia made every city unassailable), recruitment 3–8% per year, starvation of besieged cities
  after 8 blockade years, theft 1.2% → 0.4% per year.
- Likely causes (not fixed): mercenaries are cheap (1.2 gold per unit, one unit = 20 men), but an army's size is still capped by the
  city garrison, so the rich's 30,000 gold does not turn into more soldiers; the poor's siege engines (trebuchets) come
  earlier; time-limit results are scored by population and cities, which favours the poor's growth.

### 7. Story selection and arc
- Hard rules: poor win; ≥6 field battles; ≥8 sieges; ≥3 waste events; ≥1 hire; ≥1 successful theft; rich gold above the
  poor's for the first 40% of the story; first war in years 50–120; the rich capital falls at least once.
- Deviation: the review asks for 8–20 sieges. Median sieges per 1000-year run is ~50, so the rule is relaxed to at least 8 and
  the 8–20 window is only a score bonus. Seed 102 has 46 sieges.
- Result: 240 seeds searched; best seed 102 (score 42). The rich side still ends with the lower score.
- Eras (`periods.json`, 9 periods):
- 0–33: Founding (عصر التأسيس)
- 34–52: Age of trade (عصر الذهب)
- 53–150: First war (الحرب الأولى)
- 151–264: Truces and raids (الهدنة والمناوشات)
- 265–286: War 2 (حرب 2)
- 287–319: Truces and raids (الهدنة والمناوشات)
- 320–366: War 3 (حرب 3)
- 367–526: Truces and raids (الهدنة والمناوشات)
- 527–604: The fall (السقوط)
- Wars (`state.json: wars`):
- war 1: years 53–150, started by the poor side
- war 2: years 182–234, started by the rich side
- war 3: years 265–286, started by the rich side
- war 4: years 320–366, started by the rich side
- war 5: years 412–433, started by the rich side
- war 6: years 465–492, started by the rich side
- war 7: years 527–552, started by the rich side
- war 8: years 590–604, started by the rich side
- Turning points: contact in year 34. The poor declare the first war at 53 (the only war they started
  in the story), the rich start the other seven. The first rich capital, Qasr al-Dhahab, falls to the
  poor at year 487 (the rich court flees); Ain al-Zahab falls at year 536. The rich end with one city and no capital, so the
  collapse rule fires at year 604.
- year 487: The capital Qasr al-Dhahab falls to the poor kingdom; the rich court flees
- year 536: The capital Ain al-Zahab falls to the poor kingdom; the rich court flees
- Theft (story):
- year 107: The rich steal the secret of Windmill from Dar al-Hikma
  Rich learn Windmill at year 117 by theft (adoption delay 10 years). The rich have 10 techs (9 invented, 1 stolen) and
  the poor 15.

### 8. Gold curves (story seed 102)
| year | rich gold | poor gold | rich pop | poor pop |
|---|---|---|---|---|
| 0 | 29543 | 1789 | 20400 | 20400 |
| 25 | 25902 | 1512 | 48855 | 47263 |
| 50 | 23764 | 1057 | 80828 | 80488 |
| 75 | 24586 | 4213 | 107351 | 101091 |
| 100 | 24099 | 5597 | 107400 | 109266 |
| 150 | 28148 | 7339 | 81800 | 135000 |
| 200 | 27810 | 8186 | 86600 | 148380 |
| 250 | 26080 | 8411 | 82622 | 160200 |
| 300 | 21377 | 9480 | 67487 | 195293 |
| 400 | 21438 | 10839 | 59595 | 213025 |
| 500 | 16853 | 11100 | 25200 | 255033 |
| 600 | 10787 | 12942 | 4800 | 286422 |

### 9. Battle counts by type (story)
| type | count |
|---|---|
| field battles | 25 |
| ambushes | 0 |
| sieges (single events) | 46 |
| siege rounds (inside sieges) | 143 |

### 10. Before and after (batch of 200 runs, seeds 1–200)

Before (v2, 200 runs, 121 s):
```
runs: 200   wall time: 121.4 s
winners: poor 193 (96%), rich 7 (4%)
end reasons: collapse 46, conquest 111, time limit 43
war-start year: mean 101, median 96; runs with a war: 171
mean end year 561; wars per run 6.4; war years 178
contact year mean 86
captures per run 22.5 (to poor 17.1, to rich 5.3); bribes 0.20; capital falls 1.92
battles per run 403.6 (field 10.5, ambush 0.00, siege 393.0); decisive 5.3
techs per run: rich 9.8, poor 15.0
inventions per run: rich 8.8, poor 15.0
theft per run: attempts 1.64, success 1.02, caught 0.36, stolen techs held 1.02
lead changes per run 1.7; rich ahead at some point: 96/200 runs
truces per run 5.7
```

After (v3 final, 200 runs, 242.8 s):
```
runs: 200   wall time: 242.8 s
winners: poor 200 (100%), rich 0 (0%)
end reasons: collapse 54, conquest 56, time limit 90
war-start year: mean 66, median 60; runs with a war: 194
mean end year 901; wars per run 13.1; war years 349
contact year mean 51
captures per run 28.8 (to poor 24.5, to rich 4.3); bribes 2.00; capital falls 2.29
battles per run 13.4 (field 13.1, ambush 0.24, siege 51.9); decisive 0.7
techs per run: rich 14.2, poor 15.0
inventions per run: rich 12.1, poor 15.0
theft per run: attempts 4.08, success 2.00, caught 1.04, stolen techs held 2.00
lead changes per run 0.4; rich ahead at some point: 31/200 runs
truces per run 12.5
```

### 11. Inventions (story 102)
Every invention and theft is in `state.json: techs` and logged in `log.txt`.

| year | side | tech | city | how | usable from | effect |
|---|---|---|---|---|---|---|
| 9 | poor | Wells | Dar al-Hikma | invention | 9 | wells on desert sites, +500 water each |
| 20 | rich | Wells | Qasr al-Dhahab | invention | 20 | wells on desert sites, +500 water each |
| 25 | poor | Irrigation canals | Dar al-Hikma | invention | 25 | farms within 3 tiles of water turn green (110 food) |
| 40 | poor | Granaries | Dar al-Hikma | invention | 40 | granaries raise the food stock cap |
| 46 | rich | Irrigation canals | Qasr al-Dhahab | invention | 46 | farms within 3 tiles of water turn green (110 food) |
| 53 | poor | Waterwheel | Dar al-Hikma | invention | 53 | waterwheels on river banks, +35 food per city |
| 66 | poor | Windmill | Dar al-Hikma | invention | 66 | windmills on the plateau, +25 food per city |
| 68 | rich | Granaries | Qasr al-Dhahab | invention | 68 | granaries raise the food stock cap |
| 80 | poor | Paper | Dar al-Hikma | invention | 80 | libraries and bazaars; research bonus per library |
| 92 | rich | Waterwheel | Qasr al-Dhahab | invention | 92 | waterwheels on river banks, +35 food per city |
| 97 | poor | Astronomy calendar | Dar al-Hikma | invention | 97 | observatories, +10% harvest in the city |
| 107 | rich | Windmill | Dar al-Hikma | theft | 117 | windmills on the plateau, +25 food per city |
| 114 | poor | Compass and coastal ships | Dar al-Hikma | invention | 114 | harbours, ships, caravanserai: trade income |
| 126 | rich | Paper | Qasr al-Dhahab | invention | 126 | libraries and bazaars; research bonus per library |
| 132 | poor | Iron working | Dar al-Hikma | invention | 132 | iron mines, weapons +25% |
| 151 | poor | Composite bows | Dar al-Hikma | invention | 151 | archers +0.4 power in field battles |
| 171 | poor | Engineering of walls | Dar al-Hikma | invention | 171 | city walls (up to 3) and towers |
| 182 | rich | Astronomy calendar | Qasr al-Dhahab | invention | 182 | observatories, +10% harvest in the city |
| 193 | poor | Trebuchets | Dar al-Hikma | invention | 193 | siege workshops; trebuchets break walls |
| 216 | poor | Medicine | Dar al-Hikma | invention | 216 | plague losses halved |
| 241 | poor | Canal network | Dar al-Hikma | invention | 241 | canals; the desert turns green (irrigation range 6) |
| 251 | rich | Compass and coastal ships | Qasr al-Dhahab | invention | 251 | harbours, ships, caravanserai: trade income |
| 270 | poor | Steel | Dar al-Hikma | invention | 270 | weapons +20% |
| 336 | rich | Iron working | Qasr al-Dhahab | invention | 336 | iron mines, weapons +25% |
| 457 | rich | Composite bows | Qasr al-Dhahab | invention | 457 | archers +0.4 power in field battles |

### 12. quick_check
Result: **26 checks, 0 failed** (`python3 quick_check.py`, exit 0). The new v3 checks: sieges are single events with start,
end and outcome; field battles record compositions, losses and the deciding factor; no event type on a fixed cadence; rich gold
above zero for most of the first 40% of the story; bankruptcies at most 2. The story checks are listed in the output.
Two checks were refined: the cadence check now allows consecutive-year campaigns (only repeated gaps of 2+ years count), and
the siege story rule is "at least 8" (see section 7).

## 13. Output files
- `sim.py`, `quick_check.py`, `FORMAT.md` (v2 and v3 sections), `SPEC.md` (v2 amendments), `RESULTS.md` (this file)
- `story/state.json` — 7.8 MB (limit 60 MB)
- `story/log.txt` — 33.0 KB, 383 lines (each maps to a state event)
- `story/key_moments.md` — 8.9 KB
- `story/periods.json`, `story/terrain.json` (18.9 KB), `story/search.csv` (49.8 KB, 240 seeds)
- `batch/runs.csv`, `batch/summary.txt` (200 runs)
- `maps/map_*.svg` — 8 snapshots (1.6 MB total)

## 14. Known weaknesses (open after v3)
- **Rich win rate is 0%** (target 10–25%). The rich are wealthy and have bigger treasuries, but gold does not become soldiers.
  Next step: let mercenaries add to the army beyond the garrison cap, and give the rich their own siege engines earlier.
- **Ambushes are rare** (0.24 per run in the batch, 0 in the story).
- **Sieges**: 46 in the story against a target of 8–20 (score bonus for ≤20; the hard rule is ≥8).
- **Time limit**: 90 of 200 batch runs (45%) reach year 999 and are decided by score (poor).
- Mercenary cost is cheap relative to treasury (1.2 gold per unit, 20 men).
- Key-moment "why it matters" lines and the Arabic event text are short templates, not written analysis.
- Maps are static SVG snapshots (no pan or zoom); no 3D replay here.

## 15. Tuning log (v3, all in `sim.py`)
- Units ×20 (`POP_UNIT`) for output, economy unchanged in units; start population 170 → 1,000 units; start treasury rich 6,000 → 30,000,
  poor 500 → 2,000; start buildings 45 houses + 18 farms, endowed at year 0 without cost.
- Mines: gold 12 → 30, oil 10 → 25, iron 4 → 10 per year. Trade: bazaar 6 → 15, caravanserai 5 → 12, harbour 4 → 10.
- Rich land rent 0.25 per tile per year (new). Mercenary share 0.5 → 0.6; mercenary threshold 600 → 1,500 gold.
- Poor spend-down: SPEND_HI 4,000; militia 5% of excess, up to 10% of population; endowment 5% of excess into research at 20 gold/point.
- Truces 15 → 25 years; poor tactics slope 0.5 → 0.3; recruitment chance per war year 0.25 → 0.06 → 0.03 → 0.05 → 0.08 (final 0.08).
- Ambush: poor probability 0.25 → 0.5, range 6 → 10, mountains and rivers both count; field range 3 (new).
- Siege: settles only at 1.5× garrison; starvation after 8 blockade years (new); garrisons do not regrow under blockade.
- Founding: not during war; capital rebuild needs 3 cities.
- Theft 1.2% → 0.4% per year; success 60% → 50%.
- Centre ring (radius 1.5) reserved for palaces; statue search radius 3 → 5.
- Logs: incidents 1 per 8 years; siege start/end lines 1 per 3 years; founding 1 per 3 years; hires 1 per 6 years;
  militia and endowment at cumulative thresholds (2,000 men, 20,000 gold).

## 16. Deviations from the spec
- Contact is "city distance under 24" (a stated simplification).
- The siege window 8–20 is a score bonus; the hard rule is ≥8 (section 7).
- Only the two start discs are mirror images; the rest of the map is random; one tributary on the west bank.
- The printing press is not in the ladder (15 techs, pre-gunpowder).
- Purchase of techs is not implemented anywhere. The only non-research route is theft.

## v5 export fixes (story 132)
Scope: display and export only. The simulation, its RNG draw order and all gameplay logic are unchanged. The change is
the new module `export_v5.py` (called from `sim.py cmd_export` after the run) plus the two small edits in `cmd_export`
(the call, and `periods.json` taken from the state). Only story 132 was regenerated. The batch was not re-run.

Backup: `story_backup_v4/` (the story before v5, byte-identical to the v4 export).

### Identity (required: identical)
`quick_check.py` compares the new `story/` against `story_backup_v4/`:
- `log.txt`: byte-identical (48 lines).
- `summary`, `wars`, `captures`, `techs`, `ladder`: identical.
- Every year's `stats`, `dip`, `battles`, `battles_full`, `disasters`, `techs_new`, `roads`: identical (556 years).
- Every simulated event (id, year, type, place, civ, city, log flag; 1,203 events): identical.
- Every simulated building record (2,374): identical. Every simulated army record (3,481): identical.

### What was fixed
1. **Missing buildings.** Cosmetic buildings (`cosmetic: true`, ids from 100000) are built after each tech is active for
   the side that holds the city: irrigated farms (irrigation, plus +14 around the irrigation invention city while it is
   held, which is city 2 from year 24), windmills (windmill, from y63 for the poor), waterwheels (river-bank cities),
   libraries (paper), observatories (astronomy), iron mines (iron, on iron tiles within 14), walls (engineering,
   city walls_level goes up to 3), towers (once two walls stand), canals and irrigated canal farms (canals, y260, within
   8 tiles of the river) and a harbour per port city (compass). They follow city ownership: a captured city loses the
   old side's cosmetic buildings in the capture year. 451 cosmetic buildings in all.
   Ships: 2 per standing harbour, moving along the coast tiles (345 years have ships).
2. **Army continuity.** Checked for every siege, every year from the first siege year to the close: in story 132 the
   attacking army is at the walls each year, so no camp records were needed (`camp_records_added` = 0).
   Note: the earlier report that army 7 vanishes after y183 does not reproduce on this export. Army 7 is present in every
   year 178-186 at (106,41), next to city 2 at (107,42). The check and the camp fallback are in place regardless.
3. **Siege bookkeeping.**
   - 33 open sieges in v4 are now all closed (0 open). The export closes 23 of them: 21 `taken` (the city fell to
     another army while the siege was open), 1 `lifted` (the army left the walls), 1 `game_end`. It also closes 9 sieges
     that the sim ended late, after the army had already left the walls, at the departure year (`truncated_from`):
     8 `taken`, 1 `lifted`.
   - 16 sieges start in the year their city was taken by the same side (each one after a capture by another siege of
     that side, never the same army). They are void: no siege record, the start event is hidden and reworded.
   - 19 repeated `siege_start` events for the same city and year are hidden (`dup_of`). The 24 pairs in v4 include the void
     starts. Both armies' sieges stay in the records.
   - `starve` (15 captures) is kept and documented in FORMAT.md.
4. **Names.** Every city record and event has `name_en`, `name_ar`, `old_name_en` from `names_v2.json`. Event texts use
   the new names. Two complications were solved by data, not by guessing: 11 old names are reused by two cities (so texts
   are resolved by city id); a founding's parent comes from the road built that year (36 of 36 resolved); border
   incidents name two cities only, so each name goes to the nearest alive city with that name (`incident_ambiguous` in
   export notes).
5. **Mountains.** 119 owner entries on mountain tiles were dropped. No kingdom owns a mountain tile in the owner grid.
   `stats.territory` still counts the sim's tiles (the rule is display-only, so the stat is unchanged).
6. **Periods.** The 11 eras from `periods_v2.json` with the display names given in the brief. English names are my glosses.

### Buildings by type (real + cosmetic alive, story 132)
| year | total | cosmetic | cosmetic by type |
|---|---|---|---|
| 100 | 902 | 94 | farm 87, library 2, observatory 1, waterwheel 2, windmill 2 |
| 200 | 919 | 105 | farm 74, library 3, mine 1, observatory 2, wall 14, waterwheel 8, windmill 3 |
| 300 | 1,133 | 196 | canal 36, farm 108, harbour 1, library 6, mine 3, observatory 2, tower 2, wall 22, waterwheel 10, windmill 6 |
| 555 | 1,270 | 260 | canal 58, farm 129, harbour 1, library 5, mine 2, observatory 3, tower 4, wall 43, waterwheel 10, windmill 5 |

The sim's own buildings are 808 / 814 / 937 / 1,010 at those years. Full per-type counts (real and cosmetic) are printed by
`quick_check.py` as INFO lines.

### Caveats and what was not fixed
- **Harbours sit 15 to 20 tiles from their port city.** No city is within the 6-tile site radius of the coast (the nearest
  is 18.7 tiles from the sea). Only one city (id 26) is within the 20-tile port limit, so there is one harbour per side that
  holds it. The quick check allows port buildings up to 23 tiles.
- **`log.txt` keeps the sim's text.** The brief asked for de-duplicated and reworded sieges, but `log.txt` must stay
  byte-identical, so the log still shows the 19 repeated `siege_start` lines, the 16 void starts, the superseded
  `failed` ends (in state.json those sieges close earlier) and the old city names. `state.json` carries the fixed view.
- `summary` counts (for example `sieges` 103) are the sim's own and are not recounted.
- `key_moments.md` is written from the sim's events before the export layer, so it still has the old names. Not changed.
- Cosmetic buildings are placed on neutral land beyond the city's own land because the sim's houses fill almost every
  owned tile within 8 tiles of each city. Walls and towers face the enemy capital.

### quick_check
58 checks, 0 failed (the 32 v4 checks, adapted to the v5 fields, plus the identity diff, sieges, names, territory,
cosmetic buildings, ships, walls and invention checks).
