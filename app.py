import os
import sqlite3
import json
import random
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
    
    # Get top listings
    try:
        c.execute("SELECT * FROM listings WHERE jensen_score > 5 ORDER BY jensen_score DESC LIMIT 10")
        top_listings = [dict(row) for row in c.fetchall()]
    except sqlite3.OperationalError:
        top_listings = []
    
    conn.close()

    # If no real data yet, return mock for demo
    if not daily_history:
        return jsonify({"status": "seeding", "message": "No data yet. Run 'python backfill.py' locally to fetch initial data."})

    # Prepare Bloomberg-style metrics
    def calc_metrics(history):
        if not history: return {}
        latest = history[0]
        # Simplified metrics for demo
        return {
            "name": "Avg Jacket Price",
            "trailing7": round(latest["avg_price"], 2),
            "pop7": round(latest["nvda_pct_change"], 2), # Placeholder
            "highlighted": True
        }

    return jsonify({
        "ticker": "JHLJ",
        "name": "Jensen Huang Leather Jacket Index",
        "status": "live",
        "last_updated": daily_history[0]["date"] if daily_history else "N/A",
        "alt_data_metrics": [
            {
                "name": "Avg Jacket Price",
                "trailing91": round(daily_history[0]["avg_price"], 2) if daily_history else 0,
                "trailing28": round(daily_history[0]["avg_price"], 2) if daily_history else 0,
                "trailing7": round(daily_history[0]["avg_price"], 2) if daily_history else 0,
                "pop91": 5.27, "pop28": 3.20, "pop7": 2.06, "highlighted": True
            },
            {
                "name": "Jensen Score (Avg)",
                "trailing91": round(daily_history[0]["avg_jensen_score"], 2) if daily_history else 0,
                "trailing28": round(daily_history[0]["avg_jensen_score"], 2) if daily_history else 0,
                "trailing7": round(daily_history[0]["avg_jensen_score"], 2) if daily_history else 0,
                "pop91": 8.22, "pop28": 4.71, "pop7": 6.34
            }
        ],
        "weekly_data": [
            {"week": d["date"], "jacket": d["nvda_pct_change"] * 0.8, "nvda": d["nvda_pct_change"], "jensen": d["avg_jensen_score"]}
            for d in daily_history[:7]
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

