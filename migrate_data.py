#!/usr/bin/env python3
"""
Migrate data from SQLite to Neon PostgreSQL

This script transfers all data from the local SQLite database to the
production Neon PostgreSQL database. It handles:
- Properties (with all geocoding metadata)
- Rent history (linked to properties)
- Proper type conversions and NULL handling
- Batch processing for efficiency

Usage:
    export DATABASE_URL="postgresql://..."
    python3 migrate_data.py
"""

import sqlite3
import os
import sys
from typing import List, Tuple
import psycopg2
from psycopg2.extras import execute_values

# Configuration
SQLITE_DB = "data/cma_generator.db"
BATCH_SIZE = 500

def connect_sqlite() -> sqlite3.Connection:
    """Connect to SQLite database"""
    if not os.path.exists(SQLITE_DB):
        print(f"❌ Error: SQLite database not found at {SQLITE_DB}")
        sys.exit(1)

    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def connect_postgresql() -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database"""
    db_url = os.getenv('DATABASE_URL')

    if not db_url:
        print("❌ Error: DATABASE_URL environment variable not set")
        print("   Set it with: export DATABASE_URL='postgresql://...'")
        sys.exit(1)

    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"❌ Error connecting to PostgreSQL: {e}")
        sys.exit(1)

def get_row_count(conn, table: str, engine: str = 'sqlite') -> int:
    """Get row count for a table"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")

    if engine == 'sqlite':
        return cursor.fetchone()[0]
    else:  # postgresql
        return cursor.fetchone()[0]

def migrate_properties(sqlite_conn, pg_conn) -> int:
    """
    Migrate properties table from SQLite to PostgreSQL

    Returns:
        Number of rows migrated
    """
    print("\n📦 Migrating properties table...")

    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()

    # Check if data already exists
    existing_count = get_row_count(pg_conn, 'properties', 'postgresql')
    if existing_count > 0:
        print(f"⚠️  PostgreSQL properties table already has {existing_count:,} rows")
        response = input("   Continue and add more data? (y/N): ")
        if response.lower() != 'y':
            print("   Skipped properties migration")
            return 0

    # Get all properties from SQLite
    sqlite_cursor.execute("""
        SELECT
            address, unit, city, state, zip_code,
            latitude, longitude, bedrooms, bathrooms, sqft,
            property_type, year_built, tags,
            original_address, standardized_address, display_address,
            geocode_quality, geocode_variant, geocoding_status,
            geocoded_at, created_at, updated_at
        FROM properties
        ORDER BY id
    """)

    rows = sqlite_cursor.fetchall()
    total = len(rows)

    if total == 0:
        print("   No properties to migrate")
        return 0

    print(f"   Found {total:,} properties in SQLite")

    # Prepare INSERT query (excluding id, let PostgreSQL auto-generate with SERIAL)
    insert_query = """
        INSERT INTO properties (
            address, unit, city, state, zip_code,
            latitude, longitude, bedrooms, bathrooms, sqft,
            property_type, year_built, tags,
            original_address, standardized_address, display_address,
            geocode_quality, geocode_variant, geocoding_status,
            geocoded_at, created_at, updated_at
        ) VALUES %s
        RETURNING id
    """

    # Convert rows to tuples
    data = [tuple(row) for row in rows]

    # Insert in batches
    migrated = 0
    for i in range(0, len(data), BATCH_SIZE):
        batch = data[i:i+BATCH_SIZE]
        execute_values(pg_cursor, insert_query, batch)
        migrated += len(batch)
        print(f"   Progress: {migrated:,}/{total:,} ({100*migrated//total}%)", end='\r')

    pg_conn.commit()
    print(f"\n✅ Migrated {migrated:,} properties")

    return migrated

def migrate_rent_history(sqlite_conn, pg_conn) -> int:
    """
    Migrate rent_history table from SQLite to PostgreSQL

    Note: This requires properties to be migrated first since rent_history
    references property IDs. We'll match properties by address to find new IDs.

    Returns:
        Number of rows migrated
    """
    print("\n📦 Migrating rent_history table...")

    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()

    # Check if data already exists
    existing_count = get_row_count(pg_conn, 'rent_history', 'postgresql')
    if existing_count > 0:
        print(f"⚠️  PostgreSQL rent_history table already has {existing_count:,} rows")
        response = input("   Continue and add more data? (y/N): ")
        if response.lower() != 'y':
            print("   Skipped rent_history migration")
            return 0

    # Build mapping of old property IDs to new ones
    # We'll match by address since that's the most reliable identifier
    print("   Building property ID mapping...")

    # Get SQLite property mappings
    sqlite_cursor.execute("SELECT id, address, unit FROM properties ORDER BY id")
    sqlite_properties = {row['id']: (row['address'], row['unit']) for row in sqlite_cursor.fetchall()}

    # Get PostgreSQL property mappings
    pg_cursor.execute("SELECT id, address, unit FROM properties ORDER BY id")
    pg_properties = {(row[1], row[2]): row[0] for row in pg_cursor.fetchall()}

    # Create old_id -> new_id mapping
    id_mapping = {}
    for old_id, (address, unit) in sqlite_properties.items():
        if (address, unit) in pg_properties:
            id_mapping[old_id] = pg_properties[(address, unit)]

    print(f"   Mapped {len(id_mapping):,} properties")

    # Get all rent_history from SQLite
    sqlite_cursor.execute("""
        SELECT
            property_id, market_rent, actual_rent,
            status, occupancy_type,
            lease_start_date, lease_end_date, move_in_date, move_out_date,
            upload_date
        FROM rent_history
        ORDER BY id
    """)

    rows = sqlite_cursor.fetchall()
    total = len(rows)

    if total == 0:
        print("   No rent history to migrate")
        return 0

    print(f"   Found {total:,} rent records in SQLite")

    # Prepare INSERT query
    insert_query = """
        INSERT INTO rent_history (
            property_id, market_rent, actual_rent,
            status, occupancy_type,
            lease_start_date, lease_end_date, move_in_date, move_out_date,
            upload_date
        ) VALUES %s
    """

    # Convert rows to tuples with mapped property IDs
    data = []
    skipped = 0
    for row in rows:
        old_property_id = row['property_id']
        if old_property_id in id_mapping:
            new_property_id = id_mapping[old_property_id]
            data.append((
                new_property_id,
                row['market_rent'],
                row['actual_rent'],
                row['status'],
                row['occupancy_type'],
                row['lease_start_date'],
                row['lease_end_date'],
                row['move_in_date'],
                row['move_out_date'],
                row['upload_date']
            ))
        else:
            skipped += 1

    if skipped > 0:
        print(f"   ⚠️  Skipped {skipped} records (property not found)")

    if not data:
        print("   No rent history to migrate")
        return 0

    # Insert in batches
    migrated = 0
    for i in range(0, len(data), BATCH_SIZE):
        batch = data[i:i+BATCH_SIZE]
        execute_values(pg_cursor, insert_query, batch)
        migrated += len(batch)
        print(f"   Progress: {migrated:,}/{len(data):,} ({100*migrated//len(data)}%)", end='\r')

    pg_conn.commit()
    print(f"\n✅ Migrated {migrated:,} rent records")

    return migrated

def verify_migration(sqlite_conn, pg_conn):
    """Verify that data was migrated correctly"""
    print("\n🔍 Verifying migration...")

    tables = ['properties', 'rent_history']
    all_match = True

    for table in tables:
        sqlite_count = get_row_count(sqlite_conn, table, 'sqlite')
        pg_count = get_row_count(pg_conn, table, 'postgresql')

        match = "✅" if sqlite_count == pg_count else "❌"
        print(f"   {table}: SQLite={sqlite_count:,} | PostgreSQL={pg_count:,} {match}")

        if sqlite_count != pg_count:
            all_match = False

    if all_match:
        print("\n✅ Migration verified - all row counts match!")
    else:
        print("\n⚠️  Warning: Row counts don't match. Review migration logs.")

def main():
    """Main migration flow"""
    print("="*60)
    print("SQLite → Neon PostgreSQL Data Migration")
    print("="*60)

    # Connect to databases
    print("\n🔌 Connecting to databases...")
    sqlite_conn = connect_sqlite()
    print(f"   ✅ Connected to SQLite: {SQLITE_DB}")

    pg_conn = connect_postgresql()
    print("   ✅ Connected to PostgreSQL (Neon)")

    try:
        # Migrate data
        properties_migrated = migrate_properties(sqlite_conn, pg_conn)
        rent_migrated = migrate_rent_history(sqlite_conn, pg_conn)

        # Verify
        verify_migration(sqlite_conn, pg_conn)

        # Summary
        print("\n" + "="*60)
        print("Migration Summary")
        print("="*60)
        print(f"Properties migrated:    {properties_migrated:,}")
        print(f"Rent records migrated:  {rent_migrated:,}")
        print(f"Total rows migrated:    {properties_migrated + rent_migrated:,}")
        print("\n✅ Migration complete!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    main()
