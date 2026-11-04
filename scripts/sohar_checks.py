"""All numbers quoted in chapter 3 (Sohar). Reads data/03-case-sohar-flow only."""
import pandas as pd, numpy as np, os
d = os.path.join(os.path.dirname(__file__), "..", "data", "03-case-sohar-flow") + "/"
o = pd.read_csv(d + "orders.csv", parse_dates=["received", "due_date", "shipped"])
b = pd.read_csv(d + "bundles.csv", parse_dates=["tube_mill_end", "yard_in", "kettle_start", "kettle_end"])
s = pd.read_csv(d + "kettle_stops.csv", parse_dates=["start", "end"])
tm = pd.read_csv(d + "tube_mill_shifts.csv", parse_dates=["date"])
kpi = pd.read_csv(d + "kpi_monthly_report.csv")
fin = pd.read_csv(d + "finance.csv").set_index("item").value
P = {"P1 two shifts": ("2019-01-06", "2019-03-01"), "P2 night shift": ("2019-03-01", "2019-06-09"),
     "P3 pilot drain": ("2019-06-09", "2019-07-01"), "P4 after": ("2019-07-01", "2019-09-01")}
P = {k: (pd.Timestamp(a), pd.Timestamp(z)) for k, (a, z) in P.items()}
def pr(*a): print(*a)
pr("== files"); [pr(f, len(pd.read_csv(d + f))) for f in sorted(os.listdir(d)) if f.endswith(".csv")]
pr("orders", len(o), "tons", round(o.tons.sum()), "bundles", len(b))
pr("\n== 0 KPI report"); pr(kpi.to_string(index=False))
# time-average yard WIP (tons), hourly grid
grid = pd.date_range("2019-01-01", "2019-09-01", freq="h", inclusive="left")
yi = b.yard_in.values.astype("datetime64[h]"); ks = b.kettle_start.fillna(pd.Timestamp("2030-01-01")).values.astype("datetime64[h]")
add = pd.Series(b.tons.values, index=yi).groupby(level=0).sum().reindex(grid, fill_value=0)
rem = pd.Series(b.tons.values, index=ks).groupby(level=0).sum().reindex(grid, fill_value=0)
yard = (add - rem).cumsum()
# tube mill queue: tons of orders received but not yet started at tube mill (order granularity, remaining tons approx)
first = b.groupby("order_id").tube_mill_end.min()
def tmq(t):
    w = o[(o.received <= t) & (o.order_id.map(first) > t)]; return w.tons.sum()
good = b[b.inspection == "PASS"]; rej = b[b.inspection == "REJECT"]
pr("\n== 1 Little's law by period")
pr("period | good t/day | tube mill t/day | avg yard WIP t | avg yard wait d | WIP/thru d | mean order LT d | on-time % | orders shipped")
o["leadtime"] = (o.shipped - o.received).dt.total_seconds() / 86400
o["late_days"] = ((o.shipped.dt.normalize() - o.due_date).dt.days).clip(lower=0)
for k, (a, z) in P.items():
    days = (z - a).days
    g = good[(good.kettle_end >= a) & (good.kettle_end < z)].tons.sum() / days
    t_ = b[(b.tube_mill_end >= a) & (b.tube_mill_end < z)].tons.sum() / days
    wip = yard[(yard.index >= a) & (yard.index < z)].mean()
    bb = b[(b.kettle_start >= a) & (b.kettle_start < z)]
    wait = ((bb.kettle_start - bb.yard_in).dt.total_seconds() / 86400)
    wt = (wait * bb.tons).sum() / bb.tons.sum()
    sh = o[(o.shipped >= a) & (o.shipped < z)]
    pr(k, "|", round(g, 1), "|", round(t_, 1), "|", round(wip), "|", round(wt, 2), "|", round(wip / g, 2), "|", round(sh.leadtime.mean(), 1), "|", round(100 * (sh.late_days == 0).mean(), 1), "|", len(sh))
a, z = pd.Timestamp("2019-01-01"), pd.Timestamp("2019-09-01")
bb = b[b.kettle_start.notna()]
lam = bb.tons.sum() / ((z - a).days)
Wd = ((bb.kettle_start - bb.yard_in).dt.total_seconds() / 86400 * bb.tons).sum() / bb.tons.sum()
pr("Little check whole period: avg yard", round(yard.mean(), 1), "lambda t/day", round(lam, 1), "W days", round(Wd, 3), "lambda*W", round(lam * Wd, 1))
pr("yard WIP at", {str(t.date()): round(yard[t]) for t in pd.to_datetime(["2019-02-28 23:00", "2019-03-31 23:00", "2019-04-14 08:00", "2019-05-31 23:00", "2019-06-08 23:00", "2019-06-30 23:00", "2019-08-31 23:00"])})
pr("max yard WIP", round(yard.max()), yard.idxmax())
pr("tube mill queue t at", {t: round(tmq(pd.Timestamp(t))) for t in ["2019-02-14", "2019-02-28", "2019-03-10", "2019-04-14", "2019-06-20", "2019-06-30", "2019-07-31"]})
pr("\n== 1b monthly series (for chart)")
for mth in pd.period_range("2019-01", "2019-08", freq="M"):
    a, z = mth.start_time, (mth + 1).start_time
    pr(mth, "tm", round(b[(b.tube_mill_end >= a) & (b.tube_mill_end < z)].tons.sum() / mth.days_in_month, 1),
       "good", round(good[(good.kettle_end >= a) & (good.kettle_end < z)].tons.sum() / mth.days_in_month, 1),
       "orders_in", round(o[(o.received >= a) & (o.received < z)].tons.sum() / mth.days_in_month, 1),
       "yard_end", round(yard[z - pd.Timedelta(hours=1)]))
pr("\n== 2 utilisation P2 (tube mill vs kettle)")
a, z = P["P2 night shift"]
crew_h = tm[(tm.date >= a) & (tm.date < z) & (tm.crew == "Y")].shape[0] * 8
tmb = b[(b.tube_mill_end >= a) & (b.tube_mill_end < z)]
st = pd.read_csv(d + "stations.csv").set_index("item")
RATE = st.loc["tube_mill_nominal_t_per_h", ["LIGHT", "MEDIUM", "HEAVY"]].astype(float).to_dict()
pr("note: tube-mill busy hours estimated from tons/nominal rate")
tm_busy = (tmb.tons / tmb.wall.map(RATE)).sum()
co = tm[(tm.date >= a) & (tm.date < z)].changeovers.sum() * 75 / 60
pr("tube mill crew hours", crew_h, "making pipe h", round(tm_busy), "changeover h", round(co), "share making", round(100 * tm_busy / crew_h, 1), "share making+co", round(100 * (tm_busy + co) / crew_h, 1))
kb = b[(b.kettle_start >= a) & (b.kettle_start < z)]
dip = ((kb.kettle_end - kb.kettle_start).dt.total_seconds() / 3600)
hours = (z - a).days * 24
pr("kettle hours", hours, "dipping", round(dip.sum()), "share", round(100 * dip.sum() / hours, 1))
ss = s[(s.start >= a) & (s.start < z)]
pr("tube mill idle h", round(crew_h - tm_busy - co), "share", round(100 * (crew_h - tm_busy - co) / crew_h, 1), "kettle non-dip h", round(hours - dip.sum()))
pr("kettle NO_MATERIAL h in P2", round(ss[ss.reason == "NO_MATERIAL"].minutes.sum() / 60, 1))
pr("\n== 3 kettle time budget, hours per day")
for k in ["P1 two shifts", "P2 night shift", "P3 pilot drain", "P4 after"]:
    a, z = P[k]; days = (z - a).days
    kb = b[(b.kettle_start >= a) & (b.kettle_start < z)]
    dh = (kb.kettle_end - kb.kettle_start).dt.total_seconds() / 3600
    ss = s[(s.start >= a) & (s.start < z)]
    row = {"good dip": dh[kb.inspection == "PASS"].sum() / days, "reject dip": dh[kb.inspection == "REJECT"].sum() / days}
    for r in ["SHIFT_HANDOVER", "DROSS_CLEANING", "BREAKDOWN", "NO_MATERIAL"]:
        row[r] = ss[ss.reason == r].minutes.sum() / 60 / days
    pr(k, {x: round(v, 2) for x, v in row.items()}, "sum", round(sum(row.values()), 2))
a, z = P["P2 night shift"]
ss = s[(s.start >= a) & (s.start < z) & (s.reason == "SHIFT_HANDOVER")]
pr("handover stops P2: count", len(ss), "mean min", round(ss.minutes.mean(), 1), "planned 30 min x3 = 1.5 h/day")
kb = b[(b.kettle_start >= a) & (b.kettle_start < z) & b.kettle_end.notna()]
rate = kb.tons.sum() / ((kb.kettle_end - kb.kettle_start).dt.total_seconds() / 3600).sum()
pr("kettle mean rate t/h P2", round(rate, 2))
pr("\n== 4 ECT")
bb = b[b.inspection.isin(["PASS", "REJECT"])]
for k in ["P1 two shifts", "P2 night shift", "P4 after"]:
    a, z = P[k]; x = bb[(bb.tube_mill_end >= a) & (bb.tube_mill_end < z)]
    pr(k, "ect OFF share of bundles", round(100 * (x.ect == "OFF").mean(), 1))
for st in ["ON", "OFF"]:
    x = bb[(bb.ect == st) & (bb.tube_mill_end < P["P3 pilot drain"][0])]
    pr("reject rate ECT", st, "bundles", len(x), "rejects", (x.inspection == "REJECT").sum(), "pct", round(100 * (x.inspection == "REJECT").mean(), 2))
t2 = tm[(tm.date >= P["P2 night shift"][0]) & (tm.date < P["P2 night shift"][1]) & (tm.crew == "Y")]
pr("P2 ECT OFF share by shift", (100 * (t2.ect == "OFF").groupby(t2["shift"]).mean()).round(1).to_dict())
t1 = tm[(tm.date >= P["P1 two shifts"][0]) & (tm.date < P["P1 two shifts"][1]) & (tm.crew == "Y")]
pr("P1 ECT OFF share of shifts", round(100 * (t1.ect == "OFF").mean(), 1))
a, z = P["P2 night shift"]; x = b[(b.kettle_start >= a) & (b.kettle_start < z) & (b.inspection == "REJECT")]
pr("P2 rejects: bundles", len(x), "tons", round(x.tons.sum()), "kettle hours", round(((x.kettle_end - x.kettle_start).dt.total_seconds() / 3600).sum(), 1),
   "per day", round(((x.kettle_end - x.kettle_start).dt.total_seconds() / 3600).sum() / (z - a).days, 2))
pr("\n== 5 yard picking (LIFO)")
for k in ["P2 night shift", "P4 after"]:
    a, z = P[k]; newest = 0; tot = 0; oldest = 0
    kb = b[(b.kettle_start >= a) & (b.kettle_start < z)].sort_values("kettle_start")
    for _, r in kb.iterrows():
        q = b[(b.yard_in <= r.kettle_start) & ((b.kettle_start >= r.kettle_start) | b.kettle_start.isna())]
        if len(q) < 3: continue
        tot += 1; newest += r.yard_in == q.yard_in.max(); oldest += r.yard_in == q.yard_in.min()
    w = (kb.kettle_start - kb.yard_in).dt.total_seconds() / 86400
    pr(k, "picks with >=3 in yard", tot, "newest %", round(100 * newest / max(tot, 1), 1), "oldest %", round(100 * oldest / max(tot, 1), 1),
       "wait median d", round(w.median(), 2), "mean", round(w.mean(), 2), "p90", round(w.quantile(.9), 2), "max", round(w.max(), 1))
a, z = P["P2 night shift"]; kb = b[(b.kettle_start >= a) & (b.kettle_start < z)]
w = (kb.kettle_start - kb.yard_in).dt.total_seconds() / 86400
pr("P2 waits: share < 1 day", round(100 * (w < 1).mean(), 1), "share > 10 days", round(100 * (w > 10).mean(), 1))
hist = np.histogram(w, bins=[0, 1, 2, 4, 7, 10, 15, 20, 30, 60])[0]; pr("hist P2 wait d bins 0,1,2,4,7,10,15,20,30,60:", list(hist))
# order lead time is set by its slowest bundle
pr("\n== 5b order completion = last bundle")
sh = o[(o.shipped >= a) & (o.shipped < z)]
bb = b[b.order_id.isin(sh.order_id) & (b.inspection == "PASS")].copy()
bb["w"] = (bb.kettle_start - bb.yard_in).dt.total_seconds() / 86400
g = bb.groupby("order_id").w.agg(["median", "max"])
pr("orders", len(g), "median of bundle-median wait", round(g["median"].median(), 2), "median of bundle-max wait", round(g["max"].median(), 2))
pr("\n== 6 pilot test")
a, z = P["P2 night shift"]; days = (z - a).days
gk2 = good[(good.kettle_end >= a) & (good.kettle_end < z)].tons.sum() / days
ss = s[(s.start >= a) & (s.start < z)]
ho = ss[ss.reason == "SHIFT_HANDOVER"].minutes.sum() / 60 / days
x = b[(b.kettle_start >= a) & (b.kettle_start < z) & (b.inspection == "REJECT")]
rh = ((x.kettle_end - x.kettle_start).dt.total_seconds() / 3600).sum() / days
pr("P2 good t/day", round(gk2, 1), "handover h/day", round(ho, 2), "reject dip h/day", round(rh, 2), "rate", round(rate, 2))
pred = gk2 + (ho + rh * (1 - 0.006 / 0.055)) * rate * (1 - 0.006)
pr("predicted good t/day if handover recovered and ECT always ON", round(pred, 1), "gain", round(pred - gk2, 1))
a, z = P["P3 pilot drain"]; days = (z - a).days
gk3 = good[(good.kettle_end >= a) & (good.kettle_end < z)].tons.sum() / days
ss3 = s[(s.start >= a) & (s.start < z)]
pr("pilot weeks (kettle never starved?) NO_MATERIAL h", round(ss3[ss3.reason == "NO_MATERIAL"].minutes.sum() / 60, 1), "good t/day", round(gk3, 1), "gain", round(gk3 - gk2, 1))
# weekly good output and yard during pilot
for wk in pd.date_range("2019-05-19", "2019-07-14", freq="7D"):
    e = wk + pd.Timedelta(days=7)
    pr("week", wk.date(), "good t/day", round(good[(good.kettle_end >= wk) & (good.kettle_end < e)].tons.sum() / 7, 1),
       "tube mill t/day", round(b[(b.tube_mill_end >= wk) & (b.tube_mill_end < e)].tons.sum() / 7, 1), "yard end", round(yard[e - pd.Timedelta(hours=1)]))
pr("\n== 7 three measures")
tpt = fin["selling_price"] - fin["steel_and_zinc_cost"]
pr("throughput per ton OMR", tpt)
pr("throughput gain per month OMR (pilot gain x30)", round((gk3 - gk2) * 30 * tpt))
night = fin["night_shift_crew_cost"] + fin["overtime_and_power_night"]
pr("night shift cost per month", night, "months run", round((P["P2 night shift"][1] - P["P2 night shift"][0]).days / 30.4, 1), "total", round(night * (P["P2 night shift"][1] - P["P2 night shift"][0]).days / 30.4))
for t in ["2019-06-08 23:00", "2019-08-31 23:00"]:
    pr("yard WIP value at", t[:10], round(yard[pd.Timestamp(t)] * fin["wip_material_cost"]))
pr("second kettle", fin["second_kettle_quote"], "lead weeks", fin["second_kettle_lead_time"])
pr("\n== 8 Duqm customer")
du = o[o.customer == "C-DUQM-WATER"]
for k, (a, z) in P.items():
    x = du[(du.shipped >= a) & (du.shipped < z)]
    val = x.tons * fin["selling_price"]; pen = (val * (x.late_days * 0.005).clip(upper=0.10)).sum()
    pr(k, "orders", len(x), "late", int((x.late_days > 0).sum()), "max late d", int(x.late_days.max()) if len(x) else 0, "penalty OMR", round(pen))
pr("\n== 9 KPI vs reality")
pr("tube mill efficiency Feb vs Apr", kpi.set_index("month").loc[["2019-02", "2019-04", "2019-06", "2019-08"]].to_dict())
pr("\n== 10 extra details")
w = (b.kettle_start - b.yard_in).dt.total_seconds() / 86400
i = w.idxmax(); r = b.loc[i]; pr("longest wait bundle", r.bundle_id, r.order_id, o.set_index("order_id").customer[r.order_id], r.yard_in, r.kettle_start, round(w[i], 1))
t = pd.Timestamp("2019-04-14 08:00"); q = b[(b.yard_in <= t) & ((b.kettle_start > t) | b.kettle_start.isna())]
pr("yard on 2019-04-14 08:00: bundles", len(q), "tons", round(q.tons.sum()), "oldest yard_in", q.yard_in.min(), "orders", q.order_id.nunique())
pr("share of yard bundles older than 7 days", round(100 * ((t - q.yard_in).dt.days >= 7).mean(), 1))
du = o[(o.customer == "C-DUQM-WATER")]
pr("Duqm orders received Feb", len(du[(du.received >= "2019-02-01") & (du.received < "2019-03-01")]), "tons", round(du[(du.received >= "2019-02-01") & (du.received < "2019-03-01")].tons.sum()))
pr("order intake Feb t/day", round(o[(o.received >= "2019-02-01") & (o.received < "2019-03-01")].tons.sum() / 28, 1))
a, z = P["P2 night shift"]
pr("changeovers per day P2", round(tm[(tm.date >= a) & (tm.date < z)].changeovers.sum() / (z - a).days, 2))
k2 = s[(s.start >= a) & (s.start < z)]
pr("kettle available h/day P2 (24 - planned/unplanned stops)", round(24 - k2.minutes.sum() / 60 / (z - a).days, 2))
pr("late orders at 2019-04-14 (open, past due)", int(((o.received <= t) & (o.due_date < t) & ((o.shipped > t) | o.shipped.isna())).sum()))
a, z = P["P3 pilot drain"]
tq = tm[(tm.date >= "2019-06-09") & (tm.date < "2019-06-16")]
pr("tube mill tons 2019-06-09..15", round(tq.tons.sum(), 1))
pr("tube mill zero-ton days in June", int((tm[(tm.date >= "2019-06-01") & (tm.date < "2019-07-01")].groupby("date").tons.sum() < 1).sum()))
pr("kettle good t/day Jan (starved)", round(b[(b.inspection == "PASS") & (b.kettle_end >= "2019-01-01") & (b.kettle_end < "2019-02-01")].tons.sum() / 31, 1))
pr("avg yard WIP value P2", round(yard[(yard.index >= P["P2 night shift"][0]) & (yard.index < P["P2 night shift"][1])].mean() * fin["wip_material_cost"]),
   "P4", round(yard[(yard.index >= P["P4 after"][0])].mean() * fin["wip_material_cost"]))
pr("overlap cost", fin["kettle_handover_overlap_cost"], "net OE saving", fin["night_shift_crew_cost"] + fin["overtime_and_power_night"] - fin["kettle_handover_overlap_cost"])
pr("max tube mill weekly t/day on two shifts after pilot", max(round(b[(b.tube_mill_end >= wk) & (b.tube_mill_end < wk + pd.Timedelta(days=7))].tons.sum() / 7, 1) for wk in pd.date_range("2019-06-16", "2019-08-25", freq="7D")))
pr("\n== 11 narrative checks")
t = pd.Timestamp("2019-04-14 08:00"); q = b[(b.yard_in <= t) & ((b.kettle_start > t) | b.kettle_start.isna())]
pr("oldest bundle in yard 2019-04-14", q.loc[q.yard_in.idxmin()].bundle_id, "days in yard", (t - q.yard_in.min()).days)
f = b[b.kettle_start >= pd.Timestamp("2019-06-09")].sort_values("kettle_start").iloc[0]; pr("first kettle pick of pilot", f.bundle_id, f.kettle_start)
a, z = P["P2 night shift"]; kb = b[(b.kettle_start >= a) & (b.kettle_start < z)]
pr("P2 median yard wait hours", round(((kb.kettle_start - kb.yard_in).dt.total_seconds() / 3600).median(), 2))
for k in ["P1 two shifts", "P2 night shift"]:
    a, z = P[k]; x = b[(b.kettle_end >= a) & (b.kettle_end < z) & (b.inspection == "REJECT")]
    pr(k, "rejected t/day after kettle", round(x.tons.sum() / (z - a).days, 2))
a, z = P["P3 pilot drain"]; x = b[(b.kettle_start >= a) & (b.kettle_start < z) & (b.inspection == "REJECT")]
pr("pilot rejects", len(x), "made before pilot", int((x.tube_mill_end < a).sum()))
pr("\n== 12 second-edition checks")
kp = kpi.set_index("month"); st2 = pd.read_csv(d + "stations.csv").set_index("item")
std = float(st2.loc["kpi_standard_t_per_h", "LIGHT"])
for m, days, h in [("2019-02", 28, 16), ("2019-03", 31, 24), ("2019-04", 30, 24), ("2019-06", 30, 16)]:
    pr("KPI check", m, kp.loc[m, "tube_mill_tons"], "/ (", days, "x", h, "x", std, ") =", round(100 * kp.loc[m, "tube_mill_tons"] / (days * h * std), 1), "report", kp.loc[m, "tube_mill_efficiency_pct"])
def newest_share(a, z):
    kb = b[(b.kettle_start >= a) & (b.kettle_start < z)].sort_values("kettle_start"); nw = tot = 0
    for _, r in kb.iterrows():
        q = b[(b.yard_in <= r.kettle_start) & ((b.kettle_start >= r.kettle_start) | b.kettle_start.isna())]
        if len(q) < 3: continue
        tot += 1; nw += r.yard_in == q.yard_in.max()
    return tot, round(100 * nw / tot, 1)
pr("newest-first share Mar-Apr", newest_share(pd.Timestamp("2019-03-01"), pd.Timestamp("2019-05-01")), "May 1 - Jun 8 (colour tags)", newest_share(pd.Timestamp("2019-05-01"), pd.Timestamp("2019-06-09")))
for k in ["P2 night shift", "P4 after"]:
    a, z = P[k]; n = (z - a).days
    sh = o[(o.shipped >= a) & (o.shipped < z)]
    pr(k, "shipped t/day", round(sh.tons.sum() / n, 1), "order intake t/day", round(o[(o.received >= a) & (o.received < z)].tons.sum() / n, 1),
       "kettle starved h/day", round(s[(s.start >= a) & (s.start < z) & (s.reason == "NO_MATERIAL")].minutes.sum() / 60 / n, 2))
a, z = pd.Timestamp("2019-08-01"), pd.Timestamp("2019-09-01")
pr("Aug intake t/day", round(o[(o.received >= a) & (o.received < z)].tons.sum() / 31, 1), "Aug good t/day", round(good[(good.kettle_end >= a) & (good.kettle_end < z)].tons.sum() / 31, 1),
   "Aug starved h", round(s[(s.start >= a) & (s.start < z) & (s.reason == "NO_MATERIAL")].minutes.sum() / 60, 1))
pr("theoretical kettle t/day at 24 h", round(24 * rate, 1))
for k in ["P1 two shifts", "P3 pilot drain"]:
    a, z = P[k]; n = (z - a).days; sh = o[(o.shipped >= a) & (o.shipped < z)]
    pr(k, "shipped t/day", round(sh.tons.sum() / n, 1))
t = pd.Timestamp("2019-06-08 23:59")
gb = b[(b.inspection == "PASS") & (b.kettle_end <= t)]
open_o = o[(o.shipped > t) | o.shipped.isna()].order_id
w = gb[gb.order_id.isin(open_o)]
pr("galvanized good bundles waiting for their order to complete at 2019-06-08:", len(w), "bundles", round(w.tons.sum()), "t, orders", w.order_id.nunique())
def fg_wait(t):
    gb = b[(b.inspection == "PASS") & (b.kettle_end <= t)]
    oo = o[(o.shipped > t) | o.shipped.isna()].order_id
    return gb[gb.order_id.isin(oo)].tons.sum()
for k in ["P2 night shift", "P4 after"]:
    a, z = P[k]; days = pd.date_range(a, z - pd.Timedelta(days=1), freq="D") + pd.Timedelta(hours=12)
    v = [fg_wait(t) for t in days]
    pr(k, "avg galvanized tons waiting for order completion", round(sum(v) / len(v)), "value at steel_and_zinc_cost", round(sum(v) / len(v) * fin["steel_and_zinc_cost"]))
pr("max over Jan-Aug", max((round(fg_wait(t)), t.date()) for t in pd.date_range("2019-01-01", "2019-08-31", freq="D") + pd.Timedelta(hours=12)))
