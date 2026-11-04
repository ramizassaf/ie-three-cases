"""Case 1. MTBF, MTTR and availability on scheduled operating hours, not calendar hours.
Operating window from the hospital roster: Saturday to Thursday 06:00-22:00, Friday 06:00-12:00."""
import csv, os
from datetime import datetime, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "01-case-nablus-sterilizer")
P = lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
START, END = datetime(2013, 9, 1), datetime(2015, 1, 1)
wo = [w for w in csv.DictReader(open(os.path.join(D, "work_orders.csv"))) if w["wo_type"] == "CM"]
def in_window(t): return 6 <= t.hour < (12 if t.weekday() == 4 else 22)
def window_hours(a, b):
    tot, t = 0, a
    while t < b:
        nt = min(b, t + timedelta(minutes=1))
        if in_window(t): tot += (nt - t).total_seconds() / 3600
        t = nt
    return tot
cal = (END - START).total_seconds() / 3600
op = window_hours(START, END)
print(f"calendar hours {cal:.0f}  scheduled operating hours {op:.0f}  ratio {op / cal:.3f}")
print("device | failures | MTBF calendar h | MTBF operating h | MTBF operating days(16h) | MTTR clock h | downtime in window h | availability calendar | availability operating")
for d in ("STER-01", "STER-02", "STER-03"):
    ws = [w for w in wo if w["device_id"] == d]; n = len(ws)
    mttr = sum((P(w["repair_end"]) - P(w["reported_at"])).total_seconds() / 3600 for w in ws) / n
    dw = sum(window_hours(P(w["reported_at"]), P(w["repair_end"])) for w in ws)
    print(f"{d} | {n} | {cal / n:.1f} | {op / n:.1f} | {op / n / 16:.1f} | {mttr:.2f} | {dw:.0f} | {100 * (cal / n) / (cal / n + mttr):.1f}% | {100 * (1 - dw / op):.2f}%")
