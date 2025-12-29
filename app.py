import os
import sqlite3
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import yfinance as yf
import pandas as pd
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
    "tech": 5, "ceo": 5, "nvidia": 15, "jensen": 15,
    "schott": 2, "allsaints": 2, "the kooples": 2, "acne studios": 2,
    "saint laurent": 8, "rick owens": 6, "celine": 8, "tom ford": 25, "ysl": 8, "yves saint laurent": 8,
    "hermes": 12, "prada": 7, "gucci": 7, "balenciaga": 6, "chrome hearts": 12,
    "belstaff": 5, "brunello cucinelli": 10, "loro piana": 10, "undercover": 5, "julius": 4,
    "fendi": 7, "dior": 8, "berluti": 10, "isaia": 6, "brioni": 8, "kiton": 10,
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
# STOCK DATA LOGIC
# ============================================================================
def get_nvda_data():
    """Fetches the latest NVDA stock data with robust error handling."""
    try:
        nvda_ticker = yf.Ticker("NVDA")
        # Use 5d to ensure we have enough data even on weekends/holidays
        hist = nvda_ticker.history(period="7d")
        
        if len(hist) < 2:
            return None, None, "N/A"
            
        curr_price = hist["Close"].iloc[-1]
        prev_price = hist["Close"].iloc[-2]
        pct_change = ((curr_price - prev_price) / prev_price) * 100
        
        display = f"${curr_price:.2f} {'▲' if pct_change >= 0 else '▼'} {abs(pct_change):.2f}%"
        return curr_price, pct_change, display
    except Exception as e:
        print(f"Error fetching NVDA data: {e}")
        return None, None, "N/A"

def backfill_nvda_history():
    """Backfills the daily_index table with 90 days of actual NVDA price data."""
    print(f"[{datetime.now()}] Starting NVDA historical backfill...")
    try:
        nvda_ticker = yf.Ticker("NVDA")
        hist = nvda_ticker.history(period="90d")
        if hist.empty:
            print("No NVDA history found.")
            return

        hist['Pct_Chg'] = hist['Close'].pct_change() * 100

        conn = get_db_connection()
        c = conn.cursor()
        
        count = 0
        for date_ts, row in hist.iterrows():
            date_str = date_ts.date().isoformat()
            close_price = float(row['Close'])
            pct_chg = float(row['Pct_Chg']) if not pd.isna(row['Pct_Chg']) else None
            
            c.execute("""
                INSERT INTO daily_index (date, nvda_close, nvda_pct_change) 
                VALUES (?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET 
                nvda_close = excluded.nvda_close,
                nvda_pct_change = excluded.nvda_pct_change
                WHERE nvda_close IS NULL
            """, (date_str, close_price, pct_chg))
            if c.rowcount > 0:
                count += 1
        
        conn.commit()
        conn.close()
        print(f"[{datetime.now()}] NVDA backfill completed. Updated {count} rows.")
    except Exception as e:
        print(f"NVDA backfill failed: {e}")

# ============================================================================
# SCRAPER LOGIC
# ============================================================================
def run_scrape():
    print(f"[{datetime.now()}] Starting scrape...")
    try:
        client = GrailedAPIClient()
        all_products = []
        queries = [
            "leather jacket black", "biker jacket leather", "moto jacket", "cafe racer jacket",
            "celine leather jacket", "tom ford leather jacket", "ysl leather jacket", 
            "saint laurent leather jacket", "rick owens leather jacket",
            "hermes leather jacket", "chrome hearts leather jacket", "prada leather jacket",
            "gucci leather jacket", "brunello cucinelli leather", "loro piana leather",
            "fendi leather jacket", "dior leather jacket", "balenciaga leather jacket",
            "berluti leather jacket", "isaia leather jacket", "brioni leather jacket"
        ]
        
        for query in queries:
            try:
                # Increased hits_per_page to 100 for more accurate listing counts
                res = client.find_products(sold=False, on_sale=True, query_search=query, 
                                         categories=[Outerwear.LEATHER_JACKETS], hits_per_page=100)
                all_products.extend(res)
                res_sold = client.find_products(sold=True, on_sale=False, query_search=query, 
                                              categories=[Outerwear.LEATHER_JACKETS], hits_per_page=100)
                all_products.extend(res_sold)
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
            
            # Robust designer detection if Grailed fails
            if designer == "Unknown":
                for kw in ["Celine", "Tom Ford", "YSL", "Saint Laurent", "Rick Owens", "Schott", "AllSaints"]:
                    if kw.lower() in title.lower():
                        designer = kw
                        break
            
            price = float(p.get("price", 0))
            is_sold = bool(p.get("sold", False))
            sold_price = float(p.get("sold_price", 0)) if is_sold else None
            score = calculate_jensen_score(title, p.get("description", ""))
            
            c.execute("INSERT OR REPLACE INTO listings VALUES (?,?,?,?,?,?,?,?,?)",
                     (pid, title, designer, price, sold_price, is_sold, score, now, f"https://grailed.com/listings/{pid}"))
        
        # NVDA Data
        nvda_close, nvda_pct, _ = get_nvda_data()
        
        # Daily Index
        today = datetime.now().date().isoformat()
        c.execute("SELECT AVG(price), AVG(sold_price), COUNT(*), SUM(is_sold), AVG(jensen_score) FROM listings")
        row = c.fetchone()
        if row and row[0]:
            c.execute("INSERT OR REPLACE INTO daily_index (date, avg_price, median_price, avg_sold_price, total_listings, sold_count, avg_jensen_score, nvda_close, nvda_pct_change) VALUES (?,?,?,?,?,?,?,?,?)",
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
        c.execute("SELECT * FROM daily_index ORDER BY date DESC LIMIT 730")
        daily_history = [dict(row) for row in c.fetchall()]
    except sqlite3.OperationalError:
        daily_history = []
    
    # Get top listings
    try:
        c.execute("SELECT * FROM listings ORDER BY jensen_score DESC, scraped_at DESC LIMIT 20")
        top_listings = [dict(row) for row in c.fetchall()]
    except sqlite3.OperationalError:
        top_listings = []
    
    conn.close()

    # Prepare metrics
    def calc_trailing(data, field, days):
        valid_vals = [d[field] for d in data if d.get(field) is not None]
        subset = valid_vals[:days]
        return sum(subset) / len(subset) if subset else 0

    def calc_pop(data, field, days):
        valid_data = [d for d in data if d.get(field) is not None]
        if len(valid_data) < 2: return None
        
        if len(valid_data) >= days * 2:
            curr_subset = valid_data[:days]
            prev_subset = valid_data[days:days*2]
            curr_avg = sum(d[field] for d in curr_subset) / len(curr_subset)
            prev_avg = sum(d[field] for d in prev_subset) / len(prev_subset)
            return ((curr_avg - prev_avg) / prev_avg) * 100 if prev_avg else None
        
        latest = valid_data[0][field]
        oldest = valid_data[-1][field]
        return ((latest - oldest) / oldest) * 100 if oldest else None

    # Get latest NVDA for header
    _, _, nvda_display = get_nvda_data()

    return jsonify({
        "ticker": "JHLJ",
        "name": "Jensen Huang Leather Jacket Index",
        "status": "live",
        "last_updated": daily_history[0]["date"] if daily_history else "N/A",
        "nvda_display": nvda_display,
        "alt_data_metrics": [
            {
                "name": "Avg Jacket Price",
                "trailing91": round(calc_trailing(daily_history, "avg_price", 91), 2),
                "trailing28": round(calc_trailing(daily_history, "avg_price", 28), 2),
                "trailing7": round(calc_trailing(daily_history, "avg_price", 7), 2),
                "pop91": round(calc_pop(daily_history, "avg_price", 91), 2) if calc_pop(daily_history, "avg_price", 91) is not None else None,
                "pop28": round(calc_pop(daily_history, "avg_price", 28), 2) if calc_pop(daily_history, "avg_price", 28) is not None else None,
                "pop7": round(calc_pop(daily_history, "avg_price", 7), 2) if calc_pop(daily_history, "avg_price", 7) is not None else None,
                "highlighted": True
            },
            {
                "name": "Jensen Score (Avg)",
                "trailing91": round(calc_trailing(daily_history, "avg_jensen_score", 91), 2),
                "trailing28": round(calc_trailing(daily_history, "avg_jensen_score", 28), 2),
                "trailing7": round(calc_trailing(daily_history, "avg_jensen_score", 7), 2),
                "pop91": round(calc_pop(daily_history, "avg_jensen_score", 91), 2) if calc_pop(daily_history, "avg_jensen_score", 91) is not None else None,
                "pop28": round(calc_pop(daily_history, "avg_jensen_score", 28), 2) if calc_pop(daily_history, "avg_jensen_score", 28) is not None else None,
                "pop7": round(calc_pop(daily_history, "avg_jensen_score", 7), 2) if calc_pop(daily_history, "avg_jensen_score", 7) is not None else None,
            },
            {
                "name": "Daily Listings",
                "trailing91": round(calc_trailing(daily_history, "total_listings", 91), 0),
                "trailing28": round(calc_trailing(daily_history, "total_listings", 28), 0),
                "trailing7": round(calc_trailing(daily_history, "total_listings", 7), 0),
                "pop91": round(calc_pop(daily_history, "total_listings", 91), 2) if calc_pop(daily_history, "total_listings", 91) is not None else None,
                "pop28": round(calc_pop(daily_history, "total_listings", 28), 2) if calc_pop(daily_history, "total_listings", 28) is not None else None,
                "pop7": round(calc_pop(daily_history, "total_listings", 7), 2) if calc_pop(daily_history, "total_listings", 7) is not None else None,
            },
            {
                "name": "Items Sold",
                "trailing91": round(calc_trailing(daily_history, "sold_count", 91), 0),
                "trailing28": round(calc_trailing(daily_history, "sold_count", 28), 0),
                "trailing7": round(calc_trailing(daily_history, "sold_count", 7), 0),
                "pop91": round(calc_pop(daily_history, "sold_count", 91), 2) if calc_pop(daily_history, "sold_count", 91) is not None else None,
                "pop28": round(calc_pop(daily_history, "sold_count", 28), 2) if calc_pop(daily_history, "sold_count", 28) is not None else None,
                "pop7": round(calc_pop(daily_history, "sold_count", 7), 2) if calc_pop(daily_history, "sold_count", 7) is not None else None,
            }
        ],
        "weekly_data": [
            {
                "week": d["date"], 
                "jacket": round(((d["avg_price"] - daily_history[i+1]["avg_price"]) / daily_history[i+1]["avg_price"] * 100), 2) if i < len(daily_history)-1 and d["avg_price"] is not None and daily_history[i+1]["avg_price"] else None,
                "nvda": d["nvda_pct_change"] if d["nvda_pct_change"] is not None else 0,
                "jensen": d["avg_jensen_score"],
                "volume": d["total_listings"],
                "sold": d["sold_count"]
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

@app.route("/api/backfill")
def trigger_backfill():
    return jsonify({"status": "disabled", "message": "Backfill with fake data is disabled."})

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "db_exists": DB_PATH.exists()})

# ============================================================================
# MAIN
# ============================================================================
init_db()

# Scheduler for automatic updates every 6 hours
scheduler = BackgroundScheduler()
scheduler.add_job(func=run_scrape, trigger="interval", hours=6)
scheduler.start()

# Run initial checks on startup
with app.app_context():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Check if listings exist
        c.execute("SELECT COUNT(*) FROM listings")
        count = c.fetchone()[0]
        
        # Check if history exists
        c.execute("SELECT COUNT(*) FROM daily_index")
        history_count = c.fetchone()[0]
        conn.close()
        
        import threading
        if count == 0:
            print(f"Database is empty. Running initial scrape...")
            threading.Thread(target=run_scrape).start()
        
        # Always attempt backfill if history is short to ensure 90d actual data
        if history_count < 90:
            print(f"History is sparse ({history_count} rows). Running NVDA backfill...")
            threading.Thread(target=backfill_nvda_history).start()
            
    except Exception as e:
        print(f"Error during startup check: {e}")
        init_db()
        import threading
        threading.Thread(target=run_scrape).start()
        threading.Thread(target=backfill_nvda_history).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

