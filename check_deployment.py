"""
Deployment Verification Script
Run this to check if lease dates are properly deployed in production
"""
import sqlite3
from pathlib import Path

def check_database():
    db_path = Path("data/cma_generator.db")

    if not db_path.exists():
        print("❌ Database file not found!")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("=" * 80)
    print("DATABASE DEPLOYMENT STATUS CHECK")
    print("=" * 80)

    # Check properties
    cursor.execute("SELECT COUNT(*) FROM properties")
    total_props = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM properties WHERE latitude IS NOT NULL")
    geocoded = cursor.fetchone()[0]

    # Check rent_history
    cursor.execute("SELECT COUNT(*) FROM rent_history")
    total_rent = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM rent_history WHERE lease_start_date IS NOT NULL")
    with_dates = cursor.fetchone()[0]

    # Check schema
    cursor.execute("PRAGMA table_info(rent_history)")
    columns = [row[1] for row in cursor.fetchall()]
    has_lease_cols = 'lease_start_date' in columns and 'lease_end_date' in columns

    print(f"\n✓ Total Properties: {total_props}")
    print(f"✓ Geocoded Properties: {geocoded} ({geocoded/total_props*100:.1f}%)")
    print(f"✓ Total Rent History Records: {total_rent}")
    print(f"✓ Records with Lease Dates: {with_dates} ({with_dates/total_rent*100:.1f}%)")
    print(f"✓ Lease Date Columns Present: {has_lease_cols}")

    print("\n" + "=" * 80)

    if geocoded > 4000 and with_dates > 1900 and has_lease_cols:
        print("✅ DEPLOYMENT SUCCESSFUL - Database has lease dates and coordinates")
    elif geocoded < 100:
        print("⚠️  WARNING - Properties not geocoded (comparables will be empty)")
    elif with_dates < 100:
        print("⚠️  WARNING - Lease dates missing from database")
    else:
        print("⚠️  PARTIAL DEPLOYMENT - Some issues detected")

    print("=" * 80)

    conn.close()

if __name__ == "__main__":
    check_database()
