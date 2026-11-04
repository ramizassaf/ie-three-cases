"""Builds the appendix tables (markup for build.js) from the raw data of the three cases.
Usage: python3 scripts/appendix_tables.py OUT.txt"""
import csv, math, os, sys
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D1, D2, D3 = [os.path.join(ROOT, "data", x) + "/" for x in ("01-case-nablus-sterilizer", "02-case-riyadh-quality", "03-case-sohar-flow")]
L = []
def tab(cap, head, rows):
    L.append(f"!cap {cap}"); L.append("|" + "|".join(head) + "|")
    for r in rows: L.append("|" + "|".join(str(x) for x in r) + "|")
    L.append("")
def para(t): L.append(t); L.append("")
AM = {1: "كانون الثاني", 2: "شباط", 3: "آذار", 4: "نيسان", 5: "أيار", 6: "حزيران", 7: "تموز", 8: "آب", 9: "أيلول", 10: "تشرين الأول", 11: "تشرين الثاني", 12: "كانون الأول"}
f1 = lambda v: f"{v:.1f}"; f2 = lambda v: f"{v:.2f}"; f3 = lambda v: f"{v:.3f}"
# ============================================================ A. Nablus
P = lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
wo = [w for w in csv.DictReader(open(D1 + "work_orders.csv")) if w["wo_type"] == "CM"]
for w in wo:
    for k in ("reported_at", "repair_start", "repair_end"): w[k] = P(w[k])
ctrl = list(csv.DictReader(open(D1 + "controller_events.csv")))
for c in ctrl: c["t"] = P(c["timestamp"])
gen = list(csv.DictReader(open(D1 + "generator_switch_log.csv")))
tt = sorted(P(g["timestamp"]) for g in gen if g["event"].startswith("ATS_TO"))
tests = [P(g["timestamp"]) for g in gen if g["event"].startswith("ATS_TO") and g["note"] == "weekly on-load test"]
START, END = datetime(2013, 9, 1), datetime(2015, 1, 1)
DEV = ("STER-01", "STER-02", "STER-03")
L.append("# الملحق أ: جداول قضية نابلس"); L.append("")
para("كل الجداول في هذا الملحق محسوبة من ملفات البيانات الخام لقضية نابلس، بالبرنامج scripts/appendix_tables.py في المستودع المرافق github.com/ramizassaf/ie-three-cases. وفترة الرصد من أول أيلول 2013 حتى آخر كانون الأول 2014.")
# A-1 monthly CM by device
rows = []; m = START
while m < END:
    n = m.replace(year=m.year + (m.month == 12), month=m.month % 12 + 1)
    c = Counter(w["device_id"] for w in wo if m <= w["reported_at"] < n)
    rows.append([f"{AM[m.month]} {m.year}"] + [c[d] for d in DEV] + [c["STER-01"] + c["STER-02"]]); m = n
rows.append(["المجموع"] + [sum(r[i] for r in rows) for i in (1, 2, 3, 4)])
tab("جدول أ-1: أوامر العمل التصحيحية شهرياً لكل جهاز", ["الشهر", "STER-01", "STER-02", "STER-03", "جهازا اللوحة DB-A2"], rows)
# A-2 reliability incl. Weibull
hours = (END - START).total_seconds() / 3600
def weib(dev):
    ts = sorted(w["reported_at"] for w in wo if w["device_id"] == dev)
    x = sorted((b - a).total_seconds() / 86400 for a, b in zip(ts, ts[1:])); n = len(x)
    if n < 10: return n, "", "", ""
    lx = [math.log(v) for v in x]; ml = sum(lx) / n
    def g(b):
        xb = [v ** b for v in x]; return 1 / b + ml - sum(a * l for a, l in zip(xb, lx)) / sum(xb)
    lo, hi = 0.05, 20.0
    for _ in range(100):
        mid = (lo + hi) / 2; lo, hi = (mid, hi) if g(mid) > 0 else (lo, mid)
    b = (lo + hi) / 2; eta = (sum(v ** b for v in x) / n) ** (1 / b)
    Y = [math.log(-math.log(1 - (i - 0.3) / (n + 0.4))) for i in range(1, n + 1)]; mx, my = ml, sum(Y) / n
    mrr = sum((a - mx) * (c - my) for a, c in zip(lx, Y)) / sum((a - mx) ** 2 for a in lx)
    return n, f2(b), f2(mrr), f1(eta)
def in_win(t): return 6 <= t.hour < (12 if t.weekday() == 4 else 22)
def win_h(a, b):
    tot, t = 0.0, a
    while t < b:
        nt = min(b, t + timedelta(minutes=1))
        if in_win(t): tot += (nt - t).total_seconds() / 3600
        t = nt
    return tot
op_hours = win_h(START, END)
rows = []
for d in DEV:
    ws = [w for w in wo if w["device_id"] == d]; n_ = len(ws)
    mttr = sum((w["repair_end"] - w["reported_at"]).total_seconds() / 3600 for w in ws) / n_
    dwin = sum(win_h(w["reported_at"], w["repair_end"]) for w in ws)
    n, b, mrr, eta = weib(d)
    rows.append([d, n_, f1(hours / n_), f1(op_hours / n_), f2(mttr), f"{100 * (1 - dwin / op_hours):.1f}%", n, b, mrr, eta])
tab("جدول أ-2: مؤشرات الاعتمادية لكل جهاز، على الساعات التقويمية وعلى ساعات التشغيل، مع معلمات ويبل", ["الجهاز", "الأعطال", "MTBF تقويمي، ساعة", "MTBF تشغيلي، ساعة", "MTTR ساعة", "الإتاحة التشغيلية", "الفترات", "بيتا MLE", "بيتا MRR", "eta يوم"], rows)
para(f"الساعات التقويمية في فترة الرصد {hours:.0f} ساعة، وساعات التشغيل المجدولة {op_hours:.0f} ساعة: من السادسة صباحاً حتى العاشرة ليلاً من السبت إلى الخميس، ومن السادسة حتى الثانية عشرة ظهراً يوم الجمعة. والإتاحة التشغيلية هي نسبة ساعات التشغيل المجدولة التي لم يكن فيها الجهاز متوقفاً.")
para("بيتا MLE بطريقة الإمكان الأعظم، وبيتا MRR بانحدار الرتب الوسيطة كما يُحسب في Excel. ولم تُحسب معلمات ويبل للجهاز STER-03 لأن أعطاله خمسة فقط. وطريقة الحساب مشروحة في الملحق د.")
# A-3 written fault vs root alarm
prim = [c for c in ctrl if c["code"] in ("A01", "A02", "A11", "A21")]
for w in wo:
    cand = [c for c in prim if c["device_id"] == w["device_id"] and w["reported_at"] - timedelta(hours=3) <= c["t"] <= w["reported_at"]]
    w["root"] = cand[-1] if cand else None
FA = {"Steam generator fault, scale suspected": "مولد البخار، اشتباه كلس", "Door seal leak": "تسرب مانع الباب", "Temperature deviation": "انحراف الحرارة", "Controller error": "خطأ في المتحكم", "Power problem": "مشكلة كهرباء"}
codes = ["A02", "A01", "A11", "A21", "-"]
ct = defaultdict(Counter)
for w in wo: ct[w["reported_fault"]][w["root"]["code"] if w["root"] else "-"] += 1
rows = [[FA.get(k, k)] + [ct[k][c] for c in codes] + [sum(ct[k].values())] for k in FA if k in ct]
rows.append(["المجموع"] + [sum(ct[k][c] for k in ct) for c in codes] + [len(wo)])
tab("جدول أ-3: ما كتبه الفني مقابل الإنذار الجذري في سجل المتحكم، الأجهزة الثلاثة", ["ما كتبه الفني", "A02 انقطاع", "A01 هبوط جهد", "A11 الباب", "A21 الحساس", "بلا إنذار", "المجموع"], rows)
# A-4 sources by device
def after(t):
    i = bisect_right(tt, t); return i > 0 and (t - tt[i - 1]).total_seconds() <= 60
src = defaultdict(Counter)
for w in wo:
    r = w["root"]
    if not r or r["code"] not in ("A01", "A02"): k = "genuine"
    elif any(abs((r["t"] - t).total_seconds()) <= 60 for t in tests): k = "test"
    elif r["code"] == "A02": k = "outage"
    else: k = "sag"
    src[w["device_id"]][k] += 1
lab = [("outage", "تحويل في انقطاع حقيقي للشبكة"), ("test", "تحويل في الاختبار الأسبوعي"), ("sag", "هبوط جهد دون تحويل"), ("genuine", "عطل حقيقي في الجهاز")]
rows = [[l] + [src[d][k] for d in DEV] for k, l in lab] + [["المجموع"] + [sum(src[d].values()) for d in DEV]]
tab("جدول أ-4: مصدر كل أمر عمل تصحيحي، لكل جهاز", ["المصدر", "STER-01", "STER-02", "STER-03"], rows)
# A-5 sag minutes from recorder
rec = pd.read_csv(D1 + "voltage_recorder.csv", parse_dates=["timestamp"])
low = rec[rec.v_min < 196].copy()
tts = pd.Series(sorted(tt))
low["transfer"] = low.timestamp.apply(lambda t: bool(((tts - t).abs() <= pd.Timedelta(minutes=2)).any()))
rows = [[r.timestamp.strftime("%Y-%m-%d %H:%M"), f1(r.v_min), f1(r.v_avg), "نعم" if r.transfer else "لا"] for r in low.itertuples()]
tab("جدول أ-5: كل دقيقة نزل فيها أدنى جهد تحت 196 فولتاً عند مقبس STER-01", ["الدقيقة", "أدنى جهد", "متوسط الجهد", "تحويل في سجل المولد خلال دقيقتين"], rows)
# ============================================================ B. Riyadh
L.append("---"); L.append("# الملحق ب: جداول قضية الرياض"); L.append("")
para("محسوبة من ملفات قضية الرياض الخام: ستون يوماً من 25 حزيران 2017، بعينات فرعية من خمس قراءات كل ساعتين. والمواصفة من 1.0 إلى 2.0 نيوتن متر.")
tq = pd.read_csv(D2 + "torque_subgroups_60days.csv", parse_dates=["timestamp"])
sg = tq.groupby("subgroup").agg(t=("timestamp", "first"), x=("removal_torque_nm", "mean"), r=("removal_torque_nm", lambda v: v.max() - v.min()), op=("operator", "first"), resin=("resin_lot", "first")).reset_index()
xbb, rb = sg.x.mean(), sg.r.mean(); ucl, lcl = xbb + 0.577 * rb, xbb - 0.577 * rb
sg["shift"] = sg.t.dt.hour.map(lambda h: "A" if 6 <= h < 14 else ("B" if 14 <= h < 22 else "C"))
pl = pd.read_csv(D2 + "purchase_log.csv", parse_dates=["first_use"])
sw = pl[pl.supplier == "Najd Resins"].first_use.min()
rows = []
for s_ in "ABC":
    for lab_, cond in [("قبل تغيير الراتنج", sg.t < sw), ("بعده", sg.t >= sw)]:
        x = sg[(sg["shift"] == s_) & cond]
        rows.append([s_, lab_, len(x), f3(x.x.mean()), f3(x.r.mean()), int((x.x > ucl).sum()), int((x.x < lcl).sum())])
tab("جدول ب-1: متوسط العينات الفرعية ومداها بحسب الوردية، قبل تغيير الراتنج وبعده", ["الوردية", "الفترة", "العينات", "متوسط X-bar", "متوسط R", "فوق الحد الأعلى", "تحت الحد الأدنى"], rows)
para(f"الحدود محسوبة من الستين يوماً كلها: المتوسط الكلي {f3(xbb)}، ومتوسط المدى {f3(rb)}، والحد الأعلى {f3(ucl)}، والحد الأدنى {f3(lcl)}. والورديات: A من السادسة صباحاً، وB من الثانية ظهراً، وC من العاشرة ليلاً.")
# B-2 hourly profile: ambient, mold temp, xbar
cl = pd.read_csv(D2 + "cooler_log.csv", parse_dates=["timestamp"]); mt = pd.read_csv(D2 + "mold_temperature.csv", parse_dates=["timestamp"])
rows = []
for h in range(0, 24, 2):
    rows.append([f"{h:02d}:00", f1(cl[cl.timestamp.dt.hour == h].ambient_c.mean()), f1(cl[cl.timestamp.dt.hour == h].chw_supply_c.mean()),
                 f1(mt[mt.timestamp.dt.hour == h].mold_temp_c.mean()), f3(sg[sg.t.dt.hour == h].x.mean())])
tab("جدول ب-2: اليوم المتوسط ساعة بساعة: حرارة الهواء، وماء المبرد، والقالب، والعزم", ["الساعة", "الهواء °م", "ماء المبرد °م", "القالب °م", "متوسط X-bar"], rows)
para("لاحظ أن الهواء يبلغ ذروته قرب الثالثة عصراً، والقالب كذلك، بينما يبلغ العزم ذروته في الساعة الثامنة عشرة. وهذا التأخير، ثلاث ساعات، هو زمن بقاء الأغطية في الصومعة.")
# B-3 gauge R&R ANOVA
g = pd.read_csv(D2 + "gauge_rr_study.csv")
p_, o_, n_ = g.part.nunique(), g.operator.nunique(), g.trial.nunique(); gm = g.reading_nm.mean()
ssp = o_ * n_ * ((g.groupby("part").reading_nm.mean() - gm) ** 2).sum()
sso = p_ * n_ * ((g.groupby("operator").reading_nm.mean() - gm) ** 2).sum()
cell = g.groupby(["part", "operator"]).reading_nm.mean()
sspo = n_ * ((cell - cell.index.get_level_values(0).map(g.groupby("part").reading_nm.mean()) - cell.index.get_level_values(1).map(g.groupby("operator").reading_nm.mean()) + gm) ** 2).sum()
sse = ((g.reading_nm - g.set_index(["part", "operator"]).index.map(cell)) ** 2).sum()
dfp, dfo, dfpo, dfe = p_ - 1, o_ - 1, (p_ - 1) * (o_ - 1), p_ * o_ * (n_ - 1)
msp, mso, mspo, mse = ssp / dfp, sso / dfo, sspo / dfpo, sse / dfe
vr = mse; vpo = max(0, (mspo - mse) / n_); vo = max(0, (mso - mspo) / (p_ * n_)); vp = max(0, (msp - mspo) / (o_ * n_))
vgrr = vr + vo + vpo; vt = vgrr + vp
rows = [["المصدر", "درجات الحرية", "مجموع المربعات", "متوسط المربعات"]]
anova = [["القطع", dfp, f"{ssp:.4f}", f"{msp:.4f}"], ["المشغلون", dfo, f"{sso:.4f}", f"{mso:.4f}"], ["تفاعل القطعة والمشغل", dfpo, f"{sspo:.4f}", f"{mspo:.4f}"], ["التكرار، أي الخطأ", dfe, f"{sse:.4f}", f"{mse:.4f}"]]
tab("جدول ب-3: جدول تحليل التباين لدراسة القياس، 10 قطع × 3 مشغلين × 3 تكرارات", rows[0], anova)
comp = [["التكرار، الجهاز", f3(math.sqrt(vr)), f"{100 * vr / vt:.1f}%", f"{100 * math.sqrt(vr / vt):.1f}%"],
        ["إعادة الإنتاج، المشغلون مع التفاعل", f3(math.sqrt(vo + vpo)), f"{100 * (vo + vpo) / vt:.1f}%", f"{100 * math.sqrt((vo + vpo) / vt):.1f}%"],
        ["نظام القياس كله GRR", f3(math.sqrt(vgrr)), f"{100 * vgrr / vt:.1f}%", f"{100 * math.sqrt(vgrr / vt):.1f}%"],
        ["القطع نفسها", f3(math.sqrt(vp)), f"{100 * vp / vt:.1f}%", f"{100 * math.sqrt(vp / vt):.1f}%"]]
tab("جدول ب-4: مكونات التباين في دراسة القياس", ["المكون", "الانحراف المعياري", "من التباين الكلي", "من الانحراف الكلي"], comp)
para(f"نسبة نظام القياس من عرض المواصفة: 6 × {f3(math.sqrt(vgrr))} ÷ 1.0 = {100 * 6 * math.sqrt(vgrr):.1f}%. وعدد الفئات المميزة: 1.41 × {f3(math.sqrt(vp))} ÷ {f3(math.sqrt(vgrr))} = {1.41 * math.sqrt(vp) / math.sqrt(vgrr):.1f}. والنسبة التي تُقارن بحدود الدليل المعتمد هي نسبة الانحراف، في العمود الأخير.")
# B-5 holds
h = pd.read_csv(D2 + "qc_holds.csv", parse_dates=["timestamp"])
DI = {"Released after retest": "أُفرج عنها بعد إعادة الفحص", "Reworked, recapped": "أعيدت تغطيتها"}
rows = [[r.hold_id, f"{r.timestamp.day} {AM[r.timestamp.month]}", r.timestamp.strftime("%H:%M"), r.lot.split("-")[0], f3(r.max_reading_nm), r.cases_held, f"{r.retest_over_usl} من {r.retest_n}", DI.get(r.disposition, r.disposition)] for r in h.itertuples()]
tab("جدول ب-5: الحجوزات الست عشرة، 2017، وكلها من دفعات الوردية B", ["الحجز", "اليوم", "الساعة", "الدفعة", "أعلى قراءة", "الكراتين", "فوق 2.0 عند إعادة الفحص", "القرار"], rows)
cc = pd.read_csv(D2 + "customer_complaints.csv")
rows = [[r.complaint_id, r.received_date, r.lot.split("-")[0], r.customer, r.bottles] for r in cc.itertuples()]
tab("جدول ب-6: شكاوى العملاء، كلها عن صعوبة فتح الغطاء، وكلها من دفعات الوردية B", ["الشكوى", "تاريخ الاستلام", "الدفعة", "العميل", "العبوات"], rows)
# ============================================================ C. Sohar
L.append("---"); L.append("# الملحق ج: جداول قضية صحار"); L.append("")
para("محسوبة من ملفات قضية صحار الخام، من أول كانون الثاني حتى آخر آب 2019. والطن في هذه الجداول طن أنابيب.")
o = pd.read_csv(D3 + "orders.csv", parse_dates=["received", "due_date", "shipped"])
b = pd.read_csv(D3 + "bundles.csv", parse_dates=["tube_mill_end", "yard_in", "kettle_start", "kettle_end"])
s = pd.read_csv(D3 + "kettle_stops.csv", parse_dates=["start", "end"]); kpi = pd.read_csv(D3 + "kpi_monthly_report.csv")
good = b[b.inspection == "PASS"]
grid = pd.date_range("2019-01-01", "2019-09-01", freq="h", inclusive="left")
add = pd.Series(b.tons.values, index=b.yard_in.values.astype("datetime64[h]")).groupby(level=0).sum().reindex(grid, fill_value=0)
rem = pd.Series(b.tons.values, index=b.kettle_start.fillna(pd.Timestamp("2030-01-01")).values.astype("datetime64[h]")).groupby(level=0).sum().reindex(grid, fill_value=0)
yard = (add - rem).cumsum()
o["leadtime"] = (o.shipped - o.received).dt.total_seconds() / 86400; o["late"] = (o.shipped.dt.normalize() - o.due_date).dt.days.clip(lower=0)
rows = []
for i, mth in enumerate(pd.period_range("2019-01", "2019-08", freq="M")):
    a, z = mth.start_time, (mth + 1).start_time; n = mth.days_in_month; sh = o[(o.shipped >= a) & (o.shipped < z)]
    k = kpi.iloc[i]
    rows.append([AM[mth.month], f1(o[(o.received >= a) & (o.received < z)].tons.sum() / n), f1(b[(b.tube_mill_end >= a) & (b.tube_mill_end < z)].tons.sum() / n),
                 f1(good[(good.kettle_end >= a) & (good.kettle_end < z)].tons.sum() / n), round(yard[z - pd.Timedelta(hours=1)]), f1(sh.leadtime.mean()), f1(100 * (sh.late == 0).mean()), f1(k.tube_mill_efficiency_pct), f1(k.kettle_efficiency_pct)])
tab("جدول ج-1: المصنع شهراً بشهر", ["الشهر", "طلبيات جديدة طن/يوم", "الخط طن/يوم", "الحوض السليم طن/يوم", "الساحة آخر الشهر طن", "زمن الطلبية يوم", "في الموعد %", "كفاءة الخط في التقرير %", "كفاءة الحوض في التقرير %"], rows)
PER = [("ورديتان", "2019-01-06", "2019-03-01"), ("ثلاث ورديات", "2019-03-01", "2019-06-09"), ("أسابيع التجربة الأولى", "2019-06-09", "2019-07-01"), ("بعد التجربة", "2019-07-01", "2019-09-01")]
rows = []; rows2 = []
for nm, a, z in PER:
    a, z = pd.Timestamp(a), pd.Timestamp(z); n = (z - a).days
    g_ = good[(good.kettle_end >= a) & (good.kettle_end < z)].tons.sum() / n; w_ = yard[(yard.index >= a) & (yard.index < z)].mean()
    bb = b[(b.kettle_start >= a) & (b.kettle_start < z)]; wt = ((bb.kettle_start - bb.yard_in).dt.total_seconds() / 86400 * bb.tons).sum() / bb.tons.sum()
    sh = o[(o.shipped >= a) & (o.shipped < z)]
    e_ = z - pd.Timedelta(days=1)
    rows.append([nm, f"{a.day} {AM[a.month]} إلى {e_.day} {AM[e_.month]}", f1(g_), round(w_), f1(w_ / g_), f2(wt), f1(sh.leadtime.mean()), f1(100 * (sh.late == 0).mean())])
    dh = (bb.kettle_end - bb.kettle_start).dt.total_seconds() / 3600; ss = s[(s.start >= a) & (s.start < z)]
    rows2.append([nm, f2(dh[bb.inspection == "PASS"].sum() / n), f2(dh[bb.inspection == "REJECT"].sum() / n)] + [f2(ss[ss.reason == r].minutes.sum() / 60 / n) for r in ["SHIFT_HANDOVER", "DROSS_CLEANING", "BREAKDOWN", "NO_MATERIAL"]])
tab("جدول ج-2: قانون ليتل في الفترات الأربع", ["الفترة", "من إلى", "الحوض السليم طن/يوم", "متوسط الساحة طن", "الساحة ÷ الإخراج يوم", "متوسط انتظار الطن يوم", "زمن الطلبية يوم", "في الموعد %"], rows)
para("الفترة الثالثة لا تحقق شرط الاستقرار في قانون ليتل، لأن الساحة كانت تفرغ خلالها. ولهذا يختلف فيها العمودان الخامس والسادس اختلافاً كبيراً. أما على الفترة كلها، من أول كانون الثاني حتى آخر آب، فينطبق القانون تماماً، كما في الفصل الثالث.")
tab("جدول ج-3: ساعات الحوض في اليوم في الفترات الأربع", ["الفترة", "جلفنة سليمة", "جلفنة مرفوضة", "تسليم الوردية", "تنظيف الخبث", "أعطال", "لا توجد حزم"], rows2)
tm = pd.read_csv(D3 + "tube_mill_shifts.csv", parse_dates=["date"])
rows = []
for nm, a, z in PER[:2] + PER[3:]:
    t2 = tm[(tm.date >= a) & (tm.date < z) & (tm.crew == "Y")]
    x = b[(b.tube_mill_end >= a) & (b.tube_mill_end < z) & b.inspection.isin(["PASS", "REJECT"])]
    rows.append([nm] + [f1(100 * (t2[t2["shift"] == k].ect == "OFF").mean()) if (t2["shift"] == k).any() else "لا وردية" for k in "ABC"] + [f2(100 * (x.inspection == "REJECT").mean())])
tab("جدول ج-4: نسبة الورديات التي أُطفئ فيها كاشف عيوب اللحام، ونسبة الرفض بعد الحوض", ["الفترة", "الوردية A %", "الوردية B %", "الوردية C %", "حزم مرفوضة %"], rows)
rows = []
for wk in pd.date_range("2019-05-19", "2019-07-28", freq="7D"):
    e = wk + pd.Timedelta(days=7)
    rows.append([f"{wk.day} {AM[wk.month]}", f1(good[(good.kettle_end >= wk) & (good.kettle_end < e)].tons.sum() / 7), f1(b[(b.tube_mill_end >= wk) & (b.tube_mill_end < e)].tons.sum() / 7),
                 round(yard[e - pd.Timedelta(hours=1)]), round(s[(s.start >= wk) & (s.start < e) & (s.reason == "NO_MATERIAL")].minutes.sum() / 60, 1)])
tab("جدول ج-5: الأسابيع حول التجربة، وقد بدأت يوم 9 حزيران", ["الأسبوع يبدأ", "الحوض السليم طن/يوم", "الخط طن/يوم", "الساحة آخر الأسبوع طن", "ساعات الحوض بلا حزم"], rows)
fin = pd.read_csv(D3 + "finance.csv").set_index("item").value
du = o[o.customer == "C-DUQM-WATER"]; rows = []
for nm, a, z in PER:
    x = du[(du.shipped >= a) & (du.shipped < z)]; val = x.tons * fin["selling_price"]
    rows.append([nm, len(x), int((x.late > 0).sum()), int(x.late.max()) if len(x) else 0, f"{round((val * (x.late * 0.005).clip(upper=0.10)).sum()):,}"])
tab("جدول ج-6: طلبيات مقاول الدقم وغرامات التأخير", ["الفترة", "طلبيات شُحنت", "متأخرة", "أطول تأخير يوم", "الغرامة بالريال"], rows)
para("كفاءة الخط في التقرير = أطنان الخط في الشهر ÷ (ساعات الطاقم × 5.7 طن في الساعة)، وكفاءة الحوض = أطنانه السليمة ÷ (24 ساعة × أيام الشهر × 3.75). فشباط مثلاً: 2204 ÷ (28 يوماً × 16 ساعة × 5.7) = 86.3%. والمعدلان القياسيان في الملف stations.csv.")
def fg_wait(t):
    gb = good[good.kettle_end <= t]; oo = o[(o.shipped > t) | o.shipped.isna()].order_id
    return gb[gb.order_id.isin(oo)].tons.sum()
rows = []
for nm, a, z in [PER[1], PER[3]]:
    a, z = pd.Timestamp(a), pd.Timestamp(z)
    days = pd.date_range(a, z - pd.Timedelta(days=1), freq="D") + pd.Timedelta(hours=12)
    fw = sum(fg_wait(t) for t in days) / len(days); yw = yard[(yard.index >= a) & (yard.index < z)].mean()
    rows.append([nm, round(yw), f"{round(yw * fin['wip_material_cost']):,}", round(fw), f"{round(fw * fin['steel_and_zinc_cost']):,}", f"{round(yw * fin['wip_material_cost'] + fw * fin['steel_and_zinc_cost']):,}"])
tab("جدول ج-7: المخزون في مكانين: الساحة قبل الحوض، وحزم مجلفنة تنتظر اكتمال طلبيتها", ["الفترة", "الساحة، طن", "قيمتها بالريال", "مجلفنة تنتظر، طن", "قيمتها بالريال", "المجموع بالريال"], rows)
para("قيمة الساحة بتكلفة المواد قبل الزنك، 296 ريالاً للطن، وقيمة الحزم المجلفنة بتكلفة الفولاذ والزنك، 322 ريالاً للطن، كما في الملف finance.csv. والحزمة المجلفنة لا تُشحن حتى تكتمل كل حزم طلبيتها.")
open(sys.argv[1], "w").write("\n".join(L)); print("lines", len(L))
