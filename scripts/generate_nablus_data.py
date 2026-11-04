"""Case 1, Nablus sterilizer. Generates the raw data files.

The data is fictional. It is generated with a fixed seed, so every run gives the same files.
Story frame: Samer graduates from An-Najah National University in summer 2014 and joins the
maintenance department of a hospital in Nablus on 2014-09-14. He receives the records from
2013-09-01 to 2014-12-31 and installs an independent voltage recorder for four weeks.

Hidden mechanism (the answer the reader must find from the data):
- STER-01 and STER-02 sit on panel DB-A2, fed through the automatic transfer switch (ATS).
  A transfer to the generator cuts power for about 10 s. A transfer back to mains cuts it for
  under 1 s. A running cycle often aborts. The controller logs A02 POWER_INTERRUPT, and on
  restart the steam generator often raises A31. Technicians see A31 and write "scale".
- STER-03 sits on panel DB-B1 behind an online UPS. It rarely aborts.
- Weekly on-load generator tests start on Tuesday 2014-01-07 at 07:30, after the generator
  failed to start during the December 2013 storm. Failures rise from January 2014.
- Short mains sags (no outage, no generator) also trip DB-A2 machines (A01 UNDERVOLTAGE).
  Only the voltage recorder shows them.
- Feed water quality goes out of spec for three weeks in May 2014. It does not drive faults.

Usage: python3 scripts/generate_nablus_data.py
Writes the five CSV files into data/01-case-nablus-sterilizer/.
"""
import csv, math, os, random
from datetime import datetime, timedelta

SEED = 2014
rng = random.Random(SEED)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "01-case-nablus-sterilizer")
START, END = datetime(2013, 9, 1), datetime(2015, 1, 1)
TEST_FROM = datetime(2014, 1, 7, 7, 30)
REC_FROM, REC_TO = datetime(2014, 11, 9), datetime(2014, 12, 7)
M = lambda m: timedelta(minutes=m)
S = lambda s: timedelta(seconds=s)

DEVICES = {
    "STER-01": dict(panel="DB-A2", ups=False, hours=(6, 22), door=1 / 150, sensor=1 / 300),
    "STER-02": dict(panel="DB-A2", ups=False, hours=(6, 22), door=1 / 320, sensor=1 / 500),
    "STER-03": dict(panel="DB-B1", ups=True, hours=(7, 16), door=1 / 320, sensor=1 / 500),
}

# 1. Power events: outages, weekly tests, sags ---------------------------------------
def outage_rate(d):
    if d.month in (12, 1, 2): return 0.30
    if d.month in (7, 8): return 0.20
    return 0.10

gen_log, transfers, sags = [], [], []  # transfers: (time, kind, gap_seconds)
day = START
while day < END:
    n = 0
    lam, p, u = outage_rate(day), 1.0, rng.random()
    while True:  # Poisson count for the day
        p *= rng.random()
        if p < math.exp(-lam): break
        n += 1
    for _ in range(n):
        t = day + S(rng.randint(0, 86399))
        dur = M(max(3, rng.lognormvariate(math.log(25), 0.8)))
        gs = rng.uniform(3, 6); gap = rng.uniform(8, 14)
        gen_log += [(t, "MAINS_FAIL", ""), (t + S(gs), "GEN_START", ""), (t + S(gap), "ATS_TO_GEN", "")]
        transfers.append((t, "ATS_TO_GEN", gap))
        back = t + dur
        gen_log.append((back, "MAINS_RESTORED", ""))
        rt = back + S(300)
        g2 = rng.uniform(0.2, 0.8)
        gen_log += [(rt, "ATS_TO_MAINS", ""), (rt + S(180), "GEN_STOP", "cool-down")]
        transfers.append((rt, "ATS_TO_MAINS", g2))
    if day.weekday() == 1 and day >= TEST_FROM.replace(hour=0, minute=0):  # Tuesday test
        t = day + timedelta(hours=7, minutes=30) + S(rng.randint(-120, 300))
        gap = rng.uniform(1, 3)  # generator already running, short open transition
        gen_log += [(t - S(20), "GEN_START", "weekly on-load test"), (t, "ATS_TO_GEN", "weekly on-load test")]
        transfers.append((t, "ATS_TO_GEN", gap))
        rt = t + M(rng.uniform(28, 35))
        gen_log += [(rt, "ATS_TO_MAINS", "weekly on-load test"), (rt + S(180), "GEN_STOP", "weekly on-load test")]
        transfers.append((rt, "ATS_TO_MAINS", rng.uniform(0.2, 0.8)))
    if rng.random() < 0.07:  # mains sag, generator does not start
        t = day + S(rng.randint(6 * 3600, 23 * 3600))
        sags.append((t, rng.uniform(178, 194), rng.randint(1, 3)))
    day += timedelta(days=1)
gen_log.sort(); transfers.sort(); sags.sort()

# 2. Sterilizer operation, controller log, work orders --------------------------------
TECHS = ["T. Hamdan", "M. Odeh", "A. Shaker"]
MIS = [  # what technicians write after a power-triggered stop
    (0.50, "Steam generator fault, scale suspected", "Descaled steam generator", "Descaling agent", 120, (120, 240)),
    (0.15, "Door seal leak", "Replaced door gasket", "Door gasket", 450, (45, 90)),
    (0.15, "Temperature deviation", "Replaced PT100 sensor", "PT100 sensor", 380, (60, 120)),
    (0.15, "Controller error", "Reset controller, test cycle OK", "", 0, (10, 30)),
    (0.05, "Power problem", "Checked supply, test cycle OK", "", 0, (20, 40)),
]
GENUINE = {"A11": ("Door seal leak", "Replaced door gasket", "Door gasket", 450, (45, 90)),
           "A21": ("Temperature deviation", "Replaced PT100 sensor", "PT100 sensor", 380, (60, 120))}
ALARM_TEXT = {"A01": "UNDERVOLTAGE", "A02": "POWER_INTERRUPT", "A11": "DOOR_SEAL_PRESSURE",
              "A21": "TEMP_SENSOR_DEVIATION", "A31": "STEAM_GEN_LOW_LEVEL"}

def response(t):  # day shift Sat to Thu, 07:00 to 15:00
    on_shift = t.weekday() != 4 and 7 <= t.hour < 15
    return M(rng.uniform(15, 90) if on_shift else rng.uniform(60, 300))

ctrl, wos = [], []
wo_no = 1
for dev, cfg in DEVICES.items():
    genuine = []
    for code, rate in (("A11", cfg["door"]), ("A21", cfg["sensor"])):
        t = START
        while True:
            t += timedelta(days=rng.expovariate(rate))
            if t >= END: break
            genuine.append((t, code))
    genuine.sort()
    events = [(t, "T", k, g) for t, k, g in transfers] + [(t, "S", v, n) for t, v, n in sags] + [(t, "G", c, 0) for t, c in genuine]
    events.sort(key=lambda e: e[0])
    ei = 0
    pending = None  # genuine fault that happened while idle, shows at the next cycle
    busy_until = START
    day = START
    while day < END:
        h0, h1 = cfg["hours"]
        if day.weekday() == 4: h1 = h0 + 6  # Friday, short day
        t = day + timedelta(hours=h0) + M(rng.uniform(0, 20))
        day_end = day + timedelta(hours=h1)
        while t < day_end:
            if t < busy_until:
                t = busy_until + M(rng.uniform(5, 20)); continue
            dur = M(rng.gauss(58, 4)); end = t + dur
            # idle events before this cycle: log power-on for DB-A2 machines
            while ei < len(events) and events[ei][0] < t:
                et, typ, k, g = events[ei]
                if typ == "T" and k == "ATS_TO_GEN" and not cfg["ups"]:
                    ctrl.append((et + S(g), dev, "I01", "POWER_ON", ""))
                if typ == "G": pending = k
                ei += 1
            ctrl.append((t, dev, "C10", "CYCLE_START", "134C 4 min"))
            stop = None
            if pending:
                stop, pending = (t + M(rng.uniform(3, 15)), pending), None
            while ei < len(events) and events[ei][0] < end:
                et, typ, k, g = events[ei]; ei += 1
                if stop: continue
                if typ == "T":
                    p = 0.03 if cfg["ups"] else (0.85 if k == "ATS_TO_GEN" else 0.25)
                    if rng.random() < p: stop = (et + S(g), "A02")
                elif typ == "S":
                    if not cfg["ups"] and k < 196 and rng.random() < 0.5: stop = (et + S(rng.uniform(1, 40)), "A01")
                else:
                    stop = (et, k)
            if not stop:
                ctrl.append((end, dev, "C11", "CYCLE_COMPLETE", "")); t = end + M(rng.uniform(10, 35)); continue
            st, code = stop
            ctrl.append((st, dev, code, ALARM_TEXT[code], ""))
            ctrl.append((st + S(2), dev, "C19", "CYCLE_ABORTED", ""))
            last = st
            if code in ("A01", "A02"):
                a31 = rng.random() < 0.6
                if a31:
                    last = st + M(rng.uniform(2, 6))
                    ctrl.append((last, dev, "A31", ALARM_TEXT["A31"], "heater locked out"))
                need_tech = a31 or rng.random() < 0.3
                if need_tech:
                    r = rng.random(); acc = 0
                    for w, fault, action, part, cost, rep in MIS:
                        acc += w
                        if r < acc: break
                    if action.startswith("Descaled") and rng.random() < 0.1:
                        action, part, cost = "Replaced steam generator heater element", "Heater element 9 kW", 900
            else:
                need_tech = True
                fault, action, part, cost, rep = GENUINE[code]
            if need_tech:
                rep_at = last + M(rng.uniform(5, 40))
                rs = rep_at + response(rep_at)
                re = rs + M(rng.uniform(*rep))
                wos.append(dict(wo_id=f"WO-{wo_no:05d}", wo_type="CM", device_id=dev, reported_at=rep_at,
                                reported_fault=fault, technician=rng.choice(TECHS), repair_start=rs,
                                repair_end=re, action_taken=action, parts_used=part, parts_cost_ils=cost))
                wo_no += 1
                ctrl.append((re - M(1), dev, "C90", "SERVICE_RESET", ""))
                busy_until = re
                t = re + M(rng.uniform(5, 20))
            else:
                t = last + M(rng.uniform(5, 15))
        day += timedelta(days=1)
    while ei < len(events):  # trailing idle events
        et, typ, k, g = events[ei]; ei += 1
        if typ == "T" and k == "ATS_TO_GEN" and not cfg["ups"]:
            ctrl.append((et + S(g), dev, "I01", "POWER_ON", ""))
    # quarterly preventive maintenance
    for pm in (datetime(2013, 10, 15), datetime(2014, 1, 14), datetime(2014, 4, 15), datetime(2014, 7, 15), datetime(2014, 10, 14)):
        rs = pm + timedelta(hours=15, minutes=30) + M(rng.uniform(0, 30)); re = rs + M(rng.uniform(150, 210))
        wos.append(dict(wo_id="", wo_type="PM", device_id=dev, reported_at=rs, reported_fault="Quarterly PM",
                        technician=rng.choice(TECHS), repair_start=rs, repair_end=re,
                        action_taken="PM checklist, Bowie-Dick test OK", parts_used="Door gasket", parts_cost_ils=450))

wos.sort(key=lambda w: w["reported_at"])
for i, w in enumerate(wos, 1): w["wo_id"] = f"WO-{i:05d}"
ctrl.sort()

# 3. Independent voltage recorder at STER-01 outlet, 1-minute values ------------------
rec = []
gen_on = []  # intervals on generator
cur = None
for t, k, g in transfers:
    if k == "ATS_TO_GEN": cur = t
    elif cur: gen_on.append((cur, t)); cur = None
t = REC_FROM; ti = si = gi = 0
while t < REC_TO:
    nxt = t + M(1)
    hr = t.hour + t.minute / 60
    base = 229 - 7 * math.exp(-((hr - 19.5) ** 2) / 4) + rng.gauss(0, 1.5)
    while gi < len(gen_on) and gen_on[gi][1] < t: gi += 1
    on_gen = gi < len(gen_on) and gen_on[gi][0] <= t < gen_on[gi][1]
    if on_gen: base = 224 + rng.gauss(0, 3)
    vmin, vmax, avg = base - rng.uniform(1, 4), base + rng.uniform(1, 4), base
    if on_gen: vmin, vmax = base - rng.uniform(4, 10), base + rng.uniform(4, 9)
    while ti < len(transfers) and transfers[ti][0] < t: ti += 1
    j = ti
    while j < len(transfers) and transfers[j][0] < nxt:
        _, k, g = transfers[j]; j += 1
        vmin = 0.0
        vmax = max(vmax, rng.uniform(248, 262) if k == "ATS_TO_GEN" else rng.uniform(242, 255))
        avg = base * (60 - g) / 60
    while si < len(sags) and sags[si][0] + M(sags[si][2]) < t: si += 1
    j = si
    while j < len(sags) and sags[j][0] < nxt:
        st, v, n = sags[j]; j += 1
        if st <= nxt and t < st + M(n):
            vmin = min(vmin, v + rng.uniform(-1, 1)); avg = min(avg, v + rng.uniform(4, 9))
    rec.append((t, round(vmin, 1), round(avg, 1), round(vmax, 1)))
    t = nxt

# 4. Weekly feed water tests -----------------------------------------------------------
water = []
d = START + timedelta(days=(6 - START.weekday()) % 7)  # first Sunday
while d < END:
    for point in ("RO-A", "RO-B"):
        bad = point == "RO-A" and datetime(2014, 5, 4) <= d <= datetime(2014, 5, 18)
        cond = rng.uniform(7.5, 11.0) if bad else rng.uniform(1.8, 4.6)
        hard = rng.uniform(0.028, 0.045) if bad else rng.uniform(0.004, 0.017)
        water.append((d.date().isoformat(), point, round(cond, 1), round(hard, 3),
                      round(rng.uniform(5.6, 6.8), 1), round(rng.uniform(0.3, 1.6) * (3 if bad else 1), 1), "Hospital lab"))
    d += timedelta(days=7)

# 5. Write files -----------------------------------------------------------------------
os.makedirs(OUT, exist_ok=True)
fmt = lambda t: t.strftime("%Y-%m-%d %H:%M:%S")
def write(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(header); w.writerows(rows)
    print(f"{name}: {len(rows)} rows")
write("work_orders.csv", ["wo_id", "wo_type", "device_id", "reported_at", "reported_fault", "technician",
                          "repair_start", "repair_end", "action_taken", "parts_used", "parts_cost_ils"],
      [[w["wo_id"], w["wo_type"], w["device_id"], fmt(w["reported_at"]), w["reported_fault"], w["technician"],
        fmt(w["repair_start"]), fmt(w["repair_end"]), w["action_taken"], w["parts_used"], w["parts_cost_ils"]] for w in wos])
write("generator_switch_log.csv", ["timestamp", "event", "note"], [[fmt(t), e, n] for t, e, n in gen_log])
write("controller_events.csv", ["timestamp", "device_id", "code", "message", "detail"], [[fmt(t), dv, c, m, x] for t, dv, c, m, x in ctrl])
write("voltage_recorder.csv", ["timestamp", "v_min", "v_avg", "v_max"], [[fmt(t), a, b, c] for t, a, b, c in rec])
write("water_tests.csv", ["sample_date", "sample_point", "conductivity_us_cm", "hardness_mmol_l", "ph", "chloride_mg_l", "lab"], water)
