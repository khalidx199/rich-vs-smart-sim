"""v5 export layer for story 132 (display and export only).

sim.py cmd_export() calls apply() after the simulation has run and the records exist. Nothing here
calls the simulation, draws from its RNG, or changes its state. Each change is one of:
  - a field added to an existing record (names, walls_level, old_name_en, hidden/dup_of/void flags);
  - a record that carries cosmetic: true (cosmetic buildings, siege-camp armies, siege_close events).

log.txt is written by sim.py from sim.events and is not touched here.
Stdlib only.
"""
import json
import math
import os
import random
from collections import defaultdict

W, H = 160, 100
BUILD_CH = set("dsop")           # desert, silt, oasis, plateau (the sim's BUILDABLE)
COS_ID0 = 100000                 # cosmetic building ids start here (sim ids are far below)
PORT_MAX = 20.0                  # a harbour needs a coast within this many tiles of its city
INV_BOOST = 14                   # extra irrigated farms around the irrigation invention city
ERA_EN = ["The Age of Building and Seeing", "The Age of Swagger", "The First War: A Misunderstanding",
          "Truce and Stolen Secrets", "The Great War", "Truce: A Pause, Then On We Go",
          "The War of Revenge", "The Fourth War: We Are Back", "The Age of the Annoying Neighbours",
          "The Beginning of the End", "The Fall"]
ERA_AR = ["عصر نبني ونشوف", "عصر الكشخة", "الحرب الأولى: سوء تفاهم", "هدنة وسرقة أسرار", "الحرب الكبرى",
          "هدنة: فاصل ونواصل", "حرب الثأر", "الحرب الرابعة: رجعنا لكم", "زمن الجيران المزعجين",
          "بداية النهاية", "السقوط"]
ERA_BOUNDS = [(0, 71), (72, 79), (80, 96), (97, 139), (140, 216), (217, 247), (248, 302), (303, 352),
              (353, 455), (456, 492), (493, 555)]
SIDE = {"rich": 0, "poor": 1}
SIDE_KEY = {0: "rich", 1: "poor"}


def _offsets(R):
    out = []
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            d = math.hypot(dx, dy)
            if 0 < d <= R + 1e-9:
                out.append((dx, dy, d))
    out.sort(key=lambda t: (t[2], t[0], t[1]))
    return out


OFF = {R: _offsets(R) for R in range(1, 16)}


def _bfs(sources, maxd=40):
    dist = [999] * (W * H)
    frontier = list(sources)
    for s in frontier:
        dist[s] = 0
    d = 0
    while frontier and d < maxd:
        d += 1
        nxt = []
        for i in frontier:
            x, y = i % W, i // W
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H:
                        j = ny * W + nx
                        if dist[j] > d:
                            dist[j] = d
                            nxt.append(j)
        frontier = nxt
    return dist


# ---------------------------------------------------------------------------
# 1. sieges: void same-year re-sieges, close every open siege, de-duplicate start events,
#    and keep the attacking army at the walls until the siege closes
# ---------------------------------------------------------------------------
def _sieges(state, notes):
    years = state["years"]
    end = state["summary"]["end_year"]
    caps = state["captures"]
    start, endrec = {}, {}
    for r in years:
        for s in r["sieges"]:
            if s["end"] is None:
                start.setdefault(s["id"], (r["year"], s))
            else:
                endrec.setdefault(s["id"], (r["year"], s))
    arm = {r["year"]: {a["id"]: a for a in r["armies"]} for r in years}
    status = {r["year"]: r["dip"]["status"] for r in years}
    rec_at = {r["year"]: r for r in years}

    def departure(sid, sy, s, upto):
        """First year in (sy, upto) in which the siege is over for the sim's purposes: city taken by
        anyone, war over, army gone, or army no longer sieging its city. None if it runs to `upto`."""
        city, army = s["city"], s["army"]
        for y in range(sy + 1, upto):
            if any(c[0] == y and c[1] == city for c in caps):
                return y, "taken"
            if status[y] != "war":
                return y, "lifted"
            a = arm[y].get(army)
            if a is None or a.get("end") is not None:
                return y, "lifted"
            if a["mode"] != "siege" or a["target"] != city:
                return y, "lifted"
        return None

    # a siege that starts in the year its city was taken by the same side is void
    void = set()
    for sid, (sy, s) in start.items():
        if any(c[0] == sy and c[1] == s["city"] and c[3] == s["att_civ"] for c in caps):
            void.add(sid)

    closed = {}                       # sid -> (close year, outcome) for every non-void siege
    truncated = {}                    # sid -> sim end year, for sieges the sim left open after the army left
    for sid, (sy, s) in start.items():
        if sid in void:
            continue
        if sid in endrec:
            E, es = endrec[sid]
            d = departure(sid, sy, s, E)
            if d is not None:
                truncated[sid] = E
                closed[sid] = d
            else:
                closed[sid] = (E, es["outcome"])
            continue
        d = departure(sid, sy, s, end + 1)
        if d is None:
            d = (end, "game_end")
        closed[sid] = d

    # records: void sieges leave the lists; truncated and open sieges get their end record at the close year
    for r in years:
        r["sieges"] = [g for g in r["sieges"] if g["id"] not in void]
    for sid, E in truncated.items():
        rec_at[E]["sieges"] = [g for g in rec_at[E]["sieges"] if g["id"] != sid]
        for e in rec_at[E]["events"]:
            if e.get("siege") == sid and e["type"] == "siege_end":
                e["hidden"] = True
                e["superseded"] = True
    ev_n = [0]
    for sid, (close, outcome) in closed.items():
        sy, s = start[sid]
        if sid in endrec and sid not in truncated:
            continue
        e = dict(s)
        e.update({"end": close, "outcome": outcome, "reconstructed": True,
                  "rounds": max(0, close - sy), "rounds_estimated": True})
        if sid in truncated:
            e["truncated_from"] = truncated[sid]
        rec_at[close]["sieges"].append(e)
        ev_n[0] += 1
        rec_at[close]["events"].append({
            "id": "x%05d" % ev_n[0], "year": close, "type": "siege_close", "x": s["x"], "y": s["y"],
            "civ": None, "city": s["city"],
            "text_en": "Siege of %s closes: %s" % (s["city_name"], outcome),
            "text_ar": "انتهاء حصار %s: %s" % (s["city_name"], outcome), "log": False, "cosmetic": True,
            "siege": sid})

    # siege camps: the attacking army stays at the walls from its first siege year until the close
    added = 0
    fixed = 0
    for sid, (close, outcome) in closed.items():
        sy, s = start[sid]
        last_year = close if outcome in ("taken", "failed", "game_end") else close - 1
        size = s["att_start"]
        for r in years:
            y = r["year"]
            if y < sy or y > last_year:
                continue
            found = next((a for a in r["armies"] if a["id"] == s["army"]), None)
            if found is None:
                r["armies"].append({"id": s["army"], "owner": s["att_civ"], "size": size, "siege": 0,
                                    "comp": {"inf": size, "cav": 0, "arch": 0, "merc": 0},
                                    "cmdr": "siege camp", "x": s["x"], "y": s["y"], "mode": "siege",
                                    "wp": [[s["x"], s["y"]]], "target": s["city"], "end": None,
                                    "cosmetic": True, "camp": True})
                added += 1
            else:
                size = found["size"]
                if max(abs(found["x"] - s["x"]), abs(found["y"] - s["y"])) > 1 and y < close:
                    found["x"], found["y"] = s["x"], s["y"]
                    found["wp"] = [[s["x"], s["y"]]]
                    found["cosmetic_pos"] = True
                    fixed += 1

    # events: void sieges hidden; repeated siege_start events for the same city and year hidden
    seen = {}
    nvoid = 0
    ndup = 0
    for r in years:
        for e in r["events"]:
            if e.get("siege") in void and e["type"] in ("siege_start", "siege_end"):
                e["void"] = True
                e["hidden"] = True
                if e["type"] == "siege_start":
                    nvoid += 1
                    e["text_en"] = "The %s army reaches {CITY}, already its own side's city that year (no siege)" % (
                        e["civ"])
                    e["text_ar"] = "وصول جيش إلى مدينة استولى عليها جانبه في السنة نفسها (بلا حصار)"
                    e["_void_city"] = e["city"]
            elif e["type"] == "siege_start":
                key = (e["city"], r["year"])
                if key in seen:
                    e["hidden"] = True
                    e["dup_of"] = seen[key]
                    ndup += 1
                else:
                    seen[key] = e["id"]
    notes["sieges_void"] = len(void)
    notes["sieges_closed_by_reconstruction"] = sum(1 for sid in closed if sid not in endrec or sid in truncated)
    notes["sieges_truncated_to_departure"] = len(truncated)
    notes["sieges_closed_outcomes"] = {o: sum(1 for v in closed.values() if v[1] == o)
                                       for o in sorted(set(v[1] for v in closed.values()))}
    notes["camp_records_added"] = added
    notes["army_positions_fixed"] = fixed
    notes["void_start_events_hidden"] = nvoid
    notes["siege_start_duplicates_hidden"] = ndup


# ---------------------------------------------------------------------------
# 2. names and text
# ---------------------------------------------------------------------------
def _sub_once(text, mapping):
    """Replace every key of mapping in one pass (longest first), so one replacement cannot feed another."""
    if not mapping:
        return text
    keys = sorted(mapping, key=len, reverse=True)
    out, i = [], 0
    while i < len(text):
        for k in keys:
            if k and text.startswith(k, i):
                out.append(mapping[k])
                i += len(k)
                break
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _names(state, names_path, notes):
    with open(names_path, encoding="utf-8") as f:
        names = {int(k): v for k, v in json.load(f).items()}
    old_en, old_ar = {}, {}
    for r in state["years"]:
        for c in r["cities"]:
            old_en.setdefault(c["id"], c["name_en"])
            old_ar.setdefault(c["id"], c["name_ar"])
    notes["name_mismatch_old_en"] = [cid for cid in old_en if names[cid]["old_en"] != old_en[cid]]
    # The sim reuses old names (11 names belong to two cities each), so a name alone does not identify a
    # city. A city event names its city by id. A founding names its parent: the other end of the road the
    # sim built from the new city that year. A border incident names two cities by name only: each name is
    # resolved to the nearest city of that name alive that year.
    road_of = defaultdict(list)
    for r in state["years"]:
        for rd in r["roads"]:
            road_of[(r["year"], rd["a"])].append(rd["b"])
            road_of[(r["year"], rd["b"])].append(rd["a"])
    stats = {"found_parent": 0, "incident_names": 0, "incident_ambiguous": 0}
    unresolved = []
    for r in state["years"]:
        for c in r["cities"]:
            c["old_name_en"] = old_en[c["id"]]
            c["old_name_ar"] = old_ar[c["id"]]
            c["name_en"] = names[c["id"]]["en"]
            c["name_ar"] = names[c["id"]]["ar"]
        for g in r["sieges"]:
            g["city_name"] = names[g["city"]]["en"]
            g["old_city_name"] = old_en[g["city"]]
        alive_by_name = defaultdict(list)
        for c in r["cities"]:
            alive_by_name[old_en[c["id"]]].append(c)
        for e in r["events"]:
            cid = e.get("city")
            if cid is None:
                e["name_en"] = None
                e["name_ar"] = None
                e["old_name_en"] = None
                mapping_en, mapping_ar = {}, {}
                for nm, cands in alive_by_name.items():
                    if nm in e["text_en"]:
                        if len(cands) > 1:
                            stats["incident_ambiguous"] += 1
                        best = min(cands, key=lambda c: (math.hypot(c["x"] - e["x"], c["y"] - e["y"]), c["id"]))
                        mapping_en[nm] = names[best["id"]]["en"]
                        mapping_ar[old_ar[best["id"]]] = names[best["id"]]["ar"]
                        stats["incident_names"] += 1
                e["text_en"] = _sub_once(e["text_en"], mapping_en)
                e["text_ar"] = _sub_once(e["text_ar"], mapping_ar)
                continue
            e["name_en"] = names[cid]["en"]
            e["name_ar"] = names[cid]["ar"]
            e["old_name_en"] = old_en[cid]
            if e["type"] == "found":
                pold = e["text_en"].split("linked to ")[-1]
                cands = [o for o in road_of.get((r["year"], cid), []) if o != cid and old_en[o] == pold]
                if len(cands) == 1:
                    e["text_en"] = "%s founded by the %s kingdom, linked to %s" % (
                        names[cid]["en"], e["civ"], names[cands[0]]["en"])
                    stats["found_parent"] += 1
                else:
                    unresolved.append(e["id"])
                e["text_ar"] = _sub_once(e["text_ar"], {old_ar[cid]: names[cid]["ar"]})
                continue
            e["text_en"] = _sub_once(e["text_en"], {old_en[cid]: names[cid]["en"]})
            e["text_ar"] = _sub_once(e["text_ar"], {old_ar[cid]: names[cid]["ar"]})
            if "{CITY}" in e["text_en"]:
                e["text_en"] = e["text_en"].replace("{CITY}", names[e["_void_city"]]["en"])
            e.pop("_void_city", None)
    notes["names_text_stats"] = stats
    notes["found_parents_unresolved"] = unresolved
    notes["names_checked_cities"] = len(names)


# ---------------------------------------------------------------------------
# 3. cosmetic buildings, walls levels and ships
# ---------------------------------------------------------------------------
def _cos_rec(b):
    out = {"id": b["id"], "city": b["city"], "type": b["type"], "x": b["x"], "y": b["y"],
           "owner": b["owner"], "built": b["built"], "destroyed": b["destroyed"], "irr": b["irr"],
           "res": b["res"], "cosmetic": True, "rule": b["rule"]}
    if b.get("port"):
        out["port"] = True
        out["port_dist"] = b["port_dist"]
    return out


def _cosmetic(state, tch, res_list, seed, notes):
    years = state["years"]
    rng = random.Random(seed * 1009 + 77)
    dist_river = _bfs([j for j in range(W * H) if tch[j] == "r"])
    dist_oasis = _bfs([j for j in range(W * H) if tch[j] == "o"])
    sea = [j for j in range(W * H) if tch[j] == "~"]

    real_tiles, road_tiles, real_canal = set(), set(), set()
    cities_xy = {}
    for r in years:
        for b in r["bld"]:
            real_tiles.add(b["y"] * W + b["x"])
            if b["type"] == "canal":
                real_canal.add(b["y"] * W + b["x"])
        for rd in r["roads"]:
            for x, y in rd["pts"]:
                road_tiles.add(y * W + x)
        for c in r["cities"]:
            cities_xy.setdefault(c["id"], (c["x"], c["y"]))
    centre_zone = set()
    for cx, cy in cities_xy.values():
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if 0 <= cx + dx < W and 0 <= cy + dy < H:
                    centre_zone.add((cy + dy) * W + cx + dx)

    coast_land = []
    for j in range(W * H):
        if tch[j] in BUILD_CH:
            x, y = j % W, j // W
            if any(0 <= x + dx < W and 0 <= y + dy < H and tch[(y + dy) * W + x + dx] == "~"
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                coast_land.append(j)
    port_dist = {}
    for cid, (cx, cy) in cities_xy.items():
        dmin = min(math.hypot(cx - j % W, cy - j // W) for j in sea)
        if dmin <= PORT_MAX:
            port_dist[cid] = dmin
    ports = {}
    for cid in sorted(port_dist):
        cx, cy = cities_xy[cid]
        cands = sorted(coast_land, key=lambda j: (math.hypot(cx - j % W, cy - j // W), j))
        ports[cid] = [j for j in cands if math.hypot(cx - j % W, cy - j // W) <= PORT_MAX + 2][:60]

    iron_j = [y * W + x for x, y, kind, hidden in res_list if kind == "iron" and not hidden]

    # key, tech, building type, outer radius, allowed terrain, irrigated?, gap range (years between
    # builds), minimum distance from the city centre. The sim's own houses fill nearly every owned tile
    # within 5 to 8 tiles, so cosmetic buildings take owned tiles first and then neutral land out to the radius.
    RULES = [
        ("walls", "engineering", "wall", 9, BUILD_CH, False, (3, 8), 4.0),
        ("tower", "engineering", "tower", 9, BUILD_CH, False, (2, 4), 4.0),
        ("irrfarm", "irrigation", "farm", 12, set("sod"), True, (1, 3), 2.0),
        ("windmill", "windmill", "windmill", 9, BUILD_CH, False, (1, 4), 2.0),
        ("waterwheel", "waterwheel", "waterwheel", 10, BUILD_CH, False, (1, 3), 2.0),
        ("library", "paper", "library", 9, BUILD_CH, False, (2, 6), 2.0),
        ("observatory", "astronomy", "observatory", 9, BUILD_CH, False, (2, 6), 2.0),
        ("ironmine", "iron", "mine", 14, BUILD_CH, False, (2, 6), 2.0),
        ("canal", "canals", "canal", 12, set("d"), False, (1, 2), 2.0),
        ("canalfarm", "canals", "farm", 12, set("sd"), True, (1, 2), 2.0),
        ("harbour", "compass", "harbour", 0, BUILD_CH, False, (0, 0), 0.0),
    ]
    TIER_TARGET = {
        "walls": {"village": 1, "town": 2, "city": 3, "capital": 3},
        "windmill": {"village": 0, "town": 1, "city": 1, "capital": 2},
        "library": {"village": 0, "town": 1, "city": 1, "capital": 2},
        "observatory": {"village": 0, "town": 0, "city": 1, "capital": 1},
        "irrfarm": {"village": 2, "town": 3, "city": 4, "capital": 4},
        "ironmine": {"village": 1, "town": 1, "city": 1, "capital": 1},
    }

    cos_all = []
    alive = defaultdict(list)            # city id -> alive cosmetic buildings
    used = real_tiles | road_tiles | centre_zone
    real_canal_now = set(real_canal)
    next_ok = {}
    next_id = [COS_ID0]
    counts = defaultdict(int)
    state_side = {}
    owner = [-1] * (W * H)
    invention = {}
    tech_active = {}
    cities_now = {}

    def near_water(j, R):
        if dist_river[j] <= R or dist_oasis[j] <= R:
            return True
        x0, y0 = j % W, j // W
        for dx in range(-R, R + 1):
            for dy in range(-R, R + 1):
                x, y = x0 + dx, y0 + dy
                if 0 <= x < W and 0 <= y < H and (y * W + x) in real_canal_now:
                    return True
        return False

    def tiles_ok(j, k):
        # the side's own land first (see pick), neutral land otherwise; never another kingdom's land
        return j not in used and owner[j] in (k, -1)

    def target(rule_key, c, k):
        tier, cid = c["tier"], c["id"]
        j0 = c["y"] * W + c["x"]
        if rule_key == "walls":
            return TIER_TARGET["walls"][tier]
        if rule_key == "tower":
            cw = sum(1 for b in alive[cid] if b["type"] == "wall")
            return 1 if (tier != "village" and cw >= 2) else 0
        if rule_key == "irrfarm":
            base = TIER_TARGET["irrfarm"][tier]
            return base + (INV_BOOST if invention.get((k, "irrigation")) == cid else 0)
        if rule_key in ("windmill", "library", "observatory", "ironmine"):
            return TIER_TARGET[rule_key][tier]
        if rule_key == "waterwheel":
            return 1 if dist_river[j0] <= 6 else 0
        if rule_key in ("canal", "canalfarm"):
            return 4 if dist_river[j0] <= 8 else 0
        if rule_key == "harbour":
            return 1 if cid in ports else 0
        return 0

    def pick(rule, c, k):
        key, R, tset, irr, dmin = rule[0], rule[3], rule[4], rule[5], rule[7]
        cx, cy = c["x"], c["y"]
        if key == "harbour":
            for j in ports.get(c["id"], []):
                if tiles_ok(j, k):
                    return j
            return None
        if key == "ironmine":
            cands = [j for j in iron_j if math.hypot(j % W - cx, j // W - cy) <= R
                     and tch[j] in BUILD_CH and tiles_ok(j, k)]
            if not cands:
                return None
            cands.sort(key=lambda j: (owner[j] != k, math.hypot(j % W - cx, j // W - cy), j))
            return cands[0]
        enemy = [cc for cc in cities_now.values() if cc["civ"] != SIDE_KEY[k] and cc["capital"]]
        ex, ey = (enemy[0]["x"], enemy[0]["y"]) if enemy else (cx, cy)
        cands = []
        for dx, dy, d in OFF[R]:
            if d < dmin:
                continue
            x, y = cx + dx, cy + dy
            if not (0 <= x < W and 0 <= y < H):
                continue
            j = y * W + x
            if tch[j] not in tset or not tiles_ok(j, k):
                continue
            if key == "waterwheel" and dist_river[j] > 2:
                continue
            if key == "canal" and dist_river[j] > 5:
                continue
            if irr and not near_water(j, 3):
                continue
            cands.append(j)
        if not cands:
            return None
        if key in ("walls", "tower"):
            # wall and tower segments face the enemy capital; own land before neutral
            cands.sort(key=lambda j: (owner[j] != k, math.hypot(j % W - ex, j // W - ey), j))
            return cands[0]
        if key == "windmill":
            cands.sort(key=lambda j: (owner[j] != k, tch[j] != "p", math.hypot(j % W - cx, j // W - cy), j))
        else:
            cands.sort(key=lambda j: (owner[j] != k, math.hypot(j % W - cx, j // W - cy), j))
        return cands[rng.randrange(min(4, len(cands)))]

    def build(c, k, rule, j, y):
        b = {"id": next_id[0], "city": c["id"], "type": rule[2], "x": j % W, "y": j // W,
             "owner": SIDE_KEY[k], "built": y, "destroyed": None, "irr": rule[5],
             "res": "iron" if rule[0] == "ironmine" else None, "rule": rule[0]}
        next_id[0] += 1
        if rule[0] == "harbour":
            b["port"] = True
            b["port_dist"] = round(port_dist[c["id"]], 1)
            b["ship_run"] = _ship_run(j, tch, sea)
        used.add(j)
        if rule[2] == "canal":
            real_canal_now.add(j)
        alive[c["id"]].append(b)
        cos_all.append(b)
        counts[(SIDE_KEY[k], rule[2])] += 1
        return b

    for r in years:
        y = r["year"]
        if r.get("owner_full") is not None:
            owner = [{"R": 0, "P": 1, ".": -1}[ch] for ch in r["owner_full"]]
        for j, v in r["owner_chg"]:
            owner[j] = v
        cities_now = {c["id"]: c for c in r["cities"]}
        for c in r["cities"]:
            state_side.setdefault(c["id"], c["civ"])
        for side_name, tbl in state["techs"].items():
            k = SIDE[side_name]
            for key, t in tbl.items():
                tech_active[(k, key)] = t["active"]
                if t["how"] == "invention" and t["city"] is not None:
                    invention[(k, key)] = t["city"]

        changed = []
        # a city that changes hands (or disappears) loses the cosmetic buildings of the old side
        for cid in sorted(state_side):
            cur = cities_now.get(cid)
            new_side = cur["civ"] if cur is not None else None
            if new_side == state_side[cid]:
                continue
            for b in alive[cid]:
                b["destroyed"] = y
                changed.append(b)
            alive[cid] = []
            if new_side is None:
                state_side.pop(cid)
            else:
                state_side[cid] = new_side

        for c in r["cities"]:
            k = SIDE[c["civ"]]
            for rule in RULES:
                if not (tech_active.get((k, rule[1]), 10 ** 9) <= y):
                    continue
                if rule[0] == "harbour" and c["id"] not in ports:
                    continue
                want = target(rule[0], c, k)
                have = sum(1 for b in alive[c["id"]] if b["rule"] == rule[0])
                if have >= want or next_ok.get((c["id"], rule[0]), 0) > y:
                    continue
                j = pick(rule, c, k)
                if j is None:
                    next_ok[(c["id"], rule[0])] = y + 5
                    continue
                b = build(c, k, rule, j, y)
                changed.append(b)
                lo, hi = rule[6]
                next_ok[(c["id"], rule[0])] = y + (rng.randint(lo, hi) if hi > 0 else 0)

        for c in r["cities"]:
            cw = sum(1 for b in alive[c["id"]] if b["type"] == "wall")
            c["walls_level"] = min(3, c["walls"] + cw)

        ships = list(r["ships"])
        for b in cos_all:
            if b["rule"] != "harbour" or b["destroyed"] is not None or b["built"] > y:
                continue
            run = b["ship_run"]
            n = len(run)
            if n < 2:
                continue
            cycle = 2 * (n - 1)
            for off in (0, n // 2):
                t = (y - b["built"] + off) % cycle
                jj = run[t if t < n else cycle - t]
                ships.append([jj % W, jj // W, b["owner"]])
        r["ships"] = ships

        # the year's building delta: sim records first, cosmetic changes after (sorted by id)
        r["bld"] = r["bld"] + [_cos_rec(b) for b in sorted(changed, key=lambda b: b["id"])]

    # full snapshots: replay every delta from year 0 (real buildings must match the sim's snapshots)
    replay = {}
    real_ok = True
    for r in years:
        for b in r["bld"]:
            replay[b["id"]] = b
        if r["bld_full"] is not None:
            want = sorted([dict(b) for b in r["bld_full"]], key=lambda v: v["id"])
            have = sorted([dict(v) for v in replay.values() if v["destroyed"] is None and not v.get("cosmetic")],
                          key=lambda v: v["id"])
            if want != have:
                real_ok = False
            r["bld_full"] = sorted([dict(v) for v in replay.values() if v["destroyed"] is None],
                                   key=lambda v: v["id"])
    notes["cosmetic_buildings"] = len(cos_all)
    notes["cosmetic_by_type"] = {"%s:%s" % kt: n for kt, n in sorted(counts.items())}
    notes["real_snapshots_match_replay"] = real_ok
    for r in years:
        for b in r["bld"]:
            b.pop("ship_run", None)


def _ship_run(j0, tch, sea):
    x0, y0 = j0 % W, j0 // W
    run = []
    for j in sea:
        x, y = j % W, j // W
        if math.hypot(x - x0, y - y0) <= 7.5 and any(
                0 <= x + dx < W and 0 <= y + dy < H and tch[(y + dy) * W + x + dx] != "~"
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            run.append(j)
    run.sort(key=lambda j: (j % W, j // W))
    return run


# ---------------------------------------------------------------------------
# 4. mountains never belong to a kingdom (owner grid only; the sim's stats are unchanged)
# ---------------------------------------------------------------------------
def _mountain_filter(years, tch, notes):
    dropped = 0
    for r in years:
        keep = [[j, v] for j, v in r["owner_chg"] if tch[j] != "m"]
        dropped += len(r["owner_chg"]) - len(keep)
        r["owner_chg"] = keep
        if r.get("owner_full") is not None:
            s = list(r["owner_full"])
            for j in range(W * H):
                if tch[j] == "m":
                    s[j] = "."
            r["owner_full"] = "".join(s)
    notes["owner_entries_dropped_on_mountains"] = dropped


# ---------------------------------------------------------------------------
# 5. periods: the 11 eras with the display names
# ---------------------------------------------------------------------------
def _periods(story_dir, notes):
    with open(os.path.join(story_dir, "periods_v2.json"), encoding="utf-8") as f:
        raw = json.load(f)["periods"]
    out = []
    for i, (s, e, _ar, _en) in enumerate(raw):
        if (s, e) != ERA_BOUNDS[i]:
            raise ValueError("period %d bounds changed: %s" % (i, (s, e)))
        out.append([s, e, ERA_AR[i], ERA_EN[i]])
    return out


# ---------------------------------------------------------------------------
def apply(state, terrain, story_dir, seed):
    """Apply every v5 export fix to `state`, the dict sim.py is about to write. Returns the notes."""
    notes = {}
    tch = [terrain["rows"][y][x] for y in range(H) for x in range(W)]
    _mountain_filter(state["years"], tch, notes)
    _sieges(state, notes)
    _names(state, os.path.join(story_dir, "names_v2.json"), notes)
    _cosmetic(state, tch, terrain["resources"], seed, notes)
    state["periods"] = _periods(story_dir, notes)
    state["export_v5"] = notes
    return notes
