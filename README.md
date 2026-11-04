# لعبة الهندسة الصناعية في ثلاث قضايا: البيانات والبرامج

هذا المستودع يرافق كتاب «لعبة الهندسة الصناعية في ثلاث قضايا» لرامز عساف. فيه كل ملفات البيانات التي بُنيت عليها القضايا الثلاث، والبرامج التي تولدها، والبرامج التي تحسب كل رقم وجدول وشكل في الكتاب.

والبيانات خيالية، تولدها البرامج بقيم ابتدائية ثابتة: 2014 لنابلس، و2017 للرياض، و2019 لصحار. فمن يشغل برامج التوليد يحصل على الملفات نفسها حرفاً بحرف.

## المحتوى

| المجلد | ما فيه |
|---|---|
| `data/01-case-nablus-sterilizer` | خمسة ملفات: أوامر العمل، ذاكرة المتحكم، سجل المولد، فحوص الماء، مسجل الجهد |
| `data/02-case-riyadh-quality` | تسعة ملفات: قراءات العزم، حرارة القالب، سجل المبرد، دراسة القياس، الحجوزات، الشكاوى، المشتريات، الأسعار، العروض |
| `data/03-case-sohar-flow` | سبعة ملفات: الطلبيات، تتبع الحزم، توقفات الحوض، ورديات الخط، التقرير الشهري، المعدلات، المالية |
| `scripts` | برامج التوليد والتحقق والجداول والأشكال |

## التشغيل

تحتاج Python 3، و`pandas` و`numpy` و`matplotlib`، وخط Amiri للأشكال (أو اضبط المتغير `AMIRI_DIR` على مجلد الخط).

```
pip install -r requirements.txt
python3 scripts/generate_nablus_data.py
python3 scripts/generate_riyadh_quality_data.py
python3 scripts/generate_sohar_data.py
python3 scripts/nablus_chapter_numbers.py         # أرقام الفصل الأول
python3 scripts/nablus_reliability_operating.py   # MTBF والإتاحة على ساعات التشغيل
python3 scripts/riyadh_quality_checks.py          # أرقام الفصل الثاني
python3 scripts/sohar_checks.py                   # أرقام الفصل الثالث
python3 scripts/appendix_tables.py out.txt        # جداول الملاحق أ وب وج
python3 scripts/charts_cases_1_2.py               # أشكال الفصلين الأول والثاني
python3 scripts/charts_case_3.py                  # أشكال الفصل الثالث
python3 scripts/concept_maps.py                   # الخرائط الذهنية
```

## للأساتذة

أعطِ طلابك ملفات القضية قبل الفصل، واطلب منهم أن يجدوا الإنذار الجذري في نابلس، أو سبب العزم المرتفع في الرياض، أو القيد في صحار، قبل أن يقرؤوا كيف وجده سامر.

## الترخيص

البرامج بترخيص MIT (الملف `LICENSE`). والبيانات بترخيص المشاع الإبداعي CC BY 4.0 (الملف `DATA_LICENSE.md`).

---

## English summary

Companion repository for the Arabic book *The Game of Industrial Engineering in Three Cases* by Ramiz Assaf. It holds the 21 synthetic CSV files behind the three cases (a hospital sterilizer in Nablus, a bottle-cap quality problem in Riyadh, a galvanizing constraint in Sohar), the fixed-seed generators that recreate them byte for byte, and the scripts that reproduce every number, table and figure in the book. Code: MIT. Data: CC BY 4.0.
