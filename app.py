from flask import Flask, jsonify, render_template
import feedparser
import random
import re
from groq import Groq
import os
from newspaper import Article
import time

app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# =========================================
# NEWS SOURCES (MULTIPLE DEFENCE SOURCES)
# =========================================
NEWS_SOURCES = [
    "https://news.google.com/rss/search?q=defence+Gujarat",
    "https://news.google.com/rss/search?q=Indian+Navy+Gujarat",
    "https://news.google.com/rss/search?q=Indian+Army+Gujarat",
    "https://news.google.com/rss/search?q=military+base+Gujarat",
    "https://news.google.com/rss/search?q=Indian+Air+Force+Gujarat",
    "https://news.google.com/rss/search?q=Pakistan+Gujarat",
]

# Gujarat Geographic Bounds
LAT_MIN, LAT_MAX = 20.0, 24.7
LON_MIN, LON_MAX = 68.0, 74.5


cached_articles = []
last_fetch_time = 0

# =========================================
# COLLECT & SUMMARIZE NEWS
# =========================================

def extract_clean_content(entry):
    content = ""

    # Try content field first (many feeds store full content here)
    if "content" in entry:
        content = entry.content[0].value

    # Fallback to summary
    elif "summary" in entry:
        content = entry.summary

    # Fallback to description
    elif "description" in entry:
        content = entry.description

    # Remove HTML tags
    clean_text = re.sub('<.*?>', '', content).strip()

    return clean_text

def get_full_article_text(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except:
        return ""

def fetch_news():
    global cached_articles, last_fetch_time
    
    if time.time() - last_fetch_time < 600 and cached_articles:
        return cached_articles

    articles = []

    for source in NEWS_SOURCES:
        feed = feedparser.parse(source)

        for entry in feed.entries[:5]:
            # 1. Try to get full text
            full_text = get_full_article_text(entry.link)
            
            # 2. FALLBACK: If full text failed, use the feed's snippet
            if not full_text:
                full_text = extract_clean_content(entry)

            # 3. Create summary from whatever text we managed to get
            if full_text:
                # Better sentence splitting logic
                sentences = [s.strip() for s in re.split(r'[.!?]', full_text) if s.strip()]
                short_summary = '. '.join(sentences[:3])
                if short_summary:
                    short_summary += '.'
            else:
                short_summary = "No summary available."

            articles.append({
                "title": entry.title,
                "summary": short_summary,
                "link": entry.link
            })
            
    cached_articles = articles
    last_fetch_time = time.time()
    return articles


# =========================================
# GUJARAT HEATMAP API
# =========================================

CITY_COORDS = {
    "ahmedabad": (23.0225, 72.5714),
    "rajkot": (22.3039, 70.8022),
    "porbandar": (21.6417, 69.6293),
    "bhuj": (23.2420, 69.6669),
    "surat": (21.1702, 72.8311),
    "vadodara": (22.3072, 73.1812)
}


@app.route("/api/heatmap")
def heatmap():

    articles = fetch_news()

    heat_points = []
    geo_articles = []

    GUJARAT_COAST = (21.5, 69.5)

    for article in articles:

        text = (article["title"] + article["summary"]).lower()
        assigned = False

        # 1️⃣ Exact City Match
        for city, coords in CITY_COORDS.items():
            if city in text:
                lat, lon = coords
                assigned = True
                break

        # 2️⃣ Naval / Coastal Keyword
        if not assigned and any(word in text for word in [
            "navy", "naval", "coast", "port", "ship", "fleet"
        ]):
            lat, lon = GUJARAT_COAST
            assigned = True

        # 3️⃣ If no match → RANDOM inside Gujarat
        if not assigned:
            lat = random.uniform(LAT_MIN, LAT_MAX)
            lon = random.uniform(LON_MIN, LON_MAX)

        # Small jitter to prevent exact overlap
        lat += random.uniform(-0.2, 0.2)
        lon += random.uniform(-0.2, 0.2)

        heat_points.append([lat, lon, 0.8])

        geo_articles.append({
            "title": article["title"],
            "summary": article["summary"],
            "link": article["link"],
            "lat": lat,
            "lon": lon
        })

    return jsonify({
        "heat": heat_points,
        "articles": geo_articles
    })



# =========================================
# NEWSLETTER API
# =========================================
@app.route("/api/newsletters")
def newsletters():
    articles = fetch_news()
    return jsonify(articles[:25])


@app.route("/api/ai-analysis")
def ai_analysis():
    articles = fetch_news()   # your existing RSS function

    if not articles:
        return jsonify({"analysis": "No news available for analysis."})

    try:
        analysis = analyze_news_with_ai(articles)
        return jsonify({"analysis": analysis})
    except Exception as e:
        return jsonify({"analysis": f"AI Error: {str(e)}"})
    
def analyze_news_with_ai(articles):

    combined_text = ""

    for article in articles:
        combined_text += f"{article['title']}. {article['summary']}\n"

    combined_text = combined_text[:4000]

    prompt = f"""
You are an Indian defence intelligence analyst.

Provide a structured strategic assessment of the following news which will benefit Indian Armed Forces.

Output Format:

Strategic Value: High / Medium / Low

### Strategic Themes
### Operational Impact
### Maritime/Border Implications
### Geopolitical Signals
### Strategic Outlook

News:
{combined_text}
"""

    response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
            {"role": "system", "content": "You are a strategic defence analyst."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content

# =========================================
# MAIN DASHBOARD
# =========================================
@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)