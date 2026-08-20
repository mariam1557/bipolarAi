# Bipolar RAG — Clinical Decision Support (Day 2 + Day 3)

نقلنا كود الـ Colab لمشروع VS Code منظم. البنية:

```
bipolar-rag/
├── .env.example          # انسخيه لـ .env وحطي فيه الـ Gemini API key
├── requirements.txt
├── data/pdfs/             # حطي هنا ilovepdf_merged.pdf (الملف المدمج اللي على الدرايف)
├── eval/
│   └── Day2_Evaluation_Test_Set_Bipolar.xlsx
├── chroma_db/             # هيتعمل تلقائي أول مرة تشغّلي build_index.py
└── src/
    ├── config.py          # بيانات الفصول + اسم الموديل + إعدادات
    ├── ingest.py          # قراءة ilovepdf_merged.pdf وتقطيعه لـ chunks (Day 2)
    ├── build_index.py     # عمل الـ embeddings وتخزينها في ChromaDB
    ├── rag.py             # search() + grounded_answer() بصيغة الـ Day 3 (Recommendation/Excerpt/Citation + Refusal)
    ├── evaluate.py         # Precision@k على test_questions الداخلية + على ملف الإكسل الرسمي
    └── cli.py              # سؤال وجواب من التيرمينال
```

## التشغيل خطوة بخطوة

```bash
cd bipolar-rag
python -m venv venv
source venv/bin/activate        # على ويندوز: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # وحطي GEMINI_API_KEY جواه

# 1) نزّلي ilovepdf_merged.pdf من الدرايف وحطيه في data/pdfs/
python src/evaluate.py            # يكتشف الفصول ورقم الصفحة تلقائيًا وينتج data/all_chunks.json

# 2) بناء الفهرس (الموديل الافتراضي دلوقتي gte-base — استقريتِ عليه بعد المقارنة)
python src/build_index.py

# 3) اسألي أي سؤال
python src/cli.py "What medication is recommended for acute mania?"

# 4) تقييم الدقة (Precision@k) — بيستخدم نفس أسئلة الكولاب + ملف الإكسل الرسمي
python src/evaluate.py
```

## اللي اتغيّر عن نسخة الكولاب

- **ملف PDF واحد بدل تسعة**: `ingest.py` بيقرأ `ilovepdf_merged.pdf` ويكتشف بداية كل فصل ورقم الصفحة الحقيقي تلقائيًا من الهيدر المتكرر ("Bipolar disorder (update)  N") — اتجربت فعليًا على ملفك وطلعت 149 chunk بالظبط موزعة صح على الـ 9 فصول ومفيش أي section مشبوه.
- **الموديل الافتراضي بقى `gte-base`** زي ما استقريتِ عليه بعد مقارنة الـ 7 موديلات (كان في `config.py`، سطر واحد لو عايزة تغيّريه تاني).
- **منطق التقطيع (chunking)**: نفس أحدث نسخة عندك في الكولاب (بتتحقق من صحة section number وبتعالج مشكلة فصل 10 — كانت خلية 14).
- **`grounded_answer` بقت متوافقة مع سبيسيفكيشن Day 3**:
  - الرد بقى بالشكل: **Recommendation → Excerpt → Citation** (مش نص حر مع `[Source 1]`).
  - صيغة الاقتباس بقت `[Document Name, Section X.Y, Page N]` بالظبط زي ما مطلوب في الديك.
  - أضفت **Refusal logic**: لو أعلى نتيجة تشابه أضعف من threshold (قابل للتعديل في `config.py`) الموديل يرفض بدل ما يخترع إجابة — ده الحاجة اللي ملف التقييم `Day2_Evaluation_Test_Set_Bipolar.xlsx` بيختبرها (أسئلة "Not covered by this source — expected refusal").
  - الـ system prompt بقى صريح إنه ممنوع يستخدم أي معرفة برا الـ context، ومطلوب يرفض بدل ما "يلين" الرفض — زي ما مكتوب في المودیول 1 و 3 بالديك.
- الـ Gemini API key بقى بييجي من `.env` مش `getpass` (أفضل لبيئة VS Code/الترمينال).

## ملاحظة عن ملف evaluate.py

بيقرأ نفس test_questions اللي كانت في الكولاب (Precision@k)، وكمان بيحاول يقرأ `eval/Day2_Evaluation_Test_Set_Bipolar.xlsx` عشان يقولك لكل سؤال فيه: هل النظام رفض صح لما لازم يرفض، وهل بيّن الـ citation صح.
