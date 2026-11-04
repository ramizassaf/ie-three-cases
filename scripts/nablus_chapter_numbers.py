"""Case 1, Nablus sterilizer. Numbers for the chapter draft beyond the six checks.

Reads the raw files in data/01-case-nablus-sterilizer/ and prints every extra number used in
the scene, the raw data section, the decision points, the endings and the three measures.
Root alarm rule is the same as in nablus_checks.py: last primary alarm (A01, A02, A11, A21)
in the 3 hours before the work order report.
Usage: python3 scripts/nablus_chapter_numbers.py
"""
import csv, os
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "01-case-nablus-sterilizer")
P = lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
read = lambda n: list(csv.DictReader(open(os.path.join(DATA, n), encoding="utf-8")))
START, END = datetime(2013, 9, 1), datetime(2015, 1, 1)
JOIN = datetime(2014, 9, 14)
DEVS = ["STER-01", "STER-02", "STER-03"]
A = ["STER-01", "STER-02"]
H = lambda td: td.total_seconds() / 3600

allwo = read("work_orders.csv")
for w in allwo:
    for k in ("reported_at", "repair_start", "repair_end"): w[k] = P(w[k])
    w["parts_cost_ils"] = int(w["parts_cost_ils"])
wo = [w for w in allwo if w["wo_type"] == "CM"]
pm = [w for w in allwo if w["wo_type"] == "PM"]
ctrl = read("controller_events.csv")
for c in ctrl: c["t"] = P(c["timestamp"])
gen = read("generator_switch_log.csv")
for g in gen: g["t"] = P(g["timestamp"])
transfers = [g for g in gen if g["event"].startswith("ATS_TO")]
tt = [g["t"] for g in transfers]
tests = [g for g in transfers if g["note"] == "weekly on-load test"]
rec = read("voltage_recorder.csv")
water = read("water_tests.csv")

alarms = defaultdict(list)
for c in ctrl:
    if c["code"] in ("A01", "A02", "A11", "A21"): alarms[c["device_id"]].append(c)
for w in wo:
    cand = [a for a in alarms[w["device_id"]] if w["reported_at"] - timedelta(hours=3) <= a["t"] <= w["reported_at"]]
    w["root"] = cand[-1]["code"] if cand else "none"
    w["root_t"] = cand[-1]["t"] if cand else None
    w["test"] = bool(w["root_t"]) and any(abs((w["root_t"] - g["t"]).total_seconds()) <= 60 for g in tests)
    w["down_h"] = H(w["repair_end"] - w["reported_at"])
    w["tech_h"] = H(w["repair_end"] - w["repair_start"])
power = lambda w: w["root"] in ("A01", "A02")

def head(n, title):
    print(f"\n{'=' * 70}\n{n}: {title}\n{'=' * 70}")

def summary(ws, label):
    print(f"{label}: {len(ws)} CM work orders, {sum(w['down_h'] for w in ws):.0f} down h, "
          f"{sum(w['tech_h'] for w in ws):.0f} technician h, {sum(w['parts_cost_ils'] for w in ws)} ILS parts.")

# N1 -------------------------------------------------------------------------------------
head("N1", "record size and cycles per device")
print(f"Work orders: {len(allwo)} ({len(wo)} CM, {len(pm)} PM). PM parts cost: {sum(w['parts_cost_ils'] for w in pm)} ILS.")
cyc = Counter((c["device_id"], c["code"]) for c in ctrl)
print(f"{'Device':8} {'started':>8} {'complete':>9} {'aborted':>8} {'abort %':>8}")
for d in DEVS:
    s, ok, ab = cyc[(d, "C10")], cyc[(d, "C11")], cyc[(d, "C19")]
    print(f"{d:8} {s:>8} {ok:>9} {ab:>8} {ab / s:>8.1%}")
summary(wo, "All CM")
summary([w for w in wo if w["device_id"] in A], "STER-01 and STER-02 CM")
cost_all = Counter()
for w in wo: cost_all[w["parts_used"] or "(no part)"] += w["parts_cost_ils"]
print("CM parts cost by part (ILS): " + ", ".join(f"{k} {v}" for k, v in cost_all.most_common()))
ev = Counter(g["event"] for g in gen)
print(f"Generator log: {len(gen)} rows. MAINS_FAIL {ev['MAINS_FAIL']}, ATS_TO_GEN {ev['ATS_TO_GEN']}, "
      f"ATS_TO_MAINS {ev['ATS_TO_MAINS']}, weekly test transfers {len(tests)}.")

# N2 -------------------------------------------------------------------------------------
head("N2", "what Samer finds on his first day (records up to 2014-09-13)")
before = [w for w in wo if w["reported_at"] < JOIN]
for d in DEVS:
    print(f"{d}: {sum(1 for w in before if w['device_id'] == d)} CM work orders before {JOIN.date()}")
ytd = [w for w in before if w["reported_at"] >= datetime(2014, 1, 1)]
summary(ytd, "2014-01-01 to 2014-09-13")
sc = sum(1 for w in ytd if w["reported_fault"].startswith("Steam generator"))
print(f"Of these, written as steam generator or scale: {sc} ({sc / len(ytd):.0%}).")
desc = [w for w in before if w["parts_used"] == "Descaling agent"]
heat = [w for w in before if w["parts_used"] == "Heater element 9 kW"]
print(f"Descaling jobs before join: {len(desc)}. Heater elements replaced before join: {len(heat)}.")

# N3 -------------------------------------------------------------------------------------
head("N3", "CM work orders per month, STER-01 + STER-02 and STER-03")
m = Counter((w["reported_at"].strftime("%Y-%m"), w["device_id"] in A) for w in wo)
months = sorted({k[0] for k in m} | {f"{y}-{mm:02d}" for y, mm in [(2013, 9), (2013, 10), (2013, 11), (2013, 12)] + [(2014, i) for i in range(1, 13)]})
for mo in months:
    print(f"{mo}  DB-A2 {m[(mo, True)]:>3}  STER-03 {m[(mo, False)]:>2}")

# N4 -------------------------------------------------------------------------------------
head("N4", "one incident traced through three files")
case = next(w for w in wo if w["reported_at"] >= JOIN and w["test"] and w["reported_fault"].startswith("Steam"))
t0 = case["root_t"]
print(f"Work order {case['wo_id']} {case['device_id']} reported {case['reported_at']} fault '{case['reported_fault']}' "
      f"action '{case['action_taken']}' part '{case['parts_used']}' {case['parts_cost_ils']} ILS, "
      f"repair {case['repair_start']} to {case['repair_end']}, technician {case['technician']}.")
print("Generator log, 2 minutes before to 40 minutes after the root alarm:")
for g in gen:
    if t0 - timedelta(minutes=2) <= g["t"] <= t0 + timedelta(minutes=40): print(f"  {g['timestamp']}  {g['event']:15} {g['note']}")
print(f"Controller log for {case['device_id']}, 70 minutes before the alarm to repair end:")
for c in ctrl:
    if c["device_id"] == case["device_id"] and t0 - timedelta(minutes=70) <= c["t"] <= case["repair_end"]:
        print(f"  {c['timestamp']}  {c['code']}  {c['message']:22} {c['detail']}")
print(f"Weekday of the incident: {t0.strftime('%A')}.")

# N5 -------------------------------------------------------------------------------------
head("N5", "the Tuesday morning window")
tue_win = [w for w in wo if w["device_id"] in A and w["test"]]
summary(tue_win, "Root alarm within 60 s of a weekly test transfer")
print(f"Weekly tests in the log: {len(tests) // 2} Tuesdays, {len(tests)} transfers.")
first = [g for g in tests if g["event"] == "ATS_TO_GEN"]
print(f"First test {first[0]['timestamp']}. Test start times range {min(g['t'].strftime('%H:%M') for g in first)} to {max(g['t'].strftime('%H:%M') for g in first)}.")
running = 0
for g in first:  # was a DB-A2 cycle running at the test transfer?
    for d in A:
        st = [c for c in ctrl if c["device_id"] == d and c["code"] in ("C10", "C11", "C19") and c["t"] <= g["t"]]
        if st and st[-1]["code"] == "C10": running += 1
print(f"DB-A2 machine-transfers with a cycle running at the ATS_TO_GEN test transfer: {running} of {2 * len(first)}.")

# N6 -------------------------------------------------------------------------------------
head("N6", "what each ending removes, based on the past record (STER-01 + STER-02)")
aw = [w for w in wo if w["device_id"] in A]
summary(aw, "Baseline")
summary([w for w in aw if power(w)], "E1 new sterilizer on DB-A2 keeps these power stops")
summary([w for w in aw if w["parts_used"] == "Descaling agent"], "E2 water and descaling fixes target these jobs")
print(f"  of which root alarm is power: {sum(1 for w in aw if w['parts_used'] == 'Descaling agent' and power(w))}")
summary([w for w in aw if w["test"]], "E4 move weekly test out of operating hours removes")
summary([w for w in aw if power(w)], "E5 online UPS on DB-A2 removes")
summary([w for w in aw if not power(w)], "Left after E5 (door and sensor faults)")
s3 = [w for w in wo if w["device_id"] == "STER-03"]
summary(s3, "STER-03 behind UPS, for comparison")
s2 = [w for w in wo if w["device_id"] == "STER-02"]; s1 = [w for w in wo if w["device_id"] == "STER-01"]
print(f"STER-01 (2005) power-root CM: {sum(1 for w in s1 if power(w))}. STER-02 (2011) power-root CM: {sum(1 for w in s2 if power(w))}.")

# N7 -------------------------------------------------------------------------------------
head("N7", "three measures inputs, STER-01 + STER-02")
ok = sum(cyc[(d, "C11")] for d in A)
# cycle rate: completed cycles per operating hour, operating hours from first C10 to last C11/C19 each day
day_span = defaultdict(lambda: [None, None])
for c in ctrl:
    if c["device_id"] in A and c["code"] in ("C10", "C11", "C19"):
        k = (c["device_id"], c["t"].date()); s = day_span[k]
        if s[0] is None or c["t"] < s[0]: s[0] = c["t"]
        if s[1] is None or c["t"] > s[1]: s[1] = c["t"]
op_h = sum(H(b - a) for a, b in day_span.values())
rate = ok / op_h
print(f"Completed cycles: {ok}. Operating hours: {op_h:.0f}. Rate: {rate:.2f} completed cycles per operating hour.")
def op_overlap(w):  # down hours inside the device's operating window (06:00 to 22:00, Friday 06:00 to 12:00)
    tot, t = 0.0, w["reported_at"]
    while t < w["repair_end"]:
        nt = min(w["repair_end"], t + timedelta(minutes=1))
        h1 = 12 if t.weekday() == 4 else 22
        if 6 <= t.hour < h1: tot += H(nt - t)
        t = nt
    return tot
pw = [w for w in aw if power(w)]
lost_dn = sum(op_overlap(w) for w in pw)
ab = sum(1 for c in ctrl if c["device_id"] in A and c["code"] == "C19")
print(f"Power-root CM down hours inside operating window: {lost_dn:.0f}. Cycles lost to that downtime: {lost_dn * rate:.0f}.")
print(f"Aborted cycles STER-01 + STER-02 (all causes): {ab}. Total lost cycles: {ab + lost_dn * rate:.0f} "
      f"({(ab + lost_dn * rate) / (ok + ab + lost_dn * rate):.1%} of the cycles the two machines would have completed).")
pwt = [w for w in aw if w["test"]]
lt = sum(op_overlap(w) for w in pwt)
abt = sum(1 for w in pwt)  # each test-driven CM aborted one cycle
print(f"Test-driven: {lt:.0f} down h in operating window, {lt * rate + abt:.0f} lost cycles.")
print(f"Parts bought for power stops (inventory spent on the wrong cause): {sum(w['parts_cost_ils'] for w in pw)} ILS.")
print(f"Technician hours on power stops: {sum(w['tech_h'] for w in pw):.0f} h. "
      f"Of these outside day shift (not Sat to Thu 07:00 to 15:00): "
      f"{sum(w['tech_h'] for w in pw if w['repair_start'].weekday() == 4 or not 7 <= w['repair_start'].hour < 15):.0f} h.")

# N8 -------------------------------------------------------------------------------------
head("N8", "recorder rows around one STER-01 undervoltage stop and one test transfer")
for c in ctrl:
    if c["device_id"] == "STER-01" and c["code"] == "A01" and datetime(2014, 11, 9) <= c["t"] < datetime(2014, 12, 7):
        a01 = c; break
first_test = next(g for g in tests if g["event"] == "ATS_TO_GEN" and g["t"] >= datetime(2014, 11, 9))
for label, t0 in (("A01 at " + a01["timestamp"], a01["t"]), ("Test transfer at " + first_test["timestamp"], first_test["t"])):
    print(label)
    near = [g for g in gen if abs((g["t"] - t0).total_seconds()) <= 600]
    print("  generator events within 10 min: " + (", ".join(f"{g['timestamp']} {g['event']}" for g in near) or "none"))
    tm = t0.replace(second=0)
    for r in rec:
        if tm - timedelta(minutes=2) <= P(r["timestamp"]) <= tm + timedelta(minutes=2):
            print(f"  {r['timestamp']}  {r['v_min']:>6} {r['v_avg']:>6} {r['v_max']:>6}")

# N9 -------------------------------------------------------------------------------------
head("N9", "load by weekday and the source of each power stop (STER-01 + STER-02)")
days = ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]
cw = Counter(c["t"].strftime("%a") for c in ctrl if c["device_id"] in A and c["code"] == "C10")
ww = Counter(w["reported_at"].strftime("%a") for w in aw)
print(f"{'Day':4} {'cycles':>7} {'CM':>4} {'CM per 1000 cycles':>19}")
for d in days:
    print(f"{d:4} {cw[d]:>7} {ww[d]:>4} {1000 * ww[d] / cw[d]:>19.1f}")
tue = [w for w in aw if w["reported_at"].strftime("%a") == "Tue"]
print(f"Tuesday CM: {len(tue)}. Root alarm within 60 s of a weekly test transfer: {sum(1 for w in tue if w['test'])}.")
src = Counter()
for w in aw:
    if not power(w): src["door or sensor"] += 1
    elif w["test"]: src["weekly test transfer"] += 1
    elif w["root"] == "A02": src["unplanned outage transfer"] += 1
    else: src["mains sag, no transfer (A01)"] += 1
print("Source of STER-01 + STER-02 CM work orders: " + ", ".join(f"{k} {v}" for k, v in src.most_common()))
