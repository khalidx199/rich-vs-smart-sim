# sim3_worldbox: spec

Goal: a WorldBox-style history of two kingdoms on ONE timeline (no fork). We need to SEE everything grow: buildings, roads, cities and
expansion over a large map, inventions by the poor, wealth by the rich, and then a war that unfolds at a natural year. The poor (smart)
side should most likely win, and the history must be rich with events. The output drives a 3D replay: one big horizontal map plane,
with the camera panning and zooming to wherever the story is.

Earlier versions (sim1, sim2_twin_worlds) stay untouched. Only stdlib Python 3.9 (/usr/bin/python3) is available; there is no numpy.

## Names (fictional, Middle East flavour, no real peoples or religions)
- Rich, low intelligence: «الأثرياء» (al-Athriyaa'). The leader title is Sultan.
- Poor, high intelligence: «الفقراء» (al-Fuqaraa'). The leader title is Ra'is.
- Use the constants CIV_NAMES = {0: "الأثرياء", 1: "الفقراء"}; English keys: rich / poor. City names come from Arabic-flavoured fictional lists per side.

## World
- The grid is 160 × 100 tiles: big enough that expansion takes a long time.
- Terrain: desert (most), a main river N→S plus one tributary, oases, a coast on one edge, mountain ranges, and rocky plateaus.
- Resource tiles: gold, oil seeps, iron, clay, date palms, fish.
- The two starting regions mirror each other across the river, so the land is fair.
- Weather/disasters: drought, sandstorm, locusts, flood (fertile silt), plague. They hit regionally (with a centre and a radius) so they can be animated.

## Time
- Yearly ticks, 300 years.
- For animation, each year also records army WAYPOINTS: a polyline of positions within the year, plus battle positions.

## Entities (everything with x,y so it can be drawn)
- **City:** id, name, owner, x, y, founded_year, pop, tier (village → town → city → capital), walls_level 0–3, garrison, captured_history[(year, from, to)].
- **Building:** id, city_id, type, x, y (an actual tile near its city), built_year, destroyed_year, owner.
  - Types: house, farm (irrigated or dry), well, granary, market, workshop, library/academy (poor), observatory (poor), windmill/waterwheel (poor),
    mine (gold/iron), palace, statue (gold), bazaar, caravanserai, harbour, wall segment, tower, barracks, siege workshop.
  - Cities visibly GROW: houses and farms fill the tiles around the city as pop rises.
- **Road:** a polyline between connected cities, with built_year.
- **Army:** id, owner, size, composition (infantry / cavalry / archers / mercenaries / siege engines), commander name, current x,y, waypoints for the year, target.
- **Battle:** year, x, y, attacker, defender, sizes, losses, result, type (field / siege / ambush), city_id if a siege, notes (e.g. a tech that mattered).
- **Tech / invention** (poor side mostly; the rich side gets a few slowly, or buys them):
  - Each has id, name_ar, name_en, year, city where it was invented, and effect.
  - Ladder (medieval-plausible): wells → irrigation canals → granaries → waterwheel → windmill → paper → astronomy calendar (better harvests)
    → compass + coastal ships/trade → iron working → composite bows → engineering (walls) → catapults/trebuchets → medicine (plague resistance)
    → canal network ("the desert turns green") → steel → printing press? (optional) → gunpowder-free.
  - Keep it pre-gunpowder.
  - Each invention must have a visible effect on the map or the stats: new building types appear, farms turn green, ships appear, walls rise, and so on.
- **Rich side mechanics** (SEE UPDATE 2: no tech buying): a big starting treasury; gold and oil mines found by luck; mercenaries; bribes; palaces and statues; buying food.
  - Low intelligence means wasteful decisions, slow research and poor tactics (no flanking, attacking walls head-on).
  - (removed) The rich side can NOT buy techs; it researches its own, more slowly.

## Phases (emergent, not hard-coded, but tune so they usually happen)
1. **Founding and growth:** both expand into neutral land, found cities, and build.
2. **Contact:** the borders meet (roughly years 40–90). There is trade first (caravans, a bazaar), then tension (border incidents, raids).
3. **War** starts at a natural trigger: a border incident, a resource dispute (an oil/gold tile between them), or an insult.
   - There can be several wars and truces.
   - Armies move along roads and terrain; there are sieges and field battles; cities change hands BACK AND FORTH.
4. **Resolution:** decisive conquest or collapse, ideally before year 300.

## Named periods
Compute and export named periods for the on-screen timeline bar, e.g. «عصر التأسيس», «عصر الذهب», «عصر الاختراعات», «الحرب الأولى», «الهدنة»,
«الحرب الكبرى», «السقوط». Periods come from the state: (start, end, name_ar, name_en).

## Outputs (into sim3_worldbox/)
- `sim.py`: all parameters at the top. A `--quick` mode.
- `batch`: 200 runs (Pool(4) max). Win rates, average war-start year, end year, number of city captures, techs per side.
- Story selection: search seeds for the best story where the POOR win decisively. Score:
  - number of lead changes;
  - cities changing hands (both directions);
  - the rich ahead at some point (a scary moment);
  - at least one invention that visibly decides a battle (e.g. the trebuchet breaks rich walls, composite bows win a field battle);
  - a war start between years 50 and 120;
  - a final fall of the rich capital;
  - total ≥ 12 battles.
- `story/state.json`: per year, with full lists:
  - cities, buildings (current), roads, armies with waypoints, battles that year, events that year (type, x, y, text_en, text_ar);
  - civ stats (pop, gold, food, water, soldiers, techs, territory tiles, number of cities, leader);
  - the owner grid as compact strings.
  - Keep it under about 60 MB. Round floats. The buildings list may be a delta (added/removed per year) with a full snapshot every 10 years if size is an issue; document the format in FORMAT.md.
- `story/terrain.json`: the static map.
- `story/log.txt`: a readable chronicle, one line per notable event.
- `story/key_moments.md`: 25–40 cinematic moments in time order: year, place (x,y and city), what happens, why it matters. Mark the inventions.
- `story/periods.json`.
- `RESULTS.md`: setup, batch numbers, the story seed and why it was chosen, the story arc (phases, wars, turning points), inventions with the years and cities where they were made, honest caveats and any tuning done after looking at results.
- `maps/`: about 8 SVG snapshots of the story at key years, showing buildings, roads, armies and borders.
- `quick_check.py`: sanity tests (see below).

## Speed
The full batch plus story search must finish in under ~10 minutes on 4 processes. A single story run must take under ~10 s.

## Sanity checks the code must pass (quick_check.py)
- No building on water or mountain tiles. Buildings sit within radius R of their city.
- City owner = the owner of its tile. A captured city's buildings change owner; some are destroyed.
- Pop is never negative. Gold is never below 0 (debt is shown as an event, not a negative number).
- Every battle has an attacker army that was present at x,y (its waypoint ends there), and the losses ≤ the army sizes.
- An invention's effect only applies after its year. The rich never have a tech before they invent it or buy it.
- Every event line in log.txt maps to an event in state.json.

## Update (user, 2026-11-13)
- Up to 1000 years, like the reference video, but END as soon as a side wins.
- Win = the loser's last city falls, OR the loser has no capital, fewer than 2 cities, and less than 10% of the winner's pop for 5+ years.
- A typical game should resolve in about 200–700 years. Expect 6–12 named periods.

## Update 2 (user, 2026-11-13): the rich must invent too
- There is NO buying of techs. Both sides research the same ladder.
- Speed = base × intelligence, plus a capped bonus from gold spent on academies/scholars. The rich still invent about 2–4× slower.
- Inventions for both sides are logged with year, city and effect.
- New quick_check rule: a tech is only ever gained by that side's own research.

## Update 3 (user, 2026-11-13): stealing after contact
- After contact (borders meet or a trade line opens), the rich may STEAL techs the poor already have. Buying is still banned.
- Each theft is a logged event with year, source city and tech. It costs gold, can fail, and a caught spy raises tension (a possible war trigger).
- Stolen techs take 5–10 years to adopt.
- Tune it so theft narrows the gap but the rich stay behind on most techs.
- New quick_check rule: every rich tech comes from own research OR a logged successful theft after contact.


## v2 amendments (user change requests, applied in sim.py)
- **Length:** the simulation runs up to 1000 years (`MAX_YEARS = 1000`) and ENDS as soon as one side wins:
  - conquest: the loser loses its last city;
  - collapse: the loser has no capital, fewer than 2 cities and under 10% of the winner's population for 5 years;
  - otherwise at year 999 the side with the higher score wins (time limit).
- **No tech purchases.** Both sides research the same 15-tech ladder. The rich research at 0.4 times the poor
  intelligence factor and get a capped scholar bonus (paid in gold), so they invent about 2 to 3 times slower.
  Every invention is logged with year, city and effect (both sides).
- **Espionage (the only other route for the rich).** After contact, the rich may attempt to steal a tech the poor
  have and the rich lack (lowest ladder index first). Each attempt costs gold. Success gives the tech with a
  5 to 10 year adoption delay, logged as `theft`. A failed attempt is sometimes caught and logged as `spy_caught`,
  which adds border tension. Failed attempts that are not caught are silent.
- **Contact** means the city distance between the two sides is under 24 tiles (claims meet). This is a
  simplification of "the borders meet", recorded in RESULTS.md.
- **State format:** owner grid and buildings are delta-coded with a snapshot every 20 years (FORMAT.md).
