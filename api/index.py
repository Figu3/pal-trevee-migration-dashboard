#!/usr/bin/env python3
"""
Vercel serverless function entry point with demo data
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import random

app = Flask(__name__)
CORS(app)

# Generate demo data
def generate_demo_migrations(count=100):
    """Generate demo migration data"""
    migrations = []
    base_time = datetime.now() - timedelta(days=30)

    for i in range(count):
        amount_pal = random.lognormvariate(8, 2)
        timestamp = base_time + timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23)
        )

        migrations.append({
            "tx_hash": f"0x{''.join(random.choices('0123456789abcdef', k=64))}",
            "from_address": f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
            "amount_pal": amount_pal,
            "timestamp": timestamp.isoformat(),
            "block_number": 49997769 + i * 100,
            "source": random.choice(['sonic', 'ethereum'])
        })

    return sorted(migrations, key=lambda x: x['timestamp'])

# Generate demo data on module load
MIGRATIONS = generate_demo_migrations(100)

def calculate_metrics():
    """Calculate metrics from migrations"""
    if not MIGRATIONS:
        return {
            "total_migrators": 0,
            "total_pal_migrated": 0,
            "average_migration": 0,
            "median_migration": 0,
            "largest_migration": 0
        }

    amounts = [m['amount_pal'] for m in MIGRATIONS]
    unique_addresses = len(set(m['from_address'] for m in MIGRATIONS))

    return {
        "total_migrators": unique_addresses,
        "total_pal_migrated": sum(amounts),
        "average_migration": sum(amounts) / len(amounts),
        "median_migration": sorted(amounts)[len(amounts) // 2],
        "largest_migration": max(amounts),
        "total_migrations": len(MIGRATIONS)
    }

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mode": "demo"
    })

@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    """Get all migration metrics"""
    metrics = calculate_metrics()
    return jsonify({
        **metrics,
        "last_updated": datetime.now().isoformat(),
        "mode": "demo_data"
    })

@app.route("/api/statistics", methods=["GET"])
def get_statistics():
    """Get summary statistics"""
    metrics = calculate_metrics()

    return jsonify({
        "total_migrations": metrics['total_migrations'],
        "total_amount": metrics['total_pal_migrated'],
        "unique_addresses": metrics['total_migrators'],
        "first_migration": MIGRATIONS[0]['timestamp'] if MIGRATIONS else None,
        "last_migration": MIGRATIONS[-1]['timestamp'] if MIGRATIONS else None,
        "top_migrations": sorted(MIGRATIONS, key=lambda x: x['amount_pal'], reverse=True)[:10]
    })

@app.route("/api/daily-stats", methods=["GET"])
def get_daily_stats():
    """Get daily migration statistics"""
    from collections import defaultdict

    daily = defaultdict(lambda: {"count": 0, "amount": 0})

    for m in MIGRATIONS:
        date = m['timestamp'][:10]
        daily[date]["count"] += 1
        daily[date]["amount"] += m['amount_pal']

    return jsonify([
        {"date": date, **stats}
        for date, stats in sorted(daily.items())
    ])

@app.route("/api/migration-rate", methods=["GET"])
def get_migration_rate():
    """Get migration rate for specified period"""
    days = request.args.get("days", 7, type=int)
    cutoff = datetime.now() - timedelta(days=days)

    recent = [m for m in MIGRATIONS if datetime.fromisoformat(m['timestamp']) > cutoff]

    return jsonify({
        "rate": len(recent) / days if days > 0 else 0,
        "period_days": days,
        "total_in_period": len(recent)
    })

@app.route("/api/timeline", methods=["GET"])
def get_timeline():
    """Get complete migration timeline"""
    return jsonify(MIGRATIONS[:50])  # Return first 50 for performance

@app.route("/api/address/<address>", methods=["GET"])
def lookup_address(address):
    """Look up migrations for a specific address"""
    matches = [m for m in MIGRATIONS if m['from_address'].lower() == address.lower()]

    return jsonify({
        "address": address,
        "migrations": matches,
        "total_amount": sum(m['amount_pal'] for m in matches),
        "count": len(matches)
    })

@app.route("/api/large-migrations", methods=["GET"])
def get_large_migrations():
    """Get migrations above threshold"""
    threshold = request.args.get("threshold", 100000, type=float)
    large = [m for m in MIGRATIONS if m['amount_pal'] > threshold]

    return jsonify(sorted(large, key=lambda x: x['amount_pal'], reverse=True))

@app.route("/api/percentiles", methods=["GET"])
def get_percentiles():
    """Get percentile distribution"""
    amounts = sorted([m['amount_pal'] for m in MIGRATIONS])

    if not amounts:
        return jsonify({})

    percentiles = {}
    for p in [10, 25, 50, 75, 90, 95, 99]:
        idx = int(len(amounts) * p / 100)
        percentiles[f"p{p}"] = amounts[min(idx, len(amounts)-1)]

    return jsonify(percentiles)

@app.route("/api/sync-status", methods=["GET"])
def get_sync_status():
    """Get synchronization status"""
    return jsonify({
        "last_synced_block": MIGRATIONS[-1]['block_number'] if MIGRATIONS else 0,
        "last_update": datetime.now().isoformat(),
        "status": "Demo mode - using generated data"
    })

@app.route("/api/trevee/metrics", methods=["GET"])
def get_trevee_metrics():
    """Get all Trevee multi-chain metrics"""
    metrics = calculate_metrics()

    return jsonify({
        "total_supply": 1000000000,
        "total_migrated": metrics['total_pal_migrated'],
        "chains": [
            {
                "name": "Sonic",
                "chain_id": 146,
                "balance": metrics['total_pal_migrated'] * 0.6
            },
            {
                "name": "Ethereum",
                "chain_id": 1,
                "balance": metrics['total_pal_migrated'] * 0.4
            }
        ]
    })

@app.route("/api/trevee/tvl", methods=["GET"])
def get_trevee_tvl():
    """Get TVL breakdown by chain"""
    metrics = calculate_metrics()

    return jsonify({
        "sonic": metrics['total_pal_migrated'] * 0.6,
        "ethereum": metrics['total_pal_migrated'] * 0.4
    })

@app.route("/api/trevee/staking", methods=["GET"])
def get_trevee_staking():
    """Get staking statistics"""
    metrics = calculate_metrics()

    return jsonify({
        "total_staked": metrics['total_pal_migrated'] * 0.3,
        "staking_percentage": 30.0
    })

@app.route("/api/export/json", methods=["GET"])
def export_json():
    """Export migrations as JSON"""
    return jsonify(MIGRATIONS)

@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    """Export migrations as CSV"""
    import io
    import csv

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['tx_hash', 'from_address', 'amount_pal', 'timestamp', 'block_number', 'source'])
    writer.writeheader()
    writer.writerows(MIGRATIONS)

    return output.getvalue(), 200, {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename=migrations.csv'}
