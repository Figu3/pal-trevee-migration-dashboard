# PAL to TREVEE Migration Dashboard

A comprehensive real-time dashboard that tracks PAL token migration to TREVEE on the Sonic blockchain (Chain ID: 146).

![Dashboard Preview](https://img.shields.io/badge/Status-Production%20Ready-success)
![Blockchain](https://img.shields.io/badge/Blockchain-Sonic-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)

## Features

### Core Functionality
- **Real-time Migration Tracking**: Fetches all migration transactions from the Sonic blockchain
- **Comprehensive Metrics**:
  - Total unique migrators
  - Total PAL tokens migrated
  - Average and median migration sizes
  - Daily migration rates
  - Migration size distribution

### Data Visualization
- **Cumulative Migration Chart**: Track total PAL migrated over time
- **Daily Volume Chart**: See daily migration activity
- **Distribution Histogram**: Understand migration size patterns
- **Source Breakdown**: Sonic native vs Ethereum bridged migrations (pie chart)

### Advanced Features
- **SQLite Caching**: Efficient local data storage with incremental updates
- **Address Lookup**: Search specific wallet addresses
- **Top Migrations Table**: View the largest 10 migrations
- **Export Functionality**: Download data in CSV or JSON format
- **Auto-refresh**: Dashboard updates every 5 minutes
- **Dark Theme**: Professional, eye-friendly interface

## Project Structure

```
pal-trevee-dashboard/
├── backend/
│   ├── config.py              # Configuration settings
│   ├── rpc_client.py          # Sonic blockchain RPC client
│   ├── migration_tracker.py   # Migration data fetcher
│   ├── database.py            # SQLite database manager
│   ├── data_processor.py      # Metrics calculation
│   ├── sync.py                # Main sync script
│   ├── api.py                 # Flask REST API server
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── index.html             # Dashboard HTML
│   ├── styles.css             # Dark theme styles
│   └── app.js                 # Dashboard JavaScript
├── data/
│   └── migrations.db          # SQLite database (auto-created)
└── README.md
```

## Contract Addresses

- **PAL Token**: `0xe90FE2DE4A415aD48B6DcEc08bA6ae98231948Ac`
- **Migration Contract**: `0x99fe40e501151e92f10ac13ea1c06083ee170363`
- **Blockchain**: Sonic (Chain ID: 146)
- **Block Explorer**: https://sonicscan.org

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

1. **Navigate to the project directory**:
```bash
cd pal-trevee-dashboard
```

2. **Install Python dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

### Configuration

Edit `backend/config.py` to customize settings:

```python
# Optional: Set Sonicscan API key for higher rate limits
SONICSCAN_API_KEY = "your_api_key_here"

# Adjust refresh interval (in seconds)
REFRESH_INTERVAL = 300  # 5 minutes

# Set alert threshold for large migrations
LARGE_MIGRATION_THRESHOLD = 100000  # PAL tokens

# Set migration deadline (if applicable)
MIGRATION_DEADLINE = "2025-12-31 23:59:59"  # or None
```

## Usage

### Step 1: Initial Data Sync

Perform a full sync to fetch all migration data from the blockchain:

```bash
cd backend
python3 sync.py --full
```

This will:
- Connect to Sonic blockchain via RPC
- Scan for all PAL token transfers to the migration contract
- Parse and store data in SQLite database
- Display summary statistics

**Note**: Initial sync may take several minutes depending on the number of blocks to scan.

### Step 2: Start the API Server

In a new terminal window:

```bash
cd backend
python3 api.py
```

The API server will start on `http://localhost:5000`

Available endpoints:
- `GET /api/health` - Health check
- `GET /api/metrics` - All metrics
- `GET /api/statistics` - Summary statistics
- `GET /api/daily-stats` - Daily statistics
- `GET /api/migration-rate?days=7` - Migration rate
- `GET /api/timeline` - Complete timeline
- `GET /api/address/<address>` - Address lookup
- `GET /api/large-migrations?threshold=100000` - Large migrations
- `GET /api/export/json` - Export as JSON
- `GET /api/export/csv` - Export as CSV

### Step 3: Open the Dashboard

Open `frontend/index.html` in your web browser:

```bash
# macOS
open frontend/index.html

# Linux
xdg-open frontend/index.html

# Windows
start frontend/index.html
```

Or use a local web server (recommended):

```bash
cd frontend
python3 -m http.server 8000
```

Then open http://localhost:8000 in your browser.

### Step 4: Continuous Sync (Optional)

For real-time updates, run the sync script in continuous mode:

```bash
cd backend
python3 sync.py --continuous
```

This will sync new migrations every 5 minutes automatically.

## API Usage Examples

### Get All Metrics
```bash
curl http://localhost:5000/api/metrics
```

### Look Up Specific Address
```bash
curl http://localhost:5000/api/address/0x1234...
```

### Export Data as CSV
```bash
curl http://localhost:5000/api/export/csv -o migrations.csv
```

### Get Migration Rate
```bash
curl http://localhost:5000/api/migration-rate?days=7
```

## Advanced Features

### Source Chain Detection

The dashboard attempts to identify whether migrations originated from:
- **Sonic Native**: Direct migrations from Sonic blockchain PAL holders
- **Ethereum Bridge**: Bridged migrations from Ethereum

Detection logic analyzes transaction patterns and bridge-related events.

### Large Migration Alerts

Configure alerts for large migrations by editing `config.py`:

```python
LARGE_MIGRATION_THRESHOLD = 100000  # PAL tokens
ENABLE_ALERTS = True
ALERT_EMAIL = "your-email@example.com"
ALERT_DISCORD_WEBHOOK = "https://discord.com/api/webhooks/..."
```

### Known Address Labels

Label important addresses in `config.py`:

```python
KNOWN_ADDRESSES = {
    "0x1234...": "Paladin Treasury",
    "0x5678...": "Team Wallet",
}
```

### Historical Snapshots

The database automatically saves daily snapshots for trend analysis:

```python
from database import MigrationDatabase

db = MigrationDatabase()
db.save_daily_snapshot()
```

## Troubleshooting

### Issue: "Connection refused" error

**Solution**: Make sure the API server is running:
```bash
cd backend
python3 api.py
```

### Issue: No migrations found

**Solution**:
1. Verify the contract addresses in `config.py`
2. Check if the migration contract has been deployed
3. Run sync with `--full` flag to rescan from genesis

### Issue: Charts not loading

**Solution**:
1. Check browser console for errors (F12)
2. Verify API server is running on port 5000
3. Check CORS settings if accessing from different domain

### Issue: Slow sync performance

**Solution**:
1. Adjust `BATCH_SIZE` in `config.py` (default: 10000 blocks)
2. Use Sonicscan API key for higher rate limits
3. Start sync from deployment block instead of genesis

## Development

### Adding New Metrics

1. Add calculation logic to `data_processor.py`
2. Create new API endpoint in `api.py`
3. Update frontend to display the metric

### Customizing the Dashboard

- **Theme**: Edit color variables in `frontend/styles.css`
- **Charts**: Modify chart configurations in `frontend/app.js`
- **Layout**: Update HTML structure in `frontend/index.html`

### Database Schema

**migrations** table:
```sql
- id (INTEGER PRIMARY KEY)
- tx_hash (TEXT UNIQUE)
- from_address (TEXT)
- to_address (TEXT)
- amount (INTEGER)
- amount_pal (REAL)
- block_number (INTEGER)
- block_timestamp (INTEGER)
- timestamp (TEXT)
- log_index (INTEGER)
- source (TEXT)
```

## Performance Optimization

- **Incremental Sync**: Only fetches new blocks since last sync
- **Batch Processing**: Processes blocks in configurable batches
- **SQLite Indexing**: Optimized indexes for fast queries
- **API Caching**: Metrics calculated once per request
- **Rate Limiting**: Built-in delays to respect RPC limits

## Security Notes

- Never commit API keys to version control
- Use environment variables for sensitive configuration
- Validate all user inputs (especially address lookups)
- Keep dependencies updated for security patches

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - feel free to use this dashboard for your own projects.

## Support

For issues or questions:
- Open an issue on GitHub
- Check Sonic documentation: https://docs.soniclabs.com
- Visit Sonicscan: https://sonicscan.org

## Roadmap

- [ ] Email/Discord notifications for large migrations
- [ ] Price feed integration (USD value tracking)
- [ ] Wallet address labeling database
- [ ] Historical comparison charts
- [ ] Mobile app version
- [ ] WebSocket support for real-time updates
- [ ] Multi-language support

## Credits

Built with:
- Python 3.8+
- Flask (REST API)
- Chart.js (Visualizations)
- Postgres (Data storage via Prisma)
- Sonic blockchain RPC

---

**Disclaimer**: This dashboard is for informational purposes only. Always verify data directly on the blockchain explorer.

*Last updated: 2025-01-21*
