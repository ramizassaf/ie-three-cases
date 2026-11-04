"""Charts for chapter 3 (Sohar), computed from the raw data files."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import os, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
AMIRI = font_manager.FontProperties(fname=os.path.join(os.environ.get("AMIRI_DIR", "/usr/share/fonts/opentype/fonts-hosny-amiri"), "Amiri-Regular.ttf"))
OUT = os.path.join(ROOT, "figures"); D = os.path.join(ROOT, "data", "03-case-sohar-flow") + "/"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e2dc"
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#9a988f"
def fig(w=4.8, h=2.7):
    f, ax = plt.subplots(figsize=(w, h), dpi=220)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color("#9a988f")
    ax.tick_params(colors=MUTED, labelsize=7.5, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.6); ax.set_axisbelow(True)
    return f, ax
T = lambda ax, x, y, s, **k: ax.text(x, y, s, fontproperties=AMIRI, **k)
def ylabel(ax, t): ax.set_ylabel(t, fontproperties=AMIRI, fontsize=9, color=MUTED)
def xlabel(ax, t): ax.set_xlabel(t, fontproperties=AMIRI, fontsize=9, color=MUTED)
def save(f, name): f.tight_layout(); f.savefig(f"{OUT}/{name}.png", facecolor="white"); plt.close(f)
o = pd.read_csv(D + "orders.csv", parse_dates=["received", "due_date", "shipped"])
b = pd.read_csv(D + "bundles.csv", parse_dates=["tube_mill_end", "yard_in", "kettle_start", "kettle_end"])
s = pd.read_csv(D + "kettle_stops.csv", parse_dates=["start", "end"])
good = b[b.inspection == "PASS"]
P2 = (pd.Timestamp("2019-03-01"), pd.Timestamp("2019-06-09")); P4 = (pd.Timestamp("2019-07-01"), pd.Timestamp("2019-09-01"))
MN = ["كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران", "تموز", "آب"]
# 3-1 monthly flow
mon = pd.period_range("2019-01", "2019-08", freq="M"); rows = []
for m in mon:
    a, z = m.start_time, (m + 1).start_time; n = m.days_in_month
    rows.append((o[(o.received >= a) & (o.received < z)].tons.sum() / n, b[(b.tube_mill_end >= a) & (b.tube_mill_end < z)].tons.sum() / n,
                 good[(good.kettle_end >= a) & (good.kettle_end < z)].tons.sum() / n))
r = np.array(rows); x = np.arange(len(mon))
f, ax = fig(4.8, 2.9)
for i, (c, lab, mk) in enumerate([(S4, "طلبيات جديدة", "o"), (S1, "خرج من الخط", "s"), (S2, "خرج سليماً من الحوض", "D")]):
    ax.plot(x, r[:, i], color=c, lw=1.6, marker=mk, ms=3.5, label=lab)
ax.axvspan(1.5, 5.25, color=S1, alpha=0.06); T(ax, 3.4, 100, "ثلاث ورديات على الخط", fontsize=7.5, color=S1, ha="center")
ax.set_xticks(x); ax.set_xticklabels(MN, fontproperties=AMIRI, fontsize=7.5, rotation=0)
ax.set_ylim(40, 105); ylabel(ax, "طن في اليوم")
lg = ax.legend(prop=AMIRI, fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
for t in lg.get_texts(): t.set_fontproperties(AMIRI); t.set_fontsize(8)
save(f, "c3_flow")
# 3-2 yard WIP daily
grid = pd.date_range("2019-01-01", "2019-09-01", freq="h", inclusive="left")
add = pd.Series(b.tons.values, index=b.yard_in.dt.floor("h")).groupby(level=0).sum().reindex(grid, fill_value=0)
rem = pd.Series(b.tons.values, index=b.kettle_start.fillna(pd.Timestamp("2030-01-01")).dt.floor("h")).groupby(level=0).sum().reindex(grid, fill_value=0)
yard = (add - rem).cumsum().resample("D").mean()
f, ax = fig(4.8, 2.6)
ax.fill_between(yard.index, yard.values, color=S1, alpha=0.25, lw=0); ax.plot(yard.index, yard.values, color=S1, lw=1.2)
for d, lab, y in [("2019-03-01", "الوردية الثالثة", 1000), ("2019-04-14", "وصول سامر", 860), ("2019-06-09", "بدء التجربة", 1000)]:
    ax.axvline(pd.Timestamp(d), color=MUTED, lw=0.8, ls="--"); T(ax, pd.Timestamp(d) + pd.Timedelta(days=2), y, lab, fontsize=7.5, color=MUTED, ha="left")
ax.set_ylim(0, 1080); ylabel(ax, "طن في الساحة")
ax.set_xticks([pd.Timestamp(f"2019-{m:02d}-01") for m in range(1, 9)]); ax.set_xticklabels(MN, fontproperties=AMIRI, fontsize=7.5)
save(f, "c3_yard")
# 3-3 utilisation P2
tm = pd.read_csv(D + "tube_mill_shifts.csv", parse_dates=["date"]); st = pd.read_csv(D + "stations.csv").set_index("item")
RATE = st.loc["tube_mill_nominal_t_per_h", ["LIGHT", "MEDIUM", "HEAVY"]].astype(float).to_dict()
tmw = tm[(tm.date >= P2[0]) & (tm.date < P2[1])]; crew = (tmw.crew == "Y").sum() * 8
tb = b[(b.tube_mill_end >= P2[0]) & (b.tube_mill_end < P2[1])]
make = (tb.tons / tb.wall.map(RATE)).sum(); co = tmw.changeovers.sum() * float(st.loc["tube_mill_changeover_min", "LIGHT"]) / 60
kb = b[(b.kettle_start >= P2[0]) & (b.kettle_start < P2[1])]; dip = ((kb.kettle_end - kb.kettle_start).dt.total_seconds() / 3600).sum()
kh = (P2[1] - P2[0]).days * 24; starve = s[(s.start >= P2[0]) & (s.start < P2[1]) & (s.reason == "NO_MATERIAL")].minutes.sum() / 60
vals = {"خط التشكيل": [make / crew, co / crew, 1 - (make + co) / crew], "حوض الجلفنة": [dip / kh, (kh - dip - starve) / kh, starve / kh]}
f, ax = fig(4.8, 2.2); ax.grid(False); ax.grid(axis="x", color=GRID, lw=0.6)
cols = [S1, S4, S2]; labs = ["يعمل", "توقف أو تغيير مقاس", "ينتظر بلا عمل"]
for i, (k, v) in enumerate(vals.items()):
    left = 0
    for j, p in enumerate(v):
        ax.barh(i, p * 100, left=left, color=cols[j], height=0.55, label=labs[j] if i == 0 else None)
        if p > 0.04: ax.text(left + p * 50, i, f"{p*100:.1f}%", ha="center", va="center", fontsize=7.5, color="white")
        left += p * 100
ax.set_yticks([0, 1]); ax.set_yticklabels(list(vals), fontproperties=AMIRI, fontsize=9); ax.set_xlim(0, 100); ax.invert_yaxis()
xlabel(ax, "من الساعات المتاحة، آذار إلى 8 حزيران")
lg = ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.62), ncol=3)
for t in lg.get_texts(): t.set_fontproperties(AMIRI); t.set_fontsize(8)
save(f, "c3_util")
# 3-4 kettle budget P2 vs P4
def budget(a, z):
    n = (z - a).days; kb = b[(b.kettle_start >= a) & (b.kettle_start < z)]
    dh = (kb.kettle_end - kb.kettle_start).dt.total_seconds() / 3600; ss = s[(s.start >= a) & (s.start < z)]
    return [dh[kb.inspection == "PASS"].sum() / n, dh[kb.inspection == "REJECT"].sum() / n] + [ss[ss.reason == r].minutes.sum() / 60 / n for r in ["SHIFT_HANDOVER", "DROSS_CLEANING", "BREAKDOWN", "NO_MATERIAL"]]
B2, B4 = budget(*P2), budget(*P4)
cats = ["حزم مرفوضة", "تسليم الوردية", "تنظيف الخبث", "أعطال", "لا توجد حزم"]
f, ax = fig(4.8, 2.5); xx = np.arange(len(cats)); w = 0.36
b1 = ax.bar(xx - w / 2, B2[1:], w, color=S2, label="آذار إلى 8 حزيران"); b2 = ax.bar(xx + w / 2, B4[1:], w, color=S1, label="تموز وآب")
for bb in list(b1) + list(b2): ax.text(bb.get_x() + bb.get_width() / 2, bb.get_height() + 0.04, f"{bb.get_height():.2f}", ha="center", fontsize=6.5, color=INK)
ax.set_xticks(xx); ax.set_xticklabels(cats, fontproperties=AMIRI, fontsize=8.5); ylabel(ax, "ساعة في اليوم"); ax.set_ylim(0, 2.9)
T(ax, 4.45, 2.6, f"الجلفنة السليمة: {B2[0]:.2f} ثم {B4[0]:.2f} ساعة", fontsize=7.5, color=MUTED, ha="right")
lg = ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 0.88))
for t in lg.get_texts(): t.set_fontproperties(AMIRI); t.set_fontsize(8)
save(f, "c3_kettle")
# 3-5 ECT reject rate
bb = b[b.inspection.isin(["PASS", "REJECT"]) & (b.tube_mill_end < pd.Timestamp("2019-06-09"))]
rr = bb.groupby("ect").inspection.apply(lambda x: 100 * (x == "REJECT").mean())
f, ax = fig(4.8, 2.2)
bars = ax.bar(["الكاشف يعمل", "الكاشف مطفأ"], [rr["ON"], rr["OFF"]], width=0.45, color=[S1, S2])
for br in bars: ax.text(br.get_x() + br.get_width() / 2, br.get_height() + 0.1, f"{br.get_height():.2f}%", ha="center", fontsize=8, color=INK)
ax.set_xticks([0, 1]); ax.set_xticklabels(["الكاشف يعمل", "الكاشف مطفأ"], fontproperties=AMIRI, fontsize=9)
ylabel(ax, "حزم مرفوضة بعد الحوض %"); ax.set_ylim(0, 7)
save(f, "c3_ect")
# 3-6 yard wait histogram P2
w_ = (kb.kettle_start - kb.yard_in).dt.total_seconds() / 86400
edges = [0, 1, 2, 4, 7, 10, 15, 20, 30, 60, 120]; h = np.histogram(w_, bins=edges)[0]
labs = ["أقل من 1", "1-2", "2-4", "4-7", "7-10", "10-15", "15-20", "20-30", "30-60", "60-120"]
f, ax = fig(4.8, 2.6)
cols = [S1] + [S4] * 4 + [S2] * 5
bars = ax.bar(range(len(h)), 100 * h / h.sum(), color=cols, width=0.65)
for br, n in zip(bars, h): ax.text(br.get_x() + br.get_width() / 2, br.get_height() + 1, f"{n}", ha="center", fontsize=6.5, color=INK)
ax.set_xticks(range(len(h))); ax.set_xticklabels(labs, fontsize=6.5)
xlabel(ax, "أيام الانتظار في الساحة"); ylabel(ax, "من الحزم %"); ax.set_ylim(0, 82)
T(ax, 6.5, 30, "أكثر من عشرة أيام", fontsize=8, color=S2, ha="center"); T(ax, 6.5, 24, f"{100*(w_>10).mean():.1f}% من الحزم", fontsize=8, color=S2, ha="center")
save(f, "c3_wait")
# 3-7 pilot weekly
wks = pd.date_range("2019-04-14", "2019-08-25", freq="7D")
gw = [good[(good.kettle_end >= k) & (good.kettle_end < k + pd.Timedelta(days=7))].tons.sum() / 7 for k in wks]
tw = [b[(b.tube_mill_end >= k) & (b.tube_mill_end < k + pd.Timedelta(days=7))].tons.sum() / 7 for k in wks]
f, ax = fig(4.8, 2.8)
ax.plot(wks, tw, color=S4, lw=1.3, marker="s", ms=3, label="خرج من الخط")
ax.plot(wks, gw, color=S2, lw=1.8, marker="D", ms=3, label="خرج سليماً من الحوض")
ax.axhline(71.0, color=MUTED, lw=0.8, ls=":"); T(ax, pd.Timestamp("2019-06-24"), 44, "الخط المنقط: المتوسط قبل التجربة 71.0", fontsize=7.5, color=MUTED)
ax.axhline(81.9, color=S2, lw=0.8, ls="--"); T(ax, pd.Timestamp("2019-06-24"), 36, "الخط المتقطع: التنبؤ 81.9", fontsize=7.5, color=S2)
ax.axvline(pd.Timestamp("2019-06-09"), color=MUTED, lw=0.8, ls="--"); T(ax, pd.Timestamp("2019-06-11"), 93, "بدء التجربة", fontsize=7.5, color=MUTED)
ax.set_ylim(0, 100); ylabel(ax, "طن في اليوم، متوسط الأسبوع")
ax.set_xticks([pd.Timestamp(f"2019-{m:02d}-01") for m in range(5, 9)]); ax.set_xticklabels(["أيار", "حزيران", "تموز", "آب"], fontproperties=AMIRI, fontsize=8)
lg = ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2)
for t in lg.get_texts(): t.set_fontproperties(AMIRI); t.set_fontsize(8)
save(f, "c3_pilot")
print("P2 budget", [round(v, 2) for v in B2], "P4", [round(v, 2) for v in B4], "util", {k: [round(100 * x, 1) for x in v] for k, v in vals.items()}, "ect", rr.round(2).to_dict(), "hist", list(h))
print("pilot weeks good", [round(v, 1) for v in gw])
