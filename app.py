import os
import io
import csv
import sqlite3
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, request, render_template, Response
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

def load_seed_data():
    """Load historical data from seed.json if database is empty."""
    seed_path = Path(__file__).parent / "data" / "seed.json"
    if not seed_path.exists():
        print(f"No seed file found at {seed_path}")
        return
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if we already have data
    c.execute("SELECT COUNT(*) FROM daily_index")
    if c.fetchone()[0] > 0:
        print("Database already has data, skipping seed load")
        conn.close()
        return
    
    try:
        with open(seed_path, 'r') as f:
            seed_data = json.load(f)
        
        # Load daily_index
        for row in seed_data.get('daily_index', []):
            c.execute("""INSERT OR IGNORE INTO daily_index 
                (date, avg_price, median_price, avg_sold_price, total_listings, 
                 sold_count, avg_jensen_score, nvda_close, nvda_pct_change)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (row['date'], row.get('avg_price'), row.get('median_price'),
                 row.get('avg_sold_price'), row.get('total_listings'),
                 row.get('sold_count'), row.get('avg_jensen_score'),
                 row.get('nvda_close'), row.get('nvda_pct_change')))
        
        # Load listings
        for row in seed_data.get('listings', []):
            c.execute("""INSERT OR IGNORE INTO listings 
                (id, title, designer, price, sold_price, is_sold, jensen_score, scraped_at, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (row['id'], row.get('title'), row.get('designer'), row.get('price'),
                 row.get('sold_price'), row.get('is_sold'), row.get('jensen_score'),
                 row.get('scraped_at'), row.get('url')))
        
        conn.commit()
        print(f"Loaded {len(seed_data.get('daily_index', []))} daily_index rows from seed")
        print(f"Loaded {len(seed_data.get('listings', []))} listings from seed")
    except Exception as e:
        print(f"Error loading seed data: {e}")
    finally:
        conn.close()

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
    
    # Load seed data if database is empty
    load_seed_data()

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
        
        # Daily Index - calculate averages only from TODAY's scraped listings
        # This ensures consistent day-over-day comparisons
        today = datetime.now().date().isoformat()
        c.execute("""SELECT AVG(price), AVG(sold_price), COUNT(*), SUM(is_sold), AVG(jensen_score) 
                     FROM listings WHERE DATE(scraped_at) = DATE(?)""", (today,))
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

@app.route("/api/export")
def export_csv():
    """Export comprehensive CSV data including daily index, listings, and metrics."""
    conn = get_db_connection()
    c = conn.cursor()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Section 1: Summary Header
    writer.writerow(['JENSEN HUANG LEATHER JACKET INDEX - DATA EXPORT'])
    writer.writerow([f'Generated: {datetime.now().isoformat()}'])
    writer.writerow([])
    
    # Section 2: Daily Index Data
    writer.writerow(['=== DAILY INDEX DATA ==='])
    writer.writerow(['Date', 'Avg Price ($)', 'Median Price ($)', 'Avg Sold Price ($)', 
                     'Total Listings', 'Sold Count', 'Avg Jensen Score', 
                     'NVDA Close ($)', 'NVDA % Change'])
    
    c.execute("""SELECT date, avg_price, median_price, avg_sold_price, 
                        total_listings, sold_count, avg_jensen_score, 
                        nvda_close, nvda_pct_change 
                 FROM daily_index ORDER BY date DESC""")
    for row in c.fetchall():
        writer.writerow([
            row['date'],
            round(row['avg_price'], 2) if row['avg_price'] else '',
            round(row['median_price'], 2) if row['median_price'] else '',
            round(row['avg_sold_price'], 2) if row['avg_sold_price'] else '',
            row['total_listings'] or '',
            row['sold_count'] or '',
            round(row['avg_jensen_score'], 2) if row['avg_jensen_score'] else '',
            round(row['nvda_close'], 2) if row['nvda_close'] else '',
            round(row['nvda_pct_change'], 2) if row['nvda_pct_change'] else ''
        ])
    
    writer.writerow([])
    
    # Section 3: All Listings
    writer.writerow(['=== INDIVIDUAL LISTINGS ==='])
    writer.writerow(['ID', 'Title', 'Designer', 'Price ($)', 'Sold Price ($)', 
                     'Is Sold', 'Jensen Score', 'Scraped At', 'URL'])
    
    c.execute("""SELECT id, title, designer, price, sold_price, is_sold, 
                        jensen_score, scraped_at, url 
                 FROM listings ORDER BY jensen_score DESC, scraped_at DESC""")
    for row in c.fetchall():
        writer.writerow([
            row['id'],
            row['title'] or '',
            row['designer'] or '',
            round(row['price'], 2) if row['price'] else '',
            round(row['sold_price'], 2) if row['sold_price'] else '',
            'Yes' if row['is_sold'] else 'No',
            row['jensen_score'] or 0,
            row['scraped_at'] or '',
            row['url'] or ''
        ])
    
    writer.writerow([])
    
    # Section 4: Summary Statistics
    writer.writerow(['=== SUMMARY STATISTICS ==='])
    
    c.execute("""SELECT 
                    COUNT(*) as total_listings,
                    SUM(CASE WHEN is_sold THEN 1 ELSE 0 END) as total_sold,
                    AVG(price) as avg_price,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    AVG(jensen_score) as avg_jensen_score,
                    MAX(jensen_score) as max_jensen_score
                 FROM listings""")
    stats = c.fetchone()
    
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Listings Tracked', stats['total_listings'] or 0])
    writer.writerow(['Total Sold', stats['total_sold'] or 0])
    writer.writerow(['Average Price ($)', round(stats['avg_price'], 2) if stats['avg_price'] else 'N/A'])
    writer.writerow(['Min Price ($)', round(stats['min_price'], 2) if stats['min_price'] else 'N/A'])
    writer.writerow(['Max Price ($)', round(stats['max_price'], 2) if stats['max_price'] else 'N/A'])
    writer.writerow(['Average Jensen Score', round(stats['avg_jensen_score'], 2) if stats['avg_jensen_score'] else 'N/A'])
    writer.writerow(['Max Jensen Score', stats['max_jensen_score'] or 'N/A'])
    
    # Get date range
    c.execute("SELECT MIN(date) as first_date, MAX(date) as last_date FROM daily_index")
    date_range = c.fetchone()
    writer.writerow(['Data Start Date', date_range['first_date'] or 'N/A'])
    writer.writerow(['Data End Date', date_range['last_date'] or 'N/A'])
    
    conn.close()
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=jhlj_index_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )

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

# Run initial checks AFTER startup to avoid Gunicorn worker timeout
def run_startup_tasks():
    """Run startup tasks in background after worker is ready."""
    import time
    time.sleep(2)  # Small delay to ensure worker is fully started
    
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
            
            if count == 0:
                print(f"[{datetime.now()}] Database is empty. Running initial scrape...")
                run_scrape()
            
            # Always attempt backfill if history is short to ensure 90d actual data
            if history_count < 90:
                print(f"[{datetime.now()}] History is sparse ({history_count} rows). Running NVDA backfill...")
                backfill_nvda_history()
                
        except Exception as e:
            print(f"Error during startup tasks: {e}")
            init_db()
            run_scrape()
            backfill_nvda_history()

# Start background thread for startup tasks - this doesn't block the worker
import threading
startup_thread = threading.Thread(target=run_startup_tasks, daemon=True)
startup_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

