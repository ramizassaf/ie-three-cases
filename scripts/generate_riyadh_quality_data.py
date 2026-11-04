"""Case 2, Riyadh bottling line quality. Generates the raw data files.

The data is fictional. It is generated with a fixed seed, so every run gives the same files.
Story frame: Samer joins a bottled water plant in Riyadh as quality engineer in 2017. Customers
complain that caps are hard to open. The plant holds lots whenever a torque reading passes the
upper spec limit. He receives 60 days of records, 2017-06-25 to 2017-08-23.

Hidden mechanism (the answer the reader must find from the data):
- Caps are molded in-house and reach the capper through a silo, about 3 hours later.
- The chiller that cools the cap mold loses capacity when ambient air passes 42.5 C. Chilled water
  supply temperature rises, mold temperature rises, caps shrink differently, and removal torque
  rises about 3 hours later, on hot afternoons and evenings.
- The resin supplier changed in mid-July, as the heat waves grew. The resin has no effect.
- The 12 capping heads have no effect.
- The torque tester and method add measurement error. The night shift operator reads low.
- Days 51 to 60 are a holdout: the checks fit the model on days 1 to 50 and predict 51 to 60.

Usage: python3 scripts/generate_riyadh_quality_data.py
Writes the files into data/02-case-riyadh-quality/.
"""
import csv, math, os, random
from datetime import datetime, timedelta

SEED = 2017
rng = random.Random(SEED)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "02-case-riyadh-quality")
START = datetime(2017, 6, 25)
DAYS = 60
END = START + timedelta(days=DAYS)
SWITCH = datetime(2017, 7, 13, 6, 0)  # first use of the new resin lot
M = lambda m: timedelta(minutes=m)
LSL, USL = 1.0, 2.0  # removal torque spec, N m
OPS = {"A": ("S. Al-Qahtani", 0.00), "B": ("R. Mathew", 0.01), "C": ("J. Dela Cruz", -0.07)}
SIG_PART, SIG_REP = 0.08, 0.05
BASE, K_MOLD, MOLD0, LAG_H = 1.52, 0.06, 24.5, 3.0

def shift_of(t):
    return "A" if 6 <= t.hour < 14 else ("B" if 14 <= t.hour < 22 else "C")

def lot_of(t):
    d = t - timedelta(days=1) if t.hour < 6 else t  # shift C belongs to the day it started
    return f"{d.strftime('%Y%m%d')}-{shift_of(t)}"

# 1. Ambient, chiller and mold temperature, every 10 minutes ----------------------------
daily_max, x = [], 0.0
for d in range(DAYS):
    x = 0.75 * x + rng.gauss(0, 1.0)
    daily_max.append(41.8 + 0.07 * d + x)
cool, mold = [], []
t, supply_hist = START, []
while t < END:
    d = (t - START).days
    hr = t.hour + t.minute / 60
    tmax = daily_max[d]; tmin = tmax - 13.5
    amb = tmin + (tmax - tmin) * max(0.0, math.cos((hr - 15.5) / 24 * 2 * math.pi)) ** 1.3 + rng.gauss(0, 0.4)
    over = max(0.0, amb - 42.5)
    supply = 12.0 + 2.4 * over + rng.gauss(0, 0.25)
    ret = supply + 4.8 + rng.gauss(0, 0.3)
    load = min(100.0, 62 + 0.9 * max(0.0, amb - 30) + rng.gauss(0, 2)) if over == 0 else 100.0
    rh = max(4.0, 9 + 9 * math.cos((hr - 5) / 24 * 2 * math.pi) + rng.gauss(0, 1.5))
    cool.append((t, round(amb, 1), round(rh, 1), round(supply, 2), round(ret, 2), round(load, 0)))
    supply_hist.append(supply)
    lagged = supply_hist[-3] if len(supply_hist) >= 3 else supply  # mold follows about 20 min later
    mt = MOLD0 + 1.1 * (lagged - 12.0) + rng.gauss(0, 0.3)
    mold.append((t, "CAP-M1", round(mt, 2), 24))
    t += M(10)
mold_at = lambda tm: mold[max(0, min(len(mold) - 1, int((tm - START).total_seconds() // 600)))][2]

# 2. Resin purchases --------------------------------------------------------------------
purchases = []
po = 4101
d = START - timedelta(days=20)
lot_no = 1
while d < END:
    new = d >= SWITCH - timedelta(days=9)
    sup, grade, price = ("Najd Resins", "HD-5502C", 5480) if new else ("Gulf Polymers", "HP-5503", 5790)
    received = d + timedelta(days=rng.randint(6, 9))
    first_use = received + timedelta(days=rng.randint(1, 3))
    if new and first_use < SWITCH: first_use = SWITCH
    if not new and first_use >= SWITCH: first_use = SWITCH - timedelta(days=rng.randint(3, 5))
    purchases.append([f"PO-{po}", d.date().isoformat(), received.date().isoformat(), first_use.strftime("%Y-%m-%d %H:%M:%S"),
                      sup, grade, f"L{lot_no:03d}", 22, price])
    po += 1; lot_no += 1; d += timedelta(days=rng.randint(5, 7))
purchases.sort(key=lambda r: r[3])
def resin_at(tm):
    cur = purchases[0]
    for r in purchases:
        if datetime.strptime(r[3], "%Y-%m-%d %H:%M:%S") <= tm: cur = r
    return cur

# 3. Torque readings: 12 subgroups a day, 5 consecutive bottles each ------------------------
torque, sg = [], 1
true_by_sg = {}
for day in range(DAYS):
    for k in range(12):
        tm = START + timedelta(days=day, hours=2 * k) + M(rng.randint(5, 40))
        op, bias = OPS[shift_of(tm)]
        cap_t = tm - timedelta(hours=LAG_H) - M(rng.uniform(-30, 30))
        mu = BASE + K_MOLD * (mold_at(cap_t) - MOLD0)
        r = resin_at(cap_t)
        head0 = rng.randint(1, 12)
        vals = []
        for j in range(5):
            true = mu + rng.gauss(0, SIG_PART)
            read = true + bias + rng.gauss(0, SIG_REP)
            vals.append(read)
            torque.append([f"SG-{sg:04d}", (tm + timedelta(seconds=12 * j)).strftime("%Y-%m-%d %H:%M:%S"), lot_of(tm),
                           (head0 + j - 1) % 12 + 1, op, "TT-02", r[6], round(read, 3)])
        true_by_sg[sg] = (tm, vals)
        sg += 1

# 4. QC holds: a 2-hour block is held when any reading passes USL --------------------------
CASES_PER_2H = 3000
holds = []
for s, (tm, vals) in true_by_sg.items():
    if max(vals) > USL:
        retest = [mold_at(tm - timedelta(hours=LAG_H)) for _ in range(1)]
        mu = BASE + K_MOLD * (retest[0] - MOLD0)
        over = sum(1 for _ in range(32) if mu + rng.gauss(0, SIG_PART) + rng.gauss(0, SIG_REP) > USL)
        disp = "Released after retest" if over <= 1 else "Reworked, recapped"
        holds.append([f"H-{len(holds) + 1:03d}", tm.strftime("%Y-%m-%d %H:%M:%S"), lot_of(tm), f"SG-{s:04d}",
                      round(max(vals), 3), CASES_PER_2H, 32, over, disp])

# 5. Customer complaints: from the 2-hour blocks shipped with high torque ----------------------
complaints, cno = [], 1
CUST = ["Riyadh Hypermarkets", "Al-Waha Stores", "Office Water Delivery"]
held = {h[3] for h in holds if h[8].startswith("Reworked")}
for s, (tm, vals) in true_by_sg.items():
    if f"SG-{s:04d}" in held: continue
    mu = BASE + K_MOLD * (mold_at(tm - timedelta(hours=LAG_H)) - MOLD0)
    p_over = 1 - 0.5 * (1 + math.erf((USL - mu) / (SIG_PART * math.sqrt(2))))
    p_under = 0.5 * (1 + math.erf((LSL - mu) / (SIG_PART * math.sqrt(2))))
    if rng.random() < min(0.9, 12 * p_over):
        rec = tm + timedelta(days=rng.randint(3, 12))
        complaints.append([f"CC-{cno:03d}", rec.date().isoformat(), lot_of(tm), rng.choice(CUST), "Cap hard to open", rng.randint(12, 144)])
        cno += 1
    if rng.random() < min(0.9, 6 * p_under):
        rec = tm + timedelta(days=rng.randint(3, 12))
        complaints.append([f"CC-{cno:03d}", rec.date().isoformat(), lot_of(tm), rng.choice(CUST), "Leaking cap", rng.randint(12, 48)])
        cno += 1
complaints.sort(key=lambda c: c[1])
for i, c in enumerate(complaints, 1): c[0] = f"CC-{i:03d}"

# 6. Gauge R&R study: 10 caps, 3 operators, 3 trials, reference value from calibration lab ----
gauge = []
parts = [round(rng.uniform(1.30, 1.85), 3) for _ in range(10)]
for trial in (1, 2, 3):
    for key in ("A", "B", "C"):
        name, bias = OPS[key]
        for p, ref in enumerate(parts, 1):
            gauge.append([f"P{p:02d}", name, trial, round(ref + bias + rng.gauss(0, SIG_REP), 3), ref])

# 7. Cost rates and quotes -------------------------------------------------------------------
rates = [
    ["selling_price", 9.60, "SAR per case of 12 x 600 ml"],
    ["truly_variable_cost", 5.10, "SAR per case: resin, preform, cap, label, carton, water, energy"],
    ["rework_cost", 1.35, "SAR per case: decap, new cap, recap, repack"],
    ["complaint_credit", 9.60, "SAR per case credited to the customer"],
    ["line_rate", 1500, "cases per hour"],
    ["lab_retest", 0.75, "lab hours per held block"],
]
quotes = [
    ["Q-01", "New 12-head rotary capper", "Capping machine vendor", 1850000, 26, "Head-to-head torque spread under 0.05 N m"],
    ["Q-02", "Supplementary air-cooled chiller, 60 TR", "HVAC contractor", 310000, 8, "Holds chilled water supply at 12 C up to 50 C ambient"],
    ["Q-03", "Adiabatic pre-cooler pads for existing chiller condenser", "HVAC contractor", 85000, 3, "Lowers condenser inlet air by 6 C when relative humidity is under 20%"],
    ["Q-04", "Torque tester fixture, calibration and operator training", "Instrument supplier", 18000, 2, "Removes operator technique bias"],
    ["Q-05", "Return to Gulf Polymers resin, price difference per tonne", "Purchasing", 310, 0, ""],
]

# 8. Write files -------------------------------------------------------------------------------
os.makedirs(OUT, exist_ok=True)
fmt = lambda t: t.strftime("%Y-%m-%d %H:%M:%S")
def write(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(header); w.writerows(rows)
    print(f"{name}: {len(rows)} rows")
write("torque_subgroups_60days.csv", ["subgroup", "timestamp", "lot", "head", "operator", "gauge", "resin_lot", "removal_torque_nm"], torque)
write("mold_temperature.csv", ["timestamp", "mold_id", "mold_temp_c", "cavities"], [[fmt(a), b, c, e] for a, b, c, e in mold])
write("cooler_log.csv", ["timestamp", "ambient_c", "rh_pct", "chw_supply_c", "chw_return_c", "compressor_load_pct"], [[fmt(a), b, h, c, e, g] for a, b, h, c, e, g in cool])
write("purchase_log.csv", ["po", "order_date", "received_date", "first_use", "supplier", "grade", "resin_lot", "tonnes", "price_sar_per_t"], purchases)
write("gauge_rr_study.csv", ["part", "operator", "trial", "reading_nm", "lab_reference_nm"], gauge)
write("qc_holds.csv", ["hold_id", "timestamp", "lot", "subgroup", "max_reading_nm", "cases_held", "retest_n", "retest_over_usl", "disposition"], holds)
write("customer_complaints.csv", ["complaint_id", "received_date", "lot", "customer", "complaint", "bottles"], complaints)
write("cost_rates.csv", ["item", "value", "unit"], rates)
write("quotes.csv", ["quote_id", "item", "source", "price_sar", "lead_time_weeks", "vendor_claim"], quotes)
