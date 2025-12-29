"""
Jensen Huang Leather Jacket Index - API Server
Serves index data to the Bloomberg Terminal frontend.

Run: flask run --port 5000
"""

from flask import Flask, jsonify
from flask_cors import CORS
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import random

app = Flask(__name__)
CORS(app)

DB_PATH = Path(__file__).parent / "jackets.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================================
# MOCK DATA GENERATOR
# For demo purposes when real scraping isn't available
# ============================================================================

def generate_mock_data():
    """
    Generate plausible-looking mock data for the index.
    In production, this would come from the SQLite database.
    """
    base_date = datetime.now()
    
    # Generate 90 days of "historical" data
    daily_data = []
    base_jacket_price = 485  # Average leather jacket on Grailed
    base_nvda = 138.0  # NVDA price
    
    for i in range(90, 0, -1):
        date = base_date - timedelta(days=i)
        
        # Create correlated movement (the joke)
        nvda_change = random.gauss(0.3, 2.5)  # Slight upward bias
        jacket_change = nvda_change * 0.4 + random.gauss(0, 1.5)  # "Correlated"
        
        base_nvda *= (1 + nvda_change / 100)
        base_jacket_price *= (1 + jacket_change / 100)
        
        # Jensen score increases after NVDA rallies (the absurdist insight)
        jensen_boost = max(0, nvda_change * 0.5)
        
        daily_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "avg_price": round(base_jacket_price, 2),
            "avg_sold_price": round(base_jacket_price * 0.85, 2),
            "total_listings": random.randint(120, 180),
            "sold_count": random.randint(15, 35),
            "avg_jensen_score": round(6.5 + jensen_boost + random.gauss(0, 1), 1),
            "nvda_close": round(base_nvda, 2),
            "nvda_pct_change": round(nvda_change, 2),
        })
    
    return daily_data


def generate_mock_listings():
    """Generate mock Jensen-coded listings."""
    listings = [
        {
            "id": "12847291",
            "title": "Schott NYC 626 Leather Moto Jacket Black",
            "designer": "Schott NYC",
            "price": 650,
            "jensen_score": 12,
            "is_sold": False,
        },
        {
            "id": "12903847",
            "title": "AllSaints Cargo Leather Biker Jacket",
            "designer": "AllSaints",
            "price": 380,
            "jensen_score": 10,
            "is_sold": False,
        },
        {
            "id": "12756392",
            "title": "The Kooples Asymmetric Leather Jacket Black",
            "designer": "The Kooples",
            "price": 425,
            "jensen_score": 9,
            "is_sold": True,
            "sold_price": 395,
        },
        {
            "id": "12834756",
            "title": "Acne Studios Nate Clean Leather Jacket",
            "designer": "Acne Studios",
            "price": 890,
            "jensen_score": 7,
            "is_sold": False,
        },
        {
            "id": "12901234",
            "title": "Saint Laurent L01 Classic Motorcycle Jacket",
            "designer": "Saint Laurent",
            "price": 2400,
            "jensen_score": 8,
            "is_sold": False,
        },
        {
            "id": "12887654",
            "title": "Rick Owens Stooges Leather Jacket",
            "designer": "Rick Owens",
            "price": 1650,
            "jensen_score": 6,
            "is_sold": False,
        },
        {
            "id": "12776543",
            "title": "Vintage Cafe Racer Black Leather Jacket",
            "designer": "Vintage",
            "price": 245,
            "jensen_score": 8,
            "is_sold": True,
            "sold_price": 220,
        },
        {
            "id": "12998877",
            "title": "Black Leather Tech CEO Biker (NVIDIA investor energy)",
            "designer": "Unknown",
            "price": 320,
            "jensen_score": 25,  # THE HOLY GRAIL
            "is_sold": False,
        },
    ]
    return sorted(listings, key=lambda x: -x["jensen_score"])


@app.route("/api/index")
def get_index():
    """
    Main endpoint: Returns all index data for the Bloomberg Terminal.
    """
    daily_data = generate_mock_data()
    listings = generate_mock_listings()
    
    # Calculate "Alt Data Metrics" in Bloomberg style
    recent_7 = daily_data[-7:]
    recent_28 = daily_data[-28:]
    recent_91 = daily_data[-91:] if len(daily_data) >= 91 else daily_data
    
    def calc_trailing(data, field):
        vals = [d[field] for d in data if d.get(field)]
        return sum(vals) / len(vals) if vals else 0
    
    def calc_pct_change(data, field):
        if len(data) < 2:
            return 0
        start = data[0][field]
        end = data[-1][field]
        return ((end - start) / start) * 100 if start else 0
    
    alt_data_metrics = [
        {
            "name": "Avg Jacket Price",
            "trailing91": round(calc_trailing(recent_91, "avg_price"), 2),
            "trailing28": round(calc_trailing(recent_28, "avg_price"), 2),
            "trailing7": round(calc_trailing(recent_7, "avg_price"), 2),
            "pop91": round(calc_pct_change(recent_91, "avg_price"), 2),
            "pop28": round(calc_pct_change(recent_28, "avg_price"), 2),
            "pop7": round(calc_pct_change(recent_7, "avg_price"), 2),
            "highlighted": True,
        },
        {
            "name": "Jensen Score (Avg)",
            "trailing91": round(calc_trailing(recent_91, "avg_jensen_score"), 2),
            "trailing28": round(calc_trailing(recent_28, "avg_jensen_score"), 2),
            "trailing7": round(calc_trailing(recent_7, "avg_jensen_score"), 2),
            "pop91": round(calc_pct_change(recent_91, "avg_jensen_score"), 2),
            "pop28": round(calc_pct_change(recent_28, "avg_jensen_score"), 2),
            "pop7": round(calc_pct_change(recent_7, "avg_jensen_score"), 2),
        },
        {
            "name": "Daily Listings",
            "trailing91": round(calc_trailing(recent_91, "total_listings"), 0),
            "trailing28": round(calc_trailing(recent_28, "total_listings"), 0),
            "trailing7": round(calc_trailing(recent_7, "total_listings"), 0),
            "pop91": round(calc_pct_change(recent_91, "total_listings"), 2),
            "pop28": round(calc_pct_change(recent_28, "total_listings"), 2),
            "pop7": round(calc_pct_change(recent_7, "total_listings"), 2),
        },
        {
            "name": "Sold Items",
            "trailing91": round(calc_trailing(recent_91, "sold_count"), 0),
            "trailing28": round(calc_trailing(recent_28, "sold_count"), 0),
            "trailing7": round(calc_trailing(recent_7, "sold_count"), 0),
            "pop91": round(calc_pct_change(recent_91, "sold_count"), 2),
            "pop28": round(calc_pct_change(recent_28, "sold_count"), 2),
            "pop7": round(calc_pct_change(recent_7, "sold_count"), 2),
        },
        {
            "name": "NVDA Correlation (7d)",
            "trailing91": 0.73,  # The suspiciously high correlation
            "trailing28": 0.68,
            "trailing7": 0.81,
            "pop91": 2.34,
            "pop28": 5.12,
            "pop7": 8.94,
        },
    ]
    
    # Weekly price data for the time series chart
    weekly_data = []
    for i in range(0, min(12, len(daily_data)), 7):
        week = daily_data[i:i+7]
        if week:
            avg = sum(d["avg_price"] for d in week) / len(week)
            nvda_avg = sum(d["nvda_pct_change"] for d in week) / len(week)
            weekly_data.append({
                "week_ending": week[-1]["date"],
                "jacket_pct_change": round(calc_pct_change(week, "avg_price"), 2),
                "nvda_pct_change": round(nvda_avg, 2),
            })
    
    return jsonify({
        "ticker": "JHLJ",
        "name": "Jensen Huang Leather Jacket Index",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "alt_data_metrics": alt_data_metrics,
        "weekly_data": weekly_data[::-1],  # Chronological order
        "top_listings": listings[:8],
        "daily_history": daily_data[-30:],  # Last 30 days
        "data_sources": {
            "grailed": {
                "description": "Leather jacket resale marketplace",
                "panel": "~150 daily listings",
                "methodology": "Jensen-coded scoring algorithm",
            },
            "nvda": {
                "description": "NVIDIA Corp stock price",
                "source": "Yahoo Finance",
            },
        },
    })


@app.route("/api/correlation")
def get_correlation():
    """
    Returns correlation analysis between jacket prices and NVDA.
    The absurdist heart of the project.
    """
    return jsonify({
        "headline": "Leather Jacket Prices Lead NVDA by 3-5 Days",
        "r_squared": 0.67,
        "p_value": 0.003,  # "Statistically significant"
        "methodology": "Proprietary Jensen-Coded scoring + Granger causality",
        "disclaimer": "This is not financial advice. This is fashion advice.",
        "insights": [
            "Asymmetric zippers correlate with 2.3% higher next-day NVDA returns",
            "Black leather listings spike 18% in the week before earnings calls",
            "Schott NYC jackets are the most predictive brand (r=0.74)",
            "Jensen Score >10 items precede 5%+ NVDA moves 73% of the time",
        ],
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "message": "The jacket market is efficient."})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
