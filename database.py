"""
Database module for CMA Generator
Handles SQLite and PostgreSQL database operations for properties, rent history, and saved CMAs
"""

import sqlite3
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json

# Try to import PostgreSQL driver
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class Database:
    def __init__(self, db_path: str = "data/cma_generator.db"):
        """Initialize database - uses PostgreSQL if DATABASE_URL set, otherwise SQLite"""
        self.db_url = os.getenv('DATABASE_URL')
        
        if self.db_url and POSTGRES_AVAILABLE:
            self.engine = 'postgresql'
        else:
            self.engine = 'sqlite'
            self.db_path = db_path
        
        self.create_tables()

    def get_connection(self):
        """Create and return a database connection"""
        if self.engine == 'postgresql':
            conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
            return conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            return conn
    
    def _placeholder(self) -> str:
        """Return the correct parameter placeholder for the current engine"""
        return '%s' if self.engine == 'postgresql' else '?'

    def _sql(self, sql: str) -> str:
        """Convert SQL to engine-specific syntax"""
        if self.engine == 'postgresql':
            # Convert AUTOINCREMENT to SERIAL
            sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            # Convert julianday to PostgreSQL date arithmetic
            sql = re.sub(
                r"julianday\('now'\)\s*-\s*julianday\((\w+)\)",
                r"EXTRACT(EPOCH FROM (NOW() - \1))/86400",
                sql
            )
            sql = re.sub(
                r"\(julianday\('now'\)\s*-\s*julianday\((\w+)\)\)",
                r"EXTRACT(EPOCH FROM (NOW() - \1))/86400",
                sql
            )
            # Convert SQLite ? placeholders to PostgreSQL %s placeholders
            sql = sql.replace('?', '%s')
        return sql

    def create_tables(self):
        """Create all necessary database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Properties table - stores unique properties with geocoded data
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE NOT NULL,
                unit TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                latitude REAL,
                longitude REAL,
                bedrooms REAL,
                bathrooms REAL,
                sqft INTEGER,
                property_type TEXT,
                year_built INTEGER,
                tags TEXT,
                original_address TEXT,
                standardized_address TEXT,
                display_address TEXT,
                geocode_quality TEXT,
                geocode_variant TEXT,
                geocoding_status TEXT DEFAULT 'pending',
                geocoded_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Rent history table - tracks rent changes over time
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS rent_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id INTEGER NOT NULL,
                market_rent REAL,
                actual_rent REAL,
                status TEXT,
                occupancy_type TEXT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (property_id) REFERENCES properties(id)
            )
        """))

        # Create indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_properties_address
            ON properties(address)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_properties_geocoding_status
            ON properties(geocoding_status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_properties_location
            ON properties(city, state, zip_code)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_properties_specs
            ON properties(bedrooms, bathrooms)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rent_history_property
            ON rent_history(property_id, upload_date DESC)
        """)

        # External comparables table - stores RentCast and other external data
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS external_comps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                latitude REAL,
                longitude REAL,
                bedrooms REAL,
                bathrooms REAL,
                sqft INTEGER,
                rent_price REAL,
                property_type TEXT,
                year_built INTEGER,
                source TEXT NOT NULL,
                source_id TEXT,
                correlation_score REAL,
                retrieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                listing_status TEXT,
                days_on_market INTEGER,
                UNIQUE(source, source_id)
            )
        """))

        # Create indexes for external_comps
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_external_comps_location
            ON external_comps(latitude, longitude)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_external_comps_source
            ON external_comps(source, retrieved_date DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_external_comps_specs
            ON external_comps(bedrooms, bathrooms, sqft)
        """)

        # Saved CMAs table
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS saved_cmas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cma_name TEXT NOT NULL,
                subject_address TEXT NOT NULL,
                subject_beds REAL,
                subject_baths REAL,
                subject_sqft INTEGER,
                search_radius REAL,
                filters_json TEXT,
                selected_comps_json TEXT,
                avg_rent REAL,
                median_rent REAL,
                min_rent REAL,
                max_rent REAL,
                suggested_rent_low REAL,
                suggested_rent_high REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        """))

        # Comparables notes table - user notes on specific comparables
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS comp_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cma_id INTEGER NOT NULL,
                property_id INTEGER NOT NULL,
                notes TEXT,
                adjusted_rent REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cma_id) REFERENCES saved_cmas(id),
                FOREIGN KEY (property_id) REFERENCES properties(id)
            )
        """))

        # Zillow comparables cache (temporary storage for API results)
        cursor.execute(self._sql("""
            CREATE TABLE IF NOT EXISTS zillow_comps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zpid TEXT UNIQUE,
                address TEXT NOT NULL,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                latitude REAL,
                longitude REAL,
                bedrooms REAL,
                bathrooms REAL,
                sqft INTEGER,
                property_type TEXT,
                year_built INTEGER,
                rent_price REAL,
                date_closed DATE,
                days_on_market INTEGER,
                photo_url TEXT,
                listing_url TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.commit()
        conn.close()

    def insert_property(self, property_data: Dict) -> int:
        """Insert or update a property record"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO properties (
                address, unit, city, state, zip_code, latitude, longitude,
                bedrooms, bathrooms, sqft, property_type, year_built, tags,
                original_address, standardized_address, display_address,
                geocode_quality, geocode_variant, geocoding_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                unit = excluded.unit,
                city = excluded.city,
                state = excluded.state,
                zip_code = excluded.zip_code,
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                bedrooms = excluded.bedrooms,
                bathrooms = excluded.bathrooms,
                sqft = excluded.sqft,
                property_type = excluded.property_type,
                year_built = excluded.year_built,
                tags = excluded.tags,
                original_address = excluded.original_address,
                standardized_address = excluded.standardized_address,
                display_address = excluded.display_address,
                geocode_quality = excluded.geocode_quality,
                geocode_variant = excluded.geocode_variant,
                geocoding_status = excluded.geocoding_status,
                updated_at = CURRENT_TIMESTAMP
        """, (
            property_data.get('address'),
            property_data.get('unit'),
            property_data.get('city'),
            property_data.get('state'),
            property_data.get('zip_code'),
            property_data.get('latitude'),
            property_data.get('longitude'),
            property_data.get('bedrooms'),
            property_data.get('bathrooms'),
            property_data.get('sqft'),
            property_data.get('property_type'),
            property_data.get('year_built'),
            property_data.get('tags'),
            property_data.get('original_address'),
            property_data.get('standardized_address'),
            property_data.get('display_address'),
            property_data.get('geocode_quality'),
            property_data.get('geocode_variant'),
            property_data.get('geocoding_status', 'pending')
        ))

        property_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return property_id

    def insert_properties_batch(self, properties: List[Dict]) -> Dict:
        """
        Batch insert/update properties with single connection and commit

        Args:
            properties: List of property dictionaries

        Returns:
            Dictionary with 'inserted', 'updated', 'property_ids' counts
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        inserted = 0
        updated = 0
        property_ids = []

        try:
            for property_data in properties:
                # Check if property exists
                cursor.execute("SELECT id FROM properties WHERE address = ?",
                             (property_data.get('address'),))
                existing = cursor.fetchone()

                cursor.execute("""
                    INSERT INTO properties (
                        address, unit, city, state, zip_code, latitude, longitude,
                        bedrooms, bathrooms, sqft, property_type, year_built, tags,
                        original_address, standardized_address, display_address,
                        geocode_quality, geocode_variant, geocoding_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(address) DO UPDATE SET
                        unit = excluded.unit,
                        city = excluded.city,
                        state = excluded.state,
                        zip_code = excluded.zip_code,
                        latitude = excluded.latitude,
                        longitude = excluded.longitude,
                        bedrooms = excluded.bedrooms,
                        bathrooms = excluded.bathrooms,
                        sqft = excluded.sqft,
                        property_type = excluded.property_type,
                        year_built = excluded.year_built,
                        tags = excluded.tags,
                        original_address = excluded.original_address,
                        standardized_address = excluded.standardized_address,
                        display_address = excluded.display_address,
                        geocode_quality = excluded.geocode_quality,
                        geocode_variant = excluded.geocode_variant,
                        geocoding_status = excluded.geocoding_status,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    property_data.get('address'),
                    property_data.get('unit'),
                    property_data.get('city'),
                    property_data.get('state'),
                    property_data.get('zip_code'),
                    property_data.get('latitude'),
                    property_data.get('longitude'),
                    property_data.get('bedrooms'),
                    property_data.get('bathrooms'),
                    property_data.get('sqft'),
                    property_data.get('property_type'),
                    property_data.get('year_built'),
                    property_data.get('tags'),
                    property_data.get('original_address'),
                    property_data.get('standardized_address'),
                    property_data.get('display_address'),
                    property_data.get('geocode_quality'),
                    property_data.get('geocode_variant'),
                    property_data.get('geocoding_status', 'pending')
                ))

                # Get the actual property_id (works for both INSERT and UPDATE)
                if existing:
                    property_id = existing[0]  # Use existing property ID
                else:
                    property_id = cursor.lastrowid  # Use new insert ID
                property_ids.append(property_id)

                if existing:
                    updated += 1
                else:
                    inserted += 1

            # Single commit for all inserts
            conn.commit()

        finally:
            conn.close()

        return {
            'inserted': inserted,
            'updated': updated,
            'property_ids': property_ids,
            'total': len(properties)
        }

    def insert_rent_history(self, property_id: int, rent_data: Dict):
        """Insert rent history record"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO rent_history (
                property_id, market_rent, actual_rent, status, occupancy_type
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            property_id,
            rent_data.get('market_rent'),
            rent_data.get('actual_rent'),
            rent_data.get('status'),
            rent_data.get('occupancy_type')
        ))

        conn.commit()
        conn.close()

    def insert_rent_history_batch(self, rent_history_records: List[Dict]) -> int:
        """
        Batch insert rent history records with single connection and commit

        Args:
            rent_history_records: List of dicts with 'property_id' and rent data

        Returns:
            Number of records inserted
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Prepare all data as tuples for executemany (PII removed)
            values = [
                (
                    record.get('property_id'),
                    record.get('market_rent'),
                    record.get('actual_rent'),
                    record.get('status'),
                    record.get('occupancy_type')
                )
                for record in rent_history_records
            ]

            # Execute all inserts in one call
            cursor.executemany("""
                INSERT INTO rent_history (
                    property_id, market_rent, actual_rent, status, occupancy_type
                ) VALUES (?, ?, ?, ?, ?)
            """, values)

            # Single commit for all inserts
            conn.commit()

        finally:
            conn.close()

        return len(rent_history_records)

    def get_property_by_address(self, address: str) -> Optional[Dict]:
        """Retrieve property by address"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM properties WHERE address = ?", (address,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def find_comparables(self, center_lat: float, center_lon: float,
                        radius_miles: float, filters: Dict = None) -> List[Dict]:
        """
        Find comparable properties within radius using Haversine formula

        Args:
            center_lat: Latitude of subject property
            center_lon: Longitude of subject property
            radius_miles: Search radius in miles
            filters: Optional filters (beds, baths, sqft_min, sqft_max, etc.)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Haversine formula to calculate distance in miles
        # Use subquery to avoid HAVING clause on non-aggregate query
        query = self._sql("""
            SELECT * FROM (
                SELECT
                    p.*,
                    rh.market_rent,
                    rh.actual_rent,
                    rh.status,
                    rh.occupancy_type,
                    rh.upload_date,
                    (3959 * acos(
                        cos(radians(?)) * cos(radians(p.latitude)) *
                        cos(radians(p.longitude) - radians(?)) +
                        sin(radians(?)) * sin(radians(p.latitude))
                    )) AS distance_miles
                FROM properties p
                LEFT JOIN (
                    SELECT property_id, market_rent, actual_rent, status, occupancy_type,
                           upload_date,
                           ROW_NUMBER() OVER (PARTITION BY property_id ORDER BY upload_date DESC) as rn
                    FROM rent_history
                ) rh ON p.id = rh.property_id AND rh.rn = 1
                WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL
            ) AS subquery
            WHERE distance_miles <= ?
        """)

        params = [center_lat, center_lon, center_lat, radius_miles]

        # Add optional filters (must reference subquery columns)
        if filters:
            if filters.get('bedrooms'):
                query += f" AND bedrooms = {self._placeholder()}"
                params.append(filters['bedrooms'])

            if filters.get('bathrooms'):
                query += f" AND bathrooms = {self._placeholder()}"
                params.append(filters['bathrooms'])

            if filters.get('sqft_min'):
                query += f" AND sqft >= {self._placeholder()}"
                params.append(filters['sqft_min'])

            if filters.get('sqft_max'):
                query += f" AND sqft <= {self._placeholder()}"
                params.append(filters['sqft_max'])

            if filters.get('property_type'):
                query += f" AND property_type = {self._placeholder()}"
                params.append(filters['property_type'])

            if filters.get('year_built_min'):
                query += f" AND year_built >= {self._placeholder()}"
                params.append(filters['year_built_min'])

            if filters.get('year_built_max'):
                query += f" AND year_built <= {self._placeholder()}"
                params.append(filters['year_built_max'])

            if filters.get('status'):
                query += f" AND status = {self._placeholder()}"
                params.append(filters['status'])

        query += " ORDER BY distance_miles"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def save_cma(self, cma_data: Dict) -> int:
        """Save a CMA report"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO saved_cmas (
                cma_name, subject_address, subject_beds, subject_baths, subject_sqft,
                search_radius, filters_json, selected_comps_json,
                avg_rent, median_rent, min_rent, max_rent,
                suggested_rent_low, suggested_rent_high, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cma_data.get('cma_name'),
            cma_data.get('subject_address'),
            cma_data.get('subject_beds'),
            cma_data.get('subject_baths'),
            cma_data.get('subject_sqft'),
            cma_data.get('search_radius'),
            json.dumps(cma_data.get('filters', {})),
            json.dumps(cma_data.get('selected_comps', [])),
            cma_data.get('avg_rent'),
            cma_data.get('median_rent'),
            cma_data.get('min_rent'),
            cma_data.get('max_rent'),
            cma_data.get('suggested_rent_low'),
            cma_data.get('suggested_rent_high'),
            cma_data.get('notes')
        ))

        cma_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return cma_id

    def get_all_properties(self) -> List[Dict]:
        """Get all properties with latest rent data"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                p.*,
                rh.market_rent,
                rh.actual_rent,
                rh.status,
                rh.occupancy_type,
                rh.upload_date
            FROM properties p
            LEFT JOIN (
                SELECT property_id, market_rent, actual_rent, status, occupancy_type, upload_date,
                       ROW_NUMBER() OVER (PARTITION BY property_id ORDER BY upload_date DESC) as rn
                FROM rent_history
            ) rh ON p.id = rh.property_id AND rh.rn = 1
            ORDER BY p.address
        """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_geocoding(self, address: str, latitude: float, longitude: float,
                         geocode_quality: str = None, geocode_variant: str = None,
                         standardized_address: str = None):
        """Update geocoding data for a property"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Determine geocoding status based on results
        if latitude and longitude:
            geocoding_status = 'completed'
        else:
            geocoding_status = 'failed'

        cursor.execute("""
            UPDATE properties
            SET latitude = ?, longitude = ?,
                geocode_quality = ?,
                geocode_variant = ?,
                standardized_address = ?,
                geocoding_status = ?,
                geocoded_at = CURRENT_TIMESTAMP
            WHERE address = ?
        """, (latitude, longitude, geocode_quality, geocode_variant,
              standardized_address, geocoding_status, address))

        conn.commit()
        conn.close()

    def get_properties_by_geocoding_status(self, status: str = 'pending') -> List[Dict]:
        """Get properties filtered by geocoding status"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                p.*,
                rh.market_rent,
                rh.actual_rent,
                rh.status as property_status
            FROM properties p
            LEFT JOIN (
                SELECT property_id, market_rent, actual_rent, status,
                       ROW_NUMBER() OVER (PARTITION BY property_id ORDER BY upload_date DESC) as rn
                FROM rent_history
            ) rh ON p.id = rh.property_id AND rh.rn = 1
            WHERE p.geocoding_status = ?
            ORDER BY p.created_at DESC
        """, (status,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_geocoding_stats(self) -> Dict:
        """Get statistics about geocoding status"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                geocoding_status,
                COUNT(*) as count
            FROM properties
            GROUP BY geocoding_status
        """)

        rows = cursor.fetchall()
        conn.close()

        stats = {row['geocoding_status'] or 'unknown': row['count'] for row in rows}
        stats['total'] = sum(stats.values())

        return stats

    def insert_zillow_comp(self, comp_data: Dict):
        """Insert Zillow comparable data"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO zillow_comps (
                zpid, address, city, state, zip_code, latitude, longitude,
                bedrooms, bathrooms, sqft, property_type, year_built,
                rent_price, date_closed, days_on_market, photo_url, listing_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(zpid) DO UPDATE SET
                rent_price = excluded.rent_price,
                date_closed = excluded.date_closed,
                days_on_market = excluded.days_on_market,
                fetched_at = CURRENT_TIMESTAMP
        """, (
            comp_data.get('zpid'),
            comp_data.get('address'),
            comp_data.get('city'),
            comp_data.get('state'),
            comp_data.get('zip_code'),
            comp_data.get('latitude'),
            comp_data.get('longitude'),
            comp_data.get('bedrooms'),
            comp_data.get('bathrooms'),
            comp_data.get('sqft'),
            comp_data.get('property_type'),
            comp_data.get('year_built'),
            comp_data.get('rent_price'),
            comp_data.get('date_closed'),
            comp_data.get('days_on_market'),
            comp_data.get('photo_url'),
            comp_data.get('listing_url')
        ))

        conn.commit()
        conn.close()

    def get_zillow_comps_within_radius(self, center_lat: float, center_lon: float,
                                       radius_miles: float, filters: Dict = None) -> List[Dict]:
        """Get Zillow comparables within radius"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT *,
                (3959 * acos(
                    cos(radians(?)) * cos(radians(latitude)) *
                    cos(radians(longitude) - radians(?)) +
                    sin(radians(?)) * sin(radians(latitude))
                )) AS distance_miles
            FROM zillow_comps
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            HAVING distance_miles <= ?
        """

        params = [center_lat, center_lon, center_lat, radius_miles]

        if filters:
            if filters.get('bedrooms'):
                query += f" AND bedrooms = {self._placeholder()}"
                params.append(filters['bedrooms'])

            if filters.get('bathrooms'):
                query += f" AND bathrooms = {self._placeholder()}"
                params.append(filters['bathrooms'])

            if filters.get('sqft_min'):
                query += f" AND sqft >= {self._placeholder()}"
                params.append(filters['sqft_min'])

            if filters.get('sqft_max'):
                query += f" AND sqft <= {self._placeholder()}"
                params.append(filters['sqft_max'])

        query += " ORDER BY distance_miles"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def save_external_comps(self, comps: List[Dict], source: str = 'RentCast') -> int:
        """
        Save external comparable properties to database

        Args:
            comps: List of comparable property dictionaries
            source: Data source name (e.g., 'RentCast', 'Zillow')

        Returns:
            Number of comps saved (excluding duplicates)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        saved_count = 0
        for comp in comps:
            try:
                values = (
                    comp.get('address'),
                    comp.get('city'),
                    comp.get('state'),
                    comp.get('zip_code'),
                    comp.get('latitude'),
                    comp.get('longitude'),
                    comp.get('bedrooms'),
                    comp.get('bathrooms'),
                    comp.get('sqft'),
                    comp.get('rent_price') or comp.get('price'),
                    comp.get('property_type') or comp.get('propertyType'),
                    comp.get('year_built') or comp.get('yearBuilt'),
                    source,
                    comp.get('source_id') or comp.get('id') or comp.get('address'),
                    comp.get('correlation_score') or comp.get('correlation'),
                    comp.get('listing_status') or comp.get('listingStatus'),
                    comp.get('days_on_market') or comp.get('daysOnMarket')
                )

                if self.engine == 'postgresql':
                    # PostgreSQL: Use ON CONFLICT with RETURNING to detect actual inserts
                    cursor.execute("""
                        INSERT INTO external_comps (
                            address, city, state, zip_code,
                            latitude, longitude,
                            bedrooms, bathrooms, sqft,
                            rent_price, property_type, year_built,
                            source, source_id, correlation_score,
                            listing_status, days_on_market
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (source, source_id)
                        DO UPDATE SET retrieved_date = CURRENT_TIMESTAMP
                        RETURNING (xmax = 0) AS inserted
                    """, values)
                    # xmax = 0 means INSERT happened, xmax > 0 means UPDATE happened
                    result = cursor.fetchone()
                    if result and result[0]:
                        saved_count += 1
                else:
                    # SQLite: INSERT OR REPLACE always counts as new
                    cursor.execute("""
                        INSERT OR REPLACE INTO external_comps (
                            address, city, state, zip_code,
                            latitude, longitude,
                            bedrooms, bathrooms, sqft,
                            rent_price, property_type, year_built,
                            source, source_id, correlation_score,
                            listing_status, days_on_market
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, values)
                    saved_count += 1
            except Exception as e:
                # Make errors visible in Streamlit UI
                import streamlit as st
                st.warning(f"⚠️ Failed to save comp {comp.get('address')}: {str(e)}")
                continue

        conn.commit()
        conn.close()

        return saved_count

    def find_external_comps(self,
                           center_lat: float,
                           center_lon: float,
                           radius_miles: float,
                           filters: Dict = None,
                           max_age_days: int = 30,
                           source: str = None) -> List[Dict]:
        """
        Find cached external comparable properties within radius

        Args:
            center_lat: Center point latitude
            center_lon: Center point longitude
            radius_miles: Search radius in miles
            filters: Optional filters (bedrooms, bathrooms, sqft_min, sqft_max)
            max_age_days: Maximum age of cached data in days
            source: Filter by specific source (e.g., 'RentCast')

        Returns:
            List of comparable properties with distance_miles
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        query = self._sql("""
            SELECT * FROM (
                SELECT
                    *,
                    (3959 * acos(
                        cos(radians(?)) * cos(radians(latitude)) *
                        cos(radians(longitude) - radians(?)) +
                        sin(radians(?)) * sin(radians(latitude))
                    )) AS distance_miles,
                    (julianday('now') - julianday(retrieved_date)) AS age_days
                FROM external_comps
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ) AS subquery
            WHERE distance_miles <= ?
            AND age_days <= ?
        """)

        params = [center_lat, center_lon, center_lat, radius_miles, max_age_days]

        if source:
            query += f" AND source = {self._placeholder()}"
            params.append(source)

        if filters:
            if filters.get('bedrooms'):
                query += f" AND bedrooms = {self._placeholder()}"
                params.append(filters['bedrooms'])
            if filters.get('bathrooms'):
                query += f" AND bathrooms = {self._placeholder()}"
                params.append(filters['bathrooms'])
            if filters.get('sqft_min'):
                query += f" AND sqft >= {self._placeholder()}"
                params.append(filters['sqft_min'])
            if filters.get('sqft_max'):
                query += f" AND sqft <= {self._placeholder()}"
                params.append(filters['sqft_max'])

        query += " ORDER BY distance_miles, correlation_score DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_external_comps_stats(self, source: str = None) -> Dict:
        """
        Get statistics about cached external comparables

        Args:
            source: Optional filter by source

        Returns:
            Dictionary with count, oldest_date, newest_date, avg_age_days
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        if source:
            # When filtering by specific source, don't need source in SELECT or GROUP BY
            query = self._sql("""
                SELECT
                    COUNT(*) as total_count,
                    MIN(retrieved_date) as oldest_date,
                    MAX(retrieved_date) as newest_date,
                    AVG(julianday('now') - julianday(retrieved_date)) as avg_age_days
                FROM external_comps
                WHERE source = """ + self._placeholder() + """
            """)
            cursor.execute(query, (source,))
        else:
            # When not filtering, group by source and include it in SELECT
            query = self._sql("""
                SELECT
                    COUNT(*) as total_count,
                    MIN(retrieved_date) as oldest_date,
                    MAX(retrieved_date) as newest_date,
                    AVG(julianday('now') - julianday(retrieved_date)) as avg_age_days,
                    source
                FROM external_comps
                GROUP BY source
            """)
            cursor.execute(query)

        rows = cursor.fetchall()
        conn.close()

        if source:
            row = rows[0] if rows else None
            return dict(row) if row else {}
        else:
            return [dict(row) for row in rows]
