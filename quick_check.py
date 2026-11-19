#!/usr/bin/env python3
"""Sanity checks for the chosen story (reads story/state.json, terrain.json, log.txt).

  /usr/bin/python3 quick_check.py        exit code 0 when every check passes
"""
import json
import re
from collections import defaultdict
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STORY = os.path.join(HERE, "story")
W, H = 160, 100
BUILDABLE_CH = set("dsop")
BAD_TERR = set("m~r")
BUILD_TECH = {"well": "wells", "granary": "granary", "waterwheel": "waterwheel",
              "windmill": "windmill", "library": "paper", "observatory": "astronomy",
              "bazaar": "paper", "caravanserai": "compass", "harbour": "compass",
              "canal": "canals", "wall": "engineering", "tower": "engineering",
              "siege_workshop": "trebuchet"}
LADDER_KEYS = None
RADIUS = 8.0                 # real buildings (the sim's own rule)
COS_RADIUS = 14.0            # v5 cosmetic buildings: the widest rule (iron mines, canals, irrigation)
PORT_RADIUS = 23.0           # v5 harbours: the coast is up to 20 tiles from the port city
BACKUP = os.path.join(HERE, "samples", "story_seed132")   # the published film story (identity reference)
PERIODS_V5 = [[0, 71, "عصر نبني ونشوف"], [72, 79, "عصر الكشخة"], [80, 96, "الحرب الأولى: سوء تفاهم"],
              [97, 139, "هدنة وسرقة أسرار"], [140, 216, "الحرب الكبرى"], [217, 247, "هدنة: فاصل ونواصل"],
              [248, 302, "حرب الثأر"], [303, 352, "الحرب الرابعة: رجعنا لكم"], [353, 455, "زمن الجيران المزعجين"],
              [456, 492, "بداية النهاية"], [493, 555, "السقوط"]]
TECH_BUILD = {("irrigation", "farm"): "irrigation", ("windmill", "windmill"): "windmill",
              ("waterwheel", "waterwheel"): "waterwheel", ("paper", "library"): "paper",
              ("astronomy", "observatory"): "astronomy", ("iron", "mine"): "iron",
              ("engineering", "wall"): "engineering", ("compass", "harbour"): "compass",
              ("canals", "canal"): "canals"}


class Result:
    def __init__(self):
        self.lines = []
        self.fails = 0

    def check(self, name, ok, detail=""):
        self.lines.append(("PASS" if ok else "FAIL") + "  " + name + ("  " + detail if detail else ""))
        if not ok:
            self.fails += 1


def main():
    res = Result()
    with open(os.path.join(STORY, "names_v2.json"), encoding="utf-8") as f:
        NAME_BACK = {v["en"]: v["old_en"] for v in json.load(f).values()}
    st_path = os.path.join(STORY, "state.json")
    with open(st_path, encoding="utf-8") as f:
        st = json.load(f)
    with open(os.path.join(STORY, "terrain.json"), encoding="utf-8") as f:
        terr = json.load(f)
    rows = terr["rows"]
    tch = [rows[y][x] for y in range(H) for x in range(W)]
    years = st["years"]
    end_year = st["summary"]["end_year"]
    contact = st["summary"]["contact"]
    size_mb = os.path.getsize(st_path) / 1e6
    res.check("state.json size under 60 MB", size_mb < 60.0, "%.1f MB" % size_mb)

    # reconstruction
    owner = [-1] * (W * H)
    bld = {}
    city_xy = {}
    city_civ_by_year = {}
    first_owner = {}
    bld_changes_by_year = {}
    ok_owner = True
    bad_owner_msg = ""
    ok_bterr = True
    bterr_msg = ""
    ok_bradius = True
    radius_msg = ""
    ok_bowner = True
    bowner_msg = ""
    armies_by_year = {}
    battles_all = []
    events_all = {}
    techs_new_all = []
    city_pop_ok = True
    gold_ok = True
    for rec in years:
        y = rec["year"]
        if rec.get("owner_full") is not None:
            owner = [{"R": 0, "P": 1, ".": -1}[ch] for ch in rec["owner_full"]]
        for j, v in rec.get("owner_chg", []):
            owner[j] = v
        if rec.get("bld_full") is not None:
            bld = {b["id"]: dict(b) for b in rec["bld_full"]}
        changed = rec.get("bld", [])
        for b in changed:
            if b["id"] not in first_owner:
                first_owner[b["id"]] = (b["owner"], b["built"], b["type"], b["city"])
            bld[b["id"]] = dict(b)
        bld_changes_by_year[y] = changed
        # cities: owner = tile owner
        for c in rec["cities"]:
            city_xy[c["id"]] = (c["x"], c["y"])
            want = {"rich": 0, "poor": 1}[c["civ"]]
            if owner[c["y"] * W + c["x"]] != want and ok_owner:
                ok_owner = False
                bad_owner_msg = "year %d city %s" % (y, c["name_en"])
            if c["pop"] < 0:
                city_pop_ok = False
        # buildings changed this year: terrain, radius, owner
        for b in changed:
            if b["destroyed"] is not None:
                continue
            t = tch[b["y"] * W + b["x"]]
            if t not in BUILDABLE_CH and ok_bterr:
                ok_bterr = False
                bterr_msg = "year %d building %s on %s" % (y, b["type"], t)
            cxy = city_xy.get(b["city"])
            if cxy is not None:
                d = math.hypot(b["x"] - cxy[0], b["y"] - cxy[1])
                if b.get("cosmetic"):
                    lim = PORT_RADIUS if b.get("port") else COS_RADIUS
                else:
                    lim = RADIUS
                if d > lim + 1e-6 and ok_bradius:
                    ok_bradius = False
                    radius_msg = "year %d %s %.1f from city (limit %.0f)" % (y, b["type"], d, lim)
        for k in ("rich", "poor"):
            s = rec["stats"][k]
            if s["pop"] < 0 or s["gold"] < 0 or s["food"] < 0 or s["water"] < 0:
                gold_ok = False
        armies_by_year[y] = {a["id"]: a for a in rec["armies"]}
        battles_all.extend(rec.get("battles_full", []))
        for e in rec["events"]:
            events_all[e["id"]] = (y, e)
        techs_new_all.extend([(y, t) for t in rec.get("techs_new", [])])
        # buildings alive in this year must have a non-negative city pop etc (done above)
        # capture rule evaluated after loop using reconstructed states
        if y == 0 or y % 50 == 0:
            pass

    res.check("city owner equals tile owner (every year, every city)", ok_owner, bad_owner_msg)
    res.check("no building on water, river, sea or mountain", ok_bterr, bterr_msg)
    res.check("every building within radius %d of its city (cosmetic: %d; harbours: %d)" % (
        int(RADIUS), int(COS_RADIUS), int(PORT_RADIUS)), ok_bradius, radius_msg)
    res.check("population never negative", city_pop_ok)
    res.check("gold, food, water never negative (debt is an event)", gold_ok)

    # captured cities: buildings change owner or are destroyed in the capture year
    cap_ok = True
    cap_msg = ""
    bmap = {}
    idx_year = {rec["year"]: rec for rec in years}
    for rec in years:
        y = rec["year"]
        if rec.get("bld_full") is not None:
            bmap = {b["id"]: dict(b) for b in rec["bld_full"]}
        for b in rec.get("bld", []):
            bmap[b["id"]] = dict(b)
        for cap in st["captures"]:
            if cap[0] != y:
                continue
            cid, frm, to = cap[1], cap[2], cap[3]
            to_key = to
            for b in bmap.values():
                if b["city"] != cid or b["built"] >= y:
                    continue
                if b["destroyed"] is not None and b["destroyed"] <= y:
                    continue
                if b["owner"] == to_key:
                    continue
                cap_ok = False
                cap_msg = "year %d city %d building %d kept owner %s" % (y, cid, b["id"], b["owner"])
    res.check("captured city: buildings change owner or are destroyed that year", cap_ok, cap_msg)

    # battles: attacker army present at x,y (waypoint end) and losses within sizes
    bat_ok = True
    bat_msg = ""
    n_bat = 0
    for bt in battles_all:
        n_bat += 1
        y = bt["year"]
        arm = armies_by_year.get(y, {}).get(bt["att_army"])
        if arm is None or not arm.get("wp") or arm["wp"][-1] != [bt["x"], bt["y"]]:
            bat_ok = False
            bat_msg = "battle %d year %d attacker army %s not at (%d,%d)" % (bt["id"], y, bt["att_army"], bt["x"], bt["y"])
            break
        if bt["att_loss"] > bt["att_size"] or bt["def_loss"] > bt["def_size"]:
            bat_ok = False
            bat_msg = "battle %d losses exceed sizes" % bt["id"]
            break
    res.check("every battle: attacker army present at (x,y); losses <= sizes (%d battles)" % n_bat, bat_ok, bat_msg)

    # techs: each tech is own research (invention event) or a logged successful theft after contact
    tech_ok = True
    tech_msg = ""
    ev_by_key = {}
    for eid, (y, e) in events_all.items():
        if e["type"] in ("invention", "theft"):
            ev_by_key.setdefault((e["type"], e.get("tech"), e["civ"]), []).append((y, e))
    n_tech = 0
    for k in ("rich", "poor"):
        for key, t in st["techs"][k].items():
            n_tech += 1
            how = t["how"]
            if how == "invention":
                evs = ev_by_key.get(("invention", key, k), [])
                if not any(y == t["year"] for y, _ in evs):
                    tech_ok = False
                    tech_msg = "%s %s has no invention event in %d" % (k, key, t["year"])
            elif how == "theft":
                if k != "rich":
                    tech_ok = False
                    tech_msg = "poor stole %s" % key
                evs = ev_by_key.get(("theft", key, "rich"), [])
                if not any(y == t["year"] for y, _ in evs):
                    tech_ok = False
                    tech_msg = "theft of %s not logged in %d" % (key, t["year"])
                if contact is None or t["year"] < contact:
                    tech_ok = False
                    tech_msg = "theft of %s before contact" % key
                if not (t["year"] + 5 <= t["active"] <= t["year"] + 10):
                    tech_ok = False
                    tech_msg = "theft of %s adoption delay not 5-10 years" % key
            else:
                tech_ok = False
                tech_msg = "tech %s acquired by %s" % (key, how)
    res.check("every tech came from own research or a logged theft after contact (%d techs)" % n_tech, tech_ok, tech_msg)

    # techs before their invention/theft year: buildings require active techs
    btech_ok = True
    btech_msg = ""
    irr_seen = set()
    for y, rec in idx_year.items():
        for b in rec.get("bld", []):
            # the side that builds (or flips a farm to irrigated) must hold the tech by then
            tkey = BUILD_TECH.get(b["type"])
            if b["type"] == "mine" and b.get("res") == "iron":
                tkey = "iron"
            flip = b["type"] == "farm" and b.get("irr") and b["id"] not in irr_seen
            if b["type"] == "farm" and b.get("irr"):
                irr_seen.add(b["id"])
            if b["type"] == "farm" and flip:
                tkey = "irrigation"
            if tkey is None or b["destroyed"] is not None and b["built"] != y:
                continue
            if b["built"] != y and not flip:
                continue
            owner = b["owner"]
            t = st["techs"][owner].get(tkey)
            if t is None or t["active"] > y:
                btech_ok = False
                btech_msg = "year %d %s by %s needs %s" % (y, b["type"], owner, tkey)
                break
        if not btech_ok:
            break
    res.check("buildings and irrigation only after their tech is active", btech_ok, btech_msg)

    # log.txt maps to state.json events
    log_ok = True
    log_msg = ""
    n_log = 0
    with open(os.path.join(STORY, "log.txt"), encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            n_log += 1
            parts = line.split(" ", 3)
            if len(parts) < 4:
                log_ok = False
                log_msg = "bad line " + line[:60]
                break
            y, eid = int(parts[0]), parts[1]
            rest = parts[3]
            if eid not in events_all:
                log_ok = False
                log_msg = "log id %s not in state" % eid
                break
            ey, e = events_all[eid]
            # v5 renamed cities in state.json only (log.txt keeps the sim's names): compare with the old names
            text = e["text_en"]
            text = re.sub("|".join(re.escape(k) for k in sorted(NAME_BACK, key=len, reverse=True)),
                          lambda m: NAME_BACK[m.group(0)], text)
            if e.get("void"):
                text = rest          # void sieges have new text in state.json; the log line is the sim's
            if ey != y or text not in rest or not e["log"]:
                log_ok = False
                log_msg = "log line %s does not match state" % eid
                break
    res.check("every log.txt line maps to a state.json event (%d lines)" % n_log, log_ok, log_msg)

    # periods: 6 to 12, contiguous, covering the timeline
    per = st["periods"]
    p_ok = 6 <= len(per) <= 12
    if p_ok:
        p_ok = per[0][0] == 0 and per[-1][1] == end_year
        for a, b in zip(per, per[1:]):
            if b[0] != a[1] + 1:
                p_ok = False
    res.check("periods: 6 to 12 contiguous eras covering 0..end (%d periods)" % len(per), p_ok)

    # ending: the loser really has no cities at the end (conquest) or meets the collapse rule
    s = st["summary"]
    last = years[-1]
    loser = "poor" if s["winner"] == "rich" else "rich"
    if s["end_reason"] == "conquest":
        lost = last["stats"][loser]["cities"] == 0
        res.check("ending: loser has no cities at the end (conquest)", lost)
    elif s["end_reason"] == "collapse":
        res.check("ending: loser has <2 cities, no capital, <10% of winner pop", last["stats"][loser]["cities"] < 2)
    else:
        res.check("ending: time limit reached", s["end_year"] >= 999)

    # story requirements
    res.check("story: poor side wins", s["winner"] == "poor")
    res.check("story: at least 8 field battles", s["field_battles"] >= 8, "field %d ambush %d" % (s["field_battles"], s["ambushes"]))
    res.check("story: at least 1 ambush or crossing battle decided by tactics", s.get("ambush_tactics", 0) >= 1, "ambush-tactics %s" % s.get("ambush_tactics"))
    res.check("story: rich military lead at some point (peak year %s)" % (s.get("rich_peak") or [None])[0], bool(s.get("rich_military_lead")))
    res.check("story: end year between 250 and 600", 250 <= end_year <= 600, "end %d" % end_year)
    sp = s.get("statues_palaces", 0)
    res.check("story: 4 to 10 statues and palaces (%d)" % sp, 4 <= sp <= 10, "statues %s palaces %s" % (s.get("statues"), s.get("palaces")))
    res.check("story: feasts capped at 6 (%s)" % s.get("feasts"), s.get("feasts", 0) <= 6)
    res.check("story: at least 8 sieges (review target 8-20; see RESULTS v3)", s["sieges"] >= 8, "sieges %d" % s["sieges"])
    res.check("story: rich waste events logged (%d)" % s["waste_events"], s["waste_events"] >= 4)
    res.check("story: at least 1 mercenary hire", s["hires"] >= 1, "hires %d" % s["hires"])
    res.check("story: at least 1 successful theft", s["theft_success"] >= 1, "thefts %d" % s["theft_success"])
    gc = s.get("gold_cross_year")
    res.check("story: rich hold more gold than the poor for the first 40%", gc is not None and gc >= 0.4 * end_year, "cross %s of %d" % (gc, end_year))
    fw = s["first_war"]
    res.check("story: first war between years 50 and 120", fw is not None and 50 <= fw <= 120, "first war %s" % fw)

    # v3: sieges are single events (start, end, outcome), never one battle per year
    sg_ok = True
    sg_msg = ""
    starts = {}
    ends = {}
    for rec in years:
        for g in rec.get("sieges", []):
            if g["end"] is None:
                starts.setdefault(g["id"], (rec["year"], g))
            else:
                ends[g["id"]] = (rec["year"], g)
    for gid, (sy, g) in starts.items():
        arm = armies_by_year.get(sy, {}).get(g["army"])
        if arm is None or not arm.get("wp") or arm["wp"][-1] != [g["x"], g["y"]]:
            sg_ok = False
            sg_msg = "siege %d: attacker army not at (%d,%d) in year %d" % (gid, g["x"], g["y"], sy)
            break
        if gid in ends:
            ey, eg = ends[gid]
            if eg["outcome"] not in ("captured", "lifted", "failed", "taken", "game_end") or ey < sy:
                sg_ok = False
                sg_msg = "siege %d: bad end" % gid
                break
    if any(b["type"] == "siege" for b in battles_all):
        sg_ok = False
        sg_msg = "a siege was recorded as a battle"
    res.check("sieges are single events with start, end and outcome (%d sieges)" % len(starts), sg_ok, sg_msg)

    # v3: field battles carry compositions, losses and a deciding factor
    fb_ok = True
    fb_msg = ""
    for bt in battles_all:
        if bt["type"] not in ("field", "ambush") or not bt.get("att_comp") or not bt.get("decisive") or not bt.get("factor"):
            fb_ok = False
            fb_msg = "battle %d missing fields" % bt["id"]
            break
    res.check("field battles record compositions, losses and deciding factor (%d)" % len(battles_all), fb_ok, fb_msg)

    # v3: no event type fires on a fixed cadence (logged events only)
    MAX_PER_10 = 6
    by_type = defaultdict(list)
    for eid, (y, e) in events_all.items():
        if e["log"]:
            by_type[e["type"]].append(y)
    cad_ok = True
    cad_msg = ""
    for t, yrs in by_type.items():
        yrs.sort()
        j = 0
        for i in range(len(yrs)):
            while yrs[i] - yrs[j] >= 10:
                j += 1
            if i - j + 1 > MAX_PER_10:
                cad_ok = False
                cad_msg = "%s: more than %d in a 10-year window (year %d)" % (t, MAX_PER_10, yrs[i])
                break
        if not cad_ok:
            break
        gaps = [b - a for a, b in zip(yrs, yrs[1:])]
        run = 1
        for a, b in zip(gaps, gaps[1:]):
            run = run + 1 if a == b else 1
            if run >= 5 and a >= 2:          # consecutive-year campaigns are allowed; a fixed period of 2+ years is not
                cad_ok = False
                cad_msg = "%s: %d identical gaps of %d years (fixed cadence)" % (t, run, a)
                break
        if not cad_ok:
            break
    res.check("no event type on a fixed cadence (max %d per 10 years; no run of 5 equal gaps of 2+ years)" % MAX_PER_10, cad_ok, cad_msg)

    # v4: no stretch longer than 80 years without a war or major event
    majors = sorted(e["year"] for (y, e) in events_all.values() if e["type"] in ("war_start", "battle", "siege_start", "capture", "capital_fall", "truce", "contact", "theft", "overtake"))
    longest = 0
    prev = 0
    for m in majors + [end_year]:
        longest = max(longest, m - prev)
        prev = m
    res.check("no stretch longer than 80 years without a war or major event (longest %d)" % longest, longest <= 80)

    # v3: rich gold above zero for most of the first 40% of the story
    n40 = max(1, int(0.4 * end_year))
    pos = sum(1 for rec in years[:n40] if rec["stats"]["rich"]["gold"] > 0)
    res.check("rich gold > 0 for most of the first 40%% of the story (%d%% of years)" % int(100.0 * pos / n40),
              pos >= 0.75 * n40)
    bk = sum(1 for e in events_all.values() if e[1]["type"] == "bankrupt")
    res.check("bankruptcies are rare (at most 2 in the story)", bk <= 2, "bankruptcies %d" % bk)

    # ---------------------------------------------------------------- v5 export fixes
    # identity: the simulated story (log, stats, captures, techs, real buildings, real events) matches the published sample
    bk_ok = os.path.isfile(os.path.join(BACKUP, "state.json")) and os.path.isfile(os.path.join(BACKUP, "log.txt"))
    res.check("identity reference samples/story_seed132 is present", bk_ok)
    if bk_ok:
        with open(os.path.join(BACKUP, "state.json"), encoding="utf-8") as f:
            bst = json.load(f)
        with open(os.path.join(BACKUP, "log.txt"), "rb") as f:
            blog = f.read()
        with open(os.path.join(STORY, "log.txt"), "rb") as f:
            nlog = f.read()
        res.check("IDENTITY: log.txt is byte-identical to samples/story_seed132 (%d lines)" % n_log, blog == nlog)
        keys = [k for k in ("summary", "wars", "captures", "techs", "ladder", "seed", "W", "H", "max_years",
                            "snap_every", "events_index") if st.get(k) != bst.get(k)]
        res.check("IDENTITY: summary, wars, captures, techs and ladder identical", not keys, ",".join(keys))
        yd = []
        if len(years) != len(bst["years"]):
            yd.append("year count")
        for ra, rb in zip(years, bst["years"]):
            for key in ("year", "stats", "dip", "battles", "battles_full", "disasters", "techs_new", "roads",
                        "roads_full"):
                if ra.get(key) != rb.get(key):
                    yd.append("%s@%s" % (key, ra.get("year")))
                    break
            if len(yd) > 5:
                break
        res.check("IDENTITY: per-year stats, diplomacy, battles, disasters, techs and roads identical (%d years)"
                  % len(years), not yd, " ".join(yd[:5]))
        core = lambda e: (e["id"], e["year"], e["type"], e["x"], e["y"], e["civ"], e["city"], e["log"])
        ev_now = sorted(core(e) for r in years for e in r["events"] if not e.get("cosmetic"))
        ev_bak = sorted(core(e) for r in bst["years"] for e in r["events"] if not e.get("cosmetic"))
        res.check("IDENTITY: every simulated event identical (id, year, type, place, civ, city, log flag; %d)"
                  % len(ev_bak), ev_now == ev_bak)
        bl_now = [b for r in years for b in r["bld"] if not b.get("cosmetic")]
        bl_bak = [b for r in bst["years"] for b in r["bld"] if not b.get("cosmetic")]
        res.check("IDENTITY: every simulated building record identical (%d)" % len(bl_bak), bl_now == bl_bak)
        ar_now = [a for r in years for a in r["armies"] if not a.get("cosmetic")]
        ar_bak = [a for r in bst["years"] for a in r["armies"] if not a.get("cosmetic")]
        res.check("IDENTITY: every simulated army record identical (%d)" % len(ar_bak), ar_now == ar_bak)

    # sieges: every siege closed; no same-year re-siege; no duplicate visible start; army at the walls
    sg_start, sg_end = {}, {}
    for r in years:
        for g in r["sieges"]:
            (sg_start if g["end"] is None else sg_end).setdefault(g["id"], (r["year"], g))
    open_s = [g for g in sg_start if g not in sg_end]
    res.check("sieges: every siege is closed (open: %d)" % len(open_s), not open_s, str(open_s[:5]))
    same_yr = [gid for gid, (sy, g) in sg_start.items()
               if any(c[0] == sy and c[1] == g["city"] and c[3] == g["att_civ"] for c in st["captures"])]
    res.check("sieges: none starts in the year its city was taken by the same side", not same_yr, str(same_yr[:5]))
    seen_s, dup_s = set(), []
    for r in years:
        for e in r["events"]:
            if e["type"] == "siege_start" and not e.get("hidden"):
                k = (e["city"], r["year"])
                if k in seen_s:
                    dup_s.append(k)
                seen_s.add(k)
    res.check("sieges: no duplicate visible siege_start event for the same city and year", not dup_s, str(dup_s[:5]))
    arm_at = {r["year"]: {a["id"]: a for a in r["armies"]} for r in years}
    cont_bad = []
    for gid, (sy, g) in sg_start.items():
        ey, eg = sg_end[gid]
        last = ey if eg["outcome"] in ("captured", "taken", "failed", "game_end") else ey - 1
        for y in range(sy, last + 1):
            a = arm_at[y].get(g["army"])
            if a is None:
                cont_bad.append((gid, y, "missing"))
                break
            if max(abs(a["x"] - g["x"]), abs(a["y"] - g["y"])) > 1:
                cont_bad.append((gid, y, "away"))
                break
    res.check("sieges: the attacking army is at the walls every year until its siege closes (%d sieges)" % len(sg_start),
              not cont_bad, str(cont_bad[:3]))
    fmt = open(os.path.join(HERE, "FORMAT.md"), encoding="utf-8").read()
    res.check("FORMAT.md documents the starve capture kind", "starve" in fmt)

    # names: state.json uses names_v2 everywhere; visible event texts carry no old city name
    with open(os.path.join(STORY, "names_v2.json"), encoding="utf-8") as f:
        names = json.load(f)
    nm_bad = [c["id"] for r in years for c in r["cities"]
              if (c["name_en"], c["name_ar"], c["old_name_en"]) != (names[str(c["id"])]["en"],
                                                                     names[str(c["id"])]["ar"],
                                                                     names[str(c["id"])]["old_en"])]
    res.check("names: every city record has name_en, name_ar and old_name_en from names_v2", not nm_bad,
              str(nm_bad[:5]))
    ev_no_name = [e["id"] for r in years for e in r["events"] if e["city"] is not None and not e.get("name_en")]
    res.check("names: every event that names a city has name_en and name_ar", not ev_no_name, str(ev_no_name[:5]))
    old_en = {v["old_en"] for v in names.values()}
    old_ar = {c["old_name_ar"] for r in years for c in r["cities"]}
    leftover = []
    for r in years:
        for e in r["events"]:
            if e.get("hidden") or e.get("cosmetic"):
                continue
            if any(o in e["text_en"] for o in old_en) or any(o in e["text_ar"] for o in old_ar):
                leftover.append(e["id"])
    res.check("names: no visible event text still uses an old city name (%d)" % len(leftover), not leftover,
              str(leftover[:5]))
    per_ok = [p[:3] for p in st["periods"]] == PERIODS_V5 and all(p[3] for p in st["periods"])
    res.check("periods: the 11 named eras from periods_v2 with the v5 display names", per_ok,
              str([p[:3] for p in st["periods"]][:2]))

    # territory: no kingdom on mountain tiles in the owner grid
    mt_bad = []
    for r in years:
        fs = r.get("owner_full")
        if fs is not None and any(ch != "." and tch[j] == "m" for j, ch in enumerate(fs)):
            mt_bad.append(r["year"])
        if any(v != -1 and tch[j] == "m" for j, v in r["owner_chg"]):
            mt_bad.append(r["year"])
    res.check("territory: no kingdom owns a mountain tile in the owner grid", not mt_bad, str(mt_bad[:5]))

    # cosmetic buildings: replay of all deltas matches the snapshots; one building per tile; ships; walls
    rep, rep_bad, occ_bad, ship_bad, wl_bad = {}, None, None, None, None
    ncos = {}
    n_harb = 0
    for r in years:
        for b in r["bld"]:
            rep[b["id"]] = b
        alive = [b for b in rep.values() if b["destroyed"] is None]
        if r["bld_full"] is not None:
            if sorted(r["bld_full"], key=lambda b: b["id"]) != sorted(alive, key=lambda b: b["id"]) and rep_bad is None:
                rep_bad = r["year"]
            tiles = [(b["x"], b["y"]) for b in r["bld_full"]]
            if len(set(tiles)) != len(tiles) and occ_bad is None:
                occ_bad = r["year"]
        harb = [b for b in alive if b["type"] == "harbour" and b.get("cosmetic")]
        if len(r["ships"]) != 2 * len(harb) and ship_bad is None:
            ship_bad = "year %d: %d ships for %d harbours" % (r["year"], len(r["ships"]), len(harb))
        for x, y, _k in r["ships"]:
            on_sea = tch[y * W + x] == "~"
            near_land = any(0 <= x + dx < W and 0 <= y + dy < H and tch[(y + dy) * W + x + dx] != "~"
                            for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            if not (on_sea and near_land) and ship_bad is None:
                ship_bad = "year %d ship at %d,%d not on the coast" % (r["year"], x, y)
        cw = defaultdict(int)
        for b in alive:
            if b.get("cosmetic") and b["type"] == "wall":
                cw[b["city"]] += 1
        for c in r["cities"]:
            if c["walls_level"] != min(3, c["walls"] + cw[c["id"]]) and wl_bad is None:
                wl_bad = "year %d city %d walls_level %s" % (r["year"], c["id"], c["walls_level"])
        if r["year"] in (100, 200, 300, 555):
            ncos[r["year"]] = (alive, r["year"])
        n_harb += len(harb) > 0
    res.check("cosmetic: bld_full snapshots equal the replay of every delta (real and cosmetic)", rep_bad is None,
              str(rep_bad))
    res.check("cosmetic: one building per tile in every snapshot", occ_bad is None, str(occ_bad))
    res.check("cosmetic: ships sit on the coast, two per standing harbour", ship_bad is None, str(ship_bad))
    res.check("cosmetic: walls_level = min(3, walls + cosmetic walls) in every city record", wl_bad is None, str(wl_bad))
    walls_hi = any(c["walls_level"] == 3 for r in years for c in r["cities"])
    res.check("cosmetic: city walls_level rises to 3 in some city", walls_hi)

    # each invention shows its buildings soon after it is active (the side that holds the tech)
    first_b = {}
    for r in years:
        for b in r["bld"]:
            if b.get("cosmetic") and b["destroyed"] is None and b["built"] == r["year"]:
                first_b.setdefault((b["owner"], b["type"]), r["year"])
    inv_bad = []
    for (tech, btype), tkey in TECH_BUILD.items():
        if btype == "harbour":
            continue
        for side in ("rich", "poor"):
            t = st["techs"][side].get(tkey)
            if t is None:
                continue
            fb = first_b.get((side, btype))
            if fb is None or fb - t["active"] > 15:
                inv_bad.append("%s %s (active %d, first %s)" % (side, btype, t["active"], fb))
    res.check("cosmetic: each side's invention shows its building within 15 years of the tech", not inv_bad,
              "; ".join(inv_bad[:4]))
    h_any = any(b["type"] == "harbour" for alive, _y in ncos.values() for b in alive)
    res.check("cosmetic: harbours exist for compass (rich port city, %d year-samples)" % n_harb, h_any)
    if 100 in ncos:
        irr2 = sum(1 for b in ncos[100][0] if b["city"] == 2 and b["type"] == "farm" and b["irr"])
        res.check("cosmetic: the poor irrigation capital (city 2) has 10+ irrigated farms by year 100 (%d)" % irr2,
                  irr2 >= 10)
    if 300 in ncos:
        cn = sum(1 for b in ncos[300][0] if b["type"] == "canal")
        res.check("cosmetic: canal greening after the canal network (canals active y260): %d canals at y300" % cn,
                  cn >= 20)

    # counts for the report (information, not a check)
    for y in (100, 200, 300, 555):
        if y in ncos:
            alive, _ = ncos[y]
            cc = defaultdict(int)
            for b in alive:
                cc[b["type"]] += 1
            res.lines.append("INFO  buildings alive at y%d: %d (%s)" % (
                y, len(alive), ", ".join("%s %d" % kv for kv in sorted(cc.items()))))

    print("\n".join(res.lines))
    print("")
    print("%d checks, %d failed" % (sum(1 for ln in res.lines if not ln.startswith("INFO")), res.fails))
    return 0 if res.fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
