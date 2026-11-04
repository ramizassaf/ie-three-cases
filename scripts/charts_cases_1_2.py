"""Charts for chapters 1 and 2, computed from the raw data files. Arabic labels are shaped for matplotlib."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import csv, math, os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

AMIRI = font_manager.FontProperties(fname=os.path.join(os.environ.get("AMIRI_DIR", "/usr/share/fonts/opentype/fonts-hosny-amiri"), "Amiri-Regular.ttf"))
OUT = os.path.join(ROOT, "figures"); os.makedirs(OUT, exist_ok=True)
D1 = os.path.join(ROOT, "data", "01-case-nablus-sterilizer") + "/"; D2 = os.path.join(ROOT, "data", "02-case-riyadh-quality") + "/"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e2dc"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
A = lambda s: s  # matplotlib 3.11 shapes Arabic itself
P = lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
read = lambda f: list(csv.DictReader(open(f, encoding="utf-8")))

def fig(w=4.8, h=2.7):
    f, ax = plt.subplots(figsize=(w, h), dpi=220)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color("#9a988f")
    ax.tick_params(colors=MUTED, labelsize=7.5, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.6); ax.set_axisbelow(True)
    return f, ax
def ar_ticks(ax, labels, axis="x", size=9):
    (ax.set_xticklabels if axis == "x" else ax.set_yticklabels)([A(l) for l in labels], fontproperties=AMIRI, fontsize=size)
def ylabel(ax, t): ax.set_ylabel(A(t), fontproperties=AMIRI, fontsize=9, color=MUTED)
def xlabel(ax, t): ax.set_xlabel(A(t), fontproperties=AMIRI, fontsize=9, color=MUTED)
def save(f, name): f.tight_layout(); f.savefig(f"{OUT}/{name}.png", facecolor="white"); plt.close(f)
def barlabels(ax, bars, fmt="{:g}", color=INK):
    for b in bars:
        v = b.get_height(); ax.text(b.get_x() + b.get_width() / 2, v, fmt.format(v), ha="center", va="bottom", fontsize=7, color=color)

# ---------------------------------------------------------------- chapter 1
wo = [w for w in read(D1 + "work_orders.csv") if w["wo_type"] == "CM"]
for w in wo: w["t"] = P(w["reported_at"])
ctrl = read(D1 + "controller_events.csv")
for c in ctrl: c["t"] = P(c["timestamp"])
gen = read(D1 + "generator_switch_log.csv")
for g in gen: g["t"] = P(g["timestamp"])
A2 = ("STER-01", "STER-02")

# 1-1 CM per device
cnt = Counter(w["device_id"] for w in wo)
f, ax = fig(4.8, 2.4)
devs = ["STER-01", "STER-02", "STER-03"]
bars = ax.bar(devs, [cnt[d] for d in devs], width=0.5, color=[S1, S1, S3])
barlabels(ax, bars)
for i, (d, y) in enumerate(zip(devs, ["2005", "2011", "2008"])): ax.text(i, -9, y, ha="center", fontsize=7, color=MUTED)
ylabel(ax, "أوامر العمل التصحيحية"); ax.set_ylim(0, 72)
save(f, "c1_devices")

# 1-2 monthly
months = [f"2013-{m:02d}" for m in range(9, 13)] + [f"2014-{m:02d}" for m in range(1, 13)]
mc = Counter(w["t"].strftime("%Y-%m") for w in wo if w["device_id"] in A2)
f, ax = fig(4.8, 2.6)
cols = [S2 if m in ("2014-05", "2014-06") else S1 for m in months]
bars = ax.bar(range(len(months)), [mc[m] for m in months], width=0.6, color=cols)
barlabels(ax, bars)
ax.set_xticks(range(len(months))); ax.set_xticklabels([m[2:].replace("-", "/") for m in months], rotation=60, fontsize=6.5)
ax.axvline(3.5, color=MUTED, lw=0.8, ls="--"); ax.text(3.6, 15.2, A("بدء الاختبار الأسبوعي"), fontproperties=AMIRI, fontsize=7.5, color=MUTED, ha="left")
ax.text(8.5, 5.2, A("أسوأ ماء"), fontproperties=AMIRI, fontsize=7.5, color=S2, ha="center")
ylabel(ax, "أوامر عمل STER-01 و STER-02"); ax.set_ylim(0, 16)
save(f, "c1_monthly")

# 1-3 weekday rate
days = ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]; ar = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
wd = Counter(w["t"].strftime("%a") for w in wo if w["device_id"] in A2)
cy = Counter(c["t"].strftime("%a") for c in ctrl if c["device_id"] in A2 and c["code"] == "C10")
rate = [1000 * wd[d] / cy[d] for d in days]
f, ax = fig(4.8, 2.5)
bars = ax.bar(range(7), rate, width=0.55, color=[S2 if d == "Tue" else S1 for d in days])
barlabels(ax, bars, "{:.1f}")
ax.set_xticks(range(7)); ar_ticks(ax, ar)
ylabel(ax, "أعطال لكل 1000 دورة"); ax.set_ylim(0, 32)
save(f, "c1_weekday")

# 1-4 written fault vs root alarm (stacked)
prim = [c for c in ctrl if c["code"] in ("A01", "A02", "A11", "A21")]
byd = defaultdict(list)
for c in prim: byd[c["device_id"]].append(c)
for w in wo:
    cand = [c for c in byd[w["device_id"]] if w["t"] - timedelta(hours=3) <= c["t"] <= w["t"]]
    w["root"] = cand[-1]["code"] if cand else "none"
faults = [("Steam generator fault, scale suspected", "مولد البخار، كلس"), ("Door seal leak", "تسرب مانع الباب"), ("Temperature deviation", "انحراف الحرارة"), ("Controller error", "خطأ المتحكم"), ("Power problem", "مشكلة كهرباء")]
f, ax = fig(4.8, 2.6)
pw = [sum(1 for w in wo if w["reported_fault"] == e and w["root"] in ("A01", "A02")) for e, _ in faults]
ot = [sum(1 for w in wo if w["reported_fault"] == e and w["root"] not in ("A01", "A02")) for e, _ in faults]
y = list(range(len(faults)))[::-1]
ax.barh(y, pw, height=0.55, color=S1, label=A("الإنذار الجذري كهرباء"))
ax.barh(y, ot, left=pw, height=0.55, color=S3, edgecolor="white", linewidth=1, label=A("الإنذار الجذري عطل في الجهاز"))
for yy, a, b in zip(y, pw, ot): ax.text(a + b + 1, yy, f"{a} + {b}" if b else f"{a}", va="center", fontsize=7, color=INK)
ax.set_yticks(y); ar_ticks(ax, [a for _, a in faults], "y", 8.5)
ax.grid(axis="x", color=GRID, linewidth=0.6); ax.grid(axis="y", visible=False)
xlabel(ax, "أوامر العمل"); ax.set_xlim(0, 75)
leg = ax.legend(prop=AMIRI, fontsize=8, frameon=False, loc="lower right")
save(f, "c1_root")

# 1-5 recorder v_min
rec = read(D1 + "voltage_recorder.csv")
t = [P(r["timestamp"]) for r in rec]; v = [float(r["v_min"]) for r in rec]
f, ax = fig(4.8, 2.6)
ax.plot(t, v, color=S1, lw=0.6)
ax.axhline(196, color=S2, lw=1, ls="--"); ax.text(t[200], 199, A("حد الإيقاف 196 فولت"), fontproperties=AMIRI, fontsize=7.5, color=S2)
ax.set_ylim(170, 240); ylabel(ax, "أدنى جهد في الدقيقة (فولت)")
low = [(tt, vv) for tt, vv in zip(t, v) if 0 < vv < 196]
ax.scatter([a for a, _ in low], [b for _, b in low], s=10, color=S2, zorder=3)
ax.text(t[-1], 172, A("الانقطاعات الكاملة (صفر فولت) خارج حدود الرسم"), fontproperties=AMIRI, fontsize=7, color=MUTED, ha="right")
import matplotlib.dates as mdates
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m")); ax.xaxis.set_major_locator(mdates.DayLocator(interval=4))
save(f, "c1_recorder")

# 1-6 sources
src = [("انقطاع حقيقي للشبكة", 60), ("الاختبار الأسبوعي", 43), ("هبوط الجهد", 19), ("عطل حقيقي في الجهاز", 4)]
f, ax = fig(4.8, 2.1)
y = list(range(4))[::-1]
bars = ax.barh(y, [n for _, n in src], height=0.55, color=[S1, S2, S1, S3])
for yy, (_, n) in zip(y, src): ax.text(n + 1, yy, str(n), va="center", fontsize=7.5)
ax.set_yticks(y); ar_ticks(ax, [a for a, _ in src], "y", 9)
ax.grid(axis="x", color=GRID, linewidth=0.6); ax.grid(axis="y", visible=False); ax.set_xlim(0, 70)
xlabel(ax, "أوامر العمل على STER-01 و STER-02")
save(f, "c1_sources")

# ---------------------------------------------------------------- chapter 2
rows = read(D2 + "torque_subgroups_60days.csv")
sg = defaultdict(list)
for r in rows: sg[r["subgroup"]].append(r)
SG = []
for k in sorted(sg):
    g = sg[k]; vals = [float(x["removal_torque_nm"]) for x in g]
    SG.append(dict(t=P(g[0]["timestamp"]), x=sum(vals) / 5, R=max(vals) - min(vals)))
xbb = sum(s["x"] for s in SG) / len(SG); Rb = sum(s["R"] for s in SG) / len(SG)
ucl, lcl = xbb + 0.577 * Rb, xbb - 0.577 * Rb
shift = lambda t: "A" if 6 <= t.hour < 14 else ("B" if 14 <= t.hour < 22 else "C")
mold = read(D2 + "mold_temperature.csv"); mt = [float(m["mold_temp_c"]) for m in mold]
START = datetime(2017, 6, 25)
mold_at = lambda tm: mt[max(0, min(len(mt) - 1, int((tm - START).total_seconds() // 600)))]

# 2-1 X-bar chart
f, ax = fig(4.8, 3.0)
colors = {"A": "#9a988f", "B": S2, "C": S1}
for k, lab in (("A", "الوردية A، الصباح"), ("B", "الوردية B، المساء"), ("C", "الوردية C، الليل")):
    pts = [s for s in SG if shift(s["t"]) == k]
    ax.scatter([s["t"] for s in pts], [s["x"] for s in pts], s=3, color=colors[k], label=A(lab))
for yv, lab in ((ucl, "UCL"), (xbb, "CL"), (lcl, "LCL")):
    ax.axhline(yv, color=INK if lab == "CL" else MUTED, lw=0.8, ls="-" if lab == "CL" else "--"); ax.text(1.01, yv, f"{lab} {yv:.3f}", fontsize=6.5, va="center", color=MUTED, transform=ax.get_yaxis_transform())
ax.axhline(2.0, color=S2, lw=0.6, ls=":"); ax.text(SG[-1]["t"], 2.085, A("حد المواصفة الأعلى 2.0"), fontproperties=AMIRI, fontsize=7, color=S2, ha="right")
ax.set_ylim(1.25, 2.15); ylabel(ax, "متوسط العينة X-bar (نيوتن متر)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
ax.legend(prop=AMIRI, fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, markerscale=3, handletextpad=0.2)
save(f, "c2_xbar")

# 2-2 mean by hour
hr = defaultdict(list)
for s in SG: hr[s["t"].hour // 2 * 2].append(s["x"])
hrs = sorted(hr)
f, ax = fig(4.8, 2.4)
vals = [sum(hr[h]) / len(hr[h]) for h in hrs]
bars = ax.bar(range(len(hrs)), vals, width=0.6, color=[S2 if 14 <= h < 22 else (S1 if h >= 22 or h < 6 else "#9a988f") for h in hrs])
barlabels(ax, bars, "{:.3f}")
ax.set_xticks(range(len(hrs))); ax.set_xticklabels([f"{h:02d}" for h in hrs], fontsize=7.5)
ax.set_ylim(1.40, 1.74); xlabel(ax, "ساعة أخذ العينة"); ylabel(ax, "متوسط العزم")
save(f, "c2_hour")

# 2-3 stratified resin
bands = ["< 26", "26 - 29", "29 - 32", "32 +"]
g = [1.495, 1.662, None, None]; n = [1.498, 1.681, 1.817, 1.951]
f, ax = fig(4.8, 2.5)
import numpy as np
xs = np.arange(4)
b1 = ax.bar(xs - 0.17, [v or 0 for v in g], width=0.32, color=S1, label="Gulf Polymers")
b2 = ax.bar(xs + 0.17, n, width=0.32, color=S2, label="Najd Resins")
for b, v in zip(b1, g):
    if v: ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.3f}", ha="center", va="bottom", fontsize=6.5)
for b, v in zip(b2, n): ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.3f}", ha="center", va="bottom", fontsize=6.5)
ax.text(2 - 0.17, 1.42, A("عينة واحدة"), fontproperties=AMIRI, fontsize=6.5, ha="center", color=MUTED, rotation=90)
ax.set_xticks(xs); ax.set_xticklabels(bands, fontsize=8); ax.set_ylim(1.4, 2.0)
xlabel(ax, "حرارة القالب قبل 3 ساعات (درجة)"); ylabel(ax, "متوسط العزم")
ax.legend(fontsize=7.5, frameon=False, loc="upper left")
save(f, "c2_resin")

# 2-4 lag correlation
def corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
lags = list(range(7)); r = [corr([s["x"] for s in SG], [mold_at(s["t"] - timedelta(hours=L)) for s in SG]) for L in lags]
f, ax = fig(4.8, 2.3)
bars = ax.bar(lags, r, width=0.55, color=[S2 if L == 3 else S1 for L in lags]); barlabels(ax, bars, "{:.2f}")
ax.set_xticks(lags); ax.set_ylim(0, 0.9); xlabel(ax, "التأخير بالساعات"); ylabel(ax, "معامل الارتباط")
save(f, "c2_lag")

# 2-5 chiller
cool = read(D2 + "cooler_log.csv")
bins = defaultdict(list)
for c in cool: bins[int(float(c["ambient_c"]))].append(float(c["chw_supply_c"]))
amb = [a for a in sorted(bins) if a >= 34]
f, ax = fig(4.8, 2.4)
ax.plot(amb, [sum(bins[a]) / len(bins[a]) for a in amb], color=S1, lw=2, marker="o", ms=4)
ax.axvline(42.5, color=S2, lw=0.8, ls="--"); ax.text(42.6, 19, A("42.5 درجة"), fontproperties=AMIRI, fontsize=7.5, color=S2)
ax.axhline(12, color=MUTED, lw=0.6, ls=":"); ax.text(34, 12.4, A("نقطة الضبط 12"), fontproperties=AMIRI, fontsize=7, color=MUTED)
xlabel(ax, "حرارة الهواء (درجة)"); ylabel(ax, "ماء المبرد الخارج (درجة)")
save(f, "c2_chiller")

# 2-6 gauge bias
gg = read(D2 + "gauge_rr_study.csv")
ops = [("J. Dela Cruz", "دلا كروز، الليل"), ("R. Mathew", "ماثيو، المساء"), ("S. Al-Qahtani", "القحطاني، الصباح")]
bias = [sum(float(x["reading_nm"]) - float(x["lab_reference_nm"]) for x in gg if x["operator"] == o) / sum(1 for x in gg if x["operator"] == o) for o, _ in ops]
f, ax = fig(4.8, 2.2)
y = [2, 1, 0]
ax.barh(y, bias, height=0.5, color=[S2, S1, S1])
for yy, b in zip(y, bias): ax.text(b + (0.004 if b >= 0 else -0.004), yy, f"{b:+.3f}", va="center", ha="left" if b >= 0 else "right", fontsize=7.5)
ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(y); ar_ticks(ax, [a for _, a in ops], "y", 9)
ax.set_xlim(-0.11, 0.04); ax.grid(axis="x", color=GRID, linewidth=0.6); ax.grid(axis="y", visible=False)
xlabel(ax, "الفرق عن قيمة مختبر المعايرة (نيوتن متر)")
save(f, "c2_gauge")

# 2-7 holdout
H = START + timedelta(days=50)
tr = [s for s in SG if s["t"] < H]; te = [s for s in SG if s["t"] >= H]
xm = [mold_at(s["t"] - timedelta(hours=3)) for s in tr]; ym = [s["x"] for s in tr]
mx, my = sum(xm) / len(xm), sum(ym) / len(ym)
b = sum((a - mx) * (c - my) for a, c in zip(xm, ym)) / sum((a - mx) ** 2 for a in xm); a0 = my - b * mx
f, ax = fig(4.8, 2.5)
ax.plot([s["t"] for s in te], [s["x"] for s in te], color=S1, lw=1, marker="o", ms=2, label=A("الفعلي"))
ax.plot([s["t"] for s in te], [a0 + b * mold_at(s["t"] - timedelta(hours=3)) for s in te], color=S2, lw=1, ls="--", label=A("ما تنبأ به النموذج"))
ax.axhline(ucl, color=MUTED, lw=0.6, ls=":"); ax.text(te[0]["t"], ucl + 0.01, "UCL", fontsize=6.5, color=MUTED)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m")); ylabel(ax, "متوسط العزم")
ax.legend(prop=AMIRI, fontsize=8, frameon=False, loc="upper left", ncol=2)
save(f, "c2_holdout")
print("fit", round(a0, 3), round(b, 4), "ucl", round(ucl, 3), "lags", [round(x, 2) for x in r], "bias", [round(x, 3) for x in bias])
print(sorted(os.listdir(OUT)))
