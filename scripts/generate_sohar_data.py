"""Fictional data for case 3: galvanized pipe plant, Sohar, Jan-Jul 2019. Seed 2019.
Hidden mechanisms:
 1. Galvanizing kettle is the constraint; tube mill has spare capacity.
 2. Night shift added on tube mill from 2019-03-01 raises WIP, not output.
 3. Kettle loses 40 min at each of 3 shift handovers, plus dross cleaning and breakdowns.
 4. Eddy-current tester (ECT) on tube mill often OFF after March; weld defects then
    pass through the kettle and are rejected after it (kettle time wasted + remake).
 5. Yard is stacked: crane usually takes the top (newest) bundle -> LIFO -> long waits.
 6. Pilot from 2019-06-09: staggered handover, ECT always ON, earliest-due-date picking,
    tube mill back to 2 shifts and release tied to kettle buffer (rope).
"""
import csv, os, random, math, heapq
from datetime import datetime, timedelta
R = random.Random(2019)
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "03-case-sohar-flow")
T0 = datetime(2019, 1, 1); END = datetime(2019, 9, 1)
NIGHT_FROM = datetime(2019, 3, 1); PILOT = datetime(2019, 6, 9)
M = lambda d: (d - T0).total_seconds() / 60
D = lambda m: T0 + timedelta(minutes=m)
SIZES = ["DN15", "DN20", "DN25", "DN32", "DN40", "DN50", "DN80", "DN100"]
WALLS = ["LIGHT", "MEDIUM", "HEAVY"]
TM_RATE = {"LIGHT": 6.0, "MEDIUM": 5.6, "HEAVY": 5.1}   # t/h
GK_RATE = {"LIGHT": 3.45, "MEDIUM": 3.8, "HEAVY": 4.15}  # t/h
CHANGEOVER = 75; BUNDLE = 2.5
CUSTOMERS = ["C-DUQM-WATER", "C-SOHAR-BUILD", "C-MUSCAT-MEP", "C-NIZWA-AGRI", "C-SALALAH-TR", "C-EXPORT-UAE"]
def demand(t):  # t/day
    d = D(t)
    if d < datetime(2019, 2, 1): return 66
    if d < datetime(2019, 3, 1): return 84
    if d < datetime(2019, 6, 1): return 74
    return 66   # summer: midday outdoor work ban slows construction
# ---------- orders ----------
orders = []; t = 0; oid = 0
while t < M(END) - 1440 * 3:
    mean_t = 26.0
    t += R.gammavariate(6, mean_t * 1440 / demand(t) / 6)
    oid += 1
    tons = round(min(70, max(5, R.lognormvariate(math.log(22), 0.55))), 1)
    cust = R.choices(CUSTOMERS, [3 if D(t) < datetime(2019, 3, 1) and D(t) >= datetime(2019, 2, 1) else 1.2, 2, 2, 1, 1, 1.3])[0]
    orders.append(dict(order_id=f"SO-{oid:04d}", customer=cust, received=t, due=t + 21 * 1440,
                       size=R.choice(SIZES), wall=R.choices(WALLS, [0.45, 0.35, 0.20])[0], tons=tons,
                       threaded="Y" if R.random() < 0.4 else "N", shipped=None, remaining=None))
for o in orders: o["remaining"] = math.ceil(o["tons"] / BUNDLE)
# ---------- tube mill shifts ----------
def tm_on(m):
    d = D(m); h = d.hour
    if d >= PILOT or d < NIGHT_FROM: return 6 <= h < 22
    return True
def shift_of(d):
    h = d.hour
    return "A" if 6 <= h < 14 else ("B" if 14 <= h < 22 else "C")
ect = {}
day = T0
while day < END:
    for s in "ABC":
        if day >= PILOT: p_off = 0.0
        elif day < NIGHT_FROM: p_off = 0.10
        else: p_off = 0.80 if s == "C" else 0.45
        ect[(day.date(), s)] = "OFF" if R.random() < p_off else "ON"
    day += timedelta(days=1)
def ect_at(d):
    s = shift_of(d); dd = d.date() if d.hour >= 6 else (d - timedelta(days=1)).date()
    return ect[(dd, s)], dd, s
# ---------- kettle availability ----------
def kettle_blocked(m, dur=0):
    """planned stop: return (end minute, reason) if kettle at minute m cannot start a dip of length dur.
    A crew does not start a dip it cannot finish before a planned stop."""
    d = D(m); mod = d.hour * 60 + d.minute
    wins = [(600, 640, "DROSS_CLEANING")]
    if d < PILOT: wins += [(c - 15, c + 15, "SHIFT_HANDOVER") for c in (360, 840, 1320)]
    for a, b, r in wins:
        for off in (0, 1440):
            a2, b2 = a + off, b + off
            if mod < b2 and mod + dur > a2: return m + (b2 - mod), r
    return None
bd = []; t = R.expovariate(1 / (60 * 55))
while t < M(END):
    rep = R.lognormvariate(math.log(80), 0.5); bd.append((t, t + rep)); t += rep + R.expovariate(1 / (60 * 55))
# ---------- simulation ----------
released = []   # orders waiting at tube mill
order_q = list(orders); oq_i = 0
yard = []       # bundles waiting for kettle
bundles = []; bid = 0
tm_t = 0.0; tm_size = None; gk_t = 0.0
stops = []; tm_log = {}
rework = []     # bundles to remake (tons, order)
remake_q = []
def yard_tons(): return sum(b["tons"] for b in yard)
def pick_kettle(now):
    cand = [b for b in yard if b["kettle_in"] <= now]
    if not cand: return None
    if D(now) >= PILOT:
        return min(cand, key=lambda b: (orders_by[b["order_id"]]["due"], b["kettle_in"]))
    if R.random() < 0.75: return max(cand, key=lambda b: b["kettle_in"])
    return R.choice(cand)
orders_by = {o["order_id"]: o for o in orders}
bd_i = 0
# event loop: advance whichever resource is earlier
while min(tm_t, gk_t) < M(END):
    if tm_t <= gk_t:
        now = tm_t
        while oq_i < len(order_q) and order_q[oq_i]["received"] <= now:
            o = order_q[oq_i]; oq_i += 1
            o["released_q"] = True; released.append(o)
        if not tm_on(now):
            tm_t = now + 30; continue
        # rope during pilot: release only if yard buffer below 2 days of kettle
        if D(now) >= PILOT and yard_tons() > 150:
            tm_t = now + 30; continue
        job = None
        if remake_q:
            job = remake_q.pop(0)
        else:
            pend = [o for o in released if o.get("tm_left", None) is None or o["tm_left"] > 0]
            if not pend:
                tm_t = now + 30; continue
            same = [o for o in pend if o["size"] == tm_size]
            o = same[0] if same else pend[0]
            if o["size"] != tm_size:
                tm_size = o["size"]; dd = D(now)
                k = (ect_at(dd)[1], shift_of(dd)); tm_log.setdefault(k, {"tons": 0, "co": 0})["co"] += 1
                tm_t = now + CHANGEOVER; continue
            if "tm_left" not in o: o["tm_left"] = o["tons"]
            tons = round(min(BUNDLE, o["tm_left"]), 2); o["tm_left"] = round(o["tm_left"] - tons, 2)
            if o["tm_left"] <= 0: released.remove(o)
            job = (o, tons)
        o, tons = job
        dur = tons / TM_RATE[o["wall"]] * 60 * R.uniform(1.0, 1.12)
        end = now + dur; de = D(end)
        st, dd, s = ect_at(de)
        bid += 1
        p = 0.006 if st == "ON" else 0.055
        b = dict(bundle_id=f"B{bid:05d}", order_id=o["order_id"], size=o["size"], wall=o["wall"], tons=tons,
                 tm_end=end, ect=st, kettle_in=end + R.uniform(20, 45), defect=R.random() < p,
                 kettle_start=None, kettle_end=None)
        bundles.append(b); yard.append(b)
        tm_log.setdefault((dd, s), {"tons": 0, "co": 0})["tons"] += tons
        tm_t = end
    else:
        now = gk_t
        while bd_i < len(bd) and bd[bd_i][1] <= now: bd_i += 1
        if bd_i < len(bd) and bd[bd_i][0] <= now < bd[bd_i][1]:
            stops.append((now, bd[bd_i][1], "BREAKDOWN")); gk_t = bd[bd_i][1]; continue
        blk = kettle_blocked(now)
        if blk:
            stops.append((now, blk[0], blk[1])); gk_t = blk[0]; continue
        b = pick_kettle(now)
        if b is not None:
            dur = b["tons"] / GK_RATE[b["wall"]] * 60 * R.uniform(0.97, 1.06)
            blk = kettle_blocked(now, dur)
            if blk:
                stops.append((now, blk[0], blk[1])); gk_t = blk[0]; continue
        if b is None:
            nxt = min([x["kettle_in"] for x in yard] + [tm_t + 1])
            nxt = max(nxt, now + 1)
            stops.append((now, nxt, "NO_MATERIAL")); gk_t = nxt; continue
        yard.remove(b)
        b["kettle_start"] = now; b["kettle_end"] = now + dur; gk_t = now + dur
        o = orders_by[b["order_id"]]
        if b["defect"]:
            b["inspection"] = "REJECT"
            remake_q.append((o, b["tons"]))
        else:
            b["inspection"] = "PASS"; o["remaining"] -= 1
            if o["remaining"] <= 0:
                extra = (1440 if o["threaded"] == "Y" else 480) * R.uniform(0.6, 1.2)
                o["shipped"] = now + dur + extra
# merge NO_MATERIAL fragments
ms = []
for s in sorted(stops):
    if ms and ms[-1][2] == s[2] and abs(ms[-1][1] - s[0]) < 0.01: ms[-1] = (ms[-1][0], s[1], s[2])
    else: ms.append(s)
stops = [s for s in ms if s[1] - s[0] >= 1]
# ---------- write ----------
os.makedirs(OUT, exist_ok=True)
fmt = lambda m: D(m).strftime("%Y-%m-%d %H:%M") if m is not None else ""
with open(os.path.join(OUT, "orders.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["order_id", "customer", "received", "due_date", "size", "wall", "tons", "threaded", "shipped"])
    for o in orders:
        w.writerow([o["order_id"], o["customer"], fmt(o["received"]), D(o["due"]).strftime("%Y-%m-%d"), o["size"], o["wall"], o["tons"], o["threaded"],
                    fmt(o["shipped"]) if o["shipped"] and o["shipped"] < M(END) else ""])
with open(os.path.join(OUT, "bundles.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["bundle_id", "order_id", "size", "wall", "tons", "tube_mill_end", "ect", "yard_in", "kettle_start", "kettle_end", "inspection"])
    for b in bundles:
        if b["tm_end"] >= M(END): continue
        ks = b["kettle_start"] if b["kettle_start"] is not None and b["kettle_start"] < M(END) else None
        ke = b["kettle_end"] if ks is not None and b["kettle_end"] < M(END) else None
        w.writerow([b["bundle_id"], b["order_id"], b["size"], b["wall"], b["tons"], fmt(b["tm_end"]), b["ect"], fmt(b["kettle_in"]),
                    fmt(ks), fmt(ke), b.get("inspection", "") if ke else ""])
with open(os.path.join(OUT, "kettle_stops.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["start", "end", "minutes", "reason"])
    for s in stops:
        if s[0] >= M(END): continue
        e = min(s[1], M(END)); w.writerow([fmt(s[0]), fmt(e), round(e - s[0]), s[2]])
with open(os.path.join(OUT, "tube_mill_shifts.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "shift", "crew", "ect", "tons", "changeovers"])
    day = T0
    while day < END:
        for s in "ABC":
            crew = "Y" if (s != "C" or (NIGHT_FROM <= day < PILOT)) else "N"
            rec = tm_log.get((day.date(), s), {"tons": 0, "co": 0})
            w.writerow([day.strftime("%Y-%m-%d"), s, crew, ect[(day.date(), s)] if crew == "Y" else "", round(rec["tons"], 1), rec["co"]])
        day += timedelta(days=1)
# management monthly KPI report (the digested view)
import collections
mon = collections.OrderedDict()
for b in bundles:
    if b["tm_end"] < M(END):
        k = D(b["tm_end"]).strftime("%Y-%m"); mon.setdefault(k, {"tm": 0, "gk": 0, "crew_h": 0})["tm"] += b["tons"]
for b in bundles:
    if b.get("kettle_end") and b["kettle_end"] < M(END) and b.get("inspection") == "PASS":
        mon[D(b["kettle_end"]).strftime("%Y-%m")]["gk"] += b["tons"]
for (dd, s_), v in tm_log.items(): pass
day = T0
while day < END:
    k = day.strftime("%Y-%m")
    mon[k]["crew_h"] += 24 if NIGHT_FROM <= day < PILOT else 16
    mon[k].setdefault("days", 0); mon[k]["days"] += 1
    day += timedelta(days=1)
STD_TM, STD_GK = 5.7, 3.75
with open(os.path.join(OUT, "kpi_monthly_report.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["month", "tube_mill_tons", "tube_mill_efficiency_pct", "kettle_good_tons", "kettle_efficiency_pct"])
    for k, v in mon.items():
        w.writerow([k, round(v["tm"]), round(100 * v["tm"] / (v["crew_h"] * STD_TM), 1), round(v["gk"]), round(100 * v["gk"] / (v["days"] * 24 * STD_GK), 1)])
with open(os.path.join(OUT, "finance.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["item", "value", "unit"])
    for r in [("selling_price", 415, "OMR/t"), ("steel_and_zinc_cost", 322, "OMR/t"), ("wip_material_cost", 296, "OMR/t"),
              ("night_shift_crew_cost", 9400, "OMR/month"), ("overtime_and_power_night", 3100, "OMR/month"),
              ("second_kettle_quote", 1450000, "OMR"), ("second_kettle_lead_time", 40, "weeks"),
              ("late_penalty_duqm", 0.5, "pct of order value per day late, max 10"),
              ("kettle_handover_overlap_cost", 1150, "OMR/month")]:
        w.writerow(r)
with open(os.path.join(OUT, "stations.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["item", "LIGHT", "MEDIUM", "HEAVY", "note"])
    w.writerow(["tube_mill_nominal_t_per_h"] + [TM_RATE[x] for x in WALLS] + ["forming and welding line"])
    w.writerow(["kettle_nominal_t_per_h"] + [GK_RATE[x] for x in WALLS] + ["hot-dip zinc kettle, one bundle at a time"])
    w.writerow(["kpi_standard_t_per_h", STD_TM, STD_GK, "", "tube mill, kettle (used by monthly KPI report)"])
    w.writerow(["tube_mill_changeover_min", CHANGEOVER, "", "", "size change"])
    w.writerow(["bundle_max_t", BUNDLE, "", "", ""])
    w.writerow(["kettle_handover_planned_min", 30, "", "", "three handovers a day at 06:00 14:00 22:00 until 2019-06-08"])
    w.writerow(["kettle_dross_cleaning_min", 40, "", "", "daily at 10:00"])
    w.writerow(["quoted_lead_time_days", 21, "", "", "due date = received + 21 days"])
print("orders", len(orders), "bundles", len(bundles), "stops", len(stops))
