#!/usr/bin/env python3
"""Parameter sweep runner for sim3_worldbox (does not modify sim.py).

  nice -n 10 /usr/bin/python3 sweep/run_sweep.py run  [--settings a,b] [--seeds 1-60]
  nice -n 10 /usr/bin/python3 sweep/run_sweep.py summarize

Each run imports sim as a module, restores every overridden constant to its original value,
applies the setting's overrides, and runs Sim headless (record=False). Overrides are applied
inside each worker process, so they work under the macOS 'spawn' start method.
"""
import argparse
import csv
import math
import os
import statistics
import sys
from multiprocessing import Pool

SWEEP_DIR = os.path.dirname(os.path.abspath(__file__))
SIM_DIR = os.path.dirname(SWEEP_DIR)
RUNS_CSV = os.path.join(SWEEP_DIR, "sweep_runs.csv")
SUMMARY_MD = os.path.join(SWEEP_DIR, "sweep_summary.md")

GOLD_BASE = 30000.0
SETTINGS = [
    ("default", {}),
    ("gold_x0.5", {"START_GOLD": {0: GOLD_BASE * 0.5, 1: 2000.0}}),
    ("gold_x2", {"START_GOLD": {0: GOLD_BASE * 2, 1: 2000.0}}),
    ("gold_x4", {"START_GOLD": {0: GOLD_BASE * 4, 1: 2000.0}}),
    ("gold_x8", {"START_GOLD": {0: GOLD_BASE * 8, 1: 2000.0}}),
    ("gold_x16", {"START_GOLD": {0: GOLD_BASE * 16, 1: 2000.0}}),
    ("merc_max_100", {"MERC_MAX": 100}),
    ("merc_max_1600", {"MERC_MAX": 1600}),
    ("merc_max_unlim", {"MERC_MAX": 100000}),
    ("share_0.6", {"MERC_GOLD_SHARE": 0.6}),
    ("unlim_share_0.6", {"MERC_MAX": 100000, "MERC_GOLD_SHARE": 0.6}),
    # phase 2 (only if unlimited mercs do not help)
    ("unlim_army_max_5000", {"MERC_MAX": 100000, "ARMY_MAX": 5000}),
    ("unlim_cap_base_6", {"MERC_MAX": 100000, "ARMY_CAP_BASE": 6}),
    ("unlim_army5000_cap6", {"MERC_MAX": 100000, "ARMY_MAX": 5000, "ARMY_CAP_BASE": 6}),
    ("recruit_0.25", {"RECRUIT_P": 0.25}),
    ("unlim_recruit_0.25", {"MERC_MAX": 100000, "RECRUIT_P": 0.25}),
    ("unlim_share0.6_recruit_0.25_cap6", {"MERC_MAX": 100000, "MERC_GOLD_SHARE": 0.6, "RECRUIT_P": 0.25, "ARMY_CAP_BASE": 6}),
]
SETTING_NAMES = [n for n, _ in SETTINGS]
SETTING_MAP = dict(SETTINGS)
OVERRIDABLE = ["START_GOLD", "MERC_MAX", "MERC_GOLD_SHARE", "ARMY_MAX", "ARMY_CAP_BASE", "RECRUIT_P"]

FIELDS = ["seed", "setting", "winner", "end_type", "end_year", "rich_gold_end", "poor_gold_end",
          "rich_hires", "rich_hired_men", "max_rich_army", "max_rich_total_soldiers",
          "years_rich_more_cities", "rich_cities_end", "poor_cities_end"]

_sim = None
_orig = None


def _load_sim():
    global _sim, _orig
    if _sim is None:
        sys.path.insert(0, SIM_DIR)
        import sim
        _sim = sim
        _orig = {k: getattr(sim, k) for k in OVERRIDABLE}
    return _sim


def _make_tracked_class(sim):
    class Tracked(sim.Sim):
        """Same engine; records per-year stats through the public step/recruit hooks."""
        def __init__(self, seed, record=False):
            super().__init__(seed, record=record)
            self.max_army = 0
            self.max_total = 0
            self.years_more = 0

        def recruit_step(self):
            super().recruit_step()
            # armies only grow at creation (no reinforcement code), so sampling after recruit catches peaks
            mine = [A for A in self.armies.values() if A["owner"] == sim.RICH]
            if mine:
                self.max_army = max(self.max_army, max(A["size"] for A in mine))
                self.max_total = max(self.max_total, sum(A["size"] for A in mine))

        def step(self):
            super().step()
            if len(self.alive_cities(sim.RICH)) > len(self.alive_cities(sim.POOR)):
                self.years_more += 1
    return Tracked


def run_one(task):
    setting, seed = task
    sim = _load_sim()
    for k, v in _orig.items():
        setattr(sim, k, v)
    for k, v in SETTING_MAP[setting].items():
        setattr(sim, k, v)
    Tracked = _make_tracked_class(sim)
    s = Tracked(seed, record=False)
    s.run(sim.MAX_YEARS)
    et = s.end_reason
    end_type = "score" if et == "time limit" else et
    hires = sum(1 for e in s.events if e["type"] == "hire")
    hired_men = sum(e.get("count", 0) for e in s.events if e["type"] == "hire")
    return {
        "seed": seed, "setting": setting, "winner": sim.CIV_KEY[s.winner], "end_type": end_type,
        "end_year": s.end_year, "rich_gold_end": round(s.civs[sim.RICH]["gold"], 1),
        "poor_gold_end": round(s.civs[sim.POOR]["gold"], 1),
        "rich_hires": hires, "rich_hired_men": hired_men,
        "max_rich_army": s.max_army, "max_rich_total_soldiers": s.max_total,
        "years_rich_more_cities": s.years_more,
        "rich_cities_end": len(s.alive_cities(sim.RICH)), "poor_cities_end": len(s.alive_cities(sim.POOR)),
    }


def cmd_run(args):
    names = args.settings.split(",") if args.settings else SETTING_NAMES
    a, b = (int(x) for x in args.seeds.split("-"))
    seeds = list(range(a, b + 1))
    tasks = [(n, s) for n in names for s in seeds]
    rows = []
    with Pool(4) as pool:
        for i, r in enumerate(pool.imap(run_one, tasks, chunksize=1), 1):
            rows.append(r)
            if i % 30 == 0 or i == len(tasks):
                print("done %d/%d" % (i, len(tasks)), flush=True)
    # merge with existing rows for settings not rerun
    old = []
    if os.path.exists(RUNS_CSV):
        with open(RUNS_CSV) as f:
            old = [r for r in csv.DictReader(f) if r["setting"] not in set(names)]
    with open(RUNS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in old:
            w.writerow(r)
        for r in rows:
            w.writerow(r)
    print("wrote", RUNS_CSV)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


def load_rows():
    with open(RUNS_CSV) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("seed", "end_year", "max_rich_army", "max_rich_total_soldiers", "rich_hires",
                  "rich_hired_men", "years_rich_more_cities", "rich_cities_end", "poor_cities_end"):
            r[k] = int(r[k]) if r[k] not in ("", "None") else None
        for k in ("rich_gold_end", "poor_gold_end"):
            r[k] = float(r[k])
    return rows


def summarize_setting(rs):
    n = len(rs)
    wins = sum(1 for r in rs if r["winner"] == "rich")
    lo, hi = wilson(wins, n)
    ends = {k: sum(1 for r in rs if r["end_type"] == k) for k in ("collapse", "conquest", "score")}
    med_year = statistics.median(r["end_year"] for r in rs)
    med_gold = statistics.median(r["rich_gold_end"] for r in rs)
    med_hires = statistics.median(r["rich_hires"] for r in rs)
    med_army = statistics.median(r["max_rich_army"] for r in rs)
    med_total = statistics.median(r["max_rich_total_soldiers"] for r in rs)
    med_more = statistics.median(r["years_rich_more_cities"] for r in rs)
    mean_hires = sum(r["rich_hires"] for r in rs) / n
    rich_win_end = [r for r in rs if r["winner"] == "rich"]
    return {"n": n, "wins": wins, "pct": 100.0 * wins / n, "lo": lo, "hi": hi, "ends": ends,
            "med_year": med_year, "med_gold": med_gold, "med_hires": med_hires, "mean_hires": mean_hires,
            "med_army": med_army, "med_total": med_total, "med_more": med_more,
            "rich_win_end_types": {k: sum(1 for r in rich_win_end if r["end_type"] == k) for k in ("collapse", "conquest", "score")}}


def cmd_summarize(args):
    rows = load_rows()
    names = [n for n in SETTING_NAMES if any(r["setting"] == n for r in rows)]
    stats = {}
    for n in names:
        stats[n] = summarize_setting([r for r in rows if r["setting"] == n])
    out = []
    out.append("# Rich gold and mercenary sweep (sim3_worldbox)\n")
    out.append("Seeds 1-60 for every setting (paired by seed). Engine: sim.py, unmodified; constants overridden in sweep/run_sweep.py.")
    out.append("Win % = share of runs won by the rich, with a 95% Wilson interval. End types: collapse / conquest / score (engine label 'time limit', decided by score).")
    out.append("Unspent rich gold = rich treasury at the end of the run (median). 'Max army' = largest single rich army (sampled after recruitment, sizes never grow after creation); 'max total' = all rich soldiers alive at one time.\n")
    out.append("## Table\n")
    out.append("| setting | n | rich win % [95% CI] | collapse / conquest / score (all runs) | median end year | median rich gold at end | median rich hires | mean rich hires | median max single army | median max total rich soldiers | median years rich > poor cities |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for n in names:
        s = stats[n]
        out.append("| %s | %d | %.1f%% [%.1f, %.1f] (%d/%d) | %d / %d / %d | %.0f | %.0f | %.0f | %.2f | %.0f | %.0f | %.0f |" % (
            n, s["n"], s["pct"], s["lo"], s["hi"], s["wins"], s["n"], s["ends"]["collapse"], s["ends"]["conquest"],
            s["ends"]["score"], s["med_year"], s["med_gold"], s["med_hires"], s["mean_hires"], s["med_army"],
            s["med_total"], s["med_more"]))
    out.append("\n## Rich wins by end type\n")
    out.append("| setting | rich wins | by collapse | by conquest | by score |")
    out.append("|---|---|---|---|---|")
    for n in names:
        s = stats[n]
        e = s["rich_win_end_types"]
        out.append("| %s | %d | %d | %d | %d |" % (n, s["wins"], e["collapse"], e["conquest"], e["score"]))
    text = "\n".join(out) + "\n"
    with open(SUMMARY_MD, "w") as f:
        f.write(text)
    print(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "summarize"])
    ap.add_argument("--settings", default="")
    ap.add_argument("--seeds", default="1-60")
    args = ap.parse_args()
    if args.cmd == "run":
        cmd_run(args)
    else:
        cmd_summarize(args)


if __name__ == "__main__":
    main()
