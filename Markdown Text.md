# Jensen Huang Leather Jacket Index

**Alternative data for the discerning investor.**

A Bloomberg Terminal-style dashboard that tracks leather jacket resale prices on Grailed and correlates them with NVIDIA stock performance. Because markets are efficient.

![JHLJ Index](preview.png)

## The Thesis

Jensen Huang, CEO of NVIDIA, is famous for his black leather jacket. We hypothesize that:

1. The resale market for "Jensen-coded" leather jackets (black, biker style, asymmetric zips) reflects market sentiment about NVIDIA
2. Jacket prices **lead** NVDA stock by 3-5 days
3. This is definitely not financial advice

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
│  Grailed API │───▶│   Python     │───▶│   SQLite DB      │
│  (scraper)   │    │   Backend    │    │   jackets.db     │
└──────────────┘    │   (Flask)    │    └──────────────────┘
                    └──────────────┘              │
┌──────────────┐            │                     │
│  yfinance    │───▶        │                     ▼
│  (NVDA)      │            ▼              ┌──────────────┐
└──────────────┘    ┌──────────────┐       │ React        │
                    │  /api/index  │◀──────│ Bloomberg UI │
                    └──────────────┘       └──────────────┘
```

## The Jensen-Coded™ Scoring System

What makes a leather jacket "Jensen-coded"? Our proprietary algorithm:

| Signal | Weight | Notes |
|--------|--------|-------|
| Black leather | +2 | Base requirement |
| Biker/moto style | +3 | The core silhouette |
| Asymmetric zip | +2 | Classic Jensen |
| Band collar | +1 | vs. notch lapel |
| Schott/AllSaints/Kooples | +2 | Aspirational brands |
| Description mentions "tech" or "CEO" | +5 | Peak correlation |
| Description mentions "NVIDIA" or "Jensen" | +10 | The holy grail |
| Brown/tan/suede | -2 to -3 | Distinctly NOT Jensen |

## Setup

### Backend (Python)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Initialize database & run first scrape
python scraper.py

# Start API server
flask run --port 5000
```

### Frontend (React)

```bash
cd frontend

# Option 1: Drop into existing React project
cp JensenIndex.jsx your-project/src/components/

# Option 2: Use create-react-app
npx create-react-app jensen-index-app
cp JensenIndex.jsx jensen-index-app/src/
```

### Cron Job (Daily Updates)

```bash
# Add to crontab for daily 9am scraping
0 9 * * * cd /path/to/jensen-index/backend && python scraper.py >> /var/log/jensen-index.log 2>&1
```

## API Endpoints

### `GET /api/index`

Returns all index data for the Bloomberg Terminal display.

```json
{
  "ticker": "JHLJ",
  "name": "Jensen Huang Leather Jacket Index",
  "last_updated": "2024-12-28",
  "alt_data_metrics": [...],
  "weekly_data": [...],
  "top_listings": [...],
  "daily_history": [...]
}
```

### `GET /api/correlation`

Returns correlation analysis between jacket prices and NVDA.

```json
{
  "r_squared": 0.67,
  "p_value": 0.003,
  "insights": [
    "Asymmetric zippers correlate with 2.3% higher next-day NVDA returns",
    "Black leather listings spike 18% before earnings calls"
  ],
  "disclaimer": "This is not financial advice. This is fashion advice."
}
```

## Deployment

### Static Frontend (GitHub Pages)

The React component can be built and deployed to GitHub Pages:

```bash
npm run build
# Deploy to username.github.io/jensen-index
```

### Backend (Render/Railway/Fly.io)

Free tier works great for this scale:

```bash
# Render
render deploy

# Railway  
railway up

# Fly.io
fly deploy
```

### Full Stack ($0/month)

1. Frontend: GitHub Pages (free)
2. Backend: Render free tier (spins down after 15min, spins up on request)
3. Database: SQLite file in repo or Render persistent disk
4. Scraping: GitHub Actions cron (free)

## Contributing

Found a leather jacket listing that's clearly Jensen-coded but scored low? Open a PR to improve the algorithm.

## Disclaimer

This project is satire. Do not make investment decisions based on leather jacket prices. The "correlation" is generated randomly and has no predictive value.

That said, if you do find alpha in the leather jacket market, please let me know.

## License

MIT

---

*"The leather jacket market is a leading indicator for semiconductor demand."*  
*— No one, ever*
