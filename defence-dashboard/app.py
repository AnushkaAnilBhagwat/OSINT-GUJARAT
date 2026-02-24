from flask import Flask, jsonify, render_template
import feedparser
import random
import re

app = Flask(__name__)

# =========================================
# NEWS SOURCES (MULTIPLE DEFENCE SOURCES)
# =========================================
NEWS_SOURCES = [
    "https://news.google.com/rss/search?q=defence+Gujarat",
    "https://news.google.com/rss/search?q=Indian+Navy+Gujarat",
    "https://news.google.com/rss/search?q=Indian+Army+Gujarat",
    "https://news.google.com/rss/search?q=military+base+Gujarat",
]

# Gujarat Geographic Bounds
LAT_MIN, LAT_MAX = 20.0, 24.7
LON_MIN, LON_MAX = 68.0, 74.5


# =========================================
# COLLECT & SUMMARIZE NEWS
# =========================================
def fetch_news():

    articles = []

    for source in NEWS_SOURCES:
        feed = feedparser.parse(source)

        for entry in feed.entries[:10]:

            summary = entry.get("summary", "")
            clean_summary = re.sub('<.*?>', '', summary)

            full_text = (entry.title + " " + clean_summary).lower()

            # Filter for Gujarat related keywords
            if any(keyword in full_text for keyword in [
                "gujarat", "ahmedabad", "kachchh", "rajkot",
                "porbandar", "bhuj", "vadodara", "surat"
            ]):

                sentences = clean_summary.split('.')
                short_summary = '.'.join(sentences[:2]) + '.'

                articles.append({
                    "title": entry.title,
                    "summary": short_summary,
                    "link": entry.link
                })

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


# =========================================
# MAIN DASHBOARD
# =========================================
@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)