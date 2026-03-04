from flask import Flask, jsonify, render_template, request
import requests
import random
import re
from groq import Groq
import os
from newspaper import Article
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

global_intel_store = {
    "articles": [],
    "last_updated": 0,
    "metadata": {}
}

INDIAN_STATES = {
    "Andaman and Nicobar Islands": (11.7401, 92.6586),
    "Andhra Pradesh": (15.9129, 79.7400),
    "Arunachal Pradesh": (28.2180, 94.7278),
    "Assam": (26.2006, 92.9376),
    "Bihar": (25.0961, 85.3131),
    "Chandigarh": (30.7333, 76.7794),
    "Chhattisgarh": (21.2787, 81.8661),
    "Dadra and Nagar Haveli and Daman and Diu": (20.3974, 72.8328),
    "Delhi": (28.7041, 77.1025),
    "Goa": (15.2993, 74.1240),
    "Gujarat": (22.2587, 71.1924),
    "Haryana": (29.0588, 76.0856),
    "Himachal Pradesh": (31.1048, 77.1734),
    "Jammu and Kashmir": (33.7782, 76.5762),
    "Jharkhand": (23.6102, 85.2799),
    "Karnataka": (15.3173, 75.7139),
    "Kerala": (10.8505, 76.2711),
    "Ladakh": (34.1526, 77.5770),
    "Lakshadweep": (10.5667, 72.6417),
    "Madhya Pradesh": (22.9734, 78.6569),
    "Maharashtra": (19.7515, 75.7139),
    "Manipur": (24.6637, 93.9063),
    "Meghalaya": (25.4670, 91.3662),
    "Mizoram": (23.1645, 92.9376),
    "Nagaland": (26.1584, 94.5624),
    "Odisha": (20.9517, 85.0985),
    "Puducherry": (11.9416, 79.8083),
    "Punjab": (31.1471, 75.3412),
    "Rajasthan": (27.0238, 74.2179),
    "Sikkim": (27.5330, 88.5122),
    "Tamil Nadu": (11.1271, 78.6569),
    "Telangana": (18.1124, 79.0193),
    "Tripura": (23.9408, 91.9882),
    "Uttar Pradesh": (26.8467, 80.9462),
    "Uttarakhand": (30.0668, 79.0193),
    "West Bengal": (22.9868, 87.8550)
}

INTEL_KEYWORDS = [
    "military activity",
    "non state actors",
    "hacktivists",
    "internal actors",
    "Artificial Intelligence",
    "paramilitary",
    "Indian Navy",
    "Indian Army",
    "border tension",
    "maritime security",
    "Anti-Terrorism Squad"
]

# Gujarat Geographic Bounds
LAT_MIN, LAT_MAX = 20.0, 24.7
LON_MIN, LON_MAX = 68.0, 74.5


cached_articles = {}

# =========================================
# COLLECT & SUMMARIZE NEWS
# =========================================

def get_ai_summary(text):
    if not text or len(text) < 100:
        return None

    try:
        # Groq specific call
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Reliable model on Groq
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional news editor. Summarize the following news article in exactly two clear sentences."
                },
                {
                    "role": "user", 
                    "content": text[:3000] # Send only the first 3000 chars to avoid token limits
                }
            ],
            temperature=0.5,
            max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        # This will print the actual error to your terminal so you can see what's wrong
        print(f"AI Error: {e}")
        return None

@app.route("/api/fetch-all-intel")
def fetch_all_intel():
    """Master function to refresh all dashboard data at once."""
    global global_intel_store
    
    # 1. Capture UI Parameters
    keyword = request.args.get("keyword")
    location = request.args.get("location", "Gujarat")
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    sources = request.args.get("sources", "news").split(",")

    all_articles = []

    # 2. Fetch News if selected
    if "news" in sources:
        news_data = fetch_news(
            keyword=keyword, 
            location=location, 
            from_date=from_date, 
            to_date=to_date
        )
        for art in news_data:
            # Tag each article so the frontend knows how to color it
            art["source"] = "News"
            all_articles.append(art)

    # 3. Update the Global Store
    global_intel_store["articles"] = all_articles
    global_intel_store["metadata"] = {"location": location, "keyword": keyword}
    global_intel_store["last_updated"] = time.time()

    # 4. Generate Heatmap Points
    base_coords = INDIAN_STATES.get(location, (20.5937, 78.9629))
    heat_points = []
    geo_articles = []

    for article in all_articles:
        # Distribute points around the selected state center
        lat = base_coords[0] + random.uniform(-1.0, 1.0)
        lon = base_coords[1] + random.uniform(-1.0, 1.0)
        
        heat_points.append([lat, lon, 0.7])
        geo_articles.append({**article, "lat": lat, "lon": lon, "source": article.get("source", "News")})

    return jsonify({
        "heat": heat_points,
        "articles": geo_articles,
        "center": base_coords
    })
    
def fetch_news(keyword=None, location=None, from_date=None, to_date=None):
    global cached_articles

    # Construct a robust search query combining keyword and location
    search_query = ""
    if keyword and location:
        search_query = f"{keyword} AND {location}"
    elif location:
        search_query = f'"{location}"'
    else:
        search_query = " OR ".join(INTEL_KEYWORDS)

    cache_key = f"{search_query}_{from_date}_{to_date}"

    if (cache_key in cached_articles and time.time() - cached_articles[cache_key]["time"] < 600):
        return cached_articles[cache_key]["data"]

    url = "https://newsapi.org/v2/everything"
    params = {
        # 'qInTitle' ensures the keywords MUST be in the headline
        "q": search_query, 
        "language": "en",
        "sortBy": "relevancy",
        "apiKey": NEWS_API_KEY,
        "pageSize": 50
    }
    if from_date: params["from"] = from_date
    if to_date: params["to"] = to_date

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return []

    data = response.json()
    articles = []

    for item in data.get("articles", []):
        try:
            dt = datetime.strptime(item["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
        except:
            dt = datetime.now()

        # Get AI summary or fallback
        raw_text = item.get("content") or item.get("description") or item.get("title")
        short_summary = get_ai_summary(raw_text)
        if not short_summary:
            short_summary = item.get("description") or item.get("title")

        articles.append({
            "title": item["title"],
            "summary": short_summary,
            "link": item["url"],
            "published": dt.strftime("%b %d, %Y"),
            "published_dt": dt
        })

    cached_articles[cache_key] = {"data": articles, "time": time.time()}
    return articles


@app.route("/api/heatmap")
def heatmap():
    keyword = request.args.get("keyword")
    location_name = request.args.get("location", "Gujarat")
    from_date = request.args.get("from")
    to_date = request.args.get("to")

    # Fetch news using ALL filters
    articles = fetch_news(
        keyword=keyword, 
        location=location_name, 
        from_date=from_date, 
        to_date=to_date
    )
    
    # Get base coordinates for the selected state to center the heatmap
    base_coords = INDIAN_STATES.get(location_name, (22.2587, 71.1924))
    
    heat_points = []
    geo_articles = []

    for article in articles:
        # Generate jittered coordinates around the state center
        # We use a 1.0 degree spread to cover the state area roughly
        lat = base_coords[0] + random.uniform(-0.8, 0.8)
        lon = base_coords[1] + random.uniform(-0.8, 0.8)

        heat_points.append([lat, lon, 0.7]) # Intensity 0.7
        
        geo_articles.append({
            "title": article["title"],
            "summary": article["summary"],
            "link": article["link"],
            "published": article["published"],
            "lat": lat,
            "lon": lon
        })      

    return jsonify({
        "heat": heat_points,
        "articles": geo_articles,
        "center": base_coords # Return center to help frontend re-focus
    })


# =========================================
# NEWSLETTER API
# =========================================
@app.route("/api/newsletters")
def newsletters():
    # Uses pre-loaded articles from the global store
    return jsonify(global_intel_store["articles"][:25])


@app.route("/api/ai-analysis")
def ai_analysis():
    # Uses pre-loaded articles from the global store
    articles = global_intel_store["articles"]
    
    if not articles:
        return jsonify({"analysis": "No pre-loaded data found. Please run a Scan first."})

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