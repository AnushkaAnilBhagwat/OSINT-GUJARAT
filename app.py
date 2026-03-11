from flask import Flask, jsonify, render_template, request
import requests
import random
from groq import Groq
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from requests_oauthlib import OAuth1


load_dotenv()
app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

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
    global global_intel_store
    keyword = request.args.get("keyword")
    location = request.args.get("location", "Gujarat")
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    sources = request.args.get("sources", "news").split(",")

    all_articles = []

    # 1. Standalone Twitter Block
    if "twitter" in sources:
        twitter_data = fetch_twitter(keyword, location, from_date, to_date)
        for tw in twitter_data:
            tw["source"] = "Twitter" # Ensure it's tagged as Twitter
            all_articles.append(tw)

    # 2. Standalone News Block
    if "news" in sources:
        news_data = fetch_news(keyword, location, from_date, to_date)
        for art in news_data:
            art["source"] = "News"
            all_articles.append(art)

    global_intel_store["articles"] = all_articles
    
    base_coords = INDIAN_STATES.get(location, (20.59, 78.96))
    heat_points = []
    geo_articles = []

    for article in all_articles:
        lat = base_coords[0] + random.uniform(-0.1, 0.1)
        lon = base_coords[1] + random.uniform(-0.1, 0.1)
        heat_points.append([lat, lon, 0.7])
        # Pass the original source key through to the frontend
        geo_item = article.copy()
        geo_item.update({
            "lat": lat,
            "lon": lon,
            "source": article.get("source", "News")
        })
        geo_articles.append(geo_item)
        
    return jsonify({"heat": heat_points, "articles": geo_articles, "center": base_coords})

def fetch_twitter(keyword=None, location=None, from_date=None, to_date=None):
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    headers = {"Authorization": f"Bearer {bearer_token}"}
    
    # Query building
    query = f"{keyword} {location} (defence OR military OR security) -is:retweet"
    url = "https://api.twitter.com/2/tweets/search/recent"
    
    params = {
        "query": query,
        "max_results": 10,
        "tweet.fields": "created_at,text",
    }

    # API Request (Removed auth=auth to fix conflict)
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"Twitter Error: {response.text}")
        return []

    data = response.json()
    tweets = []
    for item in data.get("data", []):
        tweets.append({
            "title": item["text"][:50] + "...",
            "summary": item["text"],
            "link": f"https://twitter.com/user/status/{item['id']}",
            "published": item["created_at"][:10],
            "source": "Twitter"
        })
    return tweets

   
def fetch_news(keyword=None, location=None, from_date=None, to_date=None):
    global cached_articles

    # Use a specific term for the frequency check
    # If no keyword is selected, we fall back to "defence" as the primary threat term
    if keyword and keyword != "None":
        search_query = f"{keyword} {location}"
    else:
        search_query = f"{location} defence"
        
    cache_key = f"{search_query}_{from_date}_{to_date}_freq_filtered"
    if (cache_key in cached_articles and time.time() - cached_articles[cache_key]["time"] < 600):
        return cached_articles[cache_key]["data"]

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": search_query, 
        "language": "en",
        "sortBy": "relevancy",
        "apiKey": NEWS_API_KEY,
        "pageSize": 20
    }
    if from_date: params["from"] = from_date
    if to_date: params["to"] = to_date

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"NewsAPI Error {response.status_code}: {response.text}")
        return []

    data = response.json()
    articles = []

    for item in data.get("articles", []):
        # 1. Combine all available text to check for keyword density
        # We use .lower() to ensure case-insensitive counting
        title = (item.get("title") or "").lower()
        description = (item.get("description") or "").lower()
        content = (item.get("content") or "").lower()
        full_text_snapshot = f"{title} {description} {content}"

        # 2. Count occurrences of the threat keyword
        keyword_count = full_text_snapshot.count(keyword.lower())

        # 3. Apply the Strict Filter: only proceed if count > 1
        if keyword_count > 1:
            try:
                dt = datetime.strptime(item["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
            except:
                dt = datetime.now()

            raw_text = item.get("content") or item.get("description") or item.get("title")
            short_summary = get_ai_summary(raw_text)
            if not short_summary:
                short_summary = item.get("description") or item.get("title")

            articles.append({
                "title": item["title"],
                "summary": short_summary,
                "link": item["url"],
                "published": dt.strftime("%b %d, %Y"),
                "published_dt": dt,
                "site_source": item.get("source", {}).get("name"),
                "source": "News",
                "keyword_density": keyword_count # Optional: pass this to frontend for sorting
            })

    cached_articles[cache_key] = {"data": articles, "time": time.time()}
    return articles

# =========================================
# FETCH TWITTER DEFENCE INTEL
# =========================================

def fetch_twitter(keyword=None, location=None, from_date=None, to_date=None):
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    headers = {"Authorization": f"Bearer {bearer_token}"}
    # OAuth 1.0a Authentication
    auth = OAuth1(
        os.getenv("TWITTER_API_KEY"),
        os.getenv("API_secret_key"),
        os.getenv("Access_token"),
        os.getenv("Access_token_secret")
    )

    # Build search query
    if keyword and location:
        search_query = f"{keyword} {location} (defence OR military OR navy OR army OR security)"
    elif location:
        search_query = f"{location} (defence OR military OR navy OR army OR security)"
    else:
        search_query = "(defence OR military OR navy OR army OR security)"

    url = "https://api.twitter.com/2/tweets/search/recent"

    params = {
        "query": search_query,
        "max_results": 5,
        "tweet.fields": "created_at,text",
    }

    if from_date:
        params["start_time"] = from_date + "T00:00:00Z"
    if to_date:
        params["end_time"] = to_date + "T23:59:59Z"

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print("Twitter API Error:", response.status_code, response.text)
        return []

    data = response.json()
    tweets = []

    for item in data.get("data", []):
        try:
            dt = datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
        except:
            dt = datetime.now()

        tweets.append({
            "title": item["text"][:80] + "...",
            "summary": item["text"],
            "link": f"https://twitter.com/i/web/status/{item['id']}",
            "published": dt.strftime("%b %d, %Y"),
            "published_dt": dt,
            "source": "Twitter"
        })

    return tweets

@app.route("/api/heatmap")
def heatmap():
    keyword = request.args.get("keyword")
    location_name = request.args.get("location", "Gujarat")
    from_date = request.args.get("from")
    to_date = request.args.get("to")

    # Fetch news using ALL filters
    articles = []

    if "news" in request.args.get("sources", "news"):
        articles.extend(fetch_news(
            keyword=keyword,
            location=location_name,
            from_date=from_date,
            to_date=to_date
        ))

    if "twitter" in request.args.get("sources", ""):
        articles.extend(fetch_twitter(
            keyword=keyword,
            location=location_name,
            from_date=from_date,
            to_date=to_date
        ))
     
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
    
@app.route("/api/maritime-data")
def maritime_data():

    country_filter = request.args.get("country", "All")
    vessel_type = request.args.get("type", "All")

    ports = [
        # --- PAKISTAN ---
        {"name": "Karachi Port", "lat": 24.85, "lon": 66.99, "country": "Pakistan"},
        {"name": "Gwadar Port", "lat": 25.12, "lon": 62.33, "country": "Pakistan"},
        {"name": "Bin Qasim", "lat": 24.77, "lon": 67.33, "country": "Pakistan"},

        # --- CHINA ---
        {"name": "Shanghai Port", "lat": 31.23, "lon": 121.47, "country": "China"},
        {"name": "Ningbo-Zhoushan", "lat": 29.87, "lon": 121.55, "country": "China"},
        {"name": "Shenzhen Port", "lat": 22.50, "lon": 113.91, "country": "China"},
        {"name": "Longpo Naval Base", "lat": 18.25, "lon": 109.65, "country": "China"}, # SSBN Base Hainan

        # --- STRATEGIC INTERNATIONAL ---
        {"name": "Singapore Port", "lat": 1.28, "lon": 103.86, "country": "Singapore"},
        {"name": "Hambantota Port", "lat": 6.11, "lon": 81.10, "country": "Sri Lanka"},
        {"name": "Djibouti Port", "lat": 11.59, "lon": 43.14, "country": "Djibouti"},
        {"name": "Diego Garcia (US)", "lat": -7.31, "lon": 72.41, "country": "UK/US"},
        {"name": "Jebel Ali Port", "lat": 24.98, "lon": 55.02, "country": "UAE"},
        {"name": "NSA Bahrain (US 5th Fleet)", "lat": 26.21, "lon": 50.61, "country": "Bahrain"},

        # Bangladesh
        {"name": "Chittagong Port", "lat": 22.33, "lon": 91.82, "country": "Bangladesh"},
        {"name": "Mongla Port", "lat": 22.47, "lon": 89.58, "country": "Bangladesh"}
    ]

    vessels = [
            
        # ---------------- WEST COAST ----------------
        {"name": "MT Gulf Horizon", "lat": 19.0, "lon": 72.8, "country": "Singapore", "type": "Tanker", "time": "2026-03-10", "source": "AIS.hub"},
        {"name": "MV Persian Star", "lat": 17.2, "lon": 72.5, "country": "Iran", "type": "Cargo", "time": "2026-03-10", "source": "AIS.hub"},

        # ---------------- EAST COAST ----------------
        {"name": "MT Pacific Energy", "lat": 17.7, "lon": 83.3, "country": "Japan", "type": "Tanker", "time": "2026-03-10", "source": "AIS.hub"},
        {"name": "MV Dragon Pearl", "lat": 31.2, "lon": 122.5, "country": "China", "type": "Cargo", "time": "2026-03-10", "source": "AIS.hub"},
        
        # ---------------- ANDAMAN ----------------
        {"name": "MV Strait Runner", "lat": 9.8, "lon": 94.5, "country": "Malaysia", "type": "Cargo", "time": "2026-03-10", "source": "AIS.hub"},

        # ---------------- FISHING & COASTAL ----------------
        {"name": "MT Global Energy", "lat": 21.0, "lon": 88.0, "country": "Liberia", "type": "Tanker", "time": "2026-03-10", "source": "AIS.hub"},

        # ---------------- INDIA ----------------
        # {"name": "MV Indian Trader", "lat": 18.5, "lon": 72.2, "country": "India", "type": "Cargo"},

        # ---------------- PAKISTAN ----------------
        {"name": "PNS Zulfiquar", "lat": 24.8, "lon": 67.0, "country": "Pakistan", "type": "Naval", "time": "2026-03-10", "source": "AIS.hub"},
        {"name": "MV Pakistan Cargo", "lat": 24.7, "lon": 66.7, "country": "Pakistan", "type": "Cargo", "time": "2026-03-10", "source": "AIS.hub"},

        # ---------------- CHINA ----------------
        {"name": "PLAN Type 052D", "lat": 31.2, "lon": 121.4, "country": "China", "type": "Naval", "time": "2026-03-10", "source": "AIS.hub"},
        {"name": "MV Yangtze Trader", "lat": 29.8, "lon": 121.6, "country": "China", "type": "Cargo", "time": "2026-03-10", "source": "AIS.hub"},
        
        # --- CHINESE (PLAN) & IRANIAN PRESENCE ---
        {"name": "PLAN Type 052D", "lat": 24.50, "lon": 62.00, "country": "China", "type": "Naval", "time": "2026-03-10", "source": "AIS.hub"}, # Near Gwadar
        {"name": "Shi Yan 6 (Research)", "lat": 6.50, "lon": 79.50, "country": "China", "type": "Naval", "time": "2026-03-10", "source": "AIS.hub"}, # Near Sri Lanka
        {"name": "IRIS Dena (Frigate)", "lat": 7.50, "lon": 78.50, "country": "Iran", "type": "Naval", "time": "2026-03-10", "source": "AIS.hub"}, # Sri Lankan Waters

        # ---------------- BANGLADESH ----------------
        {"name": "BNS Bangabandhu", "lat": 22.3, "lon": 91.8, "country": "Bangladesh", "type": "Naval", "time": "2026-03-10", "source": "AIS.hub"},
        {"name": "MV Bengal Mariner", "lat": 22.4, "lon": 89.6, "country": "Bangladesh", "type": "Tanker", "time": "2026-03-10", "source": "AIS.hub"},

        # ---------------- DEEP SEA ----------------
        {"name": "MT Sea Phantom", "lat": 22.0, "lon": 88.30, "country": "Liberia", "type": "Tanker", "time": "2026-03-10", "source": "AIS.hub"},
        # ---------------- Other Destinations in AIS ----------------
        {"name": "KAFFE", "lat": 17.8, "lon": 73.0, "country": "Norway", "type": "Cargo", "time": "2026-03-10", "source": "AIS.hub"},
        {"name": "MARTIN GREEN", "lat": 17.1, "lon": 68.1, "country": "Australia", "type": "Cargo", "time": "2026-03-10", "source": "AIS.hub"},
        {"name": "JULIUSPLATE", "lat": 20.6, "lon": 69.3, "country": "Germany", "type": "Cargo", "time": "2026-03-10", "source": "AIS.hub"},
        {"name": "NZK PONT 102", "lat": 23.9, "lon": 68.0, "country": "Netherlands", "type": "Cargo", "time": "2026-03-10", "source": "AIS.hub"}

    ]
    if country_filter != "All":
        ports = [p for p in ports if p["country"] == country_filter]
        vessels = [v for v in vessels if v["country"] == country_filter]

    if vessel_type != "All":
        vessels = [v for v in vessels if v["type"] == vessel_type]

    return jsonify({
        "ports": ports,
        "vessels": vessels,
    })

    
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

# =========================================
# MARITIME DOMAIN AWARENESS PAGE
# =========================================

@app.route("/maritime")
def maritime():
    return render_template("maritime.html")

if __name__ == "__main__":
    app.run(debug=True)