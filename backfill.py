import sqlite3
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
import random
import os

# Import the classification logic from app.py to keep it consistent
from app import calculate_jensen_score, DB_PATH, init_db, run_scrape, get_db_connection

def backfill_index():
    """
    Backfills the daily_index with historical NVDA data.
    Since we don't have historical jacket prices, we use current average 
    as a baseline and add some simulated variance.
    """
    print("--- Starting Backfill ---")
    init_db()
    
    # 1. Run a fresh scrape to get current listings and baseline price
    print("Fetching current Grailed data for baseline...")
    run_scrape()
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get current baseline from the scrape we just did
    c.execute("SELECT AVG(price), AVG(jensen_score), COUNT(*) FROM listings")
    baseline = c.fetchone()
    if not baseline or not baseline[0]:
        print("Error: No baseline data found. Scrape might have failed.")
        return

    avg_price_base = baseline[0]
    avg_score_base = baseline[1]
    count_base = baseline[2]
    
    print(f"Baseline: ${avg_price_base:.2f} avg price, {avg_score_base:.1f} avg Jensen score")

    # 2. Fetch NVDA history for the last 90 days
    print("Fetching NVDA historical data...")
    nvda = yf.Ticker("NVDA")
    hist = nvda.history(period="90d")
    
    # 3. Populate daily_index
    print(f"Populating index for {len(hist)} days...")
    
    # To make it look "real", we'll simulate jacket price changes that correlate 
    # slightly with NVDA, because "efficient markets".
    for date, row in hist.iterrows():
        date_str = date.date().isoformat()
        nvda_close = float(row['Close'])
        
        # Calculate pct change if possible
        try:
            prev_close = hist['Close'].shift(1).loc[date]
            nvda_pct = ((nvda_close - prev_close) / prev_close) * 100 if prev_close else 0
        except:
            nvda_pct = 0
            
        # Simulating jacket price correlation (beta = 0.7ish as per the joke)
        # We add some random noise so it doesn't look like a perfect copy
        simulated_jacket_change = (nvda_pct * 0.7) + random.uniform(-1, 1)
        simulated_price = avg_price_base * (1 + simulated_jacket_change / 100)
        
        # Jensen score also fluctuates with "tech energy"
        simulated_score = avg_score_base + (nvda_pct * 0.05) + random.uniform(-0.2, 0.2)
        
        c.execute("""INSERT OR REPLACE INTO daily_index 
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (date_str, 
                   round(simulated_price, 2), 
                   round(simulated_price * 0.95, 2), # median
                   round(simulated_price * 0.9, 2),  # avg_sold
                   count_base + random.randint(-10, 10), 
                   int(count_base * 0.2) + random.randint(-5, 5),
                   round(simulated_score, 2),
                   round(nvda_close, 2),
                   round(nvda_pct, 2)))
        
    conn.commit()
    conn.close()
    print("--- Backfill Complete ---")
    print(f"Database saved to: {DB_PATH}")

if __name__ == "__main__":
    backfill_index()

