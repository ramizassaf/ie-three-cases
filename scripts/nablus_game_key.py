"""Case 1, Nablus sterilizer. Answer key for the investigation game.

Every value the game checks is printed here, from the raw files, with the same simple
definitions the game gives the player. Run it after any change to the data.
Usage: python3 scripts/nablus_game_key.py
"""
import csv, json, math, os
from bisect import bisect_right
from collections import Counter
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "01-case-nablus-sterilizer")
P = lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
read = lambda n: list(csv.DictReader(open(os.path.join(DATA, n), encoding="utf-8")))
START, END = datetime(2013, 9, 1), datetime(2015, 1, 1)
A = ("STER-01", "STER-02")
key = {}

wo = [w for w in read("work_orders.csv") if w["wo_type"] == "CM"]
for w in wo:
    for k in ("reported_at", "repair_start", "repair_end"): w[k] = P(w[k])
ctrl = read("controller_events.csv")
for c in ctrl: c["t"] = P(c["timestamp"])
gen = read("generator_switch_log.csv")
tt = sorted(P(g["timestamp"]) for g in gen if g["event"].startswith("ATS_TO"))
tests = [P(g["timestamp"]) for g in gen if g["event"].startswith("ATS_TO") and g["note"] == "weekly on-load test"]
water = read("water_tests.csv")
rec = read("voltage_recorder.csv")

# M1 water
bad = [x for x in water if float(x["conductivity_us_cm"]) > 5 or float(x["hardness_mmol_l"]) > 0.02]
key["m1_bad_samples"] = len(bad)
w0, w1 = datetime(2014, 5, 4), datetime(2014, 5, 25)
key["m1_cm_bad_weeks"] = sum(1 for w in wo if w["device_id"] in A and w0 <= w["reported_at"] < w1)
key["m1_rate_bad"] = round(key["m1_cm_bad_weeks"] / 3 / 2, 2)
key["m1_rate_all"] = round(sum(1 for w in wo if w["device_id"] in A) / ((END - START).days / 7) / 2, 2)

# M2 MTBF and MTTR
hours = (END - START).total_seconds() / 3600
key["m2_hours"] = round(hours)
for d in ("STER-01", "STER-02", "STER-03"):
    ws = [w for w in wo if w["device_id"] == d]
    key[f"m2_cm_{d}"] = len(ws)
    key[f"m2_mtbf_{d}"] = round(hours / len(ws), 1)
    key[f"m2_mttr_{d}"] = round(sum((w["repair_end"] - w["reported_at"]).total_seconds() / 3600 for w in ws) / len(ws), 2)

# M3 root alarm: last A01, A02, A11 or A21 on the same device in the 3 hours before the report
prim = [c for c in ctrl if c["code"] in ("A01", "A02", "A11", "A21")]
for w in wo:
    cand = [c for c in prim if c["device_id"] == w["device_id"] and w["reported_at"] - timedelta(hours=3) <= c["t"] <= w["reported_at"]]
    w["root"] = cand[-1] if cand else None
key["m3_wo114_root"] = next(w for w in wo if w["wo_id"] == "WO-00114")["root"]["code"]
key["m3_power_root_all"] = sum(1 for w in wo if w["root"] and w["root"]["code"] in ("A01", "A02"))
key["m3_cm_all"] = len(wo)
key["m3_written_power"] = sum(1 for w in wo if w["reported_fault"] == "Power problem")

# M4 weekday
days = ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]
wd = Counter(w["reported_at"].strftime("%a") for w in wo if w["device_id"] in A)
cy = Counter(c["t"].strftime("%a") for c in ctrl if c["device_id"] in A and c["code"] == "C10")
key["m4_by_day"] = {d: wd[d] for d in days}
key["m4_cycles_by_day"] = {d: cy[d] for d in days}
key["m4_top_day"] = max(days, key=lambda d: wd[d])
key["m4_tue_rate"] = round(1000 * wd["Tue"] / cy["Tue"], 1)
key["m4_max_other_rate"] = round(max(1000 * wd[d] / cy[d] for d in days if d != "Tue"), 1)

# M5 root alarm within 60 s after the last ATS transfer before it
def after_transfer(t):
    i = bisect_right(tt, t)
    return i > 0 and (t - tt[i - 1]).total_seconds() <= 60
for d in ("STER-01", "STER-02", "STER-03"):
    ws = [w for w in wo if w["device_id"] == d and w["root"]]
    key[f"m5_match_{d}"] = sum(1 for w in ws if after_transfer(w["root"]["t"]))
    key[f"m5_roots_{d}"] = len(ws)
key["m5_test_start_first"] = min(t for t in tests).strftime("%Y-%m-%d %H:%M:%S")

# M6 Weibull beta of days between consecutive CM reports, STER-01
ts = sorted(w["reported_at"] for w in wo if w["device_id"] == "STER-01")
x = sorted((b - a).total_seconds() / 86400 for a, b in zip(ts, ts[1:]))
n = len(x); lx = [math.log(v) for v in x]; ml = sum(lx) / n
def g(b):
    xb = [v ** b for v in x]
    return 1 / b + ml - sum(a * l for a, l in zip(xb, lx)) / sum(xb)
lo, hi = 0.05, 20.0
for _ in range(100):
    mid = (lo + hi) / 2
    lo, hi = (mid, hi) if g(mid) > 0 else (lo, mid)
key["m6_beta_mle"] = round((lo + hi) / 2, 2)
# median rank regression, the Excel way: F = (i - 0.3) / (n + 0.4), y = ln(-ln(1 - F)), x = ln(t), beta = SLOPE(y, x)
X = lx; Y = [math.log(-math.log(1 - (i - 0.3) / (n + 0.4))) for i in range(1, n + 1)]
mx, my = sum(X) / n, sum(Y) / n
key["m6_beta_mrr"] = round(sum((a - mx) * (b - my) for a, b in zip(X, Y)) / sum((a - mx) ** 2 for a in X), 2)
key["m6_n"] = n

# M7 recorder
low = [r for r in rec if float(r["v_min"]) < 196]
key["m7_low_minutes"] = len(low)
key["m7_zero_minutes"] = sum(1 for r in low if float(r["v_min"]) == 0)
key["m7_sag_minutes"] = sum(1 for r in low if float(r["v_min"]) > 0)
key["m7_lowest_sag"] = min(float(r["v_min"]) for r in low if float(r["v_min"]) > 0)

# M8 sources of STER-01 + STER-02 CM work orders
src = Counter()
for w in wo:
    if w["device_id"] not in A: continue
    r = w["root"]
    if not r or r["code"] not in ("A01", "A02"): src["genuine"] += 1
    elif any(abs((r["t"] - t).total_seconds()) <= 60 for t in tests): src["test"] += 1
    elif r["code"] == "A02": src["outage"] += 1
    else: src["sag"] += 1
key["m8_sources"] = dict(src)

print(json.dumps(key, indent=1, ensure_ascii=False))
