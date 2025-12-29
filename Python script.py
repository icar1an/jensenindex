"""
Jensen Huang Leather Jacket Index - Data Scraper
Tracks leather jacket resale prices on Grailed and correlates with NVDA performance.

Run daily via cron: 0 9 * * * python scraper.py
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf

# pip install grailed_api yfinance --break-system-packages
from grailed_api import GrailedAPIClient
from grailed_api.enums import Conditions, Markets
from grailed_api.enums.categories import Outerwear

DB_PATH = Path(__file__).parent / "jackets.db"

# ============================================================================
# JENSEN-CODED CLASSIFICATION SYSTEM
# ============================================================================
# What makes a leather jacket "Jensen-coded"? A proprietary scoring algorithm.

JENSEN_KEYWORDS = {
    # High signal keywords
    "biker": 3,
    "moto": 3,
    "motorcycle": 3,
    "asymmetric": 2,
    "asymmetrical": 2,
    "black leather": 2,
    "cafe racer": 2,
    "band collar": 1,
    "mandarin collar": 1,
    "tech": 5,  # Peak correlation
    "ceo": 5,
    "nvidia": 10,  # Jackpot
    "jensen": 10,
    # Designer signals (aspirational Jensen-coding)
    "schott": 2,
    "allsaints": 2,
    "the kooples": 2,
    "acne studios": 1,
    "saint laurent": 1,
    "rick owens": 1,
    # Anti-signals (distinctly NOT Jensen)
    "brown": -2,
    "tan": -2,
    "suede": -3,
    "shearling": -2,
    "bomber": -1,
    "varsity": -3,
}


def calculate_jensen_score(title: str, description: str = "") -> int:
    """
    Calculate how "Jensen-coded" a leather jacket listing is.
    Returns a score from -10 to 50+.
    """
    text = f"{title} {description}".lower()
    score = 0
    
    for keyword, weight in JENSEN_KEYWORDS.items():
        if keyword in text:
            score += weight
    
    # Bonus: Black is the only acceptable color for peak Jensen
    if "black" in text and "leather" in text:
        score += 2
    
    return score


def init_db():
    """Initialize SQLite database with schema."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Jacket listings table
    c.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY,
            title TEXT,
            designer TEXT,
            price REAL,
            sold_price REAL,
            is_sold BOOLEAN,
            jensen_score INTEGER,
            scraped_at TIMESTAMP,
            sold_at TIMESTAMP,
            url TEXT
        )
    """)
    
    # Daily aggregates for the index
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_index (
            date DATE PRIMARY KEY,
            avg_price REAL,
            median_price REAL,
            avg_sold_price REAL,
            total_listings INTEGER,
            sold_count INTEGER,
            avg_jensen_score REAL,
            nvda_close REAL,
            nvda_pct_change REAL
        )
    """)
    
    # NVDA earnings dates (for "inspiration premium" tracking)
    c.execute("""
        CREATE TABLE IF NOT EXISTS nvda_events (
            date DATE PRIMARY KEY,
            event_type TEXT,
            description TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized.")


def scrape_leather_jackets():
    """
    Scrape leather jacket listings from Grailed.
    Focuses on "Jensen-coded" items.
    """
    client = GrailedAPIClient()
    all_products = []
    
    # Search queries that maximize Jensen-coding
    queries = [
        "leather jacket black",
        "biker jacket leather",
        "moto jacket",
        "cafe racer jacket",
        "leather jacket asymmetric",
    ]
    
    for query in queries:
        print(f"Searching: {query}")
        
        # Get on-sale listings
        try:
            products = client.find_products(
                sold=False,
                on_sale=True,
                query_search=query,
                categories=[Outerwear.LEATHER_JACKETS],
                hits_per_page=40,
                page=1,
            )
            all_products.extend(products)
        except Exception as e:
            print(f"  Error fetching on_sale: {e}")
        
        # Get recently sold listings (for price realization data)
        try:
            sold_products = client.find_products(
                sold=True,
                on_sale=False,
                query_search=query,
                categories=[Outerwear.LEATHER_JACKETS],
                hits_per_page=40,
                page=1,
            )
            all_products.extend(sold_products)
        except Exception as e:
            print(f"  Error fetching sold: {e}")
    
    # Deduplicate by ID
    seen = set()
    unique_products = []
    for p in all_products:
        pid = p.get("id")
        if pid and pid not in seen:
            seen.add(pid)
            unique_products.append(p)
    
    print(f"Found {len(unique_products)} unique listings")
    return unique_products


def store_listings(products: list):
    """Store scraped listings in database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    now = datetime.now().isoformat()
    
    for p in products:
        try:
            pid = str(p.get("id", ""))
            title = p.get("title", "")
            designer = p.get("designer", {}).get("name", "Unknown")
            price = float(p.get("price", 0))
            sold_price = float(p.get("sold_price", 0)) if p.get("sold") else None
            is_sold = bool(p.get("sold", False))
            description = p.get("description", "")
            
            jensen_score = calculate_jensen_score(title, description)
            
            c.execute("""
                INSERT OR REPLACE INTO listings 
                (id, title, designer, price, sold_price, is_sold, jensen_score, scraped_at, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pid,
                title,
                designer,
                price,
                sold_price,
                is_sold,
                jensen_score,
                now,
                f"https://grailed.com/listings/{pid}",
            ))
        except Exception as e:
            print(f"Error storing listing {p.get('id')}: {e}")
    
    conn.commit()
    conn.close()
    print(f"Stored {len(products)} listings")


def fetch_nvda_data(days: int = 90):
    """Fetch NVDA stock data from Yahoo Finance."""
    end = datetime.now()
    start = end - timedelta(days=days)
    
    nvda = yf.Ticker("NVDA")
    hist = nvda.history(start=start, end=end)
    
    return hist


def compute_daily_index():
    """
    Compute the daily Jensen Huang Leather Jacket Index.
    Correlates jacket prices with NVDA performance.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get NVDA data
    nvda_data = fetch_nvda_data(90)
    
    today = datetime.now().date().isoformat()
    
    # Compute jacket metrics
    c.execute("""
        SELECT 
            AVG(price) as avg_price,
            AVG(sold_price) as avg_sold_price,
            COUNT(*) as total_listings,
            SUM(CASE WHEN is_sold THEN 1 ELSE 0 END) as sold_count,
            AVG(jensen_score) as avg_jensen_score
        FROM listings
        WHERE DATE(scraped_at) = DATE('now')
    """)
    
    row = c.fetchone()
    
    if row and row[0]:
        # Get today's NVDA data
        try:
            nvda_today = nvda_data.iloc[-1]
            nvda_close = float(nvda_today["Close"])
            nvda_prev = nvda_data.iloc[-2]["Close"] if len(nvda_data) > 1 else nvda_close
            nvda_pct_change = ((nvda_close - nvda_prev) / nvda_prev) * 100
        except:
            nvda_close = 0
            nvda_pct_change = 0
        
        c.execute("""
            INSERT OR REPLACE INTO daily_index
            (date, avg_price, median_price, avg_sold_price, total_listings, 
             sold_count, avg_jensen_score, nvda_close, nvda_pct_change)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            today,
            row[0],  # avg_price
            row[0],  # median_price (simplified)
            row[1],  # avg_sold_price
            row[2],  # total_listings
            row[3],  # sold_count
            row[4],  # avg_jensen_score
            nvda_close,
            nvda_pct_change,
        ))
        
        conn.commit()
        print(f"Computed daily index for {today}")
        print(f"  Avg Jacket Price: ${row[0]:.2f}")
        print(f"  NVDA Close: ${nvda_close:.2f} ({nvda_pct_change:+.2f}%)")
        print(f"  Avg Jensen Score: {row[4]:.1f}")
    
    conn.close()


def get_index_data(days: int = 90) -> dict:
    """
    Get index data for the API/frontend.
    Returns structured data for the Bloomberg Terminal clone.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get daily index data
    c.execute("""
        SELECT * FROM daily_index 
        ORDER BY date DESC 
        LIMIT ?
    """, (days,))
    
    daily_data = [dict(row) for row in c.fetchall()]
    
    # Get top Jensen-coded listings
    c.execute("""
        SELECT * FROM listings 
        WHERE jensen_score > 5
        ORDER BY jensen_score DESC, price DESC
        LIMIT 10
    """)
    
    top_jensen = [dict(row) for row in c.fetchall()]
    
    # Compute correlation metrics
    if len(daily_data) >= 7:
        # Calculate trailing 7-day correlation
        prices = [d["avg_price"] for d in daily_data[:7] if d["avg_price"]]
        nvda = [d["nvda_pct_change"] for d in daily_data[:7] if d["nvda_pct_change"]]
        
        # Simplified correlation (would use numpy.corrcoef in production)
        correlation = 0.73  # Placeholder - the joke is it's always suspiciously high
    else:
        correlation = None
    
    conn.close()
    
    return {
        "daily_index": daily_data,
        "top_jensen_coded": top_jensen,
        "correlation_7d": correlation,
        "last_updated": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("JENSEN HUANG LEATHER JACKET INDEX")
    print("Alternative Data for the Discerning Investor")
    print("=" * 60)
    
    init_db()
    
    print("\n[1/3] Scraping Grailed...")
    products = scrape_leather_jackets()
    
    print("\n[2/3] Storing listings...")
    store_listings(products)
    
    print("\n[3/3] Computing daily index...")
    compute_daily_index()
    
    print("\n" + "=" * 60)
    print("Index updated successfully.")
    print("=" * 60)
