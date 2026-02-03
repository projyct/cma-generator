"""
RentCast API Client - Fetch rental comparables from RentCast
API Documentation: https://developers.rentcast.io/
"""

import requests
from typing import List, Dict, Optional
import os


class RentCastClient:
    """
    Client for RentCast API to fetch rental comparables and estimates

    Free tier: 50 API requests/month
    Each request returns 1 rent estimate + up to 25 comparable properties
    """

    def __init__(self, api_key: str = None):
        """
        Initialize RentCast API client

        Args:
            api_key: RentCast API key (from https://app.rentcast.io/app/api)
                    If not provided, will check RENTCAST_API_KEY env variable
        """
        self.api_key = api_key or os.getenv('RENTCAST_API_KEY')
        self.base_url = "https://api.rentcast.io/v1"
        self.headers = {
            "X-Api-Key": self.api_key,
            "Accept": "application/json"
        }

    def get_rent_estimate(self,
                         latitude: float,
                         longitude: float,
                         bedrooms: int = None,
                         bathrooms: float = None,
                         sqft: int = None,
                         comp_count: int = 25) -> Dict:
        """
        Get rent estimate and comparable properties for a location

        Args:
            latitude: Property latitude
            longitude: Property longitude
            bedrooms: Number of bedrooms (optional filter)
            bathrooms: Number of bathrooms (optional filter)
            sqft: Square footage (optional filter)
            comp_count: Number of comparables to return (5-25, default 25)

        Returns:
            Dictionary containing:
            - rent: Estimated monthly rent
            - rentRangeLow: Low end of rent range
            - rentRangeHigh: High end of rent range
            - comparables: List of comparable properties (up to 25)

        Raises:
            Exception: If API request fails
        """
        if not self.api_key:
            raise Exception("RentCast API key not configured. Set RENTCAST_API_KEY environment variable.")

        # Build request parameters
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "compCount": min(max(comp_count, 5), 25)  # Clamp between 5-25
        }

        # Add optional filters
        if bedrooms is not None:
            params["bedrooms"] = bedrooms
        if bathrooms is not None:
            params["bathrooms"] = bathrooms
        if sqft is not None:
            params["squareFootage"] = sqft

        # Make API request
        try:
            response = requests.get(
                f"{self.base_url}/avm/rent/long-term",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise Exception("Invalid RentCast API key. Check your API key at https://app.rentcast.io/app/api")
            elif response.status_code == 429:
                raise Exception("RentCast API rate limit exceeded. Upgrade plan or wait until next month.")
            elif response.status_code == 404:
                raise Exception("No rental data available for this location.")
            else:
                raise Exception(f"RentCast API error: {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error connecting to RentCast: {e}")

    def get_comparables_for_address(self,
                                    address: str,
                                    bedrooms: int = None,
                                    bathrooms: float = None,
                                    sqft: int = None,
                                    comp_count: int = 25) -> Dict:
        """
        Get rent estimate and comparables using address (convenience method)

        Note: This method makes 2 API calls (1 for geocoding, 1 for estimate)
        Better to use get_rent_estimate() with known lat/long to save API calls

        Args:
            address: Full address string
            bedrooms: Number of bedrooms (optional)
            bathrooms: Number of bathrooms (optional)
            sqft: Square footage (optional)
            comp_count: Number of comparables (5-25)

        Returns:
            Same as get_rent_estimate()
        """
        if not self.api_key:
            raise Exception("RentCast API key not configured. Set RENTCAST_API_KEY environment variable.")

        # Build parameters
        params = {
            "address": address,
            "compCount": min(max(comp_count, 5), 25)
        }

        if bedrooms is not None:
            params["bedrooms"] = bedrooms
        if bathrooms is not None:
            params["bathrooms"] = bathrooms
        if sqft is not None:
            params["squareFootage"] = sqft

        # Make API request
        try:
            response = requests.get(
                f"{self.base_url}/avm/rent/long-term",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise Exception("Invalid RentCast API key")
            elif response.status_code == 429:
                raise Exception("RentCast API rate limit exceeded")
            elif response.status_code == 404:
                raise Exception(f"Address not found: {address}")
            else:
                raise Exception(f"RentCast API error: {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {e}")

    @staticmethod
    def normalize_comparables(api_response: Dict) -> List[Dict]:
        """
        Normalize RentCast API response to standard format for database storage

        Args:
            api_response: Raw response from get_rent_estimate()

        Returns:
            List of normalized comparable properties
        """
        comps = api_response.get('comparables', [])
        normalized = []

        for comp in comps:
            normalized.append({
                'address': comp.get('formattedAddress') or comp.get('address'),
                'city': comp.get('city'),
                'state': comp.get('state'),
                'zip_code': comp.get('zipCode'),
                'latitude': comp.get('latitude'),
                'longitude': comp.get('longitude'),
                'bedrooms': comp.get('bedrooms'),
                'bathrooms': comp.get('bathrooms'),
                'sqft': comp.get('squareFootage'),
                'rent_price': comp.get('price'),
                'property_type': comp.get('propertyType'),
                'year_built': comp.get('yearBuilt'),
                'source_id': comp.get('id'),
                'correlation_score': comp.get('correlation'),
                'listing_status': comp.get('status'),
                'days_on_market': comp.get('daysOnMarket')
            })

        return normalized

    def test_connection(self) -> bool:
        """
        Test if API key is valid and connection works

        Returns:
            True if connection successful, False otherwise
        """
        if not self.api_key:
            print("❌ No API key configured")
            return False

        try:
            # Make a minimal test request (Durham, NC)
            response = self.get_rent_estimate(
                latitude=35.9940,
                longitude=-78.8986,
                comp_count=5
            )
            print(f"✅ RentCast API connected successfully")
            print(f"   Rent estimate: ${response.get('rent', 0):,.2f}/month")
            print(f"   Comparables returned: {len(response.get('comparables', []))}")
            return True
        except Exception as e:
            print(f"❌ RentCast API connection failed: {e}")
            return False
