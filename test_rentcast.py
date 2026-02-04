#!/usr/bin/env python3
"""
Test RentCast API Integration End-to-End

Tests:
1. API connection with real credentials
2. API response for Chapel Hill, NC address
3. Response normalization
4. Database save (PostgreSQL)
5. Data retrieval from database

Usage:
    export DATABASE_URL="postgresql://..."
    export RENTCAST_API_KEY="..."
    python3 test_rentcast.py
"""

import os
import sys
from rentcast_client import RentCastClient
from database import Database

# Test coordinates for 126 Schultz, Chapel Hill, NC
TEST_LAT = 35.9132
TEST_LON = -79.0558
TEST_ADDRESS = "126 Schultz Chapel Hill, NC"

def main():
    print("="*70)
    print("RentCast Integration Test")
    print("="*70)

    # Step 1: Check environment
    print("\n1️⃣  Checking Environment...")
    api_key = os.getenv('RENTCAST_API_KEY')
    db_url = os.getenv('DATABASE_URL')

    if not api_key:
        print("❌ RENTCAST_API_KEY not set")
        sys.exit(1)
    print(f"✅ RENTCAST_API_KEY: {api_key[:10]}...")

    if not db_url:
        print("❌ DATABASE_URL not set")
        sys.exit(1)
    print(f"✅ DATABASE_URL: postgresql://... (Neon)")

    # Step 2: Test API Connection
    print("\n2️⃣  Testing RentCast API Connection...")
    client = RentCastClient(api_key=api_key)

    try:
        print(f"   Address: {TEST_ADDRESS}")
        print(f"   Coordinates: ({TEST_LAT}, {TEST_LON})")
        print(f"   Requesting 25 comparables...")

        response = client.get_rent_estimate(
            latitude=TEST_LAT,
            longitude=TEST_LON,
            bedrooms=None,
            bathrooms=None,
            sqft=None,
            comp_count=25
        )

        print(f"✅ API Response Received")
        print(f"   Rent Estimate: ${response.get('rent', 0):,.2f}")
        print(f"   Rent Range: ${response.get('rentRangeLow', 0):,.2f} - ${response.get('rentRangeHigh', 0):,.2f}")
        print(f"   Comparables in response: {len(response.get('comparables', []))}")

        # Show first comparable as example
        if response.get('comparables'):
            comp1 = response['comparables'][0]
            print(f"\n   Example Comparable:")
            print(f"     Address: {comp1.get('formattedAddress', 'N/A')}")
            print(f"     Beds/Baths: {comp1.get('bedrooms')}/{comp1.get('bathrooms')}")
            print(f"     Sqft: {comp1.get('squareFootage')}")
            print(f"     Rent: ${comp1.get('price', 0):,.2f}")
            print(f"     Correlation: {comp1.get('correlation', 0):.2f}")

    except Exception as e:
        print(f"❌ API Error: {e}")
        sys.exit(1)

    # Step 3: Test Normalization
    print("\n3️⃣  Testing Normalization...")
    try:
        normalized = client.normalize_comparables(response)
        print(f"✅ Normalized {len(normalized)} comparables")

        if normalized:
            norm1 = normalized[0]
            print(f"\n   Normalized Fields:")
            print(f"     address: {norm1.get('address')}")
            print(f"     city: {norm1.get('city')}")
            print(f"     state: {norm1.get('state')}")
            print(f"     rent_price: {norm1.get('rent_price')}")
            print(f"     bedrooms: {norm1.get('bedrooms')}")
            print(f"     bathrooms: {norm1.get('bathrooms')}")
            print(f"     sqft: {norm1.get('sqft')}")

    except Exception as e:
        print(f"❌ Normalization Error: {e}")
        sys.exit(1)

    # Step 4: Test Database Save
    print("\n4️⃣  Testing Database Save (PostgreSQL)...")
    try:
        db = Database()
        print(f"   Database Engine: {db.engine}")

        saved_count = db.save_external_comps(normalized, source='RentCast')
        print(f"✅ Saved {saved_count} comparables to database")

        if saved_count != len(normalized):
            print(f"⚠️  Warning: Expected {len(normalized)}, saved {saved_count}")

    except Exception as e:
        print(f"❌ Database Save Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 5: Test Database Retrieval
    print("\n5️⃣  Testing Database Retrieval...")
    try:
        retrieved = db.find_external_comps(
            center_lat=TEST_LAT,
            center_lon=TEST_LON,
            radius_miles=10.0,
            filters=None,
            max_age_days=30,
            source='RentCast'
        )

        print(f"✅ Retrieved {len(retrieved)} comparables from database")

        if retrieved:
            ret1 = retrieved[0]
            print(f"\n   First Retrieved Comp:")
            print(f"     address: {ret1.get('address')}")
            print(f"     rent_price: ${ret1.get('rent_price', 0):,.2f}")
            print(f"     distance_miles: {ret1.get('distance_miles', 0):.2f}")
            print(f"     age_days: {ret1.get('age_days', 0):.1f}")

    except Exception as e:
        print(f"❌ Database Retrieval Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Summary
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print(f"\nSummary:")
    print(f"  - API returned {len(response.get('comparables', []))} comps")
    print(f"  - Normalized {len(normalized)} comps")
    print(f"  - Saved {saved_count} to PostgreSQL")
    print(f"  - Retrieved {len(retrieved)} from database")
    print(f"\nRentCast integration is working correctly! ✅")

if __name__ == "__main__":
    main()
