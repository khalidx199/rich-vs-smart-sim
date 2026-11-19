# story/state.json format (v2)

Top level:
- `summary`: end result and counts (see `sim.py summary()`), `winner`, `end_year`, `end_reason`.
- `wars`: list of `[start_year, end_year, attacker, battles]`. `end_year` is null only if a war is still running.
- `captures`: list of `[year, city_id, from, to, kind]`, kind = assault or bribe.
- `periods`: list of `[start, end, name_ar, name_en]`, contiguous, covering 0..end_year (6 to 12 eras).
- `techs`: per civ key, `{tech_key: {year, how, city, active, src}}`. `how` is `invention` (own research) or `theft`.
  `active` is the year the tech can be used (equal to `year` for inventions, 5 to 10 years later for thefts).
- `ladder`: the tech ladder `[key, name_en, name_ar, cost_rp, effect_en]`.
- `years`: one record per simulated year, from year 0 to `end_year`.

Per-year record (`years[i]`):
- `year`, `stats` (per civ: pop, gold, food, water, soldiers, techs, territory, cities, leader, rp),
  `dip` (status, tension).
- `cities`: every living city (full list each year).
- `owner_chg`: list of `[tile_index, owner]` changes since the previous record, owner -1 is neutral, 0 is rich, 1 is poor.
  `tile_index = y*160 + x`.
- `owner_full`: full owner grid as a 16000-character string (`.` neutral, `R` rich, `P` poor), only on snapshot years.
- `bld`: buildings that changed this year (built, owner changed, destroyed, irrigation flipped), full records.
- `bld_full`: all living buildings, only on snapshot years. Snapshot every 20 years (`snap_every` in the top level).
  Reconstruct: start from the last `bld_full`, then apply each `bld` record by `id`. A record with `destroyed` set is gone.
- `roads`: roads built this year. `roads_full`: all roads on snapshot years.
- `armies`: living armies this year, plus armies that ended this year (`end` set). Fields: id, owner, size, siege,
  comp {inf, cav, arch, merc}, cmdr, x, y, mode, `wp` (the waypoints travelled this year, the last one is the army
  position at the end of the movement step), target, end.
- `battles_full`: battles this year (id, year, x, y, type field/ambush/siege, att/def civ, army ids, sizes, losses,
  result, notes, decisive tech keys, event id).
- `events`: every event of the year (id, year, type, x, y, civ, city, text_en, text_ar, log). `log=true` lines are in log.txt.
- `disasters`: active disasters (drought lasts several years; sandstorm, locust, flood, plague are one-year events).
  Each has type, x, y, r (radius), start, end.
- `ships`: `[x, y, civ]` for each standing harbour's ship.
- `techs_new`: `[civ_index, key, how]` for techs that completed this year.

Coordinates: `x` 0..159 (west to east), `y` 0..99 (north to south). The sea is the south edge.

## v3 changes (review)
- **Units.** Every people count, army size, garrison and battle size in state.json is a number of people
  (`pop`, `soldiers`, `food`, `water`, army `size` and `comp`, battle sizes and losses, siege sizes). Internally the
  simulation counts units of 20 people (`POP_UNIT`); the export multiplies by 20. Gold is not scaled.
- **Sieges are single events.** `years[i].sieges` lists a siege record when it starts (`end` null) and again when it
  ends (`end` set, `outcome` = captured | lifted | failed). Fields: id, army, att_civ, city, city_name, x, y, start, end,
  rounds (one round per year of siege), att_loss, def_loss, att_start, def_start, engines, outcome.
  A siege is NOT a battle record; `battles_full` holds only field and ambush battles.
- **Field and ambush battles** (`battles_full`): id, year, x, y, type (field | ambush), att_civ, def_civ, att_army, def_army,
  att_size, def_size, att_loss, def_loss, `att_comp` and `def_comp` (inf, cav, arch, merc), result, decisive (list:
  `tech:<key>`, `terrain`, `tactics`, `surprise` or `numbers`), factor (the same list as text), event id.
- **Events added:** `hire` (rich mercenaries: count, cost), `waste` (kind = feast | statue | palace), `militia`
  (poor surplus into soldiers), `endowment` (poor surplus into research points), `overtake` (the poor's income passes
  the rich's), `siege_start`, `siege_end`. Logged lines are throttled or cumulative so that no event type fires on a
  fixed cadence.
- **Rich income:** a royal-domain rent of 0.25 gold per owned tile per year, mines, taxes, trade after contact.

## v5 export fixes (story 132; export layer in `export_v5.py`)
The simulation is unchanged: every logged event, stat, capture, tech, war and battle is identical to the pre-v5 export
(`quick_check.py` checks this against `samples/story_seed132/`). Everything below is display or export only. `log.txt` is byte-identical to v4.

- `captures`: kind = `assault` | `bribe` | `starve`. **`starve`** means the city surrendered during the siege, after
  `STARVE_YEARS` blockade years with no relief (stored food gone, no reinforcements). The garrison is cut to a third and
  the city changes hands with the normal capture rules. It is a valid outcome and is kept.
- `periods`: the 11 eras of `periods_v2.json` with the display names below. `[start, end, name_ar, name_en]`, covering 0..555.
  0-71 «عصر نبني ونشوف», 72-79 «عصر الكشخة», 80-96 «الحرب الأولى: سوء تفاهم», 97-139 «هدنة وسرقة أسرار»,
  140-216 «الحرب الكبرى», 217-247 «هدنة: فاصل ونواصل», 248-302 «حرب الثأر», 303-352 «الحرب الرابعة: رجعنا لكم»,
  353-455 «زمن الجيران المزعجين», 456-492 «بداية النهاية», 493-555 «السقوط». (English names are glosses.)
- Cities (in every `years[i].cities` record): `name_en`, `name_ar` (from `story/names_v2.json`), `old_name_en` and
  `old_name_ar` (the sim's names). The sim reuses 11 old names for two cities each, so use `id`, not the name.
  `walls` is the sim's wall count. **`walls_level`** (0-3) = min(3, `walls` + cosmetic wall segments alive).
- Events: every event has `name_en`, `name_ar`, `old_name_en` (null if it names no city). `text_en`/`text_ar` use the
  new names. A founding's parent is the other end of the road built that year. Incident texts name two cities by
  name; each is resolved to the nearest alive city of that name.
  - `hidden: true`: not for display. Used for a void siege start or end, a repeated `siege_start` for the same city
    and year (`dup_of` = the event kept), and a siege end that was superseded (`superseded: true`, see sieges).
  - `void: true`: a siege start in the year its city was taken by the same side (no siege; the army just arrives).
    Its text is replaced in state.json; `log.txt` keeps the sim's line.
  - `cosmetic: true` events have type `siege_close` (log false), placed at the year a siege closes.
- Sieges (`years[i].sieges`): every siege has an end record. `outcome` is `captured` (this army took the city), `taken`
  (the city fell to another army, or another side, while the siege was open), `lifted` (the attacker left the walls,
  the war or truce ended), `failed` (the army was destroyed or repulsed), or `game_end`. A void siege has no records.
  Records with `reconstructed: true` were closed by the export: `rounds` is then an estimate (`rounds_estimated`).
  `truncated_from` = the sim's own end year when the army had already left the walls earlier. The export closes the
  siege at the departure year, and the sim's end event for that siege is marked `superseded` (the sim's log line remains).
- Armies: the attacking army of every siege is at the walls (within one tile) every year from the first siege year
  until the siege closes. If the sim has no record for it, a siege-camp record is added: `camp: true`, `cosmetic: true`,
  `cmdr` "siege camp". `cosmetic_pos: true` marks a moved position. In story 132 neither was needed.
- Buildings: a `bld` record with `cosmetic: true` is an extra building added by the export. Its `id` is at least 100000,
  `rule` says which rule placed it (walls, tower, irrfarm, windmill, waterwheel, library, observatory, ironmine, canal,
  canalfarm, harbour), and it carries the same fields as a sim building. Harbours also have `port: true` and
  `port_dist`. Cosmetic buildings are built on desert, silt, oasis or plateau tiles of the city's own land first, then on
  neutral land, within 9-14 tiles of the city. Harbours are 20 tiles or less from their port city (see RESULTS v5).
  A captured city's cosmetic buildings of the old side are destroyed in the capture year, and the new side builds its own.
  Snapshots (`bld_full`) hold the simulated and cosmetic buildings alive in that year, and equal the replay of all deltas.
- Ships: `ships` lists `[x, y, civ]`, two per standing cosmetic harbour, moving along the coast tiles near the harbour.
- Owner grid: mountain tiles are never owned (`owner_chg`, `owner_full`). `stats.territory` keeps the sim's count.
