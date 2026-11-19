#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sim3_worldbox v2: two kingdoms on one timeline (pure stdlib, Python 3.9).

  /usr/bin/python3 sim.py run --seed 7 [--quick]   one run, summary printed
  /usr/bin/python3 sim.py batch [--quick]          batch -> batch/runs.csv, batch/summary.txt
  /usr/bin/python3 sim.py search [--quick]         story seed search -> story/search.csv
  /usr/bin/python3 sim.py export --seed N          story/ + maps/ for seed N
  /usr/bin/python3 sim.py all                      batch + search + export best + quick_check
"""
import argparse
import csv
import heapq
import json
import math
import os
import random
import sys
import time
from collections import defaultdict
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
STORY_DIR = os.path.join(HERE, "story")
MAPS_DIR = os.path.join(HERE, "maps")
BATCH_DIR = os.path.join(HERE, "batch")

# ============================================================================
# PARAMETERS (every tuning change is logged in RESULTS.md)
# ============================================================================
W, H = 160, 100
POP_UNIT = 20                 # people per population unit (all stored counts are units)
MAX_YEARS = 1000
RICH, POOR = 0, 1
CIVS = (RICH, POOR)
CIV_NAMES = {0: "الأثرياء", 1: "الفقراء"}
CIV_KEY = {0: "rich", 1: "poor"}
CIV_EN = {0: "the Rich kingdom", 1: "the Poor kingdom"}
TITLE_EN = {0: "Sultan", 1: "Ra'is"}
TITLE_AR = {0: "السلطان", 1: "الرئيس"}
LEADER_POOL = {
    0: ["Mansur", "Hamdan", "Nasir", "Fadil", "Rashid", "Ziyad", "Qays", "Jabir"],
    1: ["Warraq", "Aalim", "Mirza", "Idris", "Sami", "Taqi", "Hakim", "Nadir"],
}
COMMANDERS = {
    0: ["General Sarim", "General Bahir", "General Dhiyab", "General Hadid"],
    1: ["Captain Nizar", "Captain Yasir", "Captain Tamim", "Captain Anwar"],
}
CITY_POOL = {
    0: [("Qasr al-Dhahab", "قصر الذهب"), ("Qasr al-Shams", "قصر الشمس"),
        ("Madinat al-Naft", "مدينة النفط"), ("Hisn al-Ratl", "حصن الرتل"),
        ("Bir al-Dhahab", "بئر الذهب"), ("Qasr al-Layl", "قصر الليل"),
        ("Hisn al-Miskh", "حصن المسك"), ("Ain al-Zahab", "عين الذهب"),
        ("Qasr al-Tayr", "قصر الطير"), ("Madinat al-Lulu", "مدينة اللؤلؤ"),
        ("Hisn al-Amir", "حصن الأمير"), ("Bir al-Sultan", "بئر السلطان")],
    1: [("Dar al-Hikma", "دار الحكمة"), ("Bayt al-Kitab", "بيت الكتاب"),
        ("Madinat al-Qalam", "مدينة القلم"), ("Dar al-Ilm", "دار العلم"),
        ("Ain al-Maani", "عين المعاني"), ("Hisn al-Nuqush", "حصن النقوش"),
        ("Bayt al-Hisab", "بيت الحساب"), ("Dar al-Siyar", "دار السير"),
        ("Madinat al-Warraq", "مدينة الوراق"), ("Ain al-Khatt", "عين الخط"),
        ("Hisn al-Mizan", "حصن الميزان"), ("Bayt al-Nujum", "بيت النجوم")],
}
CAPITAL_NAME = {0: CITY_POOL[0][0], 1: CITY_POOL[1][0]}

# terrain codes
DESERT, SILT, OASIS, PLATEAU, MOUNTAIN, RIVER, SEA = range(7)
TERR_CHAR = "dsopmr~"
BUILDABLE = (DESERT, SILT, OASIS, PLATEAU)
MAIN_RIVER_X = 79
RIVER_AMP = 3.0
COAST_BASE = 92
DISC_R = 13                 # mirrored start region radius
CAP_DIST_RIVER = 28         # capital distance from the river (per side)
START_Y = 42
N_MOUNTAIN_BLOBS = 9
N_PLATEAU_BLOBS = 6
N_OASES = 12
RES_COUNTS = {"gold": 12, "oil": 8, "iron": 8, "clay": 14, "palm": 24}
HIDDEN_FRAC = 0.4           # gold and oil deposits start hidden
DISCOVER_P = 0.006          # per hidden deposit per year, if owned by a civ
DISCOVER_RICH_MULT = 1.5    # rich find more by luck

# economy
START_POP = {0: 1000.0, 1: 1000.0}     # 20,000 people
START_HOUSES = 45
START_FARMS = 18
START_GOLD = {0: 30000.0, 1: 2000.0}
INTEL = {0: 0.30, 1: 1.00}          # research and tactics intelligence factor
TAX = 0.04
RICH_TAX_EFF = 0.9
MARKET_TAX = 0.25
MINE_YIELD = {"gold": 30.0, "oil": 25.0, "iron": 10.0}
TRADE_YIELD = {"bazaar": 15.0, "caravanserai": 12.0, "harbour": 10.0}
FOOD_NEED = 0.8
WATER_NEED = 0.12
LAND_FOOD = {DESERT: 0.4, SILT: 3.0, OASIS: 4.0, PLATEAU: 0.5, MOUNTAIN: 0.0, RIVER: 0.0, SEA: 0.0}
PALM_FOOD = 3.0
FISH_FOOD = 3.0
FARM_DRY = 55.0
FARM_IRR = 130.0
WINDMILL_FOOD = 25.0
WATERWHEEL_FOOD = 35.0
OBSERVATORY_MULT = 1.10
QANAT_WATER = 200.0          # every city: qanat / cistern water (desert baseline)
WATER_RIVER = 1500.0
WATER_OASIS = 800.0
WATER_WELL = 500.0
WATER_CANAL = 40.0
BASE_CAP = 120.0
HOUSE_CAP = 20.0
MARKET_CAP = 40.0
BAZAAR_CAP = 30.0
PALACE_CAP = 150.0
HOUSE_MAX = {"village": 25, "town": 45, "city": 70, "capital": 100}
TOWN_POP = 500.0
CITY_POP = 1100.0
CLAIM = {"village": 3, "town": 4, "city": 5, "capital": 6}
GROWTH = 0.03
FOOD_BUY = 2.0
WATER_BUY = 0.5
FAMINE_MAX = 0.12
STOCK_BASE = 200.0
STOCK_GRANARY = 400.0
STOCK_POP = 0.3
RESERVE = {0: 0.0, 1: 30.0}
HOUSES_PER_YEAR = 3
BUILDS_PER_YEAR = 1
MAX_NONHOUSE_PER_YEAR = 2

# research: one ladder for both sides; rich intelligence and gold bonus are capped
RP_PER_K = 5.0
LIB_BONUS = {0: 0.10, 1: 0.15}     # per library (rich: academies/scholars cost gold)
LIB_BONUS_CAP = {0: 0.30, 1: 0.45}
OBS_BONUS = 0.10
OBS_BONUS_CAP = 0.20
RICH_GOLD_RP_COST = 8.0              # gold per year per 1 RP of scholar bonus, rich only

# tech ladder: key, name_en, name_ar, cost (RP), effect_en
LADDER = [
    ("wells", "Wells", "الآبار", 60, "wells on desert sites, +500 water each"),
    ("irrigation", "Irrigation canals", "قنوات الري", 150, "farms within 3 tiles of water turn green (110 food)"),
    ("granary", "Granaries", "الأهراء", 200, "granaries raise the food stock cap"),
    ("waterwheel", "Waterwheel", "الدولاب المائي", 260, "waterwheels on river banks, +35 food per city"),
    ("windmill", "Windmill", "الطاحونة الهوائية", 300, "windmills on the plateau, +25 food per city"),
    ("paper", "Paper", "الورق", 360, "libraries and bazaars; research bonus per library"),
    ("astronomy", "Astronomy calendar", "التقويم الفلكي", 480, "observatories, +10% harvest in the city"),
    ("compass", "Compass and coastal ships", "البوصلة والسفن الساحلية", 560, "harbours, ships, caravanserai: trade income"),
    ("iron", "Iron working", "صناعة الحديد", 660, "iron mines, weapons +25%"),
    ("bows", "Composite bows", "القوس المركب", 760, "archers +0.4 power in field battles"),
    ("engineering", "Engineering of walls", "هندسة الأسوار", 880, "city walls (up to 3) and towers"),
    ("trebuchet", "Trebuchets", "المنجنيق", 1000, "siege workshops; trebuchets break walls"),
    ("medicine", "Medicine", "الطب", 1120, "plague losses halved"),
    ("canals", "Canal network", "شبكة القنوات", 1240, "canals; the desert turns green (irrigation range 6)"),
    ("steel", "Steel", "الفولاذ", 1500, "weapons +20%"),
]
TECH_INDEX = {t[0]: k for k, t in enumerate(LADDER)}
TECH_INFO = {t[0]: t for t in LADDER}

# buildings: (name_ar, cost, upkeep per year, tech key or None)
BUILD = {
    "house": ("بيت", 8, 0.0, None),
    "farm": ("مزرعة", 25, 0.10, None),
    "well": ("بئر", 40, 0.10, "wells"),
    "granary": ("أهراء", 60, 0.30, "granary"),
    "market": ("سوق", 80, 0.40, None),
    "workshop": ("ورشة", 70, 0.30, None),
    "waterwheel": ("دولاب مائي", 110, 0.20, "waterwheel"),
    "windmill": ("طاحونة", 120, 0.20, "windmill"),
    "library": ("مكتبة", 150, 0.80, "paper"),
    "observatory": ("مرصد", 180, 1.00, "astronomy"),
    "mine": ("منجم", 60, 0.50, None),
    "bazaar": ("بازار", 100, 0.50, "paper"),
    "caravanserai": ("خان القوافل", 120, 0.60, "compass"),
    "harbour": ("مرفأ", 150, 0.80, "compass"),
    "canal": ("قناة", 20, 0.05, "canals"),
    "wall": ("سور", 60, 0.20, "engineering"),
    "tower": ("برج", 90, 0.30, "engineering"),
    "barracks": ("ثكنة", 100, 0.50, None),
    "siege_workshop": ("ورشة المنجنيق", 200, 0.80, "trebuchet"),
    "palace": ("قصر", 200, 2.00, None),
    "statue": ("تمثال ذهبي", 150, 0.00, None),
}
SITE_R = {"house": 7, "farm": 8, "well": 6, "granary": 4, "market": 4, "workshop": 4,
          "waterwheel": 6, "windmill": 5, "library": 4, "observatory": 4, "mine": 8,
          "bazaar": 4, "caravanserai": 6, "harbour": 6, "canal": 8, "wall": 3,
          "tower": 3, "barracks": 4, "siege_workshop": 4, "palace": 1, "statue": 5}
NOTABLE_BUILDS = {"palace", "statue", "library", "observatory", "harbour", "wall",
                  "siege_workshop", "mine", "caravanserai", "canal", "windmill",
                  "waterwheel", "granary", "barracks", "bazaar"}

# expansion
START_CITY_POP = 150.0
FOUND_COST = 40.0
FOUND_POP = 150.0
FOUND_P = {0: 0.15, 1: 0.25}
FOUND_MIN_POP = 300.0
CITY_MAX = {0: 14, 1: 18}
SITE_MIN_DIST = 6.0
SITE_ENEMY_MIN = 8.0
SITE_RING = (7.0, 14.0)
EXPAND_END = 420

# military
ARMY_BUDGET = 6.0
ROAD_COST = 0.5
FLAT_COST = 1.0
RIVER_COST = 2.5
MTN_COST = 2.5
NODE_CAP = 9000
ARMY_MAX = 900
ARMY_MIN = 8
CAPTURE_MIN = 3
RECRUIT_EVERY = 4
RECRUIT_GARRISON_MIN = 25
ARMY_CAP_BASE = 2
LEVY_PRICE = 0.6
MERC_PRICE = 1.2
ENG_PRICE = 30.0
UPKEEP_LEVY = 0.04
UPKEEP_MERC = 0.10
UPKEEP_GARRISON = 0.02
RICH_CORRUPT = 0.004
P_INF, P_CAV, P_ARCH, P_MERC = 1.0, 1.3, 1.1, 1.3
BOWS_BONUS = 0.4
IRON_BONUS = 0.25
STEEL_BONUS = 0.20
TAC_BASE = 0.7
TAC_SLOPE = 0.3
WALL_BONUS = 0.25
TOWER_BONUS = 0.15
MOUNTAIN_DEF = 1.2
HEAD_ON = 0.75
ENG_DMG = 35.0
WALL_HP = 100.0
SANDSTORM_POWER = 0.8
AMBUSH_P = {0: 0.0, 1: 0.5}
FIELD_RANGE = 3
AMBUSH_RANGE = 10
RICH_RENT = 0.25           # rich royal domains: gold per owned tile per year
RIVER_DEF = 1.1
AMBUSH_SURPRISE = 1.35
LOSER_BASE = 0.30
LOSER_SLOPE = 0.25
WIN_BASE = 0.10
WIN_SLOPE = 0.20
MERC_SHARE_RICH = 0.6
MERC_MIN_GOLD = 1500.0
RECRUIT_P = 0.08           # random yearly chance to raise an army at war (no fixed cadence)

# diplomacy
CONTACT_DIST = 24.0
BORDER_DIST = 24.0
TENSION_BORDER = 0.35
INCIDENT_P = 0.20
INCIDENT_T = 0.6
RES_DISPUTE_P = 0.06
RES_DISPUTE_T = 0.5
INSULT_P = {0: 0.03, 1: 0.005}
INSULT_T = 1.2
TENSION_DECAY = 0.02
WAR_TENSION = 4.0
DECLARE_P = {0: 0.10, 1: 0.08}
POOR_DECLARE_RATIO = 1.0
TRUCE_YEARS = 25
SUE_P_POOR = 0.05
SUE_P_RICH = 0.04
CEASE_AFTER = 10
CEASE_P = 0.03

# espionage (the only way the rich get techs other than their own research)
SPY_COST = 8.0
THEFT_P = 0.004
THEFT_TRADE_MULT = 1.5
THEFT_SUCCESS = 0.5
THEFT_CAUGHT = 0.5          # share of failures that get caught
SPY_CAUGHT_TENSION = 1.5
ADOPT_MIN = 5
ADOPT_MAX = 10

# trade and bribes
BRIBE_P = 0.02
BRIBE_COST = 150.0
BRIBE_MIN_GOLD = 1500.0
BRIBE_LOY = 40.0
BRIBE_DIST = 12.0
CAPITAL_REBUILD = 15

# disasters
P_DROUGHT = 0.02
P_SANDSTORM = 0.05
P_LOCUST = 0.025
P_FLOOD = 0.03
P_PLAGUE = 0.012
RAD = {"drought": 18, "sandstorm": 7, "locust": 16, "flood": 5, "plague": 8}
DROUGHT_YEARS = (3, 6)

# leaders
LEADER_DEATH_BASE = 0.003
LEADER_DEATH_AGE = 0.004

SITE_RETRY = 5               # years before a failed site search is retried
BANK_GAP = 60
BANK_P = 0.5
FEAST_MIN_GOLD = 8000.0
FEAST_P = 0.01
FEAST_MAX = 6
STATUE_MAX = 8
MERC_MAX = 400             # mercenaries hired per army (units): added on top of levies, caps excluded
MERC_GOLD_SHARE = 0.15
TRUCE_MIN = 15
TRUCE_MAX = 40
FEAST_SHARE = 0.03
KM_TYPE_CAP = 6
SIEGE_RATIO = 1.5          # an army settles to besiege only if it outnumbers the garrison
STARVE_YEARS = 8           # blockade years before a besieged city surrenders
SPEND_HI = 4000.0          # poor gold above this is spent on militia
MILITIA_COST = 3.0
MILITIA_FRAC = 0.10
ENDOW_FRAC = 0.05          # share of the poor surplus endowed to schools each year
SCHOLAR_COST = 20.0        # gold per research point bought by endowment
SNAP_EVERY = 20             # full owner/building/road snapshot every N years

# ============================================================================
# GEOMETRY HELPERS
# ============================================================================


def make_offsets(R):
    out = []
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            d = math.hypot(dx, dy)
            if d <= R + 1e-9:
                out.append((dx, dy, d))
    out.sort(key=lambda t: (t[2], t[0], t[1]))
    return out


OFF = {r: make_offsets(r) for r in range(0, 10)}


def bfs_dist(sources, maxd):
    dist = [99] * (W * H)
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


def ppl(u):
    """Convert stored units to people for output."""
    return int(round(u * POP_UNIT))


def coast_y(x):
    return COAST_BASE + int(round(2.0 * math.sin(x * 0.11)))


# ============================================================================
# TERRAIN
# ============================================================================


def gen_terrain(seed):
    rng = random.Random(seed * 9973 + 11)
    terr = [DESERT] * (W * H)
    phase = rng.uniform(0, 6.283)
    cen = [MAIN_RIVER_X + int(round(RIVER_AMP * math.sin(y * 0.075 + phase))) for y in range(H)]
    for y in range(H):
        for x in range(W):
            if y >= coast_y(x):
                terr[y * W + x] = SEA
    for y in range(H):
        for x in (cen[y], cen[y] + 1):
            i = y * W + x
            if terr[i] != SEA:
                terr[i] = RIVER
    # one tributary from the west edge joining the main river
    ty = rng.randint(55, 68)
    x = 0
    while x <= cen[ty] - 1:
        i = ty * W + x
        if terr[i] != SEA:
            terr[i] = RIVER
        x += 1
        ty = min(H - 1, max(50, ty + rng.choice((-1, 0, 0, 1))))
    rivers = [i for i in range(W * H) if terr[i] == RIVER]
    # silt: flood land beside the river
    for i in rivers:
        x0, y0 = i % W, i // W
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                x, y = x0 + dx, y0 + dy
                if 0 <= x < W and 0 <= y < H:
                    j = y * W + x
                    if terr[j] == DESERT and rng.random() < 0.85:
                        terr[j] = SILT

    def blob(src, dst, n, rmin, rmax, ymin, ymax):
        for _ in range(n):
            cx = rng.randint(4, W - 5)
            cy = rng.randint(ymin, ymax)
            r = rng.uniform(rmin, rmax)
            for dy in range(-7, 8):
                for dx in range(-7, 8):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < W and 0 <= y < H:
                        d = math.hypot(dx, dy)
                        j = y * W + x
                        if d <= r * (0.7 + 0.6 * rng.random()) and terr[j] == src:
                            terr[j] = dst

    blob(DESERT, MOUNTAIN, N_MOUNTAIN_BLOBS, 3.0, 6.0, 8, 80)
    blob(DESERT, PLATEAU, N_PLATEAU_BLOBS, 3.0, 6.0, 8, 82)
    for _ in range(N_OASES):
        cx, cy = rng.randint(6, W - 7), rng.randint(10, 85)
        r = rng.choice((1, 2))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                x, y = cx + dx, cy + dy
                if 0 <= x < W and 0 <= y < H and math.hypot(dx, dy) <= r:
                    j = y * W + x
                    if terr[j] in (DESERT, SILT):
                        terr[j] = OASIS

    def mirror_x(x, y):
        return 2 * cen[y] + 1 - x

    # mirrored start regions: rich disc on the west bank, copied to the poor east bank
    rx = cen[START_Y] - 1 - CAP_DIST_RIVER
    rich_disc = []
    poor_disc = []
    for dy in range(-DISC_R, DISC_R + 1):
        for dx in range(-DISC_R, DISC_R + 1):
            if math.hypot(dx, dy) > DISC_R:
                continue
            x, y = rx + dx, START_Y + dy
            if not (0 <= x < W and 0 <= y < H):
                continue
            m = mirror_x(x, y)
            if not (0 <= m < W):
                continue
            if terr[y * W + x] == MOUNTAIN:
                terr[y * W + x] = PLATEAU
            rich_disc.append((x, y))
            poor_disc.append((m, y))
    terr[START_Y * W + rx] = DESERT
    disc_set = set(y * W + x for x, y in rich_disc) | set(y * W + x for x, y in poor_disc)
    # make the poor disc an exact mirror of the rich disc (terrain only; resources below)
    for (x, y), (m, _) in zip(rich_disc, poor_disc):
        terr[y * W + m] = terr[y * W + x]
    # resources
    res = {}
    hidden_list = []

    def place(kind, n, kinds, hidden_frac=0.0, xr=None):
        cands = [i for i in range(W * H)
                 if terr[i] in kinds and i not in disc_set and i not in res
                 and (xr is None or xr[0] <= i % W <= xr[1])]
        rng.shuffle(cands)
        for i in cands[:n]:
            hid = rng.random() < hidden_frac
            res[i] = [kind, hid]
            if hid:
                hidden_list.append(i)

    place("gold", 7, (DESERT, PLATEAU), HIDDEN_FRAC)
    place("gold", 4, (DESERT, PLATEAU), HIDDEN_FRAC, xr=(60, 100))   # disputed middle zone
    place("oil", RES_COUNTS["oil"], (DESERT,), HIDDEN_FRAC)
    place("oil", 3, (DESERT,), HIDDEN_FRAC, xr=(60, 100))
    place("iron", RES_COUNTS["iron"], (DESERT, PLATEAU))
    place("clay", RES_COUNTS["clay"], (SILT, DESERT))
    place("palm", RES_COUNTS["palm"], (OASIS, SILT))
    fish = [i for i in rivers if rng.random() < 0.08]
    for i in fish:
        res[i] = ["fish", False]
    # mirrored disc resources
    disc_res_kinds = [("palm", 2), ("iron", 1), ("gold", 1)]
    for kind, n in disc_res_kinds:
        cands = [(x, y) for x, y in rich_disc if terr[y * W + x] in (DESERT, SILT, OASIS, PLATEAU)]
        rng.shuffle(cands)
        for x, y in cands[:n]:
            m = mirror_x(x, y)
            res[y * W + x] = [kind, False]
            res[y * W + m] = [kind, False]
    return {
        "terr": terr, "res": res, "cen": cen, "hidden": hidden_list,
        "rich_cap": (rx, START_Y), "poor_cap": (mirror_x(rx, START_Y), START_Y),
        "rich_disc": rich_disc, "poor_disc": poor_disc,
    }


# ============================================================================
# SIM
# ============================================================================


class Sim:
    def __init__(self, seed, record=False):
        self.seed = seed
        self.record = record
        self.rng = random.Random(seed * 100003 + 7)
        g = gen_terrain(seed)
        self.g = g
        self.terr = g["terr"]
        self.res = g["res"]
        self.cen = g["cen"]
        self.hidden = list(g["hidden"])
        self.dist_river = bfs_dist([i for i, t in enumerate(self.terr) if t == RIVER], 8)
        self.dist_oasis = bfs_dist([i for i, t in enumerate(self.terr) if t == OASIS], 8)
        self.dist_sea = bfs_dist([i for i, t in enumerate(self.terr) if t == SEA], 8)
        self.owner = [-1] * (W * H)
        self.ocity = [-1] * (W * H)
        self.occ = [-1] * (W * H)
        self.roadset = set()
        self.canal_tiles = set()
        self.civs = {}
        for k in CIVS:
            self.civs[k] = {
                "id": k, "key": CIV_KEY[k], "gold": START_GOLD[k], "rp": 0.0,
                "techs": {}, "cities": [], "capital": None, "capital_due": -1,
                "leader": LEADER_POOL[k][0], "leader_i": 0,
                "leader_age": self.rng.randint(30, 45), "upk": 0.0,
                "last_recruit": -99, "bank_warn": -99, "names": [], "fell": False,
                "siege_built": False, "weak_years": 0, "theft_seen": 0,
            }
        self.cities = {}
        self.buildings = {}
        self.armies = {}
        self.army_hist = []
        self.roads = []
        self.events = []
        self.battles = []
        self.ids = defaultdict(int)
        self.dip = {"status": "peace", "truce_until": -1, "contact": None,
                    "tension": 0.0, "war_start": None, "attacker": None}
        self.wars = []             # [start, end, attacker, battles]
        self.captures = []         # [year, city, from, to, kind]
        self.disasters_now = []
        self.dirty = True
        self.year = 0
        self.game_over = False
        self.winner = None
        self.end_reason = None
        self.end_year = None
        self.records = []
        self.score_series = []      # (year, rich_score, poor_score)
        self.theft = {"attempts": 0, "success": 0, "caught": 0}
        self.bribes = 0
        self.fought = set()
        self.events_y = []
        self.battles_y = []
        self.bchg = set()
        self.roads_y = []
        self.owner_chg = []
        self.techs_new = []
        self.mtn_flag = set()
        self.last_stats = {}
        self.seen_builds = set()
        self.gold_series = []
        self.tech_series = []
        self.battle_log_years = []
        self.civ_series = []
        self.sieges_all = []
        self.sieges_y = []
        self.sieges_active = {}
        self.overtook = False
        self.terr_count = {k: 0 for k in CIVS}

    # ---------------- ids, events
    def nid(self, kind):
        self.ids[kind] += 1
        return self.ids[kind]

    def ev(self, etype, en, ar, x, y, civ=None, city=None, log=True, **kw):
        eid = "e%05d" % (len(self.events) + 1)
        e = {"id": eid, "year": self.year, "type": etype, "x": int(x), "y": int(y),
             "civ": CIV_KEY.get(civ) if civ is not None else None,
             "city": city, "text_en": en, "text_ar": ar, "log": bool(log)}
        e.update(kw)
        self.events.append(e)
        self.events_y.append(e)
        return e

    # ---------------- basic queries
    def alive_cities(self, civ):
        return [self.cities[c] for c in self.civs[civ]["cities"] if self.cities[c]["alive"]]

    def known(self, civ, key):
        t = self.civs[civ]["techs"].get(key)
        return t is not None and t["active"] <= self.year

    def walls(self, c):
        return c["cnt"]["wall"]

    def pop_of(self, civ):
        return sum(c["pop"] for c in self.alive_cities(civ))

    def pick_name(self, civ):
        used = self.civs[civ]["names"]
        pool = [n for n in CITY_POOL[civ] if n[0] not in used]
        if not pool:
            pool = CITY_POOL[civ]
        n = self.rng.choice(pool)
        used.append(n[0])
        return n

    def front_point(self, c):
        best = None
        bd = 1e9
        for e in self.alive_cities(1 - c["civ"]):
            d = math.hypot(e["x"] - c["x"], e["y"] - c["y"])
            if d < bd:
                bd = d
                best = (e["x"], e["y"])
        return best

    def has_known_res(self, c, kind):
        hit = c["resc"].get(kind)
        if hit is not None and self.year - hit[0] < SITE_RETRY:
            return hit[1]
        v = self._has_known_res(c, kind)
        c["resc"][kind] = (self.year, v)
        return v

    def _has_known_res(self, c, kind):
        for dx, dy, d in OFF[8]:
            x, y = c["x"] + dx, c["y"] + dy
            if 0 <= x < W and 0 <= y < H:
                j = y * W + x
                if self.owner[j] == c["civ"] and self.occ[j] == -1:
                    r = self.res.get(j)
                    if r and r[0] == kind and not r[1]:
                        return True
        return False

    def near_water(self, j, R):
        if self.dist_river[j] <= R or self.dist_oasis[j] <= R:
            return True
        if self.canal_tiles:
            x0, y0 = j % W, j // W
            for dx, dy, d in OFF[R]:
                x, y = x0 + dx, y0 + dy
                if 0 <= x < W and 0 <= y < H and (y * W + x) in self.canal_tiles:
                    return True
        return False

    # ---------------- territory
    def territory_update(self):
        if not self.dirty:
            return
        self.dirty = False
        best = [1e9] * (W * H)
        own = [-1] * (W * H)
        oc = [-1] * (W * H)
        for cid in sorted(self.cities):
            c = self.cities[cid]
            if not c["alive"]:
                continue
            cx, cy = c["x"], c["y"]
            for dx, dy, d in OFF[c["claim"]]:
                x, y = cx + dx, cy + dy
                if 0 <= x < W and 0 <= y < H:
                    j = y * W + x
                    if d < best[j]:
                        best[j] = d
                        own[j] = c["civ"]
                        oc[j] = cid
        changes = [[j, own[j]] for j in range(W * H) if own[j] != self.owner[j]]
        self.owner_chg.extend(changes)
        self.owner = own
        self.ocity = oc
        self.terr_count = {k: 0 for k in CIVS}
        for v in own:
            if v >= 0:
                self.terr_count[v] += 1
        for cid in sorted(self.cities):
            c = self.cities[cid]
            if not c["alive"]:
                continue
            bf = 0.0
            x0, y0 = c["x"], c["y"]
            for dx, dy, d in OFF[5]:
                x, y = x0 + dx, y0 + dy
                if 0 <= x < W and 0 <= y < H:
                    j = y * W + x
                    if own[j] != c["civ"]:
                        continue
                    bf += LAND_FOOD[self.terr[j]]
                    r = self.res.get(j)
                    if r and r[0] in ("palm", "fish"):
                        bf += PALM_FOOD if r[0] == "palm" else FISH_FOOD
            c["base_food"] = bf
            i = c["idx"]
            bw = QANAT_WATER
            if self.dist_river[i] <= 3:
                bw += WATER_RIVER
            if self.dist_oasis[i] <= 3:
                bw += WATER_OASIS
            c["base_water"] = bw

    # ---------------- buildings
    def add_city(self, civ, i, pop, capital=False, name=None):
        cid = self.nid("city")
        x, y = i % W, i // W
        if name is None:
            name = self.pick_name(civ)
        tier = "capital" if capital else "village"
        c = {"id": cid, "civ": civ, "name_en": name[0], "name_ar": name[1],
             "x": x, "y": y, "idx": i, "founded": self.year, "pop": float(pop),
             "stock": 0.0, "loyalty": 70.0, "garrison": 20, "walls_dmg": 0.0,
             "blockade": 0, "tier": tier, "claim": CLAIM[tier], "capital": capital,
             "captured": [], "base_food": 0.0, "base_water": 0.0, "food_prod": 0.0,
             "water_prod": 0.0, "cap": 0.0, "rp": 0.0, "alive": True, "blds": [],
             "cnt": defaultdict(int), "roads": 0, "logged_city": False,
             "nosite": {}, "resc": {}}
        self.cities[cid] = c
        self.civs[civ]["cities"].append(cid)
        self.dirty = True
        return c

    def add_building(self, c, btype, j, res=None):
        bid = self.nid("bld")
        b = {"id": bid, "city": c["id"], "type": btype, "x": j % W, "y": j // W,
             "owner": c["civ"], "built": self.year, "destroyed": None, "irr": False,
             "res": res}
        if btype == "farm" and self.known(c["civ"], "irrigation") and self.near_water(j, 3):
            b["irr"] = True
        self.buildings[bid] = b
        self.occ[j] = bid
        c["blds"].append(bid)
        cnt = c["cnt"]
        cnt[btype] += 1
        if btype == "farm" and b["irr"]:
            cnt["irr"] += 1
        if btype == "mine":
            cnt["mine_" + res] += 1
        if btype == "canal":
            self.canal_tiles.add(j)
        if btype == "caravanserai" or btype == "harbour":
            pass
        self.bchg.add(bid)
        return b

    def destroy(self, b):
        if b["destroyed"] is not None:
            return
        b["destroyed"] = self.year
        j = b["y"] * W + b["x"]
        self.occ[j] = -1
        c = self.cities[b["city"]]
        cnt = c["cnt"]
        cnt[b["type"]] -= 1
        if b["type"] == "farm" and b["irr"]:
            cnt["irr"] -= 1
        if b["type"] == "mine":
            cnt["mine_" + b["res"]] -= 1
        if b["type"] == "canal":
            self.canal_tiles.discard(j)
        self.bchg.add(b["id"])

    def find_site(self, c, btype, res=None):
        key = (btype, res)
        fail = c["nosite"].get(key)
        if fail is not None and self.year - fail < SITE_RETRY:
            return None
        j = self._find_site(c, btype, res)
        if j is None:
            c["nosite"][key] = self.year
        else:
            c["nosite"].pop(key, None)
        return j

    def _find_site(self, c, btype, res=None):
        R = SITE_R[btype]
        civ = c["civ"]
        cx, cy = c["x"], c["y"]
        terr = self.terr
        owner = self.owner
        occ = self.occ
        roadset = self.roadset
        if btype == "palace":
            for dx, dy, d in OFF[2]:
                x, y = cx + dx, cy + dy
                if 0 <= x < W and 0 <= y < H:
                    j = y * W + x
                    if owner[j] == civ and occ[j] == -1 and terr[j] in BUILDABLE and j not in roadset:
                        return j
            return None
        pref, fb = None, None
        if btype == "house":
            pref, fb = (DESERT, PLATEAU), BUILDABLE
        elif btype == "farm":
            pref, fb = (SILT, OASIS), (DESERT,)
        elif btype == "well":
            pref, fb = (DESERT,), ()
        elif btype == "windmill":
            pref, fb = (PLATEAU,), BUILDABLE
        elif btype in ("wall", "tower", "statue", "granary", "market", "workshop", "library",
                       "observatory", "bazaar", "barracks", "siege_workshop"):
            pref, fb = BUILDABLE, BUILDABLE
        elif btype == "canal":
            pref, fb = (DESERT,), ()
        elif btype in ("waterwheel", "harbour", "caravanserai", "mine"):
            pref, fb = BUILDABLE, BUILDABLE
        front = self.front_point(c) if btype in ("wall", "tower") else None

        def ok_terr(j, tset):
            return terr[j] in tset

        for pass_set in ((pref, fb) if fb else (pref,)):
            if not pass_set:
                continue
            best = None
            bestkey = None
            for dx, dy, d in OFF[R]:
                x, y = cx + dx, cy + dy
                if not (0 <= x < W and 0 <= y < H):
                    continue
                j = y * W + x
                if owner[j] != civ or occ[j] != -1:
                    continue
                if d <= 1.5 and btype != "palace":
                    continue            # the centre of each city is kept for the palace
                if btype == "caravanserai":
                    if j not in roadset or not ok_terr(j, BUILDABLE):
                        continue
                elif j in roadset:
                    continue
                if btype == "mine":
                    r = self.res.get(j)
                    if not (r and r[0] == res and not r[1]):
                        continue
                elif btype == "waterwheel":
                    if not (terr[j] in BUILDABLE and self.dist_river[j] <= 1):
                        continue
                elif btype == "harbour":
                    if not (terr[j] in BUILDABLE and self.dist_sea[j] <= 1):
                        continue
                elif btype == "canal":
                    if not (terr[j] == DESERT and self.dist_river[j] <= 5):
                        continue
                elif btype in ("wall", "tower"):
                    if not (ok_terr(j, BUILDABLE) and 2 <= d <= 3.2):
                        continue
                    if front is not None:
                        key = math.hypot(x - front[0], y - front[1])
                        if bestkey is None or key < bestkey:
                            bestkey = key
                            best = j
                        continue
                if btype in ("wall", "tower") and front is not None:
                    continue
                if not ok_terr(j, pass_set):
                    continue
                return j
            if best is not None:
                return best
        return None

    def build(self, c, btype, res=None):
        """Place and pay for a building. Returns the building or None."""
        civ = self.civs[c["civ"]]
        cost = BUILD[btype][1]
        j = self.find_site(c, btype, res)
        if j is None:
            return None
        civ["gold"] -= cost
        b = self.add_building(c, btype, j, res)
        if btype in ("statue", "palace") and c["civ"] == RICH:
            n_w = civ.get("waste_logs", 0)
            civ["waste_logs"] = n_w + 1
            self.ev("waste", "The rich build a %s in %s for %d gold" % (btype, c["name_en"], cost),
                    "الأثرياء يبنون %s في %s بتكلفة %d ذهبا" % (BUILD[btype][0], c["name_ar"], cost),
                    b["x"], b["y"], civ=RICH, city=c["id"], log=n_w < 10, kind=btype, cost=cost)
        if btype == "siege_workshop":
            civ["siege_built"] = True
        if btype == "harbour":
            self.place_ship(b)
        if btype == "farm" and self.known(c["civ"], "irrigation") and not b["irr"]:
            pass
        if btype in NOTABLE_BUILDS and (c["civ"], btype) not in self.seen_builds:
            self.seen_builds.add((c["civ"], btype))
            nm = BUILD[btype][0]
            self.ev("first_build", "First %s built in %s (%s)" % (btype, c["name_en"], CIV_KEY[c["civ"]]),
                    "أول %s في %s" % (nm, c["name_ar"]), b["x"], b["y"], civ=c["civ"],
                    city=c["id"], log=True, bld=btype)
        return b

    def place_ship(self, b):
        j0 = b["y"] * W + b["x"]
        best = None
        for dx, dy, d in OFF[4]:
            x, y = b["x"] + dx, b["y"] + dy
            if 0 <= x < W and 0 <= y < H and self.terr[y * W + x] == SEA:
                best = (x, y)
                break
        b["ship"] = list(best) if best else None

    def upgrade_farms(self, civ, R):
        n = 0
        for c in self.alive_cities(civ):
            for bid in c["blds"]:
                b = self.buildings[bid]
                if b["destroyed"] is None and b["type"] == "farm" and not b["irr"]:
                    if self.near_water(b["y"] * W + b["x"], R):
                        b["irr"] = True
                        c["cnt"]["irr"] += 1
                        self.bchg.add(bid)
                        n += 1
        return n

    # ---------------- candidates for building
    def candidates(self, c):
        civ = self.civs[c["civ"]]
        cnt = c["cnt"]
        pop = c["pop"]
        k = c["civ"]
        war = self.dip["status"] == "war"
        contact = self.dip["contact"] is not None
        food_short = c["food_prod"] < pop * FOOD_NEED
        water_short = c["water_prod"] < pop * WATER_NEED
        out = []
        kn = lambda key: self.known(k, key)
        if cnt["farm"] < 2 + pop / 50.0:
            out.append((2.0 + 3.0 * food_short + (1.0 if cnt["farm"] == 0 else 0.0), "farm", None))
        if kn("wells") and cnt["well"] < 2 + pop / 900.0:
            out.append((1.5 + 4.0 * water_short, "well", None))
        if kn("granary") and cnt["granary"] < 3:
            out.append((1.5 + 2.0 * food_short, "granary", None))
        if kn("waterwheel") and cnt["waterwheel"] < 2 and self.dist_river[c["idx"]] <= 6:
            out.append((1.5 + (1.0 if cnt["waterwheel"] == 0 else 0.0), "waterwheel", None))
        if kn("windmill") and cnt["windmill"] < 2 and pop >= 400:
            out.append((1.5, "windmill", None))
        if kn("paper") and cnt["library"] < 1 + pop / (800.0 if k == POOR else 2000.0) and pop >= 400:
            out.append((2.5 if cnt["library"] == 0 else 1.8, "library", None))
        if kn("astronomy") and cnt["observatory"] < 1 and pop >= 900:
            out.append((2.0, "observatory", None))
        if cnt["market"] < 1 + pop / 1500.0 and pop >= 800:
            out.append((1.8, "market", None))
        if kn("paper") and contact and cnt["bazaar"] < 1 and pop >= 700:
            out.append((2.0, "bazaar", None))
        if kn("compass") and cnt["caravanserai"] < 1 and pop >= 800 and c["roads"] > 0:
            out.append((1.6, "caravanserai", None))
        if kn("compass") and cnt["harbour"] < 1 and self.dist_sea[c["idx"]] <= 4:
            out.append((2.2, "harbour", None))
        for kind, sc in (("gold", 3.0), ("oil", 2.0), ("iron", 2.5)):
            if kind == "iron" and not kn("iron"):
                continue
            if cnt["mine_" + kind] < 1 and self.has_known_res(c, kind):
                out.append((sc, "mine", kind))
        if pop >= 700 and cnt["workshop"] < (4 if k == POOR else 2):
            out.append((1.0, "workshop", None))
        if kn("engineering") and self.walls(c) < 3 and pop >= 500:
            out.append((2.5 if war else 1.2, "wall", None))
        if kn("engineering") and self.walls(c) >= 1 and cnt["tower"] < 1:
            out.append((1.5 if war else 0.5, "tower", None))
        if pop >= 1000 and cnt["barracks"] < 1 and war:
            out.append((1.8, "barracks", None))
        if kn("trebuchet") and not civ["siege_built"] and war and pop >= 900:
            out.append((2.6, "siege_workshop", None))
        if c["capital"] and cnt["palace"] < 1:
            out.append((9.0, "palace", None))
        if k == RICH and civ["gold"] >= BRIBE_MIN_GOLD and pop >= 800 and cnt["statue"] < 1 \
                and sum(c2["cnt"]["statue"] for c2 in self.alive_cities(RICH)) < STATUE_MAX:
            out.append((1.2, "statue", None))
        if kn("canals") and cnt["canal"] < (6 if k == POOR else 3):
            out.append((1.8, "canal", None))
        return out

    # ---------------- yearly steps
    def step(self):
        y = self.year
        self.fought = set()
        self.territory_update()
        self.disaster_step()
        self.adopt_step()
        for k in CIVS:
            self.leader_step(k)
        self.diplomacy_step()
        for cid in sorted(self.cities):
            if self.cities[cid]["alive"]:
                self.city_step(cid)
        for k in CIVS:
            self.upkeep_step(k)
        for k in CIVS:
            self.research_step(k)
        self.theft_step()
        self.bribe_step()
        self.waste_step()
        self.spend_step()
        self.recruit_step()
        self.expansion_step()
        self.build_step()
        self.move_step()
        self.encounter_step()
        self.territory_update()
        self.check_end()
        self.record_year()

    def init_world(self):
        g = self.g
        for civ, (x, y) in ((RICH, g["rich_cap"]), (POOR, g["poor_cap"])):
            c = self.add_city(civ, y * W + x, START_POP[civ], capital=True, name=CITY_POOL[civ][0])
            self.civs[civ]["capital"] = c["id"]
            self.endow(c, "house", START_HOUSES)
            self.endow(c, "farm", START_FARMS)
        self.dirty = True
        self.territory_update()

    def leader_step(self, k):
        civ = self.civs[k]
        civ["leader_age"] += 1
        p = LEADER_DEATH_BASE + LEADER_DEATH_AGE * max(0, civ["leader_age"] - 45)
        if self.rng.random() < p:
            old = civ["leader"]
            civ["leader_i"] = (civ["leader_i"] + 1) % len(LEADER_POOL[k])
            civ["leader"] = LEADER_POOL[k][civ["leader_i"]]
            civ["leader_age"] = self.rng.randint(30, 45)
            self.dip["tension"] += 1.5          # a new ruler must prove himself at the border
            cap = self.cities.get(civ["capital"]) if civ["capital"] is not None else None
            x, y = (cap["x"], cap["y"]) if cap else (W // 2, H // 2)
            self.ev("leader_death",
                    "The %s %s (%s) dies; %s %s succeeds" % (CIV_KEY[k], TITLE_EN[k], old, TITLE_EN[k], civ["leader"]),
                    "وفاة %s %s، ويخلفه %s" % (TITLE_AR[k], CIV_NAMES[k], civ["leader"]),
                    x, y, civ=k, log=True)

    def disaster_step(self):
        y = self.year
        rng = self.rng
        self.disasters_now = [d for d in self.disasters_now if d["end"] >= y]
        if not any(d["type"] == "drought" for d in self.disasters_now) and rng.random() < P_DROUGHT:
            x, yy = self.rand_land()
            dur = rng.randint(*DROUGHT_YEARS)
            d = {"type": "drought", "x": x, "y": yy, "r": RAD["drought"], "start": y, "end": y + dur - 1}
            self.disasters_now.append(d)
            self.ev("drought", "Drought strikes the region around (%d,%d) for %d years" % (x, yy, dur),
                    "جفاف يضرب الإقليم لمدة %d سنوات" % dur, x, yy, log=True)
        if rng.random() < P_SANDSTORM:
            x, yy = self.rand_land()
            d = {"type": "sandstorm", "x": x, "y": yy, "r": RAD["sandstorm"], "start": y, "end": y}
            self.disasters_now.append(d)
            self.ev("sandstorm", "Sandstorm over (%d,%d)" % (x, yy), "عاصفة رملية فوق الإقليم", x, yy, log=False)
        if rng.random() < P_LOCUST:
            x, yy = self.rand_land()
            d = {"type": "locust", "x": x, "y": yy, "r": RAD["locust"], "start": y, "end": y}
            self.disasters_now.append(d)
            self.ev("locust", "Locust swarm eats the fields near (%d,%d)" % (x, yy),
                    "جراد يأكل المحاصيل", x, yy, log=True)
        if rng.random() < P_FLOOD:
            yy = rng.randint(15, 75)
            x = self.cen[yy]
            d = {"type": "flood", "x": x, "y": yy, "r": RAD["flood"], "start": y, "end": y}
            self.disasters_now.append(d)
            for c in self.alive_cities(RICH) + self.alive_cities(POOR):
                if math.hypot(c["x"] - x, c["y"] - yy) <= RAD["flood"] + 3:
                    c["pop"] *= 0.97
                    c["stock"] += 150.0
            self.ev("flood", "River floods; fertile silt spreads near (%d,%d)" % (x, yy),
                    "فيضان النهر يجلب الطمي الخصيب", x, yy, log=True)
        if rng.random() < P_PLAGUE:
            alive = self.alive_cities(RICH) + self.alive_cities(POOR)
            if alive:
                c0 = alive[rng.randrange(len(alive))]
                for c in alive:
                    if math.hypot(c["x"] - c0["x"], c["y"] - c0["y"]) <= RAD["plague"]:
                        loss = 0.05 if self.known(c["civ"], "medicine") else 0.10
                        c["pop"] *= (1 - loss)
                self.ev("plague", "Plague spreads from %s" % c0["name_en"],
                        "طاعون ينتشر من %s" % c0["name_ar"], c0["x"], c0["y"], civ=c0["civ"],
                        city=c0["id"], log=True)

    def rand_land(self):
        for _ in range(500):
            x = self.rng.randint(10, W - 11)
            y = self.rng.randint(10, 80)
            if self.terr[y * W + x] in BUILDABLE:
                return x, y
        return W // 2, H // 2

    def adopt_step(self):
        """Stolen techs take 5-10 years to adopt; announce adoption and apply upgrades."""
        for k in CIVS:
            for key, t in self.civs[k]["techs"].items():
                if t["how"] == "theft" and t["active"] == self.year:
                    if key == "irrigation":
                        self.upgrade_farms(k, 3)
                    if key == "canals":
                        self.upgrade_farms(k, 6)
                    self.ev("adopt", "%s adopt the stolen %s" % (CIV_KEY[k].capitalize(), key),
                            "%s يعتمدون التقنية المسروقة" % CIV_NAMES[k],
                            *self.cap_xy(k), civ=k, log=False, tech=key)

    def cap_xy(self, k):
        cap = self.cities.get(self.civs[k]["capital"]) if self.civs[k]["capital"] is not None else None
        return (cap["x"], cap["y"]) if cap else (W // 2, H // 2)

    def city_step(self, cid):
        c = self.cities[cid]
        k = c["civ"]
        civ = self.civs[k]
        y = self.year
        cnt = c["cnt"]
        pop = c["pop"]
        fmult = 1.0
        wmult = 1.0
        for d in self.disasters_now:
            dist = math.hypot(c["x"] - d["x"], c["y"] - d["y"])
            if d["type"] == "drought" and d["start"] <= y <= d["end"] and dist <= d["r"]:
                fmult *= 0.6
                wmult *= 0.5
            if d["type"] == "locust" and dist <= d["r"]:
                fmult *= 0.5
        if c["blockade"] > 0:
            fmult *= 0.5
        farm_food = cnt["irr"] * FARM_IRR + (cnt["farm"] - cnt["irr"]) * FARM_DRY
        food_prod = c["base_food"] + farm_food + WINDMILL_FOOD * cnt["windmill"] + WATERWHEEL_FOOD * cnt["waterwheel"]
        if cnt["observatory"]:
            food_prod *= OBSERVATORY_MULT
        food_prod *= fmult
        water_prod = (c["base_water"] + WATER_WELL * cnt["well"] + WATER_CANAL * cnt["canal"]) * wmult
        c["food_prod"] = food_prod
        c["water_prod"] = water_prod
        houses = cnt["house"]
        cap = (BASE_CAP + HOUSE_CAP * houses + MARKET_CAP * cnt["market"]
               + BAZAAR_CAP * cnt["bazaar"] + PALACE_CAP * cnt["palace"])
        c["cap"] = cap
        need_f = pop * FOOD_NEED
        need_w = pop * WATER_NEED
        net = food_prod - need_f
        stock_cap = STOCK_BASE + STOCK_GRANARY * cnt["granary"] + STOCK_POP * pop
        shortage = 0.0
        if net >= 0:
            c["stock"] = min(stock_cap, c["stock"] + net)
        else:
            deficit = -net
            take = min(c["stock"], deficit)
            c["stock"] -= take
            deficit -= take
            if deficit > 0 and k == RICH:
                cost = deficit * FOOD_BUY
                if civ["gold"] >= cost:
                    civ["gold"] -= cost
                    deficit = 0.0
                else:
                    part = civ["gold"] / FOOD_BUY
                    civ["gold"] = 0.0
                    deficit -= part
            if deficit > 0:
                shortage = deficit / max(1.0, need_f)
        wunmet = 0.0
        wnet = water_prod - need_w
        if wnet < 0:
            d = -wnet
            cost = d * WATER_BUY
            if civ["gold"] >= cost:
                civ["gold"] -= cost
            else:
                part = civ["gold"] / WATER_BUY
                civ["gold"] = 0.0
                wunmet = max(0.0, d - part) / max(1.0, need_w)
        if shortage > 0:
            pop *= (1 - min(FAMINE_MAX, shortage * 0.5))
            c["loyalty"] -= 3.0
        if wunmet > 0:
            pop *= (1 - min(0.1, wunmet * 0.5))
            c["loyalty"] -= 1.0
        if shortage <= 0 and wunmet <= 0 and pop < cap:
            pop += pop * GROWTH
            pop = min(pop, cap)
        elif pop > cap:
            pop -= (pop - cap) * 0.02
        c["pop"] = max(0.0, pop)
        c["loyalty"] = min(70.0, c["loyalty"] + 0.5)
        if c["blockade"] > 0 and c["blockade"] > 40:
            c["blockade"] = 40
        # garrison regrowth
        gt = max(20.0, c["pop"] * 0.05)
        if c["garrison"] < gt and c["pop"] > 200 and c["blockade"] == 0:
            c["garrison"] += min(2, int(gt - c["garrison"]) or 1)
        # taxes, mines, trade
        eff = RICH_TAX_EFF if k == RICH else 1.0
        tax = c["pop"] * TAX * eff * (1 + MARKET_TAX * min(2, cnt["market"]))
        mines = (cnt["mine_gold"] * MINE_YIELD["gold"] + cnt["mine_oil"] * MINE_YIELD["oil"]
                 + cnt["mine_iron"] * MINE_YIELD["iron"])
        trade = 0.0
        if self.dip["contact"] is not None and self.dip["status"] != "war":
            trade = (TRADE_YIELD["bazaar"] * cnt["bazaar"] + TRADE_YIELD["caravanserai"] * cnt["caravanserai"]
                     + TRADE_YIELD["harbour"] * cnt["harbour"])
        civ["gold"] += tax + mines + trade
        civ["income"] = civ.get("income", 0.0) + tax + mines + trade
        # research points: one ladder, intelligence factor, capped bonus
        libs = min(3, cnt["library"])
        bonus = min(LIB_BONUS_CAP[k], LIB_BONUS[k] * libs)
        if cnt["observatory"]:
            bonus += min(OBS_BONUS_CAP, OBS_BONUS * min(2, cnt["observatory"]))
        if k == RICH and bonus > 0:
            # scholars are paid in gold: the rich pay for their research bonus
            scholar_cost = bonus * RICH_GOLD_RP_COST * (c["pop"] / 1000.0) * 0.1
            paid = min(civ["gold"], scholar_cost)
            civ["gold"] -= paid
            if paid < scholar_cost:
                bonus *= paid / max(1e-9, scholar_cost)
        c["rp"] = c["pop"] / 1000.0 * RP_PER_K * INTEL[k] * (1.0 + bonus)
        civ["rp"] += c["rp"]
        civ["upk"] += sum(cnt[t] * BUILD[t][2] for t in BUILD if cnt.get(t, 0))
        # tier
        if c["capital"]:
            tier = "capital"
        elif c["pop"] >= CITY_POP:
            tier = "city"
        elif c["pop"] >= TOWN_POP:
            tier = "town"
        else:
            tier = "village"
        if tier != c["tier"]:
            old = c["tier"]
            c["tier"] = tier
            c["claim"] = CLAIM[tier]
            self.dirty = True
            if tier == "city" and not c["logged_city"]:
                c["logged_city"] = True
                self.ev("growth", "%s grows into a city (%d people)" % (c["name_en"], c["pop"]),
                        "%s تصبح مدينة كبرى" % c["name_ar"], c["x"], c["y"], civ=k, city=cid, log=True)

    def upkeep_step(self, k):
        civ = self.civs[k]
        if k == RICH:
            rent = RICH_RENT * self.terr_count[RICH]
            civ["gold"] += rent
            civ["income"] = civ.get("income", 0.0) + rent
        civ["inc_last"] = civ.get("income", 0.0)
        civ["income"] = 0.0
        cost = civ["upk"]
        civ["upk"] = 0.0
        for A in self.armies.values():
            if A["owner"] == k:
                cost += A["comp"]["inf"] * UPKEEP_LEVY + A["comp"]["cav"] * UPKEEP_LEVY
                cost += A["comp"]["arch"] * UPKEEP_LEVY + A["comp"]["merc"] * UPKEEP_MERC
        for c in self.alive_cities(k):
            cost += c["garrison"] * UPKEEP_GARRISON
        if k == RICH:
            cost += civ["gold"] * RICH_CORRUPT
        if civ["gold"] >= cost:
            civ["gold"] -= cost
            return
        civ["gold"] = 0.0
        if self.year - civ["bank_warn"] >= BANK_GAP and self.rng.random() < BANK_P:
            civ["bank_warn"] = self.year
            cap = self.cap_xy(k)
            self.ev("bankrupt", "%s cannot pay its bills; soldiers desert" % CIV_KEY[k].capitalize(),
                    "إفلاس %s: الجنود يفرون لعدم الأجر" % CIV_NAMES[k], cap[0], cap[1], civ=k, log=True)
        for A in self.armies.values():
            if A["owner"] == k:
                A["comp"]["merc"] = int(A["comp"]["merc"] * 0.7)     # unpaid mercenaries desert first
                self.shrink(A, 0.05)

    def next_tech(self, k):
        for n, t in enumerate(LADDER):
            if t[0] not in self.civs[k]["techs"]:
                return n
        return None

    def research_step(self, k):
        civ = self.civs[k]
        n = self.next_tech(k)
        if n is None:
            return
        key, en, ar, cost, eff = LADDER[n]
        if civ["rp"] < cost:
            return
        civ["rp"] -= cost
        c = self.invent_city(k)
        self.grant(k, key, "invention", c)

    def invent_city(self, k):
        cs = self.alive_cities(k)
        if not cs:
            return None
        if k == POOR:
            return max(cs, key=lambda c: (c["pop"] + 400 * c["cnt"]["library"] + 800 * c["cnt"]["observatory"], -c["id"]))
        return max(cs, key=lambda c: (c["pop"], -c["id"]))

    def grant(self, k, key, how, c, src=None):
        y = self.year
        civ = self.civs[k]
        active = y if how == "invention" else y + self.rng.randint(ADOPT_MIN, ADOPT_MAX)
        cid = c["id"] if c else None
        civ["techs"][key] = {"year": y, "how": how, "city": cid, "active": active,
                             "src": src["id"] if src else None}
        self.techs_new.append([k, key, how])
        _, en, ar, cost, eff = TECH_INFO[key]
        if c is None:
            x, yy = self.cap_xy(k)
        else:
            x, yy = c["x"], c["y"]
        if how == "invention":
            if key == "irrigation":
                self.upgrade_farms(k, 3)
            if key == "canals":
                self.upgrade_farms(k, 6)
            self.ev("invention",
                    "INVENTION: %s by the %s kingdom in %s (year %d): %s" % (en, CIV_KEY[k], c["name_en"], y, eff),
                    "اختراع: %s في %s — %s" % (ar, c["name_ar"], CIV_NAMES[k]),
                    x, yy, civ=k, city=cid, log=True, tech=key, effect=eff)
        elif how == "theft":
            self.ev("theft", "The rich steal the secret of %s from %s" % (en, src["name_en"]),
                    "الأثرياء يسرقون سر %s من مدينة %s" % (ar, src["name_ar"]),
                    src["x"], src["y"], civ=k, city=src["id"], log=True, tech=key, year_active=active)

    def theft_step(self):
        d = self.dip
        if d["contact"] is None or self.year < d["contact"]:
            return
        rich = self.civs[RICH]
        poor = self.civs[POOR]
        trade_link = False
        for k in CIVS:
            for c in self.alive_cities(k):
                if c["cnt"]["bazaar"] or c["cnt"]["caravanserai"] or c["cnt"]["harbour"]:
                    trade_link = True
        p = THEFT_P * (THEFT_TRADE_MULT if trade_link else 1.0)
        if self.rng.random() >= p:
            return
        cand = [key for key, *_ in LADDER if self.known(POOR, key) and key not in rich["techs"]]
        if not cand:
            return
        if rich["gold"] < SPY_COST:
            return
        rich["gold"] -= SPY_COST
        self.theft["attempts"] += 1
        key = cand[0]
        srcs = self.alive_cities(POOR)
        if not srcs:
            return
        src = max(srcs, key=lambda c: (c["pop"], -c["id"]))
        if self.rng.random() < THEFT_SUCCESS:
            self.theft["success"] += 1
            self.grant(RICH, key, "theft", None, src=src)
            # grant() used None for the city: the stolen tech is located at the source city
            rich["techs"][key]["city"] = src["id"]
        else:
            if self.rng.random() < THEFT_CAUGHT:
                self.theft["caught"] += 1
                d["tension"] += SPY_CAUGHT_TENSION
                self.ev("spy_caught", "A rich spy is caught in %s while stealing %s" % (src["name_en"], LADDER[TECH_INDEX[key]][1]),
                        "القبض على جاسوس للأثرياء في %s" % src["name_ar"], src["x"], src["y"],
                        civ=POOR, city=src["id"], log=True, tech=key)
            else:
                self.ev("spy_failed", "A theft attempt on %s fails quietly" % src["name_en"],
                        "فشلت محاولة سرقة في %s" % src["name_ar"], src["x"], src["y"],
                        civ=RICH, city=src["id"], log=False, tech=key)

    def bribe_step(self):
        if self.dip["contact"] is None or self.dip["status"] == "war":
            return
        rich = self.civs[RICH]
        if rich["gold"] < BRIBE_MIN_GOLD or self.rng.random() >= BRIBE_P:
            return
        rcs = self.alive_cities(RICH)
        best = None
        for pc in self.alive_cities(POOR):
            if pc["loyalty"] >= BRIBE_LOY:
                continue
            dd = min((math.hypot(pc["x"] - r["x"], pc["y"] - r["y"]) for r in rcs), default=1e9)
            if dd <= BRIBE_DIST and (best is None or pc["loyalty"] < best[0]["loyalty"]):
                best = (pc, dd)
        if best is None:
            return
        pc = best[0]
        rich["gold"] -= BRIBE_COST
        if self.rng.random() < 0.5:
            self.bribes += 1
            self.capture(pc, RICH, None, kind="bribe")

    def diplomacy_step(self):
        d = self.dip
        y = self.year
        rcs = self.alive_cities(RICH)
        pcs = self.alive_cities(POOR)
        if not rcs or not pcs:
            return
        bd, ca, cb = 1e9, None, None
        for a in rcs:
            for b in pcs:
                dd = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
                if dd < bd:
                    bd, ca, cb = dd, a, b
        if d["contact"] is None:
            if bd <= CONTACT_DIST:
                d["contact"] = y
                mx, my = (ca["x"] + cb["x"]) // 2, (ca["y"] + cb["y"]) // 2
                self.ev("contact", "First contact: the borders of the two kingdoms meet",
                        "أول اتصال: تلاقت حدود المملكتين", mx, my, log=True)
            return
        status = d["status"]
        mx, my = (ca["x"] + cb["x"]) // 2, (ca["y"] + cb["y"]) // 2
        if status in ("peace", "truce"):
            if bd <= BORDER_DIST:
                d["tension"] += TENSION_BORDER
                if self.rng.random() < INCIDENT_P:
                    d["tension"] += INCIDENT_T
                    self.ev("incident", "Border incident near %s and %s" % (ca["name_en"], cb["name_en"]),
                            "حادث حدودي بين %s و%s" % (ca["name_ar"], cb["name_ar"]), mx, my, log=self.throttle(d, "inc_log", 8))
                if self.rng.random() < RES_DISPUTE_P:
                    near = [r for r in self.res_known_near(ca, cb)]
                    if near:
                        d["tension"] += RES_DISPUTE_T
                        rx, ry = near[0]
                        self.ev("dispute", "Dispute over a gold or oil deposit at (%d,%d)" % (rx, ry),
                                "نزاع على منجم ذهب أو نفط عند (%d,%d)" % (rx, ry), rx, ry, log=True)
            for k in CIVS:
                if self.rng.random() < INSULT_P[k]:
                    d["tension"] += INSULT_T
                    self.ev("insult", "The %s %s insults the other court" % (CIV_KEY[k], TITLE_EN[k]),
                            "إهانة من %s %s للبلاط الآخر" % (TITLE_AR[k], CIV_NAMES[k]), mx, my,
                            civ=k, log=True)
            d["tension"] *= (1 - TENSION_DECAY)
        if status == "peace" and d["tension"] >= WAR_TENSION:
            sr = self.strength(RICH)
            sp = self.strength(POOR)
            att = None
            if self.rng.random() < DECLARE_P[RICH]:
                att = RICH
            elif sp >= POOR_DECLARE_RATIO * sr and self.rng.random() < DECLARE_P[POOR]:
                att = POOR
            if att is not None:
                self.declare_war(att, mx, my)
        elif status == "truce" and y >= d["truce_until"]:
            d["status"] = "peace"
            d["tension"] = 2.0
        elif status == "war":
            dur = y - d["war_start"]
            sr = self.strength(RICH)
            sp = self.strength(POOR)
            sue = None
            if sp < 0.5 * sr and self.rng.random() < SUE_P_POOR:
                sue = POOR
            elif sr < 0.25 * sp and self.rng.random() < SUE_P_RICH:
                sue = RICH
            elif dur >= CEASE_AFTER and self.rng.random() < CEASE_P:
                sue = -1
            if sue is not None:
                self.make_truce(sue, mx, my)

    def res_known_near(self, ca, cb):
        out = []
        for j, r in self.res.items():
            if r[0] in ("gold", "oil") and not r[1]:
                x, yy = j % W, j // W
                if math.hypot(x - ca["x"], yy - ca["y"]) <= 7 or math.hypot(x - cb["x"], yy - cb["y"]) <= 7:
                    out.append((x, yy))
                    if len(out) >= 1:
                        break
        return out

    def strength(self, k):
        s = 4.0 * len(self.alive_cities(k))
        s += sum(c["garrison"] for c in self.alive_cities(k))
        s += sum(A["size"] for A in self.armies.values() if A["owner"] == k)
        return s

    def declare_war(self, att, x, y):
        d = self.dip
        d["status"] = "war"
        d["war_start"] = self.year
        d["attacker"] = att
        self.wars.append([self.year, None, CIV_KEY[att], 0])
        self.ev("war_start", "%s declare war on the %s kingdom" % (CIV_KEY[att].capitalize(), CIV_KEY[1 - att]),
                "إعلان الحرب من %s على %s" % (CIV_NAMES[att], CIV_NAMES[1 - att]), x, y,
                civ=att, log=True)
        self.reset_armies("idle")

    def make_truce(self, who, x, y):
        d = self.dip
        d["status"] = "truce"
        d["truce_until"] = self.year + self.rng.randint(TRUCE_MIN, TRUCE_MAX)
        d["tension"] = 2.0
        if self.wars and self.wars[-1][1] is None:
            self.wars[-1][1] = self.year
        self.ev("truce", "A truce is signed; the kingdoms withdraw to their cities for %d years" % TRUCE_YEARS,
                "هدنة: ينسحب الطرفان إلى مدنهما لمدة %d سنة" % TRUCE_YEARS, x, y, log=True)
        self.reset_armies()

    def reset_armies(self, mode="retreat"):
        for aid in list(self.sieges_active):
            self.end_siege(aid, "lifted")
        for A in self.armies.values():
            A["target"] = None
            A["path"] = []
            A["mode"] = mode

    def recruit_step(self):
        """Levies come from city garrisons (capped). Mercenaries are hired with gold ON TOP of the levies
        and cost upkeep every year; unpaid mercenaries desert (see upkeep_step)."""
        if self.dip["status"] != "war":
            return
        for k in CIVS:
            civ = self.civs[k]
            if self.rng.random() >= RECRUIT_P:
                continue
            mine = [A for A in self.armies.values() if A["owner"] == k]
            ccs = self.alive_cities(k)
            ecs = self.alive_cities(1 - k)
            if not ccs or not ecs:
                continue
            if len(mine) >= ARMY_CAP_BASE + len(ccs) // 3:
                continue
            cap = self.cities.get(civ["capital"]) if civ["capital"] is not None else ccs[0]
            front = min(ecs, key=lambda e: math.hypot(e["x"] - cap["x"], e["y"] - cap["y"]))
            srcs = [c for c in ccs if c["garrison"] >= RECRUIT_GARRISON_MIN]
            if not srcs:
                continue
            src = max(srcs, key=lambda c: (c["garrison"] - 0.1 * math.hypot(c["x"] - front["x"], c["y"] - front["y"]), -c["id"]))
            levy = int(min(ARMY_MAX, src["garrison"] - 10, int(src["pop"] * 0.05)))
            if levy < ARMY_MIN:
                continue
            na = int(levy * 0.15) if self.known(k, "bows") else 0
            nc = int(levy * 0.15)
            ni = levy - na - nc
            nm = 0
            if k == RICH and civ["gold"] >= MERC_MIN_GOLD:
                nm = int(min(MERC_MAX, civ["gold"] * MERC_GOLD_SHARE / MERC_PRICE))
            ns = 0
            if civ["siege_built"] and self.known(k, "trebuchet"):
                ns = min(12, 2 + int(src["pop"] // 300))
            cost = (ni + na + nc) * LEVY_PRICE + nm * MERC_PRICE + ns * ENG_PRICE
            if civ["gold"] < cost:
                nm = 0
                ns = 0
                cost = (ni + na + nc) * LEVY_PRICE
                if civ["gold"] < cost:
                    continue
            civ["gold"] -= cost
            src["garrison"] -= levy
            aid = self.nid("army")
            A = {"id": aid, "owner": k, "size": ni + na + nc + nm, "siege": ns,
                 "comp": {"inf": ni, "cav": nc, "arch": na, "merc": nm},
                 "cmdr": self.rng.choice(COMMANDERS[k]), "x": src["x"], "y": src["y"],
                 "idx": src["idx"], "path": [], "target": None, "mode": "march",
                 "home": src["id"], "start": self.year, "end": None, "wp": [],
                 "mtn": False}
            self.armies[aid] = A
            if nm > 0:
                n_m = self.throttle(civ, "hire_log", 6)
                self.ev("hire", "The rich hire %d mercenaries under %s at %s for %d gold" % (
                    ppl(nm), A["cmdr"], src["name_en"], nm * MERC_PRICE),
                    "الأثرياء يستأجرون %d مرتزقا بقيادة %s في %s بثمن %d ذهبا" % (
                        ppl(nm), A["cmdr"], src["name_ar"], nm * MERC_PRICE),
                    src["x"], src["y"], civ=k, city=src["id"], log=n_m, count=ppl(nm),
                    cost=round(nm * MERC_PRICE, 1), army=aid)
            if len(mine) == 0:
                self.ev("muster", "%s raise their first army under %s at %s" % (
                    CIV_KEY[k].capitalize(), A["cmdr"], src["name_en"]),
                    "%s يجندون أول جيش بقيادة %s في %s" % (CIV_NAMES[k], A["cmdr"], src["name_ar"]),
                    src["x"], src["y"], civ=k, city=src["id"], log=False, army=aid)

    def choose_target(self, A):
        """Armies head for the enemy capital when they can; otherwise the nearest (rich) or the weakest (poor)."""
        enemy = self.alive_cities(1 - A["owner"])
        if not enemy:
            return None
        ax, ay = A["x"], A["y"]
        if A["owner"] == RICH:
            key = lambda c: math.hypot(c["x"] - ax, c["y"] - ay) - (25.0 if c["capital"] else 0.0)
        else:
            key = lambda c: math.hypot(c["x"] - ax, c["y"] - ay) + 8.0 * self.walls(c) + 0.3 * c["garrison"] - (25.0 if c["capital"] else 0.0)
        return min(enemy, key=key)

    def step_cost(self, i):
        if i in self.roadset:
            return ROAD_COST
        t = self.terr[i]
        if t == SEA:
            return None
        if t == RIVER:
            return RIVER_COST
        if t == MOUNTAIN:
            return MTN_COST
        return FLAT_COST

    def path_to(self, start, goal, adj=False):
        gx, gy = goal % W, goal // W

        def h(i):
            return max(abs(i % W - gx), abs(i // W - gy)) * 0.5

        def is_goal(i):
            if adj:
                return max(abs(i % W - gx), abs(i // W - gy)) <= 1
            return i == goal

        if is_goal(start):
            return []
        heap = [(h(start), 0.0, start)]
        g = {start: 0.0}
        came = {}
        closed = set()
        n = 0
        while heap:
            f, gc, i = heapq.heappop(heap)
            if i in closed:
                continue
            closed.add(i)
            if is_goal(i):
                path = []
                cur = i
                while cur != start:
                    path.append(cur)
                    cur = came[cur]
                path.reverse()
                return path
            n += 1
            if n > NODE_CAP:
                return None
            x, y = i % W, i // W
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < W and 0 <= ny < H):
                        continue
                    j = ny * W + nx
                    cst = self.step_cost(j)
                    if cst is None:
                        continue
                    if dx and dy:
                        cst *= 1.414
                    ng = gc + cst
                    if ng < g.get(j, 1e18):
                        g[j] = ng
                        came[j] = i
                        heapq.heappush(heap, (ng + h(j), ng, j))
        return None

    def shrink(self, A, frac):
        for k in ("inf", "cav", "arch", "merc"):
            A["comp"][k] = int(round(A["comp"][k] * (1 - frac)))
        A["siege"] = int(round(A["siege"] * (1 - frac * 0.5)))
        A["size"] = sum(A["comp"].values())

    def end_army(self, A, why):
        if A["end"] is not None:
            return
        self.end_siege(A["id"], "failed")
        A["end"] = self.year
        A["mode"] = "gone"
        A["why"] = why
        self.army_hist.append(A)
        self.armies.pop(A["id"], None)

    def move_step(self):
        war = self.dip["status"] == "war"
        for aid in sorted(self.armies):
            A = self.armies.get(aid)
            if A is None:
                continue
            A["mtn"] = False
            A["wp"] = [[A["x"], A["y"]]]
            if A["size"] < ARMY_MIN:
                self.end_army(A, "disband")
                continue
            if A["mode"] == "siege":
                c = self.cities.get(A["target"]) if A["target"] is not None else None
                if c is None or not c["alive"] or c["civ"] == A["owner"]:
                    A["mode"] = "idle"
                    A["target"] = None
                    self.end_siege(A["id"], "lifted")
                continue
            if not war and A["mode"] != "retreat":
                A["mode"] = "retreat"
                A["path"] = []
            if not A["path"]:
                if A["mode"] == "retreat" or not war:
                    home = self.cities.get(A["home"])
                    if home is None or not home["alive"] or home["civ"] != A["owner"]:
                        hs = self.alive_cities(A["owner"])
                        home = min(hs, key=lambda c: math.hypot(c["x"] - A["x"], c["y"] - A["y"])) if hs else None
                    if home is not None:
                        A["home"] = home["id"]
                        p = self.path_to(A["idx"], home["idx"], adj=True)
                        A["path"] = p or []
                    if not A["path"]:
                        A["mode"] = "idle"
                elif A["mode"] in ("march", "idle") and war:
                    tgt = self.choose_target(A)
                    if tgt is not None:
                        p = self.path_to(A["idx"], tgt["idx"], adj=True)
                        if p is not None:
                            A["target"] = tgt["id"]
                            A["path"] = p
                            A["mode"] = "march"
            budget = ARMY_BUDGET
            moved = []
            while budget > 0 and A["path"]:
                nxt = A["path"][0]
                cst = self.step_cost(nxt)
                if cst is None:
                    A["path"] = []
                    break
                if cst > budget:
                    break
                budget -= cst
                A["path"].pop(0)
                A["idx"] = nxt
                A["x"], A["y"] = nxt % W, nxt // W
                moved.append(nxt)
                if self.terr[nxt] in (MOUNTAIN, RIVER):
                    A["mtn"] = True
            pts = [[j % W, j // W] for j in moved]
            if len(pts) > 10:
                step = len(pts) / 10.0
                pts = [pts[int(k * step)] for k in range(10)] + [pts[-1]]
            A["wp"] += pts
            if A["mode"] == "march" and not A["path"] and A["target"] is not None:
                c = self.cities.get(A["target"])
                if c is not None and c["alive"] and c["civ"] != A["owner"] and \
                        max(abs(c["x"] - A["x"]), abs(c["y"] - A["y"])) <= 1:
                    if A["size"] >= SIEGE_RATIO * max(1, c["garrison"]) or A["siege"] > 0:
                        A["mode"] = "siege"
                        self.start_siege(A, c)
                    else:
                        A["mode"] = "idle"           # too weak to settle: wait for reinforcements
                        A["target"] = None
            if A["mode"] == "retreat" and not A["path"]:
                A["mode"] = "idle"

    def field_battle(self, att, dfn, btype, x, y, ambush=False):
        ca, cb = att["owner"], dfn["owner"]
        j = y * W + x
        storm = 1.0
        for d in self.disasters_now:
            if d["type"] == "sandstorm" and math.hypot(x - d["x"], y - d["y"]) <= d["r"]:
                storm = SANDSTORM_POWER
        na = self.rng.uniform(0.85, 1.15)
        nb = self.rng.uniform(0.85, 1.15)
        tdef = MOUNTAIN_DEF if self.terr[j] == MOUNTAIN else (RIVER_DEF if self.terr[j] == RIVER else 1.0)
        surprise = AMBUSH_SURPRISE if ambush else 1.0

        def power(A, k, ablate, noise, terrain=1.0, sp=1.0):
            comp = A["comp"]
            bows = self.known(k, "bows") and ablate != "bows"
            base = (comp["inf"] * P_INF + comp["cav"] * P_CAV
                    + comp["arch"] * (P_ARCH + (BOWS_BONUS if bows else 0.0)) + comp["merc"] * P_MERC)
            wm = 1.0
            if self.known(k, "iron") and ablate != "iron":
                wm += IRON_BONUS
            if self.known(k, "steel") and ablate != "steel":
                wm += STEEL_BONUS
            tac = (TAC_BASE + TAC_SLOPE * INTEL[k]) if ablate != "tactics" else 1.0
            return base * wm * tac * noise * terrain * sp * storm

        def outcome(ablate, terrain_on=True):
            pa = power(att, ca, ablate, na, sp=surprise)
            pd = power(dfn, cb, ablate, nb, terrain=tdef if terrain_on else 1.0)
            return pa >= pd, pa, pd

        att_win, pa, pd = outcome(None)
        deciding = []
        for key in ("bows", "iron", "steel"):
            if outcome(key)[0] != att_win and self.known(ca if att_win else cb, key):
                deciding.append("tech:" + key)
        if not deciding and tdef != 1.0 and outcome(None, terrain_on=False)[0] != att_win:
            deciding.append("terrain")
        if not deciding and outcome("tactics")[0] != att_win:
            deciding.append("tactics")
        if not deciding and ambush:
            deciding.append("surprise")
        if not deciding:
            deciding.append("numbers")
        r = pa / max(1e-9, pa + pd)
        spread = abs(2 * r - 1)
        wl = WIN_BASE + WIN_SLOPE * (1 - spread)
        ll = LOSER_BASE + LOSER_SLOPE * spread
        sa, sd = att["size"], dfn["size"]
        att_comp = dict(att["comp"])
        def_comp = dict(dfn["comp"])
        la, ld = (wl, ll) if att_win else (ll, wl)
        loss_a = int(round(sa * la))
        loss_d = int(round(sd * ld))
        self.shrink(att, la)
        self.shrink(dfn, ld)
        winner = att if att_win else dfn
        loser = dfn if att_win else att
        bid = self.nid("bat")
        ce = self.cities[self.ocity[j]] if self.ocity[j] >= 0 else None
        place = ce["name_en"] if ce else "the open ground"
        place_ar = ce["name_ar"] if ce else "الميدان المفتوح"
        factor = ", ".join(deciding)
        kind_en = {"field": "field", "ambush": "ambush"}[btype]
        en = ("%s battle at %s: %s (%s, %d men) %s %s (%s, %d men); losses %d and %d men; deciding factor: %s" % (
            kind_en, place, att["cmdr"], CIV_KEY[ca], ppl(sa), "defeats" if att_win else "is repulsed by",
            dfn["cmdr"], CIV_KEY[cb], ppl(sd), ppl(loss_a), ppl(loss_d), factor))
        ar = "%s عند %s: فاز %s" % ("كمين" if btype == "ambush" else "معركة ميدانية", place_ar, CIV_NAMES[winner["owner"]])
        bat = {"id": bid, "year": self.year, "x": x, "y": y, "type": btype,
               "att_civ": CIV_KEY[ca], "def_civ": CIV_KEY[cb], "att_army": att["id"],
               "def_army": dfn["id"], "city": None, "att_size": sa, "def_size": sd,
               "att_loss": loss_a, "def_loss": loss_d, "att_comp": att_comp, "def_comp": def_comp,
               "result": "att" if att_win else "def", "notes": [], "decisive": deciding, "factor": factor}
        self.battles.append(bat)
        self.battles_y.append(bat)
        recent = [yy for yy in self.battle_log_years if yy > self.year - 10]
        log_it = len(recent) < 6          # the chronicle shows at most six battles per decade; state has all
        if log_it:
            self.battle_log_years = recent + [self.year]
        e = self.ev("battle", en, ar, x, y, civ=winner["owner"], city=None, log=log_it, battle=bid, factor=factor)
        bat["event"] = e["id"]
        loser["mode"] = "retreat"
        loser["path"] = []
        loser["target"] = None
        if loser["size"] < ARMY_MIN:
            self.end_army(loser, "destroyed")
        if att["size"] < ARMY_MIN:
            self.end_army(att, "destroyed")
        self.fought.add(att["id"])
        self.fought.add(dfn["id"])
        return bat

    def siege_round(self, A, c):
        k_att = A["owner"]
        k_def = c["civ"]
        sg = self.sieges_active.get(A["id"])
        if sg is None:
            sg = self.start_siege(A, c)
        if A["siege"] > 0 and self.known(k_att, "trebuchet") and self.walls(c) > 0:
            c["walls_dmg"] += A["siege"] * ENG_DMG
            while c["walls_dmg"] >= WALL_HP and self.walls(c) > 0:
                c["walls_dmg"] -= WALL_HP
                segs = [self.buildings[b] for b in c["blds"]
                        if self.buildings[b]["destroyed"] is None and self.buildings[b]["type"] == "wall"]
                if segs:
                    self.destroy(segs[0])
                    if self.throttle(c, "breach_log", 5):
                        self.ev("breach", "The trebuchets of the %s break a wall of %s" % (CIV_KEY[k_att], c["name_en"]),
                                "المنجنيق يحطم سورا من %s" % c["name_ar"], c["x"], c["y"], civ=k_att,
                                city=c["id"], log=True, siege=sg["id"])
            if self.walls(c) == 0:
                c["walls_dmg"] = 0.0
        if c["garrison"] <= 0:
            if A["size"] >= CAPTURE_MIN:
                self.capture(c, k_att, A, kind="assault")
            return
        c["blockade"] += 1
        sg["rounds"] += 1
        if c["blockade"] >= STARVE_YEARS and A["size"] >= CAPTURE_MIN:
            # the blockade starves the city: it surrenders (stored food is gone, no reinforcements)
            c["garrison"] = max(0, c["garrison"] // 3)
            self.capture(c, k_att, A, kind="starve")
            return
        na = self.rng.uniform(0.85, 1.15)
        nd = self.rng.uniform(0.85, 1.15)
        walls = self.walls(c)
        tower = c["cnt"]["tower"] > 0

        def outcome(ablate):
            comp = A["comp"]
            bows = self.known(k_att, "bows") and ablate != "bows"
            base = (comp["inf"] * P_INF + comp["cav"] * P_CAV
                    + comp["arch"] * (P_ARCH + (BOWS_BONUS if bows else 0.0)) + comp["merc"] * P_MERC)
            wm = 1.0
            if self.known(k_att, "iron") and ablate != "iron":
                wm += IRON_BONUS
            if self.known(k_att, "steel") and ablate != "steel":
                wm += STEEL_BONUS
            pa = base * wm * (TAC_BASE + TAC_SLOPE * INTEL[k_att]) * na
            if walls > 0 and A["siege"] == 0:
                pa *= HEAD_ON
            wall_def = 1.0 + WALL_BONUS * walls + (TOWER_BONUS if tower else 0.0)
            pd = c["garrison"] * P_INF * wall_def * nd
            return pa >= pd, pa, pd

        att_win, pa, pd = outcome(None)
        r = pa / max(1e-9, pa + pd)
        spread = abs(2 * r - 1)
        wl = WIN_BASE + WIN_SLOPE * (1 - spread)
        ll = LOSER_BASE + LOSER_SLOPE * spread
        sa = A["size"]
        sd = c["garrison"]
        if att_win:
            loss_a = int(round(sa * wl))
            loss_d = min(sd, int(round(sd * ll)) + int(round(sd * 0.1)))
            self.shrink(A, wl)
        else:
            loss_a = int(round(sa * ll))
            loss_d = int(round(sd * wl))
            self.shrink(A, ll)
        c["garrison"] = max(0, sd - loss_d)
        sg["att_loss"] += loss_a
        sg["def_loss"] += loss_d
        if not att_win and A["size"] < ARMY_MIN:
            self.end_army(A, "repulsed")
        self.fought.add(A["id"])

    def capture(self, c, new, army, kind):
        """A winning army leaves a garrison and marches on: winners push on, they do not stop."""
        old = c["civ"]
        y = self.year
        if army is not None:
            self.end_siege(army["id"], "captured")
        c["civ"] = new
        c["captured"].append([y, CIV_KEY[old], CIV_KEY[new]])
        self.captures.append([y, c["id"], CIV_KEY[old], CIV_KEY[new], kind])
        was_capital = c["capital"]
        for bid in c["blds"]:
            b = self.buildings[bid]
            if b["destroyed"] is not None:
                continue
            b["owner"] = new
            self.bchg.add(bid)
            p = 0.5 if b["type"] == "palace" else 0.12
            if self.rng.random() < p:
                self.destroy(b)
        send = 5
        if army is not None:
            send = max(6, army["size"] // 4)
            if army["size"] > send:
                self.shrink(army, send / float(army["size"]))
            army["target"] = None
            army["path"] = []
            army["mode"] = "idle"
            if army["size"] < ARMY_MIN:
                self.end_army(army, "spent")
        c["garrison"] = send
        c["loyalty"] = 25.0
        c["blockade"] = 0
        c["walls_dmg"] = 0.0
        c["pop"] *= 0.92
        if c["id"] in self.civs[old]["cities"]:
            self.civs[old]["cities"].remove(c["id"])
        self.civs[new]["cities"].append(c["id"])
        c["capital"] = False
        if was_capital:
            self.civs[old]["capital"] = None
            self.civs[old]["capital_due"] = y + CAPITAL_REBUILD
            self.civs[old]["fell"] = True
            self.ev("capital_fall", "The capital %s falls to the %s kingdom; the %s court flees" % (
                c["name_en"], CIV_KEY[new], CIV_KEY[old]),
                "سقوط عاصمة %s: %s بيد %s" % (CIV_NAMES[old], c["name_ar"], CIV_NAMES[new]),
                c["x"], c["y"], civ=new, city=c["id"], log=True)
        for A in self.armies.values():
            if A["target"] == c["id"]:
                A["target"] = None
                A["path"] = []
                A["mode"] = "idle"
        verb = {"assault": "falls to", "bribe": "is bought over by", "starve": "surrenders to"}[kind]
        self.ev("capture", "%s %s the %s kingdom" % (c["name_en"], verb, CIV_KEY[new]),
                "سقطت %s بيد %s" % (c["name_ar"], CIV_NAMES[new]) if kind in ("assault", "starve")
                else "رشي حاكم %s فسلم المدينة إلى %s" % (c["name_ar"], CIV_NAMES[new]),
                c["x"], c["y"], civ=new, city=c["id"], log=True)
        self.dirty = True

    def encounter_step(self):
        if self.dip["status"] != "war":
            return
        for aid in sorted(self.armies):
            A = self.armies.get(aid)
            if A is None or A["id"] in self.fought:
                continue
            enemies = [B for B in self.armies.values()
                       if B["owner"] != A["owner"] and B["id"] not in self.fought
                       and max(abs(B["x"] - A["x"]), abs(B["y"] - A["y"])) <= FIELD_RANGE]
            if enemies:
                B = min(enemies, key=lambda b: b["id"])
                self.field_battle(A, B, "field", A["x"], A["y"])
                continue
            if A["mtn"] and A["owner"] == RICH:
                for B in sorted(self.armies.values(), key=lambda b: b["id"]):
                    if B["owner"] == POOR and B["id"] not in self.fought \
                            and max(abs(B["x"] - A["x"]), abs(B["y"] - A["y"])) <= AMBUSH_RANGE \
                            and self.rng.random() < AMBUSH_P[POOR]:
                        self.field_battle(B, A, "ambush", B["x"], B["y"], ambush=True)
                        break
                if A["id"] in self.fought:
                    continue
            if A["mode"] == "siege" and A["target"] is not None:
                c = self.cities.get(A["target"])
                if c is not None and c["alive"] and c["civ"] != A["owner"] \
                        and max(abs(c["x"] - A["x"]), abs(c["y"] - A["y"])) <= 1:
                    self.siege_round(A, c)
        sieged = set(A["target"] for A in self.armies.values() if A["mode"] == "siege")
        for c in self.alive_cities(RICH) + self.alive_cities(POOR):
            if c["id"] not in sieged:
                c["blockade"] = 0

    def expansion_step(self):
        if self.year > EXPAND_END or self.dip["status"] == "war":
            return
        for k in CIVS:
            civ = self.civs[k]
            cs = self.alive_cities(k)
            if not cs or len(cs) >= CITY_MAX[k]:
                continue
            if civ["gold"] < FOUND_COST + RESERVE[k]:
                continue
            if self.rng.random() >= FOUND_P[k]:
                continue
            parents = [c for c in cs if c["pop"] >= FOUND_MIN_POP]
            if not parents:
                continue
            if k == POOR:
                # smart: settle from the city nearest the frontier
                enemy = self.alive_cities(1 - k)
                if enemy:
                    parent = min(parents, key=lambda c: (min(math.hypot(c["x"] - e["x"], c["y"] - e["y"]) for e in enemy), c["id"]))
                else:
                    parent = max(parents, key=lambda c: (c["pop"], -c["id"]))
            else:
                parent = parents[self.rng.randrange(len(parents))]
            site = self.find_new_site(k, parent)
            if site is None:
                continue
            path = self.path_to(site, parent["idx"], adj=True)
            if path is None:
                continue
            civ["gold"] -= FOUND_COST
            parent["pop"] -= FOUND_POP * 0.5
            c = self.add_city(k, site, FOUND_POP)
            full = [site] + path
            self.add_road(c, parent, full)
            self.build(c, "house")
            self.build(c, "farm")
            self.ev("found", "%s founded by the %s kingdom, linked to %s" % (c["name_en"], CIV_KEY[k], parent["name_en"]),
                    "تأسيس %s على يد %s" % (c["name_ar"], CIV_NAMES[k]), c["x"], c["y"], civ=k,
                    city=c["id"], log=self.throttle(civ, "found_log", 3))

    def find_new_site(self, k, parent):
        px, py = parent["x"], parent["y"]
        allc = self.alive_cities(RICH) + self.alive_cities(POOR)
        enemy = self.alive_cities(1 - k)
        best = None
        bestsc = -1e9
        tries = 150 if k == POOR else 60
        for _ in range(tries):
            ang = self.rng.uniform(0, 2 * math.pi)
            rad = self.rng.uniform(SITE_RING[0], SITE_RING[1])
            x = int(round(px + rad * math.cos(ang)))
            y = int(round(py + rad * math.sin(ang)))
            if not (0 <= x < W and 0 <= y < H):
                continue
            j = y * W + x
            if self.terr[j] not in BUILDABLE or self.owner[j] != -1:
                continue
            if any(math.hypot(c["x"] - x, c["y"] - y) < SITE_MIN_DIST for c in allc):
                continue
            if any(math.hypot(c["x"] - x, c["y"] - y) < SITE_ENEMY_MIN for c in enemy):
                continue
            if k == POOR:
                sc = (2.0 if self.dist_river[j] <= 3 else 0.0) + (2.0 if self.dist_oasis[j] <= 3 else 0.0)
                if enemy:
                    sc -= 0.25 * min(math.hypot(e["x"] - x, e["y"] - y) for e in enemy)
                sc += 0.1 * sum(1 for dx, dy, d in OFF[3] if 0 <= x + dx < W and 0 <= y + dy < H
                                and self.terr[(y + dy) * W + x + dx] in (SILT, OASIS))
            else:
                sc = self.rng.random()
            if sc > bestsc:
                bestsc = sc
                best = j
        return best

    def add_road(self, a, b, full):
        rid = self.nid("road")
        pts = [[j % W, j // W] for j in full[::2]]
        last = [b["x"], b["y"]]
        if pts[-1] != last:
            pts.append(last)
        road = {"id": rid, "a": a["id"], "b": b["id"], "year": self.year, "civ": a["civ"], "pts": pts}
        self.roads.append(road)
        self.roads_y.append(road)
        self.roadset.update(full)
        self.roadset.add(b["idx"])
        a["roads"] += 1
        b["roads"] += 1

    def reserve(self, k):
        """Gold kept back from building: the founding cost while the civ can still expand."""
        r = RESERVE[k]
        if len(self.alive_cities(k)) < CITY_MAX[k] and self.year <= EXPAND_END:
            r += FOUND_COST
        return r

    def build_step(self):
        for cid in sorted(self.cities):
            c = self.cities[cid]
            if not c["alive"]:
                continue
            k = c["civ"]
            civ = self.civs[k]
            maxh = HOUSE_MAX["capital" if c["capital"] else c["tier"]]
            if c["pop"] > c["cap"] * 0.7:
                for _ in range(HOUSES_PER_YEAR):
                    if c["cnt"]["house"] >= maxh:
                        break
                    if civ["gold"] - BUILD["house"][1] < self.reserve(k):
                        break
                    if self.build(c, "house") is None:
                        break
            if civ["gold"] < self.reserve(k) + 20.0:
                continue
            cands = self.candidates(c)
            if not cands:
                continue
            order = sorted(cands, key=lambda t: (-t[0], t[1]))
            if k == RICH and self.rng.random() < 0.5:
                order = list(cands)
                self.rng.shuffle(order)
            placed = 0
            limit = MAX_NONHOUSE_PER_YEAR + int(civ["gold"] // (1500.0 if k == POOR else 3000.0))
            for score, btype, res in order:
                if placed >= limit:
                    break
                cost = BUILD[btype][1]
                if civ["gold"] - cost < self.reserve(k):
                    continue
                if self.build(c, btype, res) is not None:
                    placed += 1

    # ---------------- end of game, records, summary
    def check_end(self):
        y = self.year
        n = {k: len(self.alive_cities(k)) for k in CIVS}
        for loser in CIVS:
            w = 1 - loser
            if n[loser] == 0:
                self.finish(w, "conquest")
                return
        for loser in CIVS:
            w = 1 - loser
            civ = self.civs[loser]
            pl = self.pop_of(loser)
            pw = self.pop_of(w)
            no_cap = civ["capital"] is None
            weak = no_cap and n[loser] < 2 and pl < 0.10 * pw
            civ["weak_years"] = civ["weak_years"] + 1 if weak else 0
            if civ["weak_years"] >= 5:
                self.finish(w, "collapse")
                return
        # no capital: rebuild after CAPITAL_REBUILD years in the largest city
        for k in CIVS:
            civ = self.civs[k]
            if civ["capital"] is None and y >= civ["capital_due"] and n[k] >= 3:
                c = max(self.alive_cities(k), key=lambda c: (c["pop"], -c["id"]))
                c["capital"] = True
                c["tier"] = "capital"
                c["claim"] = CLAIM["capital"]
                civ["capital"] = c["id"]
                self.dirty = True
        if y >= MAX_YEARS - 1:
            rs = self.score(RICH)
            ps = self.score(POOR)
            self.finish(POOR if ps >= rs else RICH, "time limit")

    def score(self, k):
        return self.pop_of(k) + 1500.0 * len(self.alive_cities(k)) + 300.0 * len(self.civs[k]["techs"])

    def finish(self, winner, reason):
        self.game_over = True
        self.winner = winner
        self.end_reason = reason
        self.end_year = self.year
        for w in self.wars:
            if w[1] is None:
                w[1] = self.year
        self.ev("end", "End of the story: %s (%s)" % (CIV_KEY[winner] + " kingdom wins", reason),
                "نهاية القصة: فوز %s (%s)" % (CIV_NAMES[winner], reason),
                *self.cap_xy(winner), civ=winner, log=True)

    def civ_stats(self, k):
        civ = self.civs[k]
        cs = self.alive_cities(k)
        army_units = sum(A["size"] for A in self.armies.values() if A["owner"] == k)
        return {
            "pop": ppl(sum(c["pop"] for c in cs)),
            "gold": round(civ["gold"], 1),
            "food": ppl(sum(c["stock"] for c in cs)),
            "water": ppl(sum(c["water_prod"] for c in cs)),
            "soldiers": ppl(sum(c["garrison"] for c in cs) + army_units),
            "techs": len(civ["techs"]),
            "territory": self.terr_count[k],
            "cities": len(cs),
            "leader": civ["leader"],
            "rp": round(civ["rp"], 1),
            "income": round(civ.get("inc_last", 0.0), 1),
        }

    def record_year(self):
        y = self.year
        stats = {CIV_KEY[k]: self.civ_stats(k) for k in CIVS}
        self.last_stats = stats
        self.score_series.append((y, self.score(RICH), self.score(POOR)))
        self.gold_series.append((y, round(self.civs[RICH]["gold"], 1), round(self.civs[POOR]["gold"], 1)))
        self.tech_series.append((y, len(self.civs[POOR]["techs"]), len(self.civs[RICH]["techs"])))
        self.civ_series.append((y, stats["rich"]["territory"], stats["poor"]["territory"],
                                stats["rich"]["soldiers"], stats["poor"]["soldiers"]))
        self.check_overtake(y)
        if not self.record:
            self.reset_year_buffers()
            return
        snap = (y % SNAP_EVERY == 0) or self.game_over
        arm = [self.army_rec(A) for A in self.armies.values()]
        arm += [self.army_rec(A) for A in self.army_hist if A["end"] == y]
        rec = {
            "year": y,
            "stats": stats,
            "dip": {"status": self.dip["status"], "tension": round(self.dip["tension"], 2)},
            "cities": [{"id": c["id"], "civ": CIV_KEY[c["civ"]], "name_en": c["name_en"],
                        "name_ar": c["name_ar"], "x": c["x"], "y": c["y"],
                        "pop": ppl(c["pop"]), "tier": c["tier"], "walls": self.walls(c),
                        "garrison": ppl(c["garrison"]), "loyalty": round(c["loyalty"]),
                        "capital": bool(c["capital"])}
                       for c in (self.cities[i] for i in sorted(self.cities)) if c["alive"]],
            "owner_chg": self.owner_chg,
            "owner_full": "".join(".RP"[v + 1] for v in self.owner) if snap else None,
            "bld": [self.bld_rec(self.buildings[b]) for b in sorted(self.bchg)],
            "bld_full": [self.bld_rec(b) for b in sorted(self.buildings.values(), key=lambda b: b["id"])
                         if b["destroyed"] is None] if snap else None,
            "roads": [{"id": r["id"], "a": r["a"], "b": r["b"], "civ": CIV_KEY[r["civ"]], "pts": r["pts"]}
                      for r in self.roads_y],
            "roads_full": [{"id": r["id"], "a": r["a"], "b": r["b"], "civ": CIV_KEY[r["civ"]], "pts": r["pts"]}
                           for r in self.roads] if snap else None,
            "armies": arm,
            "sieges": [self.sg_out(s) for s in self.sieges_y],
            "battles": [b["id"] for b in self.battles_y],
            "battles_full": [self.bat_clean(b) for b in self.battles_y],
            "events": [dict(e) for e in self.events_y],
            "disasters": [dict(d) for d in self.disasters_now],
            "ships": [[b["ship"][0], b["ship"][1], CIV_KEY[b["owner"]]] for b in self.buildings.values()
                      if b["type"] == "harbour" and b["destroyed"] is None and b.get("ship")],
            "techs_new": self.techs_new,
        }
        self.records.append(rec)
        self.reset_year_buffers()

    def reset_year_buffers(self):
        self.owner_chg = []
        self.events_y = []
        self.battles_y = []
        self.bchg = set()
        self.roads_y = []
        self.techs_new = []
        self.sieges_y = []

    def bld_rec(self, b):
        return {"id": b["id"], "city": b["city"], "type": b["type"], "x": b["x"], "y": b["y"],
                "owner": CIV_KEY[b["owner"]], "built": b["built"], "destroyed": b["destroyed"],
                "irr": b["irr"], "res": b["res"]}

    def army_rec(self, A):
        return {"id": A["id"], "owner": CIV_KEY[A["owner"]], "size": ppl(A["size"]), "siege": A["siege"],
                "comp": {k: ppl(v) for k, v in A["comp"].items()}, "cmdr": A["cmdr"], "x": A["x"], "y": A["y"],
                "mode": A["mode"], "wp": A["wp"], "target": A["target"], "end": A["end"]}

    def clean_ev(self, e):
        return dict(e)

    def bat_clean(self, b):
        d = dict(b)
        for k in ("att_size", "def_size", "att_loss", "def_loss"):
            d[k] = ppl(d[k])
        for key in ("att_comp", "def_comp"):
            if d.get(key) is not None:
                d[key] = {k: ppl(v) for k, v in d[key].items()}
        return d

    def sg_out(self, sg):
        d = dict(sg)
        for k in ("att_start", "def_start", "att_loss", "def_loss"):
            d[k] = ppl(d[k])
        return d

    def crossed(self, d, key, amount, step):
        """True when the running total passes a multiple of step (irregular years)."""
        before = d.get(key, 0.0)
        after = before + amount
        d[key] = after
        return int(after // step) > int(before // step)

    def throttle(self, d, key, gap):
        if self.year - d.get(key, -999) >= gap:
            d[key] = self.year
            return True
        return False

    def check_overtake(self, y):
        if self.overtook or y < 30:
            return
        pi = self.civs[POOR].get("inc_last", 0.0)
        ri = self.civs[RICH].get("inc_last", 0.0)
        if pi > ri and pi > 0:
            self.overtook = True
            x, yy = self.cap_xy(POOR)
            self.ev("overtake", "The poor now out-earn the rich: %d against %d gold a year" % (pi, ri),
                    "الفقراء يكسبون الآن أكثر من الأثرياء", x, yy, civ=POOR, log=True,
                    poor_income=round(pi, 1), rich_income=round(ri, 1))

    def start_siege(self, A, c):
        sg = {"id": self.nid("siege"), "army": A["id"], "att_civ": CIV_KEY[A["owner"]],
              "city": c["id"], "city_name": c["name_en"], "x": A["x"], "y": A["y"],
              "start": self.year, "end": None, "rounds": 0, "att_loss": 0, "def_loss": 0,
              "att_start": A["size"], "def_start": c["garrison"], "engines": A["siege"], "outcome": None}
        self.sieges_active[A["id"]] = sg
        self.sieges_all.append(sg)
        self.sieges_y.append(sg)
        self.ev("siege_start", "Siege of %s begins: %s army of %d men under %s" % (
            c["name_en"], CIV_KEY[A["owner"]], ppl(A["size"]), A["cmdr"]),
            "بدء حصار %s بجيش من %d رجل" % (c["name_ar"], ppl(A["size"])), A["x"], A["y"],
            civ=A["owner"], city=c["id"], log=self.crossed(self.dip, "siege_total", 1, 5), siege=sg["id"])
        return sg

    def end_siege(self, aid, outcome):
        sg = self.sieges_active.pop(aid, None)
        if sg is None:
            return None
        sg["end"] = self.year
        sg["outcome"] = outcome
        self.sieges_y.append(sg)
        c = self.cities.get(sg["city"])
        cn = c["name_en"] if c else sg["city_name"]
        cn_ar = c["name_ar"] if c else sg["city_name"]
        self.ev("siege_end", "Siege of %s ends after %d rounds: %s" % (cn, sg["rounds"], outcome),
                "انتهاء حصار %s بعد %d جولة: %s" % (cn_ar, sg["rounds"], outcome),
                sg["x"], sg["y"], civ=None, city=sg["city"], log=self.crossed(self.dip, "siege_end_total", 1, 5), siege=sg["id"], outcome=outcome)
        return sg

    def waste_step(self):
        civ = self.civs[RICH]
        if civ.get("feasts", 0) >= FEAST_MAX or civ["gold"] < FEAST_MIN_GOLD or self.rng.random() >= FEAST_P:
            return
        civ["feasts"] = civ.get("feasts", 0) + 1
        cost = civ["gold"] * FEAST_SHARE
        civ["gold"] -= cost
        x, y = self.cap_xy(RICH)
        self.ev("waste", "The rich court holds a lavish feast and spends %d gold on it" % cost,
                "وليمة فاخرة للأثرياء تنفق %d ذهبا" % cost, x, y, civ=RICH, log=True, kind="feast",
                cost=round(cost, 1))

    def spend_step(self):
        """The poor do not hoard: gold above SPEND_HI goes to militia (more soldiers in every city)."""
        civ = self.civs[POOR]
        excess = civ["gold"] - SPEND_HI
        if excess <= 0:
            return
        budget = excess * 0.05 / MILITIA_COST
        raised = 0
        for c in sorted(self.alive_cities(POOR), key=lambda c: (-c["pop"], c["id"])):
            if budget <= 0:
                break
            room = int(max(0.0, MILITIA_FRAC * c["pop"] - c["garrison"]))
            add = min(room, int(budget))
            if add > 0:
                c["garrison"] += add
                budget -= add
                raised += add
        if raised:
            civ["gold"] -= raised * MILITIA_COST
            x, y = self.cap_xy(POOR)
            self.ev("militia", "The poor raise %d militia men from their surplus" % ppl(raised),
                    "الفقراء يجندون %d من الحراس من فائض خزينتهم" % ppl(raised), x, y, civ=POOR,
                    log=self.crossed(civ, "militia_total", raised, 2000.0), count=ppl(raised))
        excess = civ["gold"] - SPEND_HI
        if excess > 0 and self.year >= 20:
            gold_in = excess * ENDOW_FRAC
            civ["gold"] -= gold_in
            civ["rp"] += gold_in / SCHOLAR_COST
            x, y = self.cap_xy(POOR)
            self.ev("endowment", "The poor endow schools: %d gold buys %d research points" % (
                gold_in, gold_in / SCHOLAR_COST), "الفقراء يوقفون %d ذهبا لتمويل المدارس" % gold_in,
                x, y, civ=POOR, log=self.crossed(civ, "endow_total", gold_in, 20000.0), gold=round(gold_in, 1))

    def endow(self, c, btype, n):
        self.territory_update()
        for _ in range(n):
            j = self.find_site(c, btype)
            if j is None:
                break
            self.add_building(c, btype, j)

    def run(self, nyears=MAX_YEARS):
        self.init_world()
        for y in range(nyears):
            self.year = y
            self.step()
            if self.game_over:
                break
        if not self.game_over:
            self.finish(POOR if self.score(POOR) >= self.score(RICH) else RICH, "time limit")
        return self

    def summary(self):
        s = {"seed": self.seed, "winner": CIV_KEY[self.winner], "end_year": self.end_year,
             "end_reason": self.end_reason}
        ws = self.wars
        s["war_count"] = len(ws)
        s["first_war"] = ws[0][0] if ws else None
        s["war_starts"] = " ".join(str(w[0]) for w in ws)
        s["war_years"] = sum((w[1] or self.end_year) - w[0] for w in ws)
        s["contact"] = self.dip["contact"]
        caps = self.captures
        s["captures"] = len(caps)
        s["captures_to_poor"] = sum(1 for c in caps if c[3] == "poor")
        s["captures_to_rich"] = sum(1 for c in caps if c[3] == "rich")
        s["capital_falls"] = sum(1 for e in self.events if e["type"] == "capital_fall")
        s["bribes"] = self.bribes
        bs = self.battles
        s["battles"] = len(bs)
        s["field_battles"] = sum(1 for b in bs if b["type"] == "field")
        s["ambushes"] = sum(1 for b in bs if b["type"] == "ambush")
        s["sieges"] = len(self.sieges_all)
        s["siege_captures"] = sum(1 for g in self.sieges_all if g["outcome"] == "captured")
        s["siege_lifted"] = sum(1 for g in self.sieges_all if g["outcome"] == "lifted")
        s["siege_failed"] = sum(1 for g in self.sieges_all if g["outcome"] == "failed")
        s["siege_rounds"] = sum(g["rounds"] for g in self.sieges_all)
        s["decisive_battles"] = sum(1 for b in bs if any(d != "numbers" for d in b["decisive"]))
        s["hires"] = sum(1 for e in self.events if e["type"] == "hire")
        s["hired_men"] = sum(e.get("count", 0) for e in self.events if e["type"] == "hire")
        s["waste_events"] = sum(1 for e in self.events if e["type"] == "waste")
        s["statues"] = sum(1 for e in self.events if e["type"] == "waste" and e.get("kind") == "statue")
        s["palaces"] = sum(1 for e in self.events if e["type"] == "waste" and e.get("kind") == "palace")
        s["feasts"] = sum(1 for e in self.events if e["type"] == "waste" and e.get("kind") == "feast")
        s["bankruptcies"] = sum(1 for e in self.events if e["type"] == "bankrupt")
        ov = [e["year"] for e in self.events if e["type"] == "overtake"]
        s["overtake_year"] = ov[0] if ov else None
        cross = None
        for y, rg, pg in self.gold_series:
            if y >= 1 and rg <= pg:
                cross = y
                break
        s["gold_cross_year"] = cross
        n40 = max(1, int(0.4 * (self.end_year or 0)))
        s["rich_gold_pos_frac40"] = round(sum(1 for y, rg, pg in self.gold_series[:n40] if rg > 0) / float(n40), 3)
        s["techs_rich"] = len(self.civs[RICH]["techs"])
        s["techs_poor"] = len(self.civs[POOR]["techs"])
        s["inventions_rich"] = sum(1 for t in self.civs[RICH]["techs"].values() if t["how"] == "invention")
        s["inventions_poor"] = sum(1 for t in self.civs[POOR]["techs"].values() if t["how"] == "invention")
        s["thefts"] = sum(1 for t in self.civs[RICH]["techs"].values() if t["how"] == "theft")
        s["theft_attempts"] = self.theft["attempts"]
        s["theft_success"] = self.theft["success"]
        s["theft_caught"] = self.theft["caught"]
        sc = self.score_series
        flips = 0
        prev = None
        for y, r, p in sc:
            if self.dip["contact"] is None or y < self.dip["contact"]:
                continue
            d = p - r
            if d == 0:
                continue
            sgn = 1 if d > 0 else -1
            if prev is not None and sgn != prev:
                flips += 1
            prev = sgn
        s["lead_changes"] = flips
        s["rich_ahead"] = any(r > p for y, r, p in sc if self.dip["contact"] is not None and y >= self.dip["contact"])
        s["final_rich_cities"] = len(self.alive_cities(RICH))
        s["final_poor_cities"] = len(self.alive_cities(POOR))
        s["final_rich_pop"] = ppl(self.pop_of(RICH))
        s["final_poor_pop"] = ppl(self.pop_of(POOR))
        s["truces"] = sum(1 for e in self.events if e["type"] == "truce")
        # tech gap (poor techs minus rich techs) at 25, 50, 75 percent of the game
        for frac in (25, 50, 75):
            target = int(frac / 100.0 * (self.end_year or 0))
            near = min(self.tech_series, key=lambda t: abs(t[0] - target)) if self.tech_series else None
            s["tech_gap_%d" % frac] = (near[1] - near[2]) if near else None
        # scary rich peak: first year the rich lead in territory or hold 1.2x the poor's soldiers
        peak = None
        best = -1.0
        for y, rt, pt, rs, ps in self.civ_series:
            lead = rt > pt or rs > 1.2 * ps
            if lead and rs / float(max(1, ps)) > best:
                best = rs / float(max(1, ps))
                peak = (y, rt, pt, rs, ps)
        s["rich_peak"] = peak
        s["rich_military_lead"] = peak is not None
        s["ambush_tactics"] = sum(1 for b in self.battles if b["type"] == "ambush" and
                                  any(d in ("tactics", "surprise") for d in b["decisive"]))
        s["statues_palaces"] = s["statues"] + s["palaces"]
        return s


def run_one(seed, record=False):
    sim = Sim(seed, record=record)
    sim.init_world_marker = True
    sim.run(MAX_YEARS)
    return sim


def worker(seed):
    sim = run_one(seed, record=False)
    return sim.summary()


# ============================================================================
# BATCH, SEARCH, EXPORT
# ============================================================================
BATCH_RUNS = 200
BATCH_RUNS_QUICK = 8
SEARCH_SEEDS = 240
SEARCH_SEEDS_QUICK = 12
POOLS = 4


def write_csv(path, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def cmd_batch(quick):
    n = BATCH_RUNS_QUICK if quick else BATCH_RUNS
    seeds = list(range(1, n + 1))
    t0 = time.time()
    with Pool(POOLS) as pool:
        rows = pool.map(worker, seeds)
    dt = time.time() - t0
    write_csv(os.path.join(BATCH_DIR, "runs.csv" if not quick else "runs_quick.csv"), rows)
    lines = []
    n_runs = len(rows)
    wins = defaultdict(int)
    for r in rows:
        wins[r["winner"]] += 1
    def mean(key):
        vals = [r[key] for r in rows if r[key] is not None]
        return sum(vals) / len(vals) if vals else float("nan")
    lines.append("runs: %d   wall time: %.1f s" % (n_runs, dt))
    lines.append("winners: poor %d (%.0f%%), rich %d (%.0f%%)" % (
        wins["poor"], 100.0 * wins["poor"] / n_runs, wins["rich"], 100.0 * wins["rich"] / n_runs))
    lines.append("end reasons: " + ", ".join("%s %d" % (k, sum(1 for r in rows if r["end_reason"] == k))
                                             for k in sorted(set(r["end_reason"] for r in rows))))
    fw = [r["first_war"] for r in rows if r["first_war"] is not None]
    lines.append("war-start year: mean %.0f, median %s; runs with a war: %d" % (
        sum(fw) / len(fw) if fw else float("nan"), sorted(fw)[len(fw) // 2] if fw else "-", len(fw)))
    lines.append("mean end year %.0f; wars per run %.1f; war years %.0f" % (
        mean("end_year"), mean("war_count"), mean("war_years")))
    lines.append("contact year mean %.0f" % mean("contact"))
    lines.append("captures per run %.1f (to poor %.1f, to rich %.1f); bribes %.2f; capital falls %.2f" % (
        mean("captures"), mean("captures_to_poor"), mean("captures_to_rich"), mean("bribes"), mean("capital_falls")))
    lines.append("battles per run %.1f (field %.1f, ambush %.2f, siege %.1f); decisive %.1f" % (
        mean("battles"), mean("field_battles"), mean("ambushes"), mean("sieges"), mean("decisive_battles")))
    lines.append("techs per run: rich %.1f, poor %.1f" % (mean("techs_rich"), mean("techs_poor")))
    lines.append("inventions per run: rich %.1f, poor %.1f" % (mean("inventions_rich"), mean("inventions_poor")))
    lines.append("theft per run: attempts %.2f, success %.2f, caught %.2f, stolen techs held %.2f" % (
        mean("theft_attempts"), mean("theft_success"), mean("theft_caught"), mean("thefts")))
    lines.append("lead changes per run %.1f; rich ahead at some point: %d/%d runs" % (
        mean("lead_changes"), sum(1 for r in rows if r["rich_ahead"]), n_runs))
    lines.append("truces per run %.1f" % mean("truces"))
    n_tl = sum(1 for r in rows if r["end_reason"] == "time limit")
    lines.append("rich win rate %.1f%%; time-limit runs %.1f%% (%d of %d)" % (
        100.0 * wins["rich"] / n_runs, 100.0 * n_tl / n_runs, n_tl, n_runs))
    lines.append("mean end year %.0f (range %d-%d)" % (mean("end_year"), min(r["end_year"] for r in rows), max(r["end_year"] for r in rows)))
    lines.append("tech gap, poor minus rich, at 25%%/50%%/75%% of the game: %.1f / %.1f / %.1f" % (
        mean("tech_gap_25"), mean("tech_gap_50"), mean("tech_gap_75")))
    lines.append("statues+palaces per run %.1f; feasts per run %.1f; ambush-by-tactics per run %.2f" % (
        mean("statues_palaces"), mean("feasts"), mean("ambush_tactics")))
    text = "\n".join(lines)
    with open(os.path.join(BATCH_DIR, "summary.txt" if not quick else "summary_quick.txt"), "w") as f:
        f.write(text + "\n")
    print(text)
    return rows


def story_score(s):
    """Hard rules (review v4), then a score that rewards visible drama."""
    end = s["end_year"] or 0
    if s["winner"] != "poor":
        return -1.0
    if not (250 <= end <= 600):
        return -1.0
    if s["field_battles"] < 8:
        return -1.0
    if s["sieges"] < 8:
        return -1.0
    if s["first_war"] is None or not (50 <= s["first_war"] <= 120):
        return -1.0
    if s["capital_falls"] < 1:
        return -1.0
    if s["statues_palaces"] < 4:
        return -1.0
    if s["ambush_tactics"] < 1:
        return -1.0
    if s["theft_success"] < 1:
        return -1.0
    if not s["rich_military_lead"]:
        return -1.0
    if s["hires"] < 1:
        return -1.0
    if s["gold_cross_year"] is None or s["gold_cross_year"] < 0.4 * end:
        return -1.0
    sc = 0.0
    sc += min(s["lead_changes"], 6) * 2.0
    both = min(s["captures_to_poor"], s["captures_to_rich"])
    sc += min(both, 4) * 3.0 + (4.0 if both >= 1 else 0.0)
    sc += 4.0 if s["rich_ahead"] else 0.0
    sc += 6.0 if s["decisive_battles"] > 0 else 0.0
    sc += 2.0 if s["overtake_year"] is not None else 0.0
    sc += min(s["field_battles"] + s["ambushes"], 25) * 0.2
    sc += 3.0 if 4 <= s["statues_palaces"] <= 10 else 0.0
    return sc


def cmd_search(quick):
    n = SEARCH_SEEDS_QUICK if quick else SEARCH_SEEDS
    seeds = list(range(1, n + 1))
    with Pool(POOLS) as pool:
        rows = pool.map(worker, seeds)
    out = []
    for r in rows:
        r = dict(r)
        r["story_score"] = round(story_score(r), 2)
        out.append(r)
    out.sort(key=lambda r: (-r["story_score"], r["seed"]))
    write_csv(os.path.join(STORY_DIR, "search.csv"), out)
    best = out[0]
    print("best seed %d score %.2f winner %s end %s" % (best["seed"], best["story_score"], best["winner"], best["end_year"]))
    return best["seed"], out


def periods_for(sim):
    """Named eras, 6 to 12 contiguous segments: founding, trade, the four longest wars, the gaps between
    them (truces and raids), and the fall after the first capital falls."""
    contact = sim.dip["contact"]
    last = sim.end_year
    if contact is None:
        contact = last
    segs = [[0, contact - 1, "عصر التأسيس", "Founding"]]
    fw = sim.wars[0][0] if sim.wars else None
    if fw is not None and fw > contact:
        segs.append([contact, fw - 1, "عصر الذهب", "Age of trade"])
    wars = [(w[0], w[1] or last, k) for k, w in enumerate(sim.wars)]

    def weight(w):
        return sum(1 for c in sim.captures if w[0] <= c[0] <= w[1]) + sum(1 for b in sim.battles if w[0] <= b["year"] <= w[1]) * 0.1
    major = []
    if wars:
        major = [wars[0]] + sorted(sorted(wars[1:], key=lambda w: -weight(w))[:3], key=lambda w: w[0])
    falls = [e["year"] for e in sim.events if e["type"] == "capital_fall"]
    biggest = max([weight(w) for w in major], default=0)
    cur = segs[-1][1]
    for n, w in enumerate(major):
        if w[0] > cur + 1:
            segs.append([cur + 1, w[0] - 1, "الهدنة والمناوشات", "Truces and raids"])
        if n == 0:
            nm = ("الحرب الأولى", "First war")
        elif weight(w) == biggest:
            nm = ("الحرب الكبرى", "Great war")
        else:
            nm = ("حرب %d" % (n + 1), "War %d" % (n + 1))
        segs.append([w[0], w[1], nm[0], nm[1]])
        cur = w[1]
    if cur < last:
        segs.append([cur + 1, last, "الهدنة والمناوشات", "Truces and raids"])
    if falls:
        segs = [x for x in segs if x[0] < falls[0]]
        segs.append([falls[0], last, "السقوط", "The fall"])
    segs.sort(key=lambda x: x[0])
    out = []
    t = 0
    for x in segs:
        x = [max(x[0], t), x[1], x[2], x[3]]
        if x[1] < x[0]:
            continue
        out.append(x)
        t = x[1] + 1
    if out:
        out[-1][1] = last
    return out


def cmd_export(seed):
    t0 = time.time()
    sim = run_one(seed, record=True)
    dt = time.time() - t0
    os.makedirs(STORY_DIR, exist_ok=True)
    os.makedirs(MAPS_DIR, exist_ok=True)
    summ = sim.summary()
    g = sim.g
    terrain = {
        "W": W, "H": H, "legend": {"d": "desert", "s": "silt (fertile flood land)", "o": "oasis",
                                  "p": "plateau", "m": "mountain", "r": "river", "~": "sea"},
        "rows": ["".join(TERR_CHAR[t] for t in sim.terr[y * W:(y + 1) * W]) for y in range(H)],
        "resources": [[j % W, j // W, v[0], bool(v[1])] for j, v in sorted(sim.res.items())],
        "river_centre": sim.cen, "rich_capital": list(g["rich_cap"]), "poor_capital": list(g["poor_cap"]),
        "mirror_disc_radius": 13,
    }
    with open(os.path.join(STORY_DIR, "terrain.json"), "w") as f:
        json.dump(terrain, f, separators=(",", ":"))
    cvs = {"rich": CIV_NAMES[RICH], "poor": CIV_NAMES[POOR]}
    state = {
        "format": "state.json v2 (see FORMAT.md)",
        "seed": seed, "W": W, "H": H, "max_years": MAX_YEARS, "snap_every": SNAP_EVERY,
        "civ_names": {"rich": CIV_NAMES[RICH], "poor": CIV_NAMES[POOR]},
        "summary": summ, "wars": sim.wars, "captures": sim.captures,
        "periods": periods_for(sim),
        "years": sim.records,
        "techs": {CIV_KEY[k]: {key: dict(v) for key, v in sim.civs[k]["techs"].items()} for k in CIVS},
        "ladder": [[t[0], t[1], t[2], t[3], t[4]] for t in LADDER],
        "events_index": len(sim.events),
    }
    # v5: display and export fixes (export_v5.py). Records only; the simulation is already finished.
    import export_v5
    export_v5.apply(state, terrain, STORY_DIR, seed)
    sp = os.path.join(STORY_DIR, "state.json")
    with open(sp, "w") as f:
        json.dump(state, f, ensure_ascii=False, separators=(",", ":"))
    # plain-text log: one line per logged event
    with open(os.path.join(STORY_DIR, "log.txt"), "w") as f:
        for e in sim.events:
            if e["log"]:
                f.write("%03d %s [%s] %s\n" % (e["year"], e["id"], e["type"], e["text_en"]))
    with open(os.path.join(STORY_DIR, "periods.json"), "w") as f:
        json.dump({"periods": state["periods"]}, f, ensure_ascii=False, indent=1)
    write_key_moments(sim)
    print("export seed %d: run+export %.1f s, state.json %.1f MB, years %d, winner %s (%s)" % (
        seed, dt, os.path.getsize(sp) / 1e6, len(sim.records), summ["winner"], summ["end_reason"]))
    return sim


WEIGHT = {"militia": 1, "endowment": 1, "hire": 5, "waste": 4, "siege_start": 6, "siege_end": 5, "overtake": 8, "invention": 9, "capital_fall": 10, "war_start": 8, "capture": 7, "theft": 7,
          "breach": 6, "spy_caught": 4, "bribe": 6, "contact": 5, "truce": 4,
          "end": 10, "battle": 5, "leader_death": 2, "drought": 2, "plague": 2,
          "flood": 2, "bankrupt": 3, "growth": 1, "incident": 2, "insult": 1,
          "first_build": 2, "found": 1, "dispute": 2, "muster": 1, "locust": 2,
          "adopt": 0}


def write_key_moments(sim):
    bat_by_id = {b["id"]: b for b in sim.battles}
    cand = []
    for e in sim.events:
        if not e["log"]:
            continue
        t = e["type"]
        w = WEIGHT.get(t, 0)
        if t == "battle":
            b = bat_by_id.get(e.get("battle"))
            w = 5
            if b is not None:
                if any(d.startswith("tech:") for d in b["decisive"]):
                    w += 4
                elif any(d != "numbers" for d in b["decisive"]):
                    w += 2
                w += min(3, (b["att_loss"] + b["def_loss"]) // 150)
        if t == "invention":
            w += 1
        if w <= 0:
            continue
        cand.append((w, e))
    cand.sort(key=lambda t: (-t[0], t[1]["year"], t[1]["id"]))
    per_type = defaultdict(int)
    chosen = []
    years = set()
    for w, e in cand:
        if len(chosen) >= 36:
            break
        if per_type[e["type"]] >= KM_TYPE_CAP:
            continue
        if e["year"] in years and len(chosen) >= 25:
            continue
        chosen.append(e)
        years.add(e["year"])
        per_type[e["type"]] += 1
    chosen.sort(key=lambda e: (e["year"], e["id"]))
    lines = ["# Key moments: story (seed %d)" % sim.seed, "",
             "Auto-selected by event weight with a cap of %d per event type (review v3: no type dominates). "
             "The why-it-matters lines are generated from the event fields." % KM_TYPE_CAP, ""]
    for n, e in enumerate(chosen, 1):
        tag = {"invention": " **[INVENTION]**", "theft": " **[THEFT]**", "waste": " **[WASTE]**",
               "hire": " **[HIRE]**", "overtake": " **[OVERTAKE]**"}.get(e["type"], "")
        city = sim.cities[e["city"]]["name_en"] if e.get("city") is not None and e["city"] in sim.cities else "the field"
        lines.append("%d. **Year %d** — (%d, %d), %s%s" % (n, e["year"], e["x"], e["y"], city, tag))
        lines.append("   - What happens: %s" % e["text_en"])
        lines.append("   - Why it matters: %s" % why_text(sim, e))
        lines.append("")
    with open(os.path.join(STORY_DIR, "key_moments.md"), "w") as f:
        f.write("\n".join(lines) + "\n")



def why_text(sim, e):
    t = e["type"]
    if t == "invention":
        return "Effect: %s. Unlocks buildings and changes the balance from this year on." % e.get("effect", "")
    if t == "theft":
        return "Stolen, not researched: the rich gain %s after the contact year; it becomes usable %d-%d years later." % (
            TECH_INFO[e["tech"]][1], ADOPT_MIN, ADOPT_MAX)
    if t == "capital_fall":
        return "The seat of government is lost; a new capital is due after %d years." % CAPITAL_REBUILD
    if t == "war_start":
        return "Tension had built past %.1f; the war starts and armies march along roads and terrain." % WAR_TENSION
    if t == "capture":
        return "The city changes hands; its buildings change owner and some are destroyed."
    if t == "battle":
        return "Deciding factor: %s." % e.get("factor", "numbers")
    if t == "siege_start":
        return "Armies sit at the walls; the siege record shows rounds and losses until it ends."
    if t == "siege_end":
        return "The siege closes: %s." % e.get("outcome", "")
    if t == "hire":
        return "Gold buys soldiers: %d mercenaries, paid in advance." % e.get("count", 0)
    if t == "waste":
        return "A visible luxury: %s." % e["text_en"]
    if t == "overtake":
        return "Wealth flips: the poor's income is now higher than the rich's."
    if t == "truce":
        return "A pause in fighting; armies go home."
    if t == "contact":
        return "From here on trade, espionage and border incidents are possible."
    if t == "end":
        return "The loser has no cities left, or its capital is gone with fewer than 2 cities and under 10% of the winner's population."
    return e["text_en"]



# ============================================================================
# SVG MAPS
# ============================================================================
TERR_COL = {DESERT: "#e8d7a3", SILT: "#c7b26a", OASIS: "#6fae5e", PLATEAU: "#c9a97f",
            MOUNTAIN: "#8c8478", RIVER: "#3a7bd5", SEA: "#1f4e8c"}


def owner_at_year(sim_states, y):
    return None


def export_maps(seed, sim):
    """Eight SVG snapshots at key years."""
    recs = sim.records
    years_index = {r["year"]: r for r in recs}
    contact = sim.dip["contact"] or 0
    keys = [0, contact]
    if sim.wars:
        keys.append(sim.wars[0][0])
        keys.append((sim.wars[0][0] + (sim.wars[0][1] or sim.end_year)) // 2)
    caps = [c[0] for c in sim.captures]
    if caps:
        keys.append(caps[0])
        keys.append(caps[len(caps) // 2])
    falls = [e["year"] for e in sim.events if e["type"] == "capital_fall"]
    if falls:
        keys.append(falls[0])
    keys.append(sim.end_year)
    uniq = []
    for k in keys:
        k = min(max(0, k), sim.end_year)
        if k not in uniq:
            uniq.append(k)
    chosen = sorted(uniq)[:8]
    while len(chosen) < 8:
        extra = [y for y in range(0, sim.end_year + 1, 50) if y not in chosen]
        if not extra:
            break
        chosen.append(extra[0])
    chosen = sorted(chosen)
    # reconstruct per-year state for the chosen years
    owner = [-1] * (W * H)
    bld = {}
    roads = {}
    out = []
    ci = 0
    for r in recs:
        if r["owner_full"] is not None:
            owner = [{"R": 0, "P": 1, ".": -1}[ch] for ch in r["owner_full"]]
        for j, v in r["owner_chg"]:
            owner[j] = v
        if r["bld_full"] is not None:
            bld = {b["id"]: b for b in r["bld_full"]}
        for b in r["bld"]:
            bld[b["id"]] = b
        if r["roads_full"] is not None:
            roads = {rd["id"]: rd for rd in r["roads_full"]}
        for rd in r["roads"]:
            roads[rd["id"]] = rd
        if r["year"] in chosen:
            out.append((r["year"], r, list(owner), dict(bld), dict(roads)))
    for y, r, owner_s, bld_s, roads_s in out:
        svg = render_svg(sim, y, r, owner_s, bld_s, roads_s)
        with open(os.path.join(MAPS_DIR, "map_%04d.svg" % y), "w") as f:
            f.write(svg)
    return [o[0] for o in out]


def render_svg(sim, y, r, owner, bld, roads):
    cell = 6
    width = W * cell
    height = H * cell + 70
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (
        width, height, width, height)]
    parts.append('<rect width="100%%" height="100%%" fill="#f6f1e4"/>')
    # terrain runs
    for yy in range(H):
        xx = 0
        row = sim.terr[yy * W:(yy + 1) * W]
        while xx < W:
            t = row[xx]
            x2 = xx
            while x2 + 1 < W and row[x2 + 1] == t:
                x2 += 1
            parts.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>' % (
                xx * cell, yy * cell, (x2 - xx + 1) * cell, cell, TERR_COL[t]))
            xx = x2 + 1
    # owner tint
    tint = {0: "#d4a017", 1: "#2e8b57"}
    for yy in range(H):
        for xx in range(W):
            o = owner[yy * W + xx]
            if o >= 0:
                parts.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" fill-opacity="0.22"/>' % (
                    xx * cell, yy * cell, cell, cell, tint[o]))
    # roads
    for rd in roads.values():
        pts = " ".join("%.1f,%.1f" % (p[0] * cell + cell / 2, p[1] * cell + cell / 2) for p in rd["pts"])
        col = "#7a5a2a" if rd["civ"] == "rich" else "#1d5e3a"
        parts.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.6" stroke-opacity="0.85"/>' % (pts, col))
    # buildings
    bcol = {"house": "#8b6f47", "farm": "#7cc35a", "well": "#2d6cb5", "granary": "#c79a3a",
            "market": "#c0392b", "workshop": "#555", "library": "#7d3c98", "observatory": "#5b2c6f",
            "mine": "#f1c40f", "palace": "#ffffff", "statue": "#ffd700", "bazaar": "#e67e22",
            "caravanserai": "#e67e22", "harbour": "#117a65", "canal": "#5dade2", "wall": "#222",
            "tower": "#111", "barracks": "#444", "siege_workshop": "#6e2c00", "waterwheel": "#1a5276",
            "windmill": "#999"}
    for b in bld.values():
        if b["destroyed"] is not None:
            continue
        rad = 2.2 if b["type"] in ("house", "farm") else 2.8
        parts.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="#000" stroke-width="0.2"/>' % (
            b["x"] * cell + cell / 2, b["y"] * cell + cell / 2, rad, bcol.get(b["type"], "#000")))
    # cities
    for c in r["cities"]:
        col = "#8a6d00" if c["civ"] == "rich" else "#0f5132"
        parts.append('<rect x="%.1f" y="%.1f" width="7" height="7" fill="%s" stroke="#000"/>' % (
            c["x"] * cell - 0.5, c["y"] * cell - 0.5, col))
        parts.append('<text x="%.1f" y="%.1f" font-size="7" font-family="sans-serif" fill="#000">%s</text>' % (
            c["x"] * cell + 6, c["y"] * cell - 2, c["name_en"]))
    # armies with waypoints
    for A in r["armies"]:
        if A["end"] is not None and A["end"] != y and A["mode"] == "gone":
            continue
        col = "#b8860b" if A["owner"] == "rich" else "#0b6b3a"
        if len(A["wp"]) > 1:
            pts = " ".join("%.1f,%.1f" % (p[0] * cell + cell / 2, p[1] * cell + cell / 2) for p in A["wp"])
            parts.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.2" stroke-dasharray="3,2"/>' % (pts, col))
        parts.append('<circle cx="%.1f" cy="%.1f" r="4.2" fill="%s" stroke="#000" stroke-width="0.6"/>' % (
            A["x"] * cell + cell / 2, A["y"] * cell + cell / 2, col))
        parts.append('<text x="%.1f" y="%.1f" font-size="6" font-family="sans-serif" fill="#fff">%d</text>' % (
            A["x"] * cell + cell / 2 - 3, A["y"] * cell + cell / 2 + 2, A["size"]))
    # battles
    for bt in r.get("battles_full", []):
        x, yy = bt["x"], bt["y"]
        parts.append('<text x="%.1f" y="%.1f" font-size="10" font-family="sans-serif" fill="#c00" font-weight="bold">X</text>' % (
            x * cell - 3, yy * cell + 4))
    # legend
    per = None
    for p in (sim_periods_cache.get(sim.seed) or []):
        if p[0] <= y <= p[1]:
            per = p
    label = "Year %d" % y + ((" — " + per[3] + " / " + per[2]) if per else "")
    parts.append('<text x="8" y="%d" font-size="13" font-family="sans-serif" font-weight="bold">%s</text>' % (
        H * cell + 20, label))
    st = r["stats"]
    line2 = "Rich: pop %d, cities %d, techs %d   |   Poor: pop %d, cities %d, techs %d   |   status: %s" % (
        st["rich"]["pop"], st["rich"]["cities"], st["rich"]["techs"],
        st["poor"]["pop"], st["poor"]["cities"], st["poor"]["techs"], r["dip"]["status"])
    parts.append('<text x="8" y="%d" font-size="11" font-family="sans-serif">%s</text>' % (H * cell + 40, line2))
    parts.append('<text x="8" y="%d" font-size="10" font-family="sans-serif" fill="#444">'
                 'gold/green = Rich (Sultan) and Poor (Ra\'is) tint; squares = cities; dashed = army route; numbers = soldiers; X = battle</text>' % (H * cell + 60))
    parts.append("</svg>")
    return "\n".join(parts)


sim_periods_cache = {}


# ============================================================================
# CLI
# ============================================================================


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "batch", "search", "export", "all"])
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        sim = run_one(a.seed or 1, record=False)
        s = sim.summary()
        for k, v in s.items():
            print("%s: %s" % (k, v))
        return 0
    if a.cmd == "batch":
        cmd_batch(a.quick)
        return 0
    if a.cmd == "search":
        cmd_search(a.quick)
        return 0
    if a.cmd == "export":
        if a.seed is None:
            ap.error("export needs --seed")
        sim = cmd_export(a.seed)
        sim_periods_cache[sim.seed] = periods_for(sim)
        export_maps(a.seed, sim)
        return 0
    if a.cmd == "all":
        cmd_batch(a.quick)
        seed, _ = cmd_search(a.quick)
        sim = cmd_export(seed)
        sim_periods_cache[sim.seed] = periods_for(sim)
        export_maps(seed, sim)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
