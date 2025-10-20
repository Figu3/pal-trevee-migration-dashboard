"""
Data processor for calculating migration metrics and analytics
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import statistics
from database import MigrationDatabase


class MigrationDataProcessor:
    """Process and analyze migration data"""

    def __init__(self, db: MigrationDatabase):
        self.db = db

    def get_all_metrics(self) -> Dict:
        """Calculate all metrics for the dashboard"""
        stats = self.db.get_statistics()
        daily_stats = self.db.get_daily_stats()
        cumulative_data = self._calculate_cumulative_data(daily_stats)
        distribution = self._calculate_distribution()
        source_breakdown = self._calculate_source_breakdown(stats)

        return {
            "summary": {
                "total_unique_addresses": stats["unique_addresses"],
                "total_pal_migrated": stats["total_pal_migrated"],
                "total_migrations": stats["total_migrations"],
                "average_migration_size": stats["average_migration_size"],
                "median_migration_size": stats["median_migration_size"],
            },
            "daily_stats": daily_stats,
            "cumulative_data": cumulative_data,
            "distribution": distribution,
            "source_breakdown": source_breakdown,
            "top_migrations": stats["top_migrations"],
            "last_updated": datetime.now().isoformat()
        }

    def _calculate_cumulative_data(self, daily_stats: List[Dict]) -> List[Dict]:
        """Calculate cumulative migrations over time"""
        cumulative = []
        total_migrations = 0
        total_pal = 0

        for day in daily_stats:
            total_migrations += day["migrations"]
            total_pal += day["total_pal"]

            cumulative.append({
                "date": day["date"],
                "cumulative_migrations": total_migrations,
                "cumulative_pal": total_pal,
                "daily_migrations": day["migrations"],
                "daily_pal": day["total_pal"]
            })

        return cumulative

    def _calculate_distribution(self) -> Dict:
        """Calculate distribution of migration sizes"""
        migrations = self.db.get_all_migrations()

        if not migrations:
            return {"bins": [], "counts": []}

        amounts = [m["amount_pal"] for m in migrations]

        # Define bins for histogram
        bins = [0, 100, 500, 1000, 5000, 10000, 50000, 100000, 500000, float('inf')]
        bin_labels = [
            "0-100",
            "100-500",
            "500-1K",
            "1K-5K",
            "5K-10K",
            "10K-50K",
            "50K-100K",
            "100K-500K",
            "500K+"
        ]

        counts = [0] * len(bin_labels)

        for amount in amounts:
            for i in range(len(bins) - 1):
                if bins[i] <= amount < bins[i + 1]:
                    counts[i] += 1
                    break

        return {
            "labels": bin_labels,
            "counts": counts,
            "bins": bins[:-1]  # Exclude infinity
        }

    def _calculate_source_breakdown(self, stats: Dict) -> Dict:
        """Calculate percentage breakdown by source"""
        source_dist = stats["source_distribution"]

        total_migrations = sum(s["count"] for s in source_dist)
        total_pal = sum(s["total_pal"] for s in source_dist)

        breakdown = {
            "sonic": {"count": 0, "pal": 0, "percentage": 0, "pal_percentage": 0},
            "ethereum": {"count": 0, "pal": 0, "percentage": 0, "pal_percentage": 0},
            "unknown": {"count": 0, "pal": 0, "percentage": 0, "pal_percentage": 0}
        }

        for source in source_dist:
            source_name = source["source"]
            if source_name in breakdown:
                breakdown[source_name]["count"] = source["count"]
                breakdown[source_name]["pal"] = source["total_pal"]

                if total_migrations > 0:
                    breakdown[source_name]["percentage"] = (source["count"] / total_migrations) * 100

                if total_pal > 0:
                    breakdown[source_name]["pal_percentage"] = (source["total_pal"] / total_pal) * 100

        return breakdown

    def calculate_migration_rate(self, days: int = 7) -> Dict:
        """Calculate migration rate over the last N days"""
        daily_stats = self.db.get_daily_stats()

        if not daily_stats or len(daily_stats) < days:
            return {
                "daily_average_migrations": 0,
                "daily_average_pal": 0,
                "period_days": 0
            }

        # Get last N days
        recent_stats = daily_stats[-days:]

        total_migrations = sum(s["migrations"] for s in recent_stats)
        total_pal = sum(s["total_pal"] for s in recent_stats)

        return {
            "daily_average_migrations": total_migrations / days,
            "daily_average_pal": total_pal / days,
            "period_days": days,
            "total_migrations_in_period": total_migrations,
            "total_pal_in_period": total_pal
        }

    def get_address_lookup(self, address: str) -> Dict:
        """Get all migrations for a specific address"""
        migrations = self.db.get_migrations_by_address(address)

        if not migrations:
            return {
                "address": address,
                "found": False,
                "migrations": []
            }

        total_pal = sum(m["amount_pal"] for m in migrations)

        return {
            "address": address,
            "found": True,
            "migration_count": len(migrations),
            "total_pal_migrated": total_pal,
            "migrations": migrations
        }

    def detect_large_migrations(self, threshold: float) -> List[Dict]:
        """Detect migrations above a certain threshold"""
        migrations = self.db.get_all_migrations()

        large_migrations = [
            m for m in migrations
            if m["amount_pal"] >= threshold
        ]

        return sorted(large_migrations, key=lambda x: x["amount_pal"], reverse=True)

    def get_migration_timeline(self) -> List[Dict]:
        """Get complete migration timeline"""
        migrations = self.db.get_all_migrations()

        timeline = []
        cumulative_pal = 0

        for migration in migrations:
            cumulative_pal += migration["amount_pal"]

            timeline.append({
                "timestamp": migration["timestamp"],
                "block_number": migration["block_number"],
                "from_address": migration["from_address"],
                "amount_pal": migration["amount_pal"],
                "cumulative_pal": cumulative_pal,
                "tx_hash": migration["tx_hash"]
            })

        return timeline

    def calculate_percentiles(self) -> Dict:
        """Calculate percentile distribution of migration sizes"""
        migrations = self.db.get_all_migrations()

        if not migrations:
            return {}

        amounts = sorted([m["amount_pal"] for m in migrations])

        percentiles = [10, 25, 50, 75, 90, 95, 99]
        result = {}

        for p in percentiles:
            index = int(len(amounts) * p / 100)
            result[f"p{p}"] = amounts[index] if index < len(amounts) else 0

        return result
