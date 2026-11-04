"""Case 2, Riyadh bottling line quality. The five first checks, plus stratification, lag, holdout
and the three measures.

Reads the raw files in data/02-case-riyadh-quality/ and prints every number used in the case.
Pure Python, no packages, so anyone can rerun it.
Usage: python3 scripts/riyadh_quality_checks.py
"""
import csv, math, os
from collections import Counter, defaultdict
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "02-case-riyadh-quality")
P = lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
read = lambda n: list(csv.DictReader(open(os.path.join(DATA, n), encoding="utf-8")))
LSL, USL = 1.0, 2.0
A2, D3, D4, d2 = 0.577, 0.0, 2.114, 2.326  # constants for n = 5
START = datetime(2017, 6, 25)
HOLDOUT = START + timedelta(days=50)
mean = lambda v: sum(v) / len(v)
def sd(v):
    m = mean(v); return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
def head(n, title):
    print(f"\n{'=' * 70}\n{n}: {title}\n{'=' * 70}")

rows = read("torque_subgroups_60days.csv")
for r in rows: r["t"] = P(r["timestamp"]); r["v"] = float(r["removal_torque_nm"])
sgs = defaultdict(list)
for r in rows: sgs[r["subgroup"]].append(r)
SG = []
for k in sorted(sgs):
    g = sgs[k]; v = [r["v"] for r in g]
    SG.append(dict(id=k, t=g[0]["t"], lot=g[0]["lot"], op=g[0]["operator"], resin=g[0]["resin_lot"],
                   xbar=mean(v), R=max(v) - min(v), v=v, heads=[int(r["head"]) for r in g]))
mold = read("mold_temperature.csv")
mt = [float(m["mold_temp_c"]) for m in mold]
mold_at = lambda tm: mt[max(0, min(len(mt) - 1, int((tm - START).total_seconds() // 600)))]
cool = read("cooler_log.csv")
for c in cool:
    for k in ("ambient_c", "rh_pct", "chw_supply_c", "compressor_load_pct"): c[k] = float(c[k])
pur = read("purchase_log.csv")
gauge = read("gauge_rr_study.csv")
holds = read("qc_holds.csv")
comp = read("customer_complaints.csv")
rates = {r["item"]: float(r["value"]) for r in read("cost_rates.csv")}
quotes = read("quotes.csv")
shift = lambda t: "A" if 6 <= t.hour < 14 else ("B" if 14 <= t.hour < 22 else "C")

# Check 1 -------------------------------------------------------------------------------
head("Check 1", "X-bar and R chart, 60 days, subgroups of 5")
xbb = mean([s["xbar"] for s in SG]); Rb = mean([s["R"] for s in SG])
ucl, lcl = xbb + A2 * Rb, xbb - A2 * Rb
uclr, lclr = D4 * Rb, D3 * Rb
print(f"Subgroups: {len(SG)}, readings: {len(rows)}. Grand mean {xbb:.3f} N m, R-bar {Rb:.3f} N m.")
print(f"X-bar chart: UCL {ucl:.3f}, CL {xbb:.3f}, LCL {lcl:.3f}. R chart: UCL {uclr:.3f}, LCL {lclr:.3f}.")
above = [s for s in SG if s["xbar"] > ucl]; below = [s for s in SG if s["xbar"] < lcl]
rout = [s for s in SG if s["R"] > uclr]
print(f"X-bar points above UCL: {len(above)}. Below LCL: {len(below)}. R points above UCL: {len(rout)}.")
print("X-bar points above UCL by shift: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(shift(s['t']) for s in above).items())))
print("X-bar points below LCL by shift: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(shift(s['t']) for s in below).items())))
hrs = Counter(s["t"].hour for s in above)
print("X-bar points above UCL by sampling hour: " + ", ".join(f"{h:02d}h {hrs[h]}" for h in sorted(hrs)))
print("First 5 subgroups:")
for s in SG[:5]:
    print(f"  {s['id']} {s['t']} {' '.join(f'{x:.3f}' for x in s['v'])}  xbar {s['xbar']:.3f}  R {s['R']:.3f}")

# Check 2 -------------------------------------------------------------------------------
head("Check 2", "run rules: 8 in a row on one side of the centre line")
runs, cur, side = [], [], 0
for s in SG:
    sd_ = 1 if s["xbar"] > xbb else -1
    if sd_ == side: cur.append(s)
    else:
        if len(cur) >= 8: runs.append((side, cur))
        cur, side = [s], sd_
if len(cur) >= 8: runs.append((side, cur))
print(f"Runs of 8 or more on one side: {len(runs)} ({sum(1 for r in runs if r[0] > 0)} above, {sum(1 for r in runs if r[0] < 0)} below).")
for sgn, r in runs:
    print(f"  {'above' if sgn > 0 else 'below'}: {len(r)} points, {r[0]['t']} to {r[-1]['t']}")
day = defaultdict(list)
for s in SG: day[s["t"].hour // 2 * 2].append(s["xbar"])
print("Mean of X-bar by sampling hour: " + ", ".join(f"{h:02d}h {mean(v):.3f}" for h, v in sorted(day.items())))

# Check 3 -------------------------------------------------------------------------------
head("Check 3", "capability: within-subgroup sigma vs overall sigma")
allv = [r["v"] for r in rows]
s_w = Rb / d2; s_o = sd(allv); mu = mean(allv)
cp = (USL - LSL) / (6 * s_w); cpk = min(USL - mu, mu - LSL) / (3 * s_w)
pp = (USL - LSL) / (6 * s_o); ppk = min(USL - mu, mu - LSL) / (3 * s_o)
print(f"Spec {LSL} to {USL} N m. Mean {mu:.3f}. Sigma within (R-bar/d2) {s_w:.3f}. Sigma overall {s_o:.3f}.")
print(f"Cp {cp:.2f}, Cpk {cpk:.2f}. Pp {pp:.2f}, Ppk {ppk:.2f}.")
print(f"Readings above USL: {sum(1 for x in allv if x > USL)}. Below LSL: {sum(1 for x in allv if x < LSL)}. Of {len(allv)}.")
print(f"Share of overall variance that lies between subgroups: {1 - s_w ** 2 / s_o ** 2:.0%}.")

# Check 4 -------------------------------------------------------------------------------
head("Check 4", "timing of the shift vs every input change")
switch = min(P(p["first_use"]) for p in pur if p["supplier"] == "Najd Resins")
pre = [s for s in SG if s["t"] < switch]; post = [s for s in SG if s["t"] >= switch]
print(f"Resin switch to Najd Resins, first use {switch}. Price {[p['price_sar_per_t'] for p in pur if p['supplier'] == 'Najd Resins'][0]} "
      f"vs {[p['price_sar_per_t'] for p in pur if p['supplier'] == 'Gulf Polymers'][0]} SAR per t.")
dmax = defaultdict(float)
for c in cool: dmax[c["timestamp"][:10]] = max(dmax[c["timestamp"][:10]], c["ambient_c"])
sw = switch.date().isoformat()
for lab, ks in (("before", [k for k in dmax if k < sw]), ("after", [k for k in dmax if k >= sw])):
    print(f"Days {lab} the switch: {len(ks)}. Days with peak ambient above 44 C: {sum(1 for k in ks if dmax[k] > 44)}. Holds per 10 days: {10 * sum(1 for h in holds if (h['timestamp'][:10] < sw) == (lab == 'before')) / len(ks):.1f}.")
print(f"Naive comparison: mean X-bar before {mean([s['xbar'] for s in pre]):.3f} ({len(pre)} subgroups), "
      f"after {mean([s['xbar'] for s in post]):.3f} ({len(post)}). Holds before {sum(1 for h in holds if P(h['timestamp']) < switch)}, after {sum(1 for h in holds if P(h['timestamp']) >= switch)}.")
for s in SG: s["mold3"] = mold_at(s["t"] - timedelta(hours=3))
bands = [(0, 26), (26, 29), (29, 32), (32, 99)]
print("Stratified by mold temperature 3 h before sampling:")
print(f"  {'band C':10} {'Gulf n':>7} {'Gulf mean':>10} {'Najd n':>7} {'Najd mean':>10}")
for lo, hi in bands:
    g = [s["xbar"] for s in pre if lo <= s["mold3"] < hi]; n = [s["xbar"] for s in post if lo <= s["mold3"] < hi]
    f = lambda v: f"{mean(v):.3f}" if v else "-"
    print(f"  {f'{lo}-{hi}' if hi < 99 else f'{lo}+':10} {len(g):>7} {f(g):>10} {len(n):>7} {f(n):>10}")
hv = defaultdict(list)
for s_ in SG:
    for h, v in zip(s_["heads"], s_["v"]): hv[h].append(v - s_["xbar"])  # deviation from own subgroup mean removes time effects
hm = {h: mean(v) for h, v in hv.items()}
res_sd = sd([x for v in hv.values() for x in v]); se_h = res_sd / math.sqrt(len(rows) / 12)
print("Head effect (reading minus its subgroup mean), by capping head: " + ", ".join(f"H{h} {hm[h]:+.3f}" for h in sorted(hm)))
print(f"Range of head effects: {max(hm.values()) - min(hm.values()):.3f} N m. Expected range from chance alone (3.26 standard errors): {3.26 * se_h:.3f} N m.")
ov = defaultdict(list)
for r in rows: ov[r["operator"]].append(r["v"])
print("Mean by operator (shift): " + ", ".join(f"{k} {mean(v):.3f}" for k, v in sorted(ov.items())))
def corr(a, b):
    ma, mb = mean(a), mean(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
print("Correlation of X-bar with mold temperature L hours earlier:")
cl = {}
for L in range(0, 7):
    cl[L] = corr([s["xbar"] for s in SG], [mold_at(s["t"] - timedelta(hours=L)) for s in SG])
print("  " + ", ".join(f"L={L} h r={c:.2f}" for L, c in cl.items()) + f". Peak at {max(cl, key=cl.get)} h.")
bins = defaultdict(list)
for c in cool: bins[int(c["ambient_c"] // 1)].append(c["chw_supply_c"])
print("Chilled water supply by ambient band: " + ", ".join(f"{a} C {mean(v):.1f}" for a, v in sorted(bins.items()) if a >= 38))
print(f"10-minute rows with ambient above 42.5 C: {sum(1 for c in cool if c['ambient_c'] > 42.5)} of {len(cool)}. "
      f"With compressor at 100%: {sum(1 for c in cool if c['compressor_load_pct'] >= 100)}.")
print(f"Correlation of mold temperature with chilled water supply 20 minutes earlier: "
      f"{corr([mt[i] for i in range(2, len(mt))], [cool[i - 2]['chw_supply_c'] for i in range(2, len(mt))]):.2f}.")

# Holdout -------------------------------------------------------------------------------
head("Check 4b", "holdout: fit on days 1 to 50, predict days 51 to 60")
tr = [s for s in SG if s["t"] < HOLDOUT]; te = [s for s in SG if s["t"] >= HOLDOUT]
x = [s["mold3"] for s in tr]; y = [s["xbar"] for s in tr]
b = sum((a - mean(x)) * (c - mean(y)) for a, c in zip(x, y)) / sum((a - mean(x)) ** 2 for a in x); a0 = mean(y) - b * mean(x)
print(f"Fit: X-bar = {a0:.3f} + {b:.4f} x mold temperature 3 h earlier. Training subgroups {len(tr)}.")
pred = [a0 + b * s["mold3"] for s in te]
err = [s["xbar"] - p for s, p in zip(te, pred)]
print(f"Holdout subgroups {len(te)}. RMSE {math.sqrt(mean([e * e for e in err])):.3f} N m. Mean error {mean(err):+.3f}.")
print(f"Holdout subgroups predicted above UCL: {sum(1 for p in pred if p > ucl)}. Actual above UCL: {sum(1 for s in te if s['xbar'] > ucl)}. "
      f"Both: {sum(1 for s, p in zip(te, pred) if p > ucl and s['xbar'] > ucl)}.")
print(f"Holdout correlation of predicted and actual X-bar: {corr(pred, [s['xbar'] for s in te]):.2f}.")

# Check 5 -------------------------------------------------------------------------------
head("Check 5", "gauge R&R, ANOVA method, 10 parts x 3 operators x 3 trials")
for g in gauge: g["x"] = float(g["reading_nm"]); g["ref"] = float(g["lab_reference_nm"])
parts = sorted({g["part"] for g in gauge}); ops = sorted({g["operator"] for g in gauge}); n, p_, o_ = 3, len(parts), len(ops)
gm = mean([g["x"] for g in gauge])
pm = {p: mean([g["x"] for g in gauge if g["part"] == p]) for p in parts}
om = {o: mean([g["x"] for g in gauge if g["operator"] == o]) for o in ops}
cm = {(p, o): mean([g["x"] for g in gauge if g["part"] == p and g["operator"] == o]) for p in parts for o in ops}
ssp = o_ * n * sum((pm[p] - gm) ** 2 for p in parts); sso = p_ * n * sum((om[o] - gm) ** 2 for o in ops)
sspo = n * sum((cm[(p, o)] - pm[p] - om[o] + gm) ** 2 for p in parts for o in ops)
sse = sum((g["x"] - cm[(g["part"], g["operator"])]) ** 2 for g in gauge)
msp, mso, mspo, mse = ssp / (p_ - 1), sso / (o_ - 1), sspo / ((p_ - 1) * (o_ - 1)), sse / (p_ * o_ * (n - 1))
v_rep = mse; v_po = max(0.0, (mspo - mse) / n); v_o = max(0.0, (mso - mspo) / (p_ * n)); v_p = max(0.0, (msp - mspo) / (o_ * n))
v_grr = v_rep + v_o + v_po; v_tot = v_grr + v_p
print(f"Sigma repeatability {math.sqrt(v_rep):.3f}, reproducibility {math.sqrt(v_o + v_po):.3f}, GRR {math.sqrt(v_grr):.3f}, part {math.sqrt(v_p):.3f} N m.")
print(f"%GRR of total variation: {math.sqrt(v_grr / v_tot):.1%}. %GRR of tolerance (6 sigma / {USL - LSL:.1f}): {6 * math.sqrt(v_grr) / (USL - LSL):.1%}. ndc: {1.41 * math.sqrt(v_p / v_grr):.1f}.")
print("AIAG guide: under 10% acceptable, 10% to 30% marginal, over 30% not acceptable. ndc 5 or more.")
for o in ops:
    bias = mean([g["x"] - g["ref"] for g in gauge if g["operator"] == o])
    print(f"  {o}: mean bias vs lab reference {bias:+.3f} N m")
gr = [g for g in gauge if g["operator"] != "J. Dela Cruz"]
print(f"Without the night operator, sigma of reading minus reference: {sd([g['x'] - g['ref'] for g in gr]):.3f}. With all three: {sd([g['x'] - g['ref'] for g in gauge]):.3f}.")
night = [s for s in SG if shift(s["t"]) == "C"]
print(f"Night shift X-bar below LCL: {sum(1 for s in night if s['xbar'] < lcl)} of {len(night)}.")

# Three measures -------------------------------------------------------------------------
head("Measures", "throughput, inventory, operating expense over the 60 days")
tvc = rates["selling_price"] - rates["truly_variable_cost"]
held = sum(int(h["cases_held"]) for h in holds); rew = [h for h in holds if h["disposition"].startswith("Reworked")]
rcases = sum(int(h["cases_held"]) for h in rew)
cb = sum(int(c["bottles"]) for c in comp if c["complaint"] == "Cap hard to open")
print(f"Throughput per case (price minus truly variable cost): {tvc:.2f} SAR.")
print(f"Holds: {len(holds)} blocks, {held} cases held. Released after retest: {len(holds) - len(rew)}. Reworked: {len(rew)} blocks, {rcases} cases.")
print(f"Rework cost: {rcases * rates['rework_cost']:.0f} SAR. Lab retest hours: {len(holds) * rates['lab_retest']:.1f}. "
      f"Held cases as stock waiting for retest: {held} cases, {held * rates['truly_variable_cost']:.0f} SAR at truly variable cost.")
print(f"Line hours of output reworked: {rcases / rates['line_rate']:.1f} h.")
print(f"Complaints: {len(comp)} ({', '.join(f'{k} {v}' for k, v in Counter(c['complaint'] for c in comp).items())}). "
      f"Bottles {sum(int(c['bottles']) for c in comp)}. Credit {sum(int(c['bottles']) for c in comp) / 12 * rates['complaint_credit']:.0f} SAR.")
print(f"Complaints from lots made before the resin switch: {sum(1 for c in comp if c['lot'][:8] < switch.strftime('%Y%m%d'))}: " + ", ".join(c['complaint_id'] + ' ' + c['lot'] for c in comp if c['lot'][:8] < switch.strftime('%Y%m%d')))
print("Complaints by customer: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(c['customer'] for c in comp).items())))
print("Complaints by lot shift: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(c['lot'][-1] for c in comp).items())))
print("Holds by shift: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(h['lot'][-1] for h in holds).items())))
hh = [s for s in SG if s["id"] in {h["subgroup"] for h in holds}]
print(f"Held subgroups with mold temperature 3 h earlier above 29 C: {sum(1 for s in hh if s['mold3'] > 29)} of {len(hh)}.")
t_new = sum(float(p["tonnes"]) for p in pur if p["supplier"] == "Najd Resins" and P(p["first_use"]) < START + timedelta(days=60))
print(f"Najd Resins tonnes in use within the 60 days: {t_new:.0f}. Saving vs Gulf Polymers: {t_new * 310:.0f} SAR.")
for q in quotes:
    print(f"  {q['quote_id']} {q['item']}: {int(q['price_sar'])} SAR, {q['lead_time_weeks']} weeks. {q['vendor_claim']}")
drop = lambda c: 6.0 if c["rh_pct"] < 20 else 0.0
pc = [c for c in cool if c["ambient_c"] - drop(c) > 42.5]
hot = [c for c in cool if c["ambient_c"] > 42.5]
print(f"Relative humidity in rows above 42.5 C: max {max(c['rh_pct'] for c in hot):.1f}%, under 20% in {sum(1 for c in hot if c['rh_pct'] < 20)} of {len(hot)}.")
print(f"10-minute rows above 42.5 C after a 6 C pre-cooler drop: {len(pc)} of {len(cool)} "
      f"(from {sum(1 for c in cool if c['ambient_c'] > 42.5)}). Highest ambient after the drop: {max(c['ambient_c'] - drop(c) for c in cool):.1f} C.")
qp = {q["quote_id"]: int(q["price_sar"]) for q in quotes}
print(f"Plan Q-03 + Q-04: {qp['Q-03'] + qp['Q-04']} SAR. Q-02 + Q-04: {qp['Q-02'] + qp['Q-04']} SAR. Q-01: {qp['Q-01']} SAR. Difference Q-02 vs Q-03: {qp['Q-02'] - qp['Q-03']} SAR.")
ni = [s for s in SG if shift(s["t"]) == "C"]; dy = [s for s in SG if shift(s["t"]) == "A"]
print(f"Mean X-bar night shift {mean([s['xbar'] for s in ni]):.3f}, morning shift {mean([s['xbar'] for s in dy]):.3f}. Mean mold temperature 3 h before: night {mean([s['mold3'] for s in ni]):.1f} C, morning {mean([s['mold3'] for s in dy]):.1f} C.")
def sim(fix_amb):
    over = 0
    for s in SG:
        t0 = s["t"] - timedelta(hours=3)
        i = max(0, min(len(cool) - 1, int((t0 - START).total_seconds() // 600) - 2))
        a = cool[i]["ambient_c"] - (drop(cool[i]) if fix_amb == 6 else fix_amb)
        m = 24.5 + 1.1 * (2.4 * max(0.0, a - 42.5))
        shift_ = a0 + b * m - (a0 + b * s["mold3"])
        over += sum(1 for v in s["v"] if v + shift_ > USL)
    return over
print(f"Readings above USL, recomputed with the fitted slope: as is {sim(0)}, with 6 C pre-cooler {sim(6)}, with chiller holding 12 C {sim(99)}.")

# Scene ---------------------------------------------------------------------------------
head("Scene", "Sunday 2017-08-20, hold H-016")
h = next(h for h in holds if h["hold_id"] == "H-016")
s = next(s for s in SG if s["id"] == h["subgroup"])
print(f"{h['hold_id']} {h['timestamp']} lot {h['lot']} subgroup {s['id']} readings {' '.join(f'{x:.3f}' for x in s['v'])}, "
      f"heads {s['heads']}, operator {s['op']}. Retest {h['retest_over_usl']} of {h['retest_n']} over USL. {h['disposition']}.")
t0 = s["t"] - timedelta(hours=3)
for c in cool:
    if t0 - timedelta(minutes=10) <= P(c["timestamp"]) <= t0 + timedelta(minutes=10):
        print(f"  cooler {c['timestamp']} ambient {c['ambient_c']} rh {c['rh_pct']} supply {c['chw_supply_c']} load {c['compressor_load_pct']:.0f}")
print(f"  mold temperature 3 h before sampling: {s['mold3']:.1f} C")
print(f"  peak ambient that day: {dmax['2017-08-20']:.1f} C")
print(f"Holds on Sunday to Thursday {sum(1 for x in holds if P(x['timestamp']).weekday() not in (4, 5))}, Friday and Saturday {sum(1 for x in holds if P(x['timestamp']).weekday() in (4, 5))}.")
ah = defaultdict(list); mh = defaultdict(list)
for c, m in zip(cool, mt):
    ah[int(c["timestamp"][11:13])].append(c["ambient_c"])
for i, m in enumerate(mt): mh[int(mold[i]["timestamp"][11:13])].append(m)
print("Mean ambient by hour: " + ", ".join(f"{h:02d}h {mean(v):.1f}" for h, v in sorted(ah.items())))
print("Mean mold temperature by hour: " + ", ".join(f"{h:02d}h {mean(v):.1f}" for h, v in sorted(mh.items())))
print(f"Hottest hour on average: {max(ah, key=lambda h: mean(ah[h])):02d}h. Hottest mold hour: {max(mh, key=lambda h: mean(mh[h])):02d}h.")
