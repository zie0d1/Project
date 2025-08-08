from flask import Flask, render_template, request, jsonify
import requests
import xml.etree.ElementTree as ET
import os

app = Flask(__name__)

# إعدادات بسيطة — ضع مفتاحك هنا إن رغبت (اختياري)
32f7cafdf37959dd289c0bfe8003c1493f09 = os.environ.get("32f7cafdf37959dd289c0bfe8003c1493f09", None)
EMAIL = "your.email@example.com"  # ضع بريدك هنا للتوافق مع سياسات NCBI

def search_pubmed(query, retmax=3):
    """
    يبحث على PubMed ويجلب عناوين/مُلخصات محدودة (كمثال مبدأي).
    يعتمد على NCBI E-utilities (esearch + efetch).
    """
    base_esearch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "xml",
        "email": EMAIL
    }
    if 32f7cafdf37959dd289c0bfe8003c1493f09:
        params["api_key"] = 32f7cafdf37959dd289c0bfe8003c1493f09

    r = requests.get(base_esearch, params=params, timeout=15)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    ids = [id_el.text for id_el in root.findall(".//Id")]
    summaries = []
    if ids:
        # efetch to get summaries/abstracts
        base_efetch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params2 = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml", "email": EMAIL}
        if 32f7cafdf37959dd289c0bfe8003c1493f09:
            params2["api_key"] = 32f7cafdf37959dd289c0bfe8003c1493f09
        r2 = requests.get(base_efetch, params=params2, timeout=15)
        r2.raise_for_status()
        root2 = ET.fromstring(r2.text)
        for article in root2.findall(".//PubmedArticle"):
            title_el = article.find(".//ArticleTitle")
            abstract_el = article.find(".//Abstract/AbstractText")
            title = title_el.text if title_el is not None else ""
            abstract = abstract_el.text if abstract_el is not None else ""
            summaries.append({"title": title, "abstract": abstract})
    return summaries

def synthesize_sections(query, pubmed_summaries):
    """
    طريقة مبسطة لاستخراج أقسام: تعريف، سبب/عائلة فيروسية، طرق انتقال، الوقاية/علاج، مصادر.
    هذه نسخة أولية: تحسّن المعالجة الطبيعية للنص مطلوب لاحقًا (NLP, summarization).
    """
    definition = ""
    cause = ""
    transmission = ""
    prevention = ""
    refs = []

    # أخذ أول ملخص كتعريف مبدئي
    if pubmed_summaries:
        definition = pubmed_summaries[0].get("abstract", "")[:800]
    # توليد نص تجريبي من بقية المُلخصات
    for s in pubmed_summaries:
        text = (s.get("abstract") or "").strip()
        if not text:
            continue
        refs.append(s.get("title","")[:150])
        # تقسيم بسيط بحسب كلمات مفتاحية
        lower = text.lower()
        if "transmission" in lower or "transmit" in lower or "contact" in lower or "bite" in lower:
            transmission += text + "\n\n"
        elif "vaccine" in lower or "prevention" in lower or "treatment" in lower or "therapy" in lower:
            prevention += text + "\n\n"
        elif "virus" in lower or "viridae" in lower or "rhabdo" in lower:
            cause += text + "\n\n"
        else:
            # افتراضي نضعه في تعريف أو الوقاية بحسب الطول
            if len(definition) < 200:
                definition += "\n\n" + text
            else:
                prevention += "\n\n" + text

    # إن لم نجد أقسام، نؤدي بعض القيم الافتراضية القصيرة
    if not cause:
        cause = "لم تتوفر معلومات محددة عن عائلة الفيروس في النتائج المختارة."
    if not transmission:
        transmission = "المصادر المختارة تشير أن أسلوب الانتقال يتعلق عادةً بعضات/لعاب الحيوانات المصابة والتلامس المباشر."
    if not prevention:
        prevention = "الوقاية تعتمد على التطعيم، التعليم، والعزل للحالات المشتبه بها. راجع مراجع إضافية."

    return {
        "title": query,
        "definition": definition,
        "cause": cause,
        "transmission": transmission,
        "prevention": prevention,
        "references": refs
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.json or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error":"empty query"}), 400
    try:
        summaries = search_pubmed(query, retmax=4)
        out = synthesize_sections(query, summaries)
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
