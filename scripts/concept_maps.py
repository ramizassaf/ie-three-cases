"""One-page concept maps: problem -> hypotheses -> data -> tools -> decision -> result."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
FB = font_manager.FontProperties(fname=os.path.join(os.environ.get("AMIRI_DIR", "/usr/share/fonts/opentype/fonts-hosny-amiri"), "Amiri-Bold.ttf"))
FR = font_manager.FontProperties(fname=os.path.join(os.environ.get("AMIRI_DIR", "/usr/share/fonts/opentype/fonts-hosny-amiri"), "Amiri-Regular.ttf"))
NAVY, ORANGE, GREEN, RED, INK, MUTED, BG = "#1F3A4D", "#C9541F", "#1a8a5a", "#b8322a", "#1b1b1b", "#6b6a66", "#f5f2ea"
STEPS = ["المشكلة", "الفرضيات", "البيانات", "الأدوات", "القرار", "النتيجة"]
COL = [NAVY, ORANGE, "#3f6e8c", "#3f6e8c", NAVY, GREEN]
def draw(name, title, boxes, lesson):
    W, H = 100, 145
    f = plt.figure(figsize=(4.6, 6.67), dpi=240); ax = f.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    ax.text(W - 4, H - 5, title, fontproperties=FB, fontsize=13, color=NAVY, ha="right", va="center")
    ax.plot([4, W - 4], [H - 9.5, H - 9.5], color=ORANGE, lw=1.2)
    LH = 4.5; PAD = 2.6; gap = 3.4
    heights = [max(2 * PAD + LH * len(b), 9) for b in boxes]
    total = sum(heights) + gap * 5; avail = (H - 13) - 15
    extra = (avail - total) / 6 if total < avail else 0
    heights = [h + extra for h in heights]
    y = H - 13
    for i, (lines, h) in enumerate(zip(boxes, heights)):
        top = y; bot = y - h
        ax.add_patch(FancyBboxPatch((4, bot), W - 8, h, boxstyle="round,pad=0,rounding_size=1.6", fc=BG, ec=COL[i], lw=1.1))
        ax.add_patch(FancyBboxPatch((W - 21, bot), 17, h, boxstyle="round,pad=0,rounding_size=1.6", fc=COL[i], ec="none"))
        ax.text(W - 12.5, (top + bot) / 2, f"{i+1}\n{STEPS[i]}", fontproperties=FB, fontsize=8.6, color="white", ha="center", va="center", linespacing=1.3)
        ly = (top + bot) / 2 + LH * (len(lines) - 1) / 2
        for ln in lines:
            mark = None
            if ln.startswith("✗"): mark, ln = RED, ln[1:].strip()
            elif ln.startswith("✓"): mark, ln = GREEN, ln[1:].strip()
            x = W - 24
            if mark:
                ax.add_patch(Circle((W - 24.6, ly + 0.2), 0.9, color=mark)); x = W - 27
            ax.text(x, ly, ln, fontproperties=FR, fontsize=7.1, color=INK, ha="right", va="center")
            ly -= LH
        y = bot - gap
        if i < 5: ax.add_patch(FancyArrowPatch(((W - 25) / 2 + 2, bot - 0.2), ((W - 25) / 2 + 2, bot - gap + 0.3), arrowstyle="-|>", mutation_scale=7, color=MUTED, lw=0.9))
    ax.add_patch(FancyBboxPatch((4, 3), W - 8, 9, boxstyle="round,pad=0,rounding_size=1.6", fc=NAVY, ec="none"))
    ax.text(W / 2, 7.5, lesson, fontproperties=FB, fontsize=8.2, color="white", ha="center", va="center")
    ax.add_patch(Circle((8, H - 5), 0.9, color=RED)); ax.text(10.2, H - 5, "مرفوضة", fontproperties=FR, fontsize=6.5, color=MUTED, ha="left", va="center")
    ax.add_patch(Circle((21, H - 5), 0.9, color=GREEN)); ax.text(23.2, H - 5, "مقبولة", fontproperties=FR, fontsize=6.5, color=MUTED, ha="left", va="center")
    f.savefig(os.path.join(ROOT, "figures", f"{name}.png"), facecolor="white"); plt.close(f)
draw("c1_map", "خريطة القضية الأولى: المعقّم الذي لم يكن مريضاً", [
 ["جهازا المبنى A يتوقفان مرة كل سبعة أيام عمل، 63 عطلاً لكل منهما.", "والحل المقترح: شراء جهاز جديد بدل STER-01."],
 ["✗ العمر: STER-02 أحدث بست سنوات، وأعطاله مثل STER-01.", "✗ الكلس والماء: أسوأ ماء جاء في أقل الأسابيع أعطالاً.", "✗ الحمل: الثلاثاء من أقل الأيام دورات، و27.9 عطلاً لكل ألف دورة.", "✓ الكهرباء: 126 من 131 إنذاراً جذرياً كهربائي.", "✓ الاختبار الأسبوعي وهبوط الجهد: 43 و19 عطلاً."],
 ["أوامر العمل، وذاكرة المتحكم، وسجل مفتاح التحويل،", "وفحوص الماء، ومسجل جهد صنعه سامر بنفسه."],
 ["الإنذار الجذري والتسلسل الزمني، ومعدل لكل ألف دورة،", "MTBF والإتاحة على ساعات التشغيل، ومطابقة الستين ثانية، وويبل."],
 ["نقل الاختبار إلى الجمعة بلا تكلفة، ونموذج أمر عمل جديد،", "ومزود طاقة غير منقطعة للوحة DB-A2، والقياس بعد كل خطوة."],
 ["122 من 126 عطلاً سببها الكهرباء، و4 فقط أعطال حقيقية.", "نقل الاختبار وحده يزيل 43 أمر عمل، وسُحب طلب الشراء."]],
 "الفني كتب رأيه، والجهاز كتب ما حدث")
draw("c2_map", "خريطة القضية الثانية: الغطاء الذي لا يُفتح", [
 ["16 حجزاً وشكاوى «الغطاء لا يُفتح»، كلها في الوردية B.", "والحل المقترح: آلة تغطية جديدة بـ 1,850,000 ريال."],
 ["✗ الرؤوس اهترأت: مدى آثار الرؤوس 0.016، والصدفة وحدها 0.015.", "✗ الراتنج الجديد: 1.495 مقابل 1.498 عند حرارة القالب نفسها.", "✓ حرارة القالب قبل ثلاث ساعات: الارتباط 0.75.", "✓ المبرد يفقد السيطرة فوق 42.5 درجة.", "✓ تحيز قياس في الليل: −0.085 نيوتن متر."],
 ["3600 قراءة عزم، وحرارة القالب، وسجل المبرد، ودراسة القياس،", "وأوامر شراء الراتنج، والحجوزات، والشكاوى، وعروض الأسعار."],
 ["مخططا X-bar وR، وقاعدة الثماني نقاط، وCpk مقابل Ppk،", "والتقسيم الطبقي، والارتباط المتأخر، وGauge R&R، والاختبار المحجوز."],
 ["مثبت لجهاز العزم وتدريب بـ 18,000 ريال، ومبرد مسبق بـ 85,000،", "ومراقبة حرارة القالب، والبقاء على الراتنج الجديد، وسحب عرض الآلة."],
 ["103,000 ريال بدل 1,850,000، والقراءات فوق 2.0 من 31 إلى 1 بالحساب.", "واختفى تحيز المشغل الليلي، وسُحب الإنذار عنه."]],
 "كل قراءة ثلاثة أشياء: المقاس، والأداة، والإنسان")
draw("c3_map", "خريطة القضية الثالثة: الحوض الذي لا ينام", [
 ["65.8% فقط من الطلبيات في موعدها رغم وردية ثالثة على الخط.", "وغرامات تأخير لمقاول الدقم، وتقرير يتهم طاقم الليل."],
 ["✗ طاقم الليل كسول: الخط ينتظر 29.2% من ساعات طاقمه.", "✓ الحوض هو القيد حتى حزيران: لا ينتظر دقيقة واحدة.", "✓ ساعات القيد تضيع: 2.46 ساعة يومياً في تسليم الوردية.", "✓ الكاشف المطفأ: رفض 5.77% مقابل 0.64%.", "✗ البطاقات الملونة تكفي: الأحدث أولاً من 74.8% إلى 72.6% فقط."],
 ["الطلبيات، وتتبع 7453 حزمة، وتوقفات الحوض، وورديات الخط،", "والتقرير الشهري، والمعدلات الاسمية، والأسعار والتكاليف."],
 ["قانون ليتل: 343.4 = 73.3 × 4.683، وتحليل ساعات المحطتين،", "وميزانية ساعات القيد، والرفض بحسب الكاشف، وتوزيع الانتظار."],
 ["خطة أنيل للتسليم المتداخل، وكاشف دائم، وصفوف بحسب الموعد،", "وورديتان وحبل عند 150 طناً. ولم تُبلَّغ المبيعات، وكان هذا خطأً."],
 ["الحوض من 71.0 إلى 80.5 طن يومياً، وتحرر نحو 960 ألف ريال من المخزون.", "لكن القيد انتقل إلى السوق، وخسر المصنع المرحلة القادمة من الدقم."]],
 "إن انكسر القيد، فابحث عنه من جديد، وقد يكون خارج المصنع")
print("ok")
