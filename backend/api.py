#!/usr/bin/env python3
"""
Flask API server for the migration dashboard
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime
import os

from database import MigrationDatabase
from data_processor import MigrationDataProcessor
from config import LARGE_MIGRATION_THRESHOLD

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Initialize database and processor
db = MigrationDatabase()
processor = MigrationDataProcessor(db)


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    """Get all migration metrics"""
    try:
        metrics = processor.get_all_metrics()
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/statistics", methods=["GET"])
def get_statistics():
    """Get summary statistics"""
    try:
        stats = db.get_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/daily-stats", methods=["GET"])
def get_daily_stats():
    """Get daily migration statistics"""
    try:
        stats = db.get_daily_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/migration-rate", methods=["GET"])
def get_migration_rate():
    """Get migration rate for specified period"""
    try:
        days = request.args.get("days", 7, type=int)
        rate = processor.calculate_migration_rate(days)
        return jsonify(rate)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/timeline", methods=["GET"])
def get_timeline():
    """Get complete migration timeline"""
    try:
        timeline = processor.get_migration_timeline()
        return jsonify(timeline)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/address/<address>", methods=["GET"])
def lookup_address(address):
    """Look up migrations for a specific address"""
    try:
        result = processor.get_address_lookup(address)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/large-migrations", methods=["GET"])
def get_large_migrations():
    """Get migrations above threshold"""
    try:
        threshold = request.args.get("threshold", LARGE_MIGRATION_THRESHOLD, type=float)
        migrations = processor.detect_large_migrations(threshold)
        return jsonify(migrations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/percentiles", methods=["GET"])
def get_percentiles():
    """Get percentile distribution"""
    try:
        percentiles = processor.calculate_percentiles()
        return jsonify(percentiles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/json", methods=["GET"])
def export_json():
    """Export all migrations as JSON"""
    try:
        filepath = "../data/export.json"
        db.export_to_json(filepath)

        return send_file(
            filepath,
            mimetype="application/json",
            as_attachment=True,
            download_name=f"migrations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    """Export all migrations as CSV"""
    try:
        filepath = "../data/export.csv"
        db.export_to_csv(filepath)

        return send_file(
            filepath,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"migrations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sync-status", methods=["GET"])
def get_sync_status():
    """Get synchronization status"""
    try:
        last_block = db.get_last_synced_block()

        return jsonify({
            "last_synced_block": last_block,
            "last_update": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Create data directory if it doesn't exist
    os.makedirs("../data", exist_ok=True)

    print("Starting PAL to TREVEE Migration API Server...")
    print("API available at http://localhost:5000")
    print("\nAvailable endpoints:")
    print("  GET /api/health - Health check")
    print("  GET /api/metrics - All metrics")
    print("  GET /api/statistics - Summary statistics")
    print("  GET /api/daily-stats - Daily statistics")
    print("  GET /api/migration-rate?days=7 - Migration rate")
    print("  GET /api/timeline - Complete timeline")
    print("  GET /api/address/<address> - Address lookup")
    print("  GET /api/large-migrations?threshold=100000 - Large migrations")
    print("  GET /api/percentiles - Percentile distribution")
    print("  GET /api/export/json - Export as JSON")
    print("  GET /api/export/csv - Export as CSV")
    print("  GET /api/sync-status - Sync status")

    app.run(host="0.0.0.0", port=5000, debug=True)
