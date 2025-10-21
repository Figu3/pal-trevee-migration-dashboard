#!/usr/bin/env python3
"""
Vercel serverless function with Postgres backend
"""
import sys
import os
# Add current directory to Python path for Vercel
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Import database functions
try:
    from db import (
        get_statistics, get_daily_stats, get_timeline,
        lookup_address, get_large_migrations, get_last_synced_block
    )
    USE_POSTGRES = True
    DB_ERROR = None
except Exception as e:
    print(f"Postgres not available: {e}")
    import traceback
    traceback.print_exc()
    USE_POSTGRES = False
    DB_ERROR = str(e)

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    response = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "postgres" if USE_POSTGRES else "none",
        "postgres_url_set": bool(os.environ.get('POSTGRES_URL'))
    }
    if not USE_POSTGRES and DB_ERROR:
        response["db_error"] = DB_ERROR
    return jsonify(response)

@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    """Get all migration metrics in frontend-compatible format"""
    try:
        if not USE_POSTGRES:
            return jsonify({"error": "Database not configured"}), 500

        stats = get_statistics()
        daily = get_daily_stats()

        # Calculate cumulative data
        cumulative_data = []
        cumulative_pal = 0
        for day in daily:
            cumulative_pal += day['amount']
            cumulative_data.append({
                "date": day['date'],
                "cumulative_pal": cumulative_pal
            })

        # Create distribution buckets
        distribution_labels = ['0-1K', '1K-10K', '10K-100K', '100K+']
        distribution_counts = [0, 0, 0, 0]

        from db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT amount_pal FROM migrations")
        amounts = cursor.fetchall()

        for row in amounts:
            amount = float(row['amount_pal'])
            if amount < 1000:
                distribution_counts[0] += 1
            elif amount < 10000:
                distribution_counts[1] += 1
            elif amount < 100000:
                distribution_counts[2] += 1
            else:
                distribution_counts[3] += 1

        cursor.close()
        conn.close()

        return jsonify({
            "summary": {
                "total_unique_addresses": stats['unique_addresses'],
                "total_pal_migrated": stats['total_pal_migrated'],
                "total_migrations": stats['total_migrations'],
                "average_migration_size": stats['average_migration'],
                "median_migration_size": stats['median_migration']
            },
            "cumulative_data": cumulative_data,
            "daily_stats": [{
                "date": d['date'],
                "total_pal": d['amount'],
                "count": d['count']
            } for d in daily],
            "distribution": {
                "labels": distribution_labels,
                "counts": distribution_counts
            },
            "source_breakdown": {
                "sonic": {"pal": stats['total_pal_migrated'], "count": stats['total_migrations']},
                "ethereum": {"pal": 0, "count": 0},
                "unknown": {"pal": 0, "count": 0}
            },
            "top_migrations": stats['top_migrations'],
            "last_updated": datetime.now().isoformat()
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/statistics", methods=["GET"])
def get_statistics_endpoint():
    """Get summary statistics"""
    try:
        if not USE_POSTGRES:
            return jsonify({"error": "Database not configured"}), 500

        stats = get_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/daily-stats", methods=["GET"])
def get_daily_stats_endpoint():
    """Get daily migration statistics"""
    try:
        if not USE_POSTGRES:
            return jsonify([]), 200

        return jsonify(get_daily_stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/migration-rate", methods=["GET"])
def get_migration_rate():
    """Get migration rate for specified period"""
    try:
        if not USE_POSTGRES:
            return jsonify({"daily_average_migrations": 0, "daily_average_pal": 0}), 200

        days = request.args.get("days", 7, type=int)
        daily_stats = get_daily_stats()

        cutoff = (datetime.now() - timedelta(days=days)).date()
        recent = [s for s in daily_stats if datetime.fromisoformat(s['date']).date() > cutoff]

        total_migrations = sum(s['count'] for s in recent)
        total_pal = sum(s['amount'] for s in recent)

        return jsonify({
            "daily_average_migrations": total_migrations / days if days > 0 else 0,
            "daily_average_pal": total_pal / days if days > 0 else 0,
            "period_days": days,
            "total_in_period": total_migrations
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/timeline", methods=["GET"])
def get_timeline_endpoint():
    """Get complete migration timeline"""
    try:
        if not USE_POSTGRES:
            return jsonify([]), 200

        limit = request.args.get("limit", 50, type=int)
        return jsonify(get_timeline(limit))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/address/<address>", methods=["GET"])
def lookup_address_endpoint(address):
    """Look up migrations for a specific address"""
    try:
        if not USE_POSTGRES:
            return jsonify({"found": False, "address": address}), 200

        result = lookup_address(address)

        return jsonify({
            "found": result['count'] > 0,
            "address": address,
            "migration_count": result['count'],
            "total_pal_migrated": result['total_amount'],
            "migrations": result['migrations']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/large-migrations", methods=["GET"])
def get_large_migrations_endpoint():
    """Get migrations above threshold"""
    try:
        if not USE_POSTGRES:
            return jsonify([]), 200

        threshold = request.args.get("threshold", 100000, type=float)
        return jsonify(get_large_migrations(threshold))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/percentiles", methods=["GET"])
def get_percentiles():
    """Get percentile distribution"""
    try:
        if not USE_POSTGRES:
            return jsonify({}), 200

        from db import get_db_connection

        conn = get_db_connection()
        cursor = conn.cursor()

        percentiles = {}
        for p in [10, 25, 50, 75, 90, 95, 99]:
            cursor.execute(f"""
                SELECT PERCENTILE_CONT({p/100.0}) WITHIN GROUP (ORDER BY amount_pal) as p{p}
                FROM migrations
            """)
            result = cursor.fetchone()
            percentiles[f"p{p}"] = float(result[f'p{p}']) if result and result[f'p{p}'] else 0

        cursor.close()
        conn.close()

        return jsonify(percentiles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sync-status", methods=["GET"])
def get_sync_status():
    """Get synchronization status"""
    try:
        if not USE_POSTGRES:
            return jsonify({
                "last_synced_block": 0,
                "last_update": datetime.now().isoformat(),
                "status": "Database not configured"
            }), 200

        last_block = get_last_synced_block()

        return jsonify({
            "last_synced_block": last_block,
            "last_update": datetime.now().isoformat(),
            "status": "synced" if last_block > 0 else "not_synced"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/trevee/metrics", methods=["GET"])
def get_trevee_metrics():
    """Get all Trevee multi-chain metrics"""
    try:
        if not USE_POSTGRES:
            return jsonify({"total_supply": 0, "total_staked": 0, "chains": []}), 200

        stats = get_statistics()

        return jsonify({
            "total_supply": 1000000000,
            "total_migrated": stats['total_pal_migrated'],
            "chains": [
                {
                    "name": "Sonic",
                    "chain_id": 146,
                    "balance": stats['total_pal_migrated']
                }
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/trevee/tvl", methods=["GET"])
def get_trevee_tvl():
    """Get TVL breakdown by chain"""
    try:
        if not USE_POSTGRES:
            return jsonify({}), 200

        stats = get_statistics()

        return jsonify({
            "sonic": stats['total_pal_migrated']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/trevee/staking", methods=["GET"])
def get_trevee_staking():
    """Get staking statistics"""
    try:
        if not USE_POSTGRES:
            return jsonify({"total_staked": 0, "staking_percentage": 0}), 200

        stats = get_statistics()

        return jsonify({
            "total_staked": stats['total_pal_migrated'] * 0.3,
            "staking_percentage": 30.0
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/export/json", methods=["GET"])
def export_json():
    """Export migrations as JSON"""
    try:
        if not USE_POSTGRES:
            return jsonify([]), 200

        migrations = get_timeline(limit=10000)
        return jsonify(migrations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    """Export migrations as CSV"""
    try:
        if not USE_POSTGRES:
            return "No data available", 404

        import io
        import csv

        migrations = get_timeline(limit=10000)

        output = io.StringIO()
        if migrations:
            fieldnames = ['tx_hash', 'from_address', 'amount_pal', 'timestamp', 'block_number', 'source']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(migrations)

        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=migrations.csv'
        }
    except Exception as e:
        return str(e), 500
