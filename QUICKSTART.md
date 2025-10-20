# Quick Start Guide

Get the PAL to TREVEE Migration Dashboard running in 5 minutes!

## 1. Install Dependencies

```bash
cd pal-trevee-dashboard/backend
pip install -r requirements.txt
```

## 2. Sync Migration Data

Fetch all migration data from Sonic blockchain:

```bash
python3 sync.py --full
```

Wait for the sync to complete. You should see output like:
```
Found 150 migration events in 45.2 seconds
Successfully inserted 150 migrations
Total PAL Migrated: 1,234,567.89
```

## 3. Start API Server

In a new terminal:

```bash
python3 api.py
```

You should see:
```
Starting PAL to TREVEE Migration API Server...
API available at http://localhost:5000
```

## 4. Open Dashboard

Open `frontend/index.html` in your browser:

```bash
# From the project root
open frontend/index.html
```

OR start a local web server:

```bash
cd frontend
python3 -m http.server 8000
```

Then visit: http://localhost:8000

## 5. Keep Data Updated (Optional)

For continuous updates, run in a third terminal:

```bash
cd backend
python3 sync.py --continuous
```

This will automatically sync new migrations every 5 minutes.

---

## Troubleshooting

**No data showing?**
- Make sure you ran `sync.py --full` first
- Check that API server is running on port 5000

**API errors?**
- Verify you're connected to the internet
- Sonic RPC might be rate-limiting (add delays in config.py)

**Charts not loading?**
- Open browser console (F12) to see errors
- Try using a local web server instead of opening HTML directly

---

## What's Next?

- ✅ Dashboard is now tracking migrations in real-time!
- 📊 Explore the charts and statistics
- 🔍 Try the address lookup feature
- 📥 Export data as CSV or JSON
- ⚙️ Customize settings in `backend/config.py`

For detailed documentation, see [README.md](README.md)
