# Usage Guide - PAL to TREVEE Migration Dashboard

## Table of Contents
1. [Quick Start with Demo Data](#quick-start-with-demo-data)
2. [Using Real Blockchain Data](#using-real-blockchain-data)
3. [Dashboard Features](#dashboard-features)
4. [API Reference](#api-reference)
5. [Common Tasks](#common-tasks)

---

## Quick Start with Demo Data

Perfect for testing the dashboard without waiting for blockchain syncs!

### Option 1: Using the Run Script (Easiest)

```bash
cd pal-trevee-dashboard
./run.sh
```

When prompted, choose option 1 (Generate demo data).

### Option 2: Manual Setup

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Generate demo data
python3 demo_data.py --migrations 200 --addresses 50

# 3. Start API server
python3 api.py
```

In a new terminal:
```bash
# 4. Open dashboard
cd frontend
python3 -m http.server 8000
```

Visit: http://localhost:8000

---

## Using Real Blockchain Data

### First-Time Sync

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Sync all migrations from blockchain
python3 sync.py --full
```

**Note**: Initial sync scans ~1.3 million blocks and may take 30-60 minutes depending on:
- Network speed
- RPC rate limits
- Number of migrations

### Incremental Updates

After the initial sync, update with new data:

```bash
python3 sync.py
```

This only fetches new blocks since the last sync (much faster!).

### Continuous Monitoring

For real-time tracking:

```bash
python3 sync.py --continuous
```

This runs sync every 5 minutes automatically.

---

## Dashboard Features

### 1. Summary Cards

- **Unique Migrators**: Total distinct wallet addresses
- **Total PAL Migrated**: Sum of all migrated PAL tokens
- **Total Migrations**: Number of migration transactions
- **Average Migration**: Mean migration size (with median)

### 2. Migration Rate Stats

- **7-Day Average**: Daily migration count over last week
- **7-Day PAL Rate**: Daily PAL volume over last week
- **Migration Deadline**: Contract deadline (if set)

### 3. Charts

#### Cumulative PAL Migrated
- Line chart showing total PAL over time
- Useful for tracking growth trends

#### Daily Migration Volume
- Bar chart of daily PAL migrated
- Identify peak migration days

#### Migration Size Distribution
- Histogram of migration sizes
- Understand typical migration patterns
- Bins: 0-100, 100-500, 500-1K, 1K-5K, etc.

#### Source Breakdown
- Pie chart: Sonic native vs Ethereum bridged
- Shows migration origin distribution

### 4. Top Migrations Table

- 10 largest migrations by PAL amount
- Click addresses/transactions to view on Sonicscan
- Real-time updates

### 5. Address Lookup

Search any wallet address to see:
- Total migrations from that address
- Total PAL migrated
- Individual transaction details
- Transaction links to block explorer

### 6. Export Data

Download complete migration data:
- **CSV Format**: For spreadsheets (Excel, Google Sheets)
- **JSON Format**: For programmatic analysis

---

## API Reference

Base URL: `http://localhost:5000/api`

### Endpoints

#### GET `/health`
Health check
```bash
curl http://localhost:5000/api/health
```

#### GET `/metrics`
All dashboard metrics in one call
```bash
curl http://localhost:5000/api/metrics
```

Response:
```json
{
  "summary": {
    "total_unique_addresses": 150,
    "total_pal_migrated": 450000.50,
    "average_migration_size": 3000.00
  },
  "daily_stats": [...],
  "cumulative_data": [...],
  "distribution": {...},
  "source_breakdown": {...},
  "top_migrations": [...]
}
```

#### GET `/statistics`
Summary statistics only
```bash
curl http://localhost:5000/api/statistics
```

#### GET `/daily-stats`
Daily migration statistics
```bash
curl http://localhost:5000/api/daily-stats
```

#### GET `/migration-rate?days=7`
Migration rate over N days
```bash
curl http://localhost:5000/api/migration-rate?days=7
curl http://localhost:5000/api/migration-rate?days=30
```

#### GET `/address/<address>`
Lookup specific address
```bash
curl http://localhost:5000/api/address/0x1234567890abcdef1234567890abcdef12345678
```

#### GET `/large-migrations?threshold=100000`
Migrations above threshold
```bash
curl http://localhost:5000/api/large-migrations?threshold=100000
```

#### GET `/export/csv`
Export as CSV
```bash
curl http://localhost:5000/api/export/csv -o migrations.csv
```

#### GET `/export/json`
Export as JSON
```bash
curl http://localhost:5000/api/export/json -o migrations.json
```

---

## Common Tasks

### Check Sync Status

```bash
curl http://localhost:5000/api/sync-status
```

### Find Large Migrations (>50K PAL)

```bash
curl http://localhost:5000/api/large-migrations?threshold=50000
```

### Export for Analysis

```bash
# Download CSV
curl http://localhost:5000/api/export/csv -o migrations_$(date +%Y%m%d).csv

# Download JSON
curl http://localhost:5000/api/export/json -o migrations_$(date +%Y%m%d).json
```

### Monitor Specific Address

```bash
ADDRESS="0x1234567890abcdef1234567890abcdef12345678"
curl http://localhost:5000/api/address/$ADDRESS | python3 -m json.tool
```

### Get Migration Timeline

```bash
curl http://localhost:5000/api/timeline | python3 -m json.tool
```

### Clear Database and Start Fresh

```bash
cd backend
python3 demo_data.py --clear
```

### Regenerate Demo Data

```bash
cd backend

# 500 migrations, 100 addresses
python3 demo_data.py --clear --migrations 500 --addresses 100
```

### Custom Sync Range

Edit `backend/config.py`:
```python
START_BLOCK = 50000000  # Start from specific block
```

Then run:
```bash
python3 sync.py --full
```

---

## Tips & Tricks

### Performance Optimization

1. **Use Sonicscan API Key**: Set in `config.py` for higher rate limits
2. **Adjust Batch Size**: Increase `BATCH_SIZE` for faster syncs (but more memory usage)
3. **Start from Deployment**: Use contract deployment block instead of genesis

### Monitoring

Create a cron job for automatic updates:
```bash
# Edit crontab
crontab -e

# Add line (sync every hour)
0 * * * * cd /path/to/pal-trevee-dashboard/backend && python3 sync.py
```

### Custom Alerts

Edit `backend/config.py`:
```python
LARGE_MIGRATION_THRESHOLD = 100000  # Alert for migrations > 100K PAL
ENABLE_ALERTS = True
ALERT_EMAIL = "your-email@example.com"
```

### Integration with Other Tools

The API can be used by:
- Discord bots
- Telegram bots
- Slack notifications
- Custom analytics scripts
- Trading bots

Example Discord webhook:
```python
import requests

# Get large migrations
response = requests.get('http://localhost:5000/api/large-migrations?threshold=100000')
migrations = response.json()

# Send to Discord
for migration in migrations[:5]:
    message = f"🚨 Large migration: {migration['amount_pal']:,.2f} PAL"
    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
```

---

## Troubleshooting

### Dashboard shows "Connection refused"
- Make sure API server is running: `python3 api.py`
- Check port 5000 is not in use: `lsof -i :5000`

### Sync is very slow
- Reduce `BATCH_SIZE` in `config.py`
- Use Sonicscan API key
- Check internet connection

### No migrations found
- Migration may not have started yet
- Verify contract addresses in `config.py`
- Check contract deployment block

### Charts not rendering
- Open browser console (F12) to see errors
- Make sure Chart.js is loading
- Try different browser

---

## Next Steps

1. ✅ Dashboard is running!
2. 📊 Explore the visualizations
3. 🔍 Try address lookups
4. 📥 Export data for analysis
5. ⚙️ Customize settings
6. 🤖 Integrate with your tools

For more information, see [README.md](README.md)
