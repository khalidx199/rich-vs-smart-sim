# Rich gold and mercenary sweep (sim3_worldbox)

Seeds 1-60 for every setting (paired by seed). Engine: sim.py, unmodified; constants overridden in sweep/run_sweep.py.
Win % = share of runs won by the rich, with a 95% Wilson interval. End types: collapse / conquest / score (engine label 'time limit', decided by score).
Unspent rich gold = rich treasury at the end of the run (median). 'Max army' = largest single rich army (sampled after recruitment, sizes never grow after creation); 'max total' = all rich soldiers alive at one time.

## Table

| setting | n | rich win % [95% CI] | collapse / conquest / score (all runs) | median end year | median rich gold at end | median rich hires | mean rich hires | median max single army | median max total rich soldiers | median years rich > poor cities |
|---|---|---|---|---|---|---|---|---|---|---|
| default | 60 | 25.0% [15.8, 37.2] (15/60) | 25 / 18 / 17 | 780 | 25640 | 10 | 11.07 | 480 | 960 | 30 |
| gold_x0.5 | 60 | 25.0% [15.8, 37.2] (15/60) | 25 / 20 / 15 | 780 | 28300 | 10 | 11.57 | 480 | 1025 | 34 |
| gold_x2 | 60 | 33.3% [22.7, 45.9] (20/60) | 22 / 21 / 17 | 828 | 33367 | 11 | 12.42 | 480 | 1024 | 64 |
| gold_x4 | 60 | 35.0% [24.2, 47.6] (21/60) | 21 / 20 / 19 | 827 | 37762 | 11 | 12.63 | 480 | 1027 | 60 |
| gold_x8 | 60 | 33.3% [22.7, 45.9] (20/60) | 22 / 20 / 18 | 814 | 39510 | 12 | 12.87 | 480 | 1041 | 65 |
| gold_x16 | 60 | 33.3% [22.7, 45.9] (20/60) | 23 / 20 / 17 | 856 | 49193 | 12 | 13.20 | 480 | 1060 | 65 |
| merc_max_100 | 60 | 6.7% [2.6, 15.9] (4/60) | 31 / 18 / 11 | 610 | 12739 | 8 | 8.60 | 179 | 420 | 3 |
| merc_max_1600 | 60 | 85.0% [73.9, 91.9] (51/60) | 19 / 26 / 15 | 649 | 63575 | 11 | 10.35 | 1680 | 3961 | 330 |
| merc_max_unlim | 60 | 80.0% [68.2, 88.2] (48/60) | 24 / 28 / 8 | 608 | 25316 | 11 | 10.05 | 4716 | 8490 | 289 |
| share_0.6 | 60 | 25.0% [15.8, 37.2] (15/60) | 28 / 17 / 15 | 756 | 23673 | 10 | 11.20 | 480 | 960 | 32 |
| unlim_share_0.6 | 60 | 61.7% [49.0, 72.9] (37/60) | 21 / 19 / 20 | 730 | 4385 | 9 | 8.00 | 14406 | 15793 | 217 |
| unlim_army_max_5000 | 60 | 80.0% [68.2, 88.2] (48/60) | 24 / 28 / 8 | 608 | 25316 | 11 | 10.05 | 4716 | 8490 | 289 |
| unlim_cap_base_6 | 60 | 83.3% [72.0, 90.7] (50/60) | 24 / 26 / 10 | 640 | 21929 | 12 | 10.92 | 4930 | 8224 | 336 |
| unlim_army5000_cap6 | 60 | 83.3% [72.0, 90.7] (50/60) | 24 / 26 / 10 | 640 | 21929 | 12 | 10.92 | 4930 | 8224 | 336 |
| recruit_0.25 | 60 | 56.7% [44.1, 68.4] (34/60) | 11 / 43 / 6 | 454 | 37317 | 12 | 13.45 | 479 | 1554 | 122 |
| unlim_recruit_0.25 | 60 | 75.0% [62.8, 84.2] (45/60) | 14 / 37 / 9 | 386 | 12165 | 12 | 11.57 | 3246 | 5961 | 106 |
| unlim_share0.6_recruit_0.25_cap6 | 60 | 38.3% [27.1, 51.0] (23/60) | 14 / 31 / 15 | 362 | 1080 | 4 | 6.67 | 12082 | 12721 | 10 |

## Rich wins by end type

| setting | rich wins | by collapse | by conquest | by score |
|---|---|---|---|---|
| default | 15 | 2 | 6 | 7 |
| gold_x0.5 | 15 | 3 | 6 | 6 |
| gold_x2 | 20 | 4 | 8 | 8 |
| gold_x4 | 21 | 2 | 8 | 11 |
| gold_x8 | 20 | 2 | 8 | 10 |
| gold_x16 | 20 | 2 | 9 | 9 |
| merc_max_100 | 4 | 0 | 0 | 4 |
| merc_max_1600 | 51 | 15 | 26 | 10 |
| merc_max_unlim | 48 | 19 | 27 | 2 |
| share_0.6 | 15 | 2 | 6 | 7 |
| unlim_share_0.6 | 37 | 14 | 15 | 8 |
| unlim_army_max_5000 | 48 | 19 | 27 | 2 |
| unlim_cap_base_6 | 50 | 21 | 25 | 4 |
| unlim_army5000_cap6 | 50 | 21 | 25 | 4 |
| recruit_0.25 | 34 | 6 | 26 | 2 |
| unlim_recruit_0.25 | 45 | 10 | 33 | 2 |
| unlim_share0.6_recruit_0.25_cap6 | 23 | 6 | 16 | 1 |
