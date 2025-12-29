import os
import sqlite3
import json
import random
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import yfinance as yf
from apscheduler.schedulers.background import BackgroundScheduler
from grailed_api import GrailedAPIClient
from grailed_api.enums.categories import Outerwear

app = Flask(__name__, template_folder="templates")
CORS(app)

# Use /tmp for database on Render to ensure we have write permissions, 
# otherwise use local jackets.db.
DB_PATH = Path("/tmp/jackets.db") if os.environ.get("RENDER") else Path(__file__).parent / "jackets.db"

# ============================================================================
# JENSEN-CODED CLASSIFICATION SYSTEM
# ============================================================================
JENSEN_KEYWORDS = {
    "biker": 3, "moto": 3, "motorcycle": 3, "asymmetric": 2, "asymmetrical": 2,
    "black leather": 2, "cafe racer": 2, "band collar": 1, "mandarin collar": 1,
    "tech": 5, "ceo": 5, "nvidia": 10, "jensen": 10,
    "schott": 2, "allsaints": 2, "the kooples": 2, "acne studios": 1,
    "saint laurent": 1, "rick owens": 1,
    "brown": -2, "tan": -2, "suede": -3, "shearling": -2, "bomber": -1, "varsity": -3,
}

def calculate_jensen_score(title: str, description: str = "") -> int:
    text = f"{title} {description}".lower()
    score = sum(weight for kw, weight in JENSEN_KEYWORDS.items() if kw in text)
    if "black" in text and "leather" in text: score += 2
    return score

# ============================================================================
# DATABASE LOGIC
# ============================================================================
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS listings (
        id TEXT PRIMARY KEY, title TEXT, designer TEXT, price REAL, 
        sold_price REAL, is_sold BOOLEAN, jensen_score INTEGER, 
        scraped_at TIMESTAMP, url TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS daily_index (
        date DATE PRIMARY KEY, avg_price REAL, median_price REAL, 
        avg_sold_price REAL, total_listings INTEGER, sold_count INTEGER, 
        avg_jensen_score REAL, nvda_close REAL, nvda_pct_change REAL)""")
    conn.commit()
    conn.close()

# ============================================================================
# SCRAPER LOGIC
# ============================================================================
def run_scrape():
    print(f"[{datetime.now()}] Starting scrape...")
    try:
        client = GrailedAPIClient()
        all_products = []
        queries = ["leather jacket black", "biker jacket leather", "moto jacket", "cafe racer jacket"]
        
        for query in queries:
            try:
                res = client.find_products(sold=False, on_sale=True, query_search=query, 
                                         categories=[Outerwear.LEATHER_JACKETS], hits_per_page=20)
                all_products.extend(res.get("hits", []))
                res_sold = client.find_products(sold=True, on_sale=False, query_search=query, 
                                              categories=[Outerwear.LEATHER_JACKETS], hits_per_page=20)
                all_products.extend(res_sold.get("hits", []))
            except Exception as e:
                print(f"Error searching {query}: {e}")

        # Store in DB
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()
        for p in all_products:
            pid = str(p.get("id", ""))
            if not pid: continue
            title = p.get("title", "")
            designer = p.get("designer", {}).get("name", "Unknown")
            price = float(p.get("price", 0))
            is_sold = bool(p.get("sold", False))
            sold_price = float(p.get("sold_price", 0)) if is_sold else None
            score = calculate_jensen_score(title, p.get("description", ""))
            
            c.execute("INSERT OR REPLACE INTO listings VALUES (?,?,?,?,?,?,?,?,?)",
                     (pid, title, designer, price, sold_price, is_sold, score, now, f"https://grailed.com/listings/{pid}"))
        
        # NVDA Data
        nvda = yf.Ticker("NVDA")
        hist = nvda.history(period="5d")
        nvda_close = hist["Close"].iloc[-1]
        nvda_prev = hist["Close"].iloc[-2]
        nvda_pct = ((nvda_close - nvda_prev) / nvda_prev) * 100
        
        # Daily Index
        today = datetime.now().date().isoformat()
        c.execute("SELECT AVG(price), AVG(sold_price), COUNT(*), SUM(is_sold), AVG(jensen_score) FROM listings")
        row = c.fetchone()
        if row and row[0]:
            c.execute("INSERT OR REPLACE INTO daily_index VALUES (?,?,?,?,?,?,?,?,?)",
                     (today, row[0], row[0], row[1], row[2], row[3], row[4], nvda_close, nvda_pct))
        
        conn.commit()
        conn.close()
        print(f"[{datetime.now()}] Scrape completed successfully.")
        return True
    except Exception as e:
        print(f"Scrape failed: {e}")
        return False

# ============================================================================
# API ROUTES
# ============================================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/index")
def get_index():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get daily history
    try:
        c.execute("SELECT * FROM daily_index ORDER BY date DESC LIMIT 90")
        daily_history = [dict(row) for row in c.fetchall()]
    except sqlite3.OperationalError:
        # Table might not exist yet if init_db wasn't successful or no scrape run
        daily_history = []
    
    # Get top listings (Relaxed filter to ensure we show real listings even if scores are low)
    try:
        c.execute("SELECT * FROM listings ORDER BY jensen_score DESC, scraped_at DESC LIMIT 20")
        top_listings = [dict(row) for row in c.fetchall()]
    except sqlite3.OperationalError:
        top_listings = []
    
    conn.close()

    # Prepare metrics
    def calc_trailing(data, field, days):
        subset = data[:days]
        vals = [d[field] for d in subset if d.get(field) is not None]
        return sum(vals) / len(vals) if vals else 0

    def calc_pop(data, field, days):
        if len(data) < days * 2:
            # Fallback: if we don't have 2 full periods, compare latest to oldest available in first period
            if len(data) < 2: return 0
            latest = data[0][field]
            oldest = data[-1][field]
            return ((latest - oldest) / oldest) * 100 if oldest else 0
        
        curr_subset = data[:days]
        prev_subset = data[days:days*2]
        
        curr_vals = [d[field] for d in curr_subset if d.get(field) is not None]
        prev_vals = [d[field] for d in prev_subset if d.get(field) is not None]
        
        if not curr_vals or not prev_vals: return 0
        
        curr_avg = sum(curr_vals) / len(curr_vals)
        prev_avg = sum(prev_vals) / len(prev_vals)
        
        return ((curr_avg - prev_avg) / prev_avg) * 100 if prev_avg else 0

    def calc_correlation(data, field1, field2, days):
        subset = data[:days]
        v1 = [d[field1] for d in subset if d.get(field1) is not None and d.get(field2) is not None]
        v2 = [d[field2] for d in subset if d.get(field1) is not None and d.get(field2) is not None]
        
        if len(v1) < 3: return 0
        
        res = stats.pearsonr(v1, v2)
        return res[0] if not np.isnan(res[0]) else 0

    # Calculate correlation for Jensen Correlation tab
    prices = [d["avg_price"] for d in daily_history if d["avg_price"] is not None]
    nvda = [d["nvda_close"] for d in daily_history if d["nvda_close"] is not None]
    
    r_squared = 0
    p_value = 0
    if len(prices) > 5 and len(nvda) > 5:
        min_len = min(len(prices), len(nvda))
        slope, intercept, r_value, p_val, std_err = stats.linregress(prices[:min_len], nvda[:min_len])
        r_squared = r_value**2
        p_value = p_val

    return jsonify({
        "ticker": "JHLJ",
        "name": "Jensen Huang Leather Jacket Index",
        "status": "live",
        "last_updated": daily_history[0]["date"] if daily_history else "N/A",
        "r_squared": round(r_squared, 4),
        "p_value": round(p_value, 4),
        "alt_data_metrics": [
            {
                "name": "Avg Jacket Price",
                "trailing91": round(calc_trailing(daily_history, "avg_price", 91), 2),
                "trailing28": round(calc_trailing(daily_history, "avg_price", 28), 2),
                "trailing7": round(calc_trailing(daily_history, "avg_price", 7), 2),
                "pop91": round(calc_pop(daily_history, "avg_price", 91), 2),
                "pop28": round(calc_pop(daily_history, "avg_price", 28), 2),
                "pop7": round(calc_pop(daily_history, "avg_price", 7), 2),
                "highlighted": True
            },
            {
                "name": "Jensen Score (Avg)",
                "trailing91": round(calc_trailing(daily_history, "avg_jensen_score", 91), 2),
                "trailing28": round(calc_trailing(daily_history, "avg_jensen_score", 28), 2),
                "trailing7": round(calc_trailing(daily_history, "avg_jensen_score", 7), 2),
                "pop91": round(calc_pop(daily_history, "avg_jensen_score", 91), 2),
                "pop28": round(calc_pop(daily_history, "avg_jensen_score", 28), 2),
                "pop7": round(calc_pop(daily_history, "avg_jensen_score", 7), 2)
            },
            {
                "name": "Daily Listings",
                "trailing91": round(calc_trailing(daily_history, "total_listings", 91), 0),
                "trailing28": round(calc_trailing(daily_history, "total_listings", 28), 0),
                "trailing7": round(calc_trailing(daily_history, "total_listings", 7), 0),
                "pop91": round(calc_pop(daily_history, "total_listings", 91), 2),
                "pop28": round(calc_pop(daily_history, "total_listings", 28), 2),
                "pop7": round(calc_pop(daily_history, "total_listings", 7), 2)
            },
            {
                "name": "Items Sold",
                "trailing91": round(calc_trailing(daily_history, "sold_count", 91), 0),
                "trailing28": round(calc_trailing(daily_history, "sold_count", 28), 0),
                "trailing7": round(calc_trailing(daily_history, "sold_count", 7), 0),
                "pop91": round(calc_pop(daily_history, "sold_count", 91), 2),
                "pop28": round(calc_pop(daily_history, "sold_count", 28), 2),
                "pop7": round(calc_pop(daily_history, "sold_count", 7), 2)
            },
            {
                "name": "NVDA Correlation (R)",
                "trailing91": round(calc_correlation(daily_history, "avg_price", "nvda_close", 91), 3),
                "trailing28": round(calc_correlation(daily_history, "avg_price", "nvda_close", 28), 3),
                "trailing7": round(calc_correlation(daily_history, "avg_price", "nvda_close", 7), 3),
                "pop91": 0, "pop28": 0, "pop7": 0 # PoP on correlation is less meaningful
            },
            {
                "name": "Price/NVDA Ratio",
                "trailing91": round(calc_trailing(daily_history, "avg_price", 91) / calc_trailing(daily_history, "nvda_close", 91), 2) if calc_trailing(daily_history, "nvda_close", 91) else 0,
                "trailing28": round(calc_trailing(daily_history, "avg_price", 28) / calc_trailing(daily_history, "nvda_close", 28), 2) if calc_trailing(daily_history, "nvda_close", 28) else 0,
                "trailing7": round(calc_trailing(daily_history, "avg_price", 7) / calc_trailing(daily_history, "nvda_close", 7), 2) if calc_trailing(daily_history, "nvda_close", 7) else 0,
                "pop91": round(calc_pop(daily_history, "avg_price", 91) - calc_pop(daily_history, "nvda_close", 91), 2),
                "pop28": round(calc_pop(daily_history, "avg_price", 28) - calc_pop(daily_history, "nvda_close", 28), 2),
                "pop7": round(calc_pop(daily_history, "avg_price", 7) - calc_pop(daily_history, "nvda_close", 7), 2)
            }
        ],
        "weekly_data": [
            {
                "week": d["date"], 
                "jacket": round(((d["avg_price"] - daily_history[i+1]["avg_price"]) / daily_history[i+1]["avg_price"] * 100), 2) if i < len(daily_history)-1 and daily_history[i+1]["avg_price"] else 0,
                "nvda": d["nvda_pct_change"] if d["nvda_pct_change"] is not None else 0,
                "jensen": d["avg_jensen_score"]
            }
            for i, d in enumerate(daily_history)
        ][::-1],
        "top_listings": top_listings,
        "daily_history": daily_history
    })

@app.route("/api/scrape")
def trigger_scrape():
    success = run_scrape()
    return jsonify({"status": "success" if success else "error"})

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "db_exists": DB_PATH.exists()})

# ============================================================================
# MAIN
# ============================================================================
init_db()

# Scheduler for automatic updates every 6 hours
# (Keep it frequent enough to be 'live' but not so much we get rate limited)
scheduler = BackgroundScheduler()
scheduler.add_job(func=run_scrape, trigger="interval", hours=6)
scheduler.start()

if __name__ == "__main__":
    # For local testing, you can run a scrape once
    # run_scrape() 
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

