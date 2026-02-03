"""
Geocoding module using Nominatim (OpenStreetMap) and U.S. Census Geocoder
Handles address-to-coordinates conversion with rate limiting and fallback strategies
"""

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
from typing import Optional, Tuple, Dict, List
import os
import requests
import csv
import io

from address_cleaner import AddressCleaner


class Geocoder:
    """Geocoder using Nominatim with rate limiting"""

    def __init__(self, user_agent: str = "cma_generator_demo", email: str = None):
        """
        Initialize geocoder

        Args:
            user_agent: User agent string for Nominatim
            email: Email for Nominatim usage policy compliance
        """
        self.user_agent = user_agent
        self.email = email or os.getenv('GEOCODING_EMAIL', 'noreply@example.com')
        self.geolocator = Nominatim(user_agent=self.user_agent, timeout=10)
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Nominatim requires 1 request per second max

    def _rate_limit(self):
        """Enforce rate limiting (max 1 request per second)"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def geocode(self, address: str, max_retries: int = 3) -> Optional[Tuple[float, float]]:
        """
        Geocode an address to latitude/longitude with fallback strategy

        Args:
            address: Full address string
            max_retries: Maximum number of retry attempts per variant

        Returns:
            Tuple of (latitude, longitude) or None if all attempts fail
        """
        # Get standardized address variants to try
        variants = AddressCleaner.create_geocoding_variants(address)

        # Try each variant
        for variant in variants:
            result = self._geocode_single(variant, max_retries)
            if result:
                return result

        return None

    def geocode_with_quality(self, address: str, max_retries: int = 3) -> Dict:
        """
        Geocode an address and return coordinates with quality metadata

        Args:
            address: Full address string
            max_retries: Maximum number of retry attempts per variant

        Returns:
            Dictionary with keys: latitude, longitude, quality, variant_used, original_address
            Quality levels: 'exact', 'street', 'city', 'zip', 'failed'
        """
        result = {
            'latitude': None,
            'longitude': None,
            'quality': 'failed',
            'variant_used': None,
            'original_address': address,
            'standardized_address': None
        }

        # Get standardized address variants
        variants = AddressCleaner.create_geocoding_variants(address)

        if not variants:
            return result

        result['standardized_address'] = variants[0] if variants else address

        # Try each variant and track which one worked
        for idx, variant in enumerate(variants):
            coords = self._geocode_single(variant, max_retries)
            if coords:
                result['latitude'] = coords[0]
                result['longitude'] = coords[1]
                result['variant_used'] = variant

                # Determine quality based on which variant worked
                if idx == 0:
                    result['quality'] = 'exact'  # Full address
                elif idx == 1:
                    result['quality'] = 'street'  # Street-level (no unit)
                elif idx == 2:
                    result['quality'] = 'city'   # City-level
                else:
                    result['quality'] = 'zip'    # ZIP code level

                return result

        return result

    def _geocode_single(self, address: str, max_retries: int = 3) -> Optional[Tuple[float, float]]:
        """
        Geocode a single address variant

        Args:
            address: Address string to geocode
            max_retries: Maximum number of retry attempts

        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        for attempt in range(max_retries):
            try:
                self._rate_limit()

                location = self.geolocator.geocode(address)

                if location:
                    return (location.latitude, location.longitude)

            except GeocoderTimedOut:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return None

            except GeocoderServiceError as e:
                # Don't print for each variant attempt, let caller handle logging
                return None

            except Exception as e:
                # Don't print for each variant attempt
                return None

        return None

    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Reverse geocode coordinates to an address

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            Address string or None
        """
        try:
            self._rate_limit()
            location = self.geolocator.reverse(f"{latitude}, {longitude}")
            return location.address if location else None

        except Exception as e:
            print(f"Error reverse geocoding ({latitude}, {longitude}): {e}")
            return None

    def geocode_batch_nominatim(self, addresses: list, progress_callback=None) -> dict:
        """
        Geocode a batch of addresses one-at-a-time using Nominatim (SLOW - use geocode_batch instead)

        Args:
            addresses: List of address strings
            progress_callback: Optional callback function(current, total, address)

        Returns:
            Dictionary mapping addresses to (lat, lon) tuples or None
        """
        results = {}
        total = len(addresses)

        for idx, address in enumerate(addresses, 1):
            if progress_callback:
                progress_callback(idx, total, address)

            coords = self.geocode(address)
            results[address] = coords

        return results


def calculate_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula

    Args:
        lat1, lon1: First coordinate
        lat2, lon2: Second coordinate

    Returns:
        Distance in miles
    """
    from math import radians, cos, sin, asin, sqrt

    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    # Radius of earth in miles
    r = 3959

    return c * r


class CensusGeocoder:
    """
    U.S. Census Bureau Geocoder
    - Free, no API key required
    - High quality for U.S. addresses
    - Supports batch geocoding (up to 10,000 addresses)
    - No rate limits for reasonable usage
    """

    BASE_URL = "https://geocoding.geo.census.gov/geocoder"

    def __init__(self, benchmark: str = "Public_AR_Current"):
        """
        Initialize Census Geocoder

        Args:
            benchmark: Benchmark name (default: Public_AR_Current for latest)
        """
        self.benchmark = benchmark

    def geocode_single(self, street: str, city: str = None, state: str = None,
                      zip_code: str = None) -> Optional[Dict]:
        """
        Geocode a single address using Census API

        Args:
            street: Street address (e.g., "123 Main St")
            city: City name
            state: State code (2 letters)
            zip_code: ZIP code

        Returns:
            Dict with latitude, longitude, quality, matched_address or None
        """
        # Build address parameters
        params = {
            'benchmark': self.benchmark,
            'format': 'json'
        }

        if street and city and state:
            # Use address components
            params['street'] = street
            if city:
                params['city'] = city
            if state:
                params['state'] = state
            if zip_code:
                params['zip'] = zip_code
            endpoint = f"{self.BASE_URL}/locations/address"
        else:
            # Fallback to one-line address
            address_parts = [p for p in [street, city, state, zip_code] if p]
            params['address'] = ', '.join(address_parts)
            endpoint = f"{self.BASE_URL}/locations/onelineaddress"

        try:
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Parse response
            if data.get('result', {}).get('addressMatches'):
                match = data['result']['addressMatches'][0]
                coords = match['coordinates']

                return {
                    'latitude': coords['y'],
                    'longitude': coords['x'],
                    'quality': 'exact',  # Census generally provides exact matches
                    'matched_address': match.get('matchedAddress', ''),
                    'tiger_line_id': match.get('tigerLine', {}).get('tigerLineId')
                }

            return None

        except Exception as e:
            print(f"Census geocoding error: {e}")
            return None

    def geocode_batch(self, addresses: List[Dict]) -> List[Dict]:
        """
        Geocode multiple addresses using Census batch API

        Args:
            addresses: List of dicts with keys: id, street, city, state, zip_code
                      Example: {'id': '1', 'street': '123 Main St', 'city': 'Durham',
                               'state': 'NC', 'zip_code': '27701'}

        Returns:
            List of dicts with keys: id, latitude, longitude, quality, matched_address, status
        """
        if len(addresses) > 10000:
            raise ValueError("Census batch geocoder limited to 10,000 addresses per request")

        # Create CSV in memory
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)

        # Write addresses in Census format: ID, Street, City, State, ZIP
        for addr in addresses:
            row = [
                addr.get('id', ''),
                addr.get('street', ''),
                addr.get('city', ''),
                addr.get('state', ''),
                addr.get('zip_code', '')
            ]
            writer.writerow(row)

        # Prepare request
        csv_content = csv_buffer.getvalue()
        files = {'addressFile': ('addresses.csv', csv_content, 'text/csv')}
        data = {
            'benchmark': self.benchmark,
            'returntype': 'locations'
        }

        endpoint = f"{self.BASE_URL}/locations/addressbatch"

        try:
            response = requests.post(endpoint, files=files, data=data, timeout=120)
            response.raise_for_status()

            # Parse CSV response
            results = []
            reader = csv.reader(io.StringIO(response.text))

            for row in reader:
                if len(row) < 6:
                    continue

                # Census batch response format:
                # ID, Input Address, Match (Match/No_Match/Tie), Match Type, Matched Address,
                # Lon/Lat (x,y), Tiger Line ID, Side
                result = {
                    'id': row[0],
                    'input_address': row[1],
                    'match_status': row[2],  # Match, No_Match, or Tie
                    'status': 'success' if row[2] == 'Match' else 'failed'
                }

                if row[2] == 'Match' and len(row) >= 6:
                    # Parse coordinates from "lon,lat" format
                    coords = row[5].split(',')
                    if len(coords) == 2:
                        try:
                            result['longitude'] = float(coords[0])
                            result['latitude'] = float(coords[1])
                            result['quality'] = 'exact'
                            result['matched_address'] = row[4] if len(row) > 4 else ''
                        except (ValueError, IndexError):
                            result['status'] = 'failed'
                            result['latitude'] = None
                            result['longitude'] = None
                else:
                    result['latitude'] = None
                    result['longitude'] = None
                    result['quality'] = 'failed'

                results.append(result)

            return results

        except Exception as e:
            print(f"Census batch geocoding error: {e}")
            return []

    def geocode_with_quality(self, address: str, city: str = None,
                            state: str = None, zip_code: str = None) -> Dict:
        """
        Geocode address with quality metadata (compatible with Nominatim interface)

        Args:
            address: Street address or full address string
            city: City name (optional if address is full)
            state: State code (optional if address is full)
            zip_code: ZIP code (optional)

        Returns:
            Dict with latitude, longitude, quality, variant_used, original_address
        """
        result = {
            'latitude': None,
            'longitude': None,
            'quality': 'failed',
            'variant_used': None,
            'original_address': address,
            'standardized_address': None
        }

        # If no components provided, try to parse from address string
        if not city and not state:
            # Try address variants
            variants = AddressCleaner.create_geocoding_variants(address)

            for variant in variants:
                # Parse variant components
                parts = variant.split(',')
                if len(parts) >= 3:
                    street = parts[0].strip()
                    city_part = parts[1].strip()
                    state_zip = parts[2].strip().split()
                    state_part = state_zip[0] if state_zip else None
                    zip_part = state_zip[1] if len(state_zip) > 1 else None

                    census_result = self.geocode_single(street, city_part, state_part, zip_part)

                    if census_result:
                        result['latitude'] = census_result['latitude']
                        result['longitude'] = census_result['longitude']
                        result['quality'] = census_result['quality']
                        result['variant_used'] = variant
                        result['standardized_address'] = census_result.get('matched_address', variant)
                        return result
        else:
            # Use provided components
            census_result = self.geocode_single(address, city, state, zip_code)

            if census_result:
                result['latitude'] = census_result['latitude']
                result['longitude'] = census_result['longitude']
                result['quality'] = census_result['quality']
                result['variant_used'] = f"{address}, {city}, {state} {zip_code}"
                result['standardized_address'] = census_result.get('matched_address', '')

        return result
