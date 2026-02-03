"""
CSV Parser for AppFolio Rent Roll exports
Extracts property data and rent information from AppFolio CSV format
"""

import pandas as pd
import re
from typing import Dict, List, Tuple, Optional


class RentRollParser:
    """Parser for AppFolio rent roll CSV files"""

    # ZIP code to city lookup for fallback (Durham/Chapel Hill/Triangle area)
    ZIP_TO_CITY = {
        '27501': 'Angier',
        '27502': 'Apex',
        '27503': 'Bahama',
        '27504': 'Bonlee',
        '27505': 'Bullock',
        '27506': 'Bunn',
        '27507': 'Butner',
        '27508': 'Cary',
        '27509': 'Cameron',
        '27510': 'Carrboro',
        '27511': 'Cary',
        '27512': 'Cary',
        '27513': 'Cary',
        '27514': 'Chapel Hill',
        '27515': 'Chapel Hill',
        '27516': 'Chapel Hill',
        '27517': 'Chapel Hill',
        '27519': 'Cary',
        '27520': 'Clayton',
        '27521': 'Coats',
        '27522': 'Creedmoor',
        '27523': 'Apex',
        '27524': 'Four Oaks',
        '27525': 'Franklinton',
        '27526': 'Fuquay Varina',
        '27529': 'Garner',
        '27530': 'Goldsboro',
        '27545': 'Hillsborough',
        '27551': 'Mebane',
        '27560': 'Morrisville',
        '27562': 'New Hill',
        '27571': 'Pittsboro',
        '27587': 'Wake Forest',
        '27591': 'Wendell',
        '27592': 'Willow Spring',
        '27597': 'Zebulon',
        '27603': 'Raleigh',
        '27604': 'Raleigh',
        '27605': 'Raleigh',
        '27606': 'Raleigh',
        '27607': 'Raleigh',
        '27608': 'Raleigh',
        '27609': 'Raleigh',
        '27610': 'Raleigh',
        '27612': 'Raleigh',
        '27613': 'Raleigh',
        '27614': 'Raleigh',
        '27615': 'Raleigh',
        '27616': 'Raleigh',
        '27617': 'Raleigh',
        '27701': 'Durham',
        '27703': 'Durham',
        '27704': 'Durham',
        '27705': 'Durham',
        '27707': 'Durham',
        '27712': 'Durham',
        '27713': 'Durham',
    }

    @staticmethod
    def parse_address(unit_field: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Extract address components from unit field
        Format: "-> ADDRESS - FULL ADDRESS CITY, STATE ZIP"
        Or: "-> ADDRESS CITY, STATE ZIP" (without hyphen separator)

        Returns:
            Tuple of (full_address, unit, city, state, zip_code)
        """
        if not unit_field or not isinstance(unit_field, str):
            return None, None, None, None, None

        # Pattern 1: "-> ADDRESS - FULL_ADDRESS City, State Zip"
        # Example: "-> 1 Autumn Woods Dr - 1 Autumn Woods Dr Durham, NC 27713"
        # Supports ZIP+4 format (e.g., 27713-5229)
        pattern1 = r'->\s*(.+?)\s*-\s*(.+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)'
        match = re.search(pattern1, unit_field)

        if match:
            short_address = match.group(1).strip()
            full_address_with_city = match.group(2).strip()
            state = match.group(3).strip()
            zip_code_raw = match.group(4).strip()
            # Strip ZIP+4 to just 5 digits for consistency
            zip_code = zip_code_raw.split('-')[0]

            # Extract city as the last word(s) before the comma
            # Split the full address to get just the street part
            # Handle multi-word cities like "Chapel Hill", "Cary"
            parts = full_address_with_city.split()

            # Known multi-word cities in the area
            multi_word_cities = ['Chapel Hill']

            city = None
            full_address = full_address_with_city

            if len(parts) >= 2:
                # Check for 2-word city at end
                potential_two_word = f"{parts[-2]} {parts[-1]}"
                if potential_two_word in multi_word_cities:
                    city = potential_two_word
                    street_parts = parts[:-2]
                    full_address = ' '.join(street_parts) if street_parts else ''
                else:
                    # Single word city
                    city = parts[-1]
                    street_parts = parts[:-1]
                    full_address = ' '.join(street_parts)
            elif len(parts) == 1:
                # Only one word - could be city only or street only
                # Assume it's street if no hyphen (no unit), otherwise could be city
                full_address = full_address_with_city
                city = None

            # Construct complete address with proper comma placement
            # USPS standard: [Number Street], [City], [State ZIP]
            # NO comma after house number
            if city:
                complete_address = f"{full_address}, {city}, {state} {zip_code}"
            else:
                complete_address = f"{full_address}, {state} {zip_code}"

            # Only return unit if short_address differs from full_address
            # If they're the same, there's no actual unit designation
            unit = short_address if short_address != full_address else None

            return complete_address, unit, city, state, zip_code

        # Pattern 2: "-> ADDRESS City, State Zip" (no hyphen separator)
        # Example: "-> 1003 Christopher Chapel Hill, NC 27517"
        # Supports ZIP+4 format
        # City must be 1-3 capitalized words immediately before comma (handles "Chapel Hill", "Research Triangle Park", etc.)
        # Use more specific pattern: city words start with capital and contain lowercase
        pattern2 = r'->\s*(.+)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)'
        match2 = re.search(pattern2, unit_field)

        if match2:
            street_address = match2.group(1).strip()
            city = match2.group(2).strip()
            state = match2.group(3).strip()
            zip_code_raw = match2.group(4).strip()
            # Strip ZIP+4 to just 5 digits
            zip_code = zip_code_raw.split('-')[0]

            # Remove trailing comma if present
            street_address = street_address.rstrip(',').strip()

            # Construct complete address with proper comma placement
            complete_address = f"{street_address}, {city}, {state} {zip_code}"

            # No hyphen means no separate unit designation
            return complete_address, None, city, state, zip_code

        # Pattern 3: Missing ZIP code - "-> ADDRESS - FULL_ADDRESS City, State" (no ZIP)
        # Example: "-> x1113 Gurley St Unit A - 1113 Gurley St Unit A Durham, NC"
        # For these cases, we can't reliably parse city, so just use the full address
        pattern3 = r'->\s*(.+?)\s*-\s*(.+?),\s*([A-Z]{2})$'
        match3 = re.search(pattern3, unit_field)

        if match3:
            short_address = match3.group(1).strip()
            full_address = match3.group(2).strip()
            state = match3.group(3).strip()

            # Remove trailing comma if present
            full_address = full_address.rstrip(',').strip()

            # Can't reliably extract city without ZIP, use empty
            city = None
            zip_code = None

            # Construct complete address
            complete_address = f"{full_address}, {state}"

            # Only return unit if short_address differs from full_address
            unit = short_address if short_address != full_address else None

            return complete_address, unit, city, state, zip_code

        # Pattern 4: Missing ZIP, no hyphen - "-> ADDRESS City, State"
        pattern4 = r'->\s*(.+?),\s*([A-Z]{2})$'
        match4 = re.search(pattern4, unit_field)

        if match4:
            street_address = match4.group(1).strip()
            state = match4.group(2).strip()

            # Remove trailing comma if present
            street_address = street_address.rstrip(',').strip()

            # Can't reliably extract city without ZIP
            city = None
            zip_code = None

            # Construct complete address
            complete_address = f"{street_address}, {state}"

            # No hyphen means no separate unit designation
            return complete_address, None, city, state, zip_code

        # If we get here, no pattern matched
        return None, None, None, None, None

    @staticmethod
    def get_city_from_zip(zip_code: str) -> Optional[str]:
        """
        Lookup city name from ZIP code as fallback

        Args:
            zip_code: 5-digit ZIP code

        Returns:
            City name or None if not found
        """
        if zip_code and len(zip_code) >= 5:
            return RentRollParser.ZIP_TO_CITY.get(zip_code[:5])
        return None

    @staticmethod
    def parse_beds_baths(bd_ba_field: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Parse bedrooms and bathrooms from BD/BA field
        Format: "3/2.50" or "2/1.00" or "--/--"

        Returns:
            Tuple of (bedrooms, bathrooms)
        """
        if not bd_ba_field or bd_ba_field == '--/--':
            return None, None

        try:
            parts = bd_ba_field.split('/')
            bedrooms = float(parts[0]) if parts[0] != '--' else None
            bathrooms = float(parts[1]) if parts[1] != '--' else None
            return bedrooms, bathrooms
        except (ValueError, IndexError):
            return None, None

    @staticmethod
    def clean_currency(value: str) -> Optional[float]:
        """
        Clean currency values by removing commas and dollar signs

        Args:
            value: String like "2,500.00" or "$1,250.00"

        Returns:
            Float value or None
        """
        if pd.isna(value) or value == '':
            return None

        try:
            # Remove commas, dollar signs, and whitespace
            cleaned = str(value).replace(',', '').replace('$', '').strip()
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    @staticmethod
    def clean_sqft(value: str) -> Optional[int]:
        """
        Clean square footage values

        Args:
            value: String like "1,789" or "850"

        Returns:
            Integer value or None
        """
        cleaned = RentRollParser.clean_currency(value)
        return int(cleaned) if cleaned else None

    @staticmethod
    def parse_csv(file_path: str) -> List[Dict]:
        """
        Parse AppFolio rent roll CSV file

        Args:
            file_path: Path to the CSV file

        Returns:
            List of property dictionaries
        """
        # Read CSV
        df = pd.read_csv(file_path)

        properties = []
        current_address_info = None

        for idx, row in df.iterrows():
            unit_field = row.get('Unit', '')

            # Check if this is a property header line (starts with "->")
            if isinstance(unit_field, str) and unit_field.startswith('->'):
                address, unit, city, state, zip_code = RentRollParser.parse_address(unit_field)
                if address:
                    current_address_info = {
                        'address': address,
                        'unit': unit,
                        'city': city,
                        'state': state,
                        'zip_code': zip_code
                    }
                continue

            # Get Unit column value from data row
            unit_column = row.get('Unit', '')
            if isinstance(unit_column, float) or pd.isna(unit_column):
                unit_column = ''
            else:
                unit_column = str(unit_column).strip()

            # Skip summary rows (e.g., "2 Units", "3 Units")
            if unit_column and 'Units' in unit_column:
                continue

            # Skip rows without bed/bath data
            bd_ba = row.get('BD/BA', '')
            if not bd_ba or bd_ba == '':
                continue

            # Parse property data
            if current_address_info:
                bedrooms, bathrooms = RentRollParser.parse_beds_baths(bd_ba)
                sqft = RentRollParser.clean_sqft(row.get('Sqft', ''))
                market_rent = RentRollParser.clean_currency(row.get('Market Rent', ''))
                actual_rent = RentRollParser.clean_currency(row.get('Rent', ''))

                # Extract tags
                tags = row.get('Tags', '')
                if pd.isna(tags):
                    tags = ''

                # Determine status only (no tenant info)
                status = row.get('Status', '')
                if pd.isna(status):
                    status = ''

                # Derive occupancy type (simple: Occupied or Vacant)
                occupancy_type = 'Vacant' if 'vacant' in status.lower() else 'Occupied'

                # Skip PII fields:
                # - No tenant names
                # - No lease dates
                # - No deposit amounts
                # - No payment history (past_due, nsf_count, late_count)

                # Determine final unit designation
                # Priority: Data row unit > Header unit
                base_address = current_address_info['address']
                header_unit = current_address_info['unit']

                # Check if unit is in data row (Format 2: "Unit A", "Unit B")
                if unit_column and unit_column.strip():
                    final_unit = unit_column

                    # Build unique address with unit BEFORE city (USPS standard)
                    # Format: "123 Main St Unit A, Durham, NC 27701"
                    # Split at first comma to separate street from city/state/zip
                    parts = base_address.split(',', 1)
                    if len(parts) == 2:
                        street = parts[0].strip()
                        city_state_zip = parts[1].strip()
                        unique_address = f"{street} {final_unit}, {city_state_zip}"
                    else:
                        # Fallback if no comma found
                        street = base_address
                        unique_address = f"{base_address} {final_unit}"
                else:
                    # No unit in data row, address already has unit if it's Format 3
                    final_unit = header_unit
                    unique_address = base_address

                    # Extract street portion for display_address
                    parts = base_address.split(',', 1)
                    if len(parts) == 2:
                        street = parts[0].strip()
                    else:
                        street = base_address

                # City fallback: If city is missing or looks malformed, use ZIP lookup
                city = current_address_info['city']
                zip_code = current_address_info['zip_code']

                # Detect malformed city (has multiple words that look like street addresses)
                # Malformed = more than 2 words (e.g., "Royal Stock Lane Cary" instead of "Cary" or "Chapel Hill")
                if city and len(city.split()) > 2:
                    # Likely malformed - try ZIP lookup
                    zip_city = RentRollParser.get_city_from_zip(zip_code)
                    if zip_city:
                        city = zip_city
                elif not city and zip_code:
                    # No city parsed, use ZIP lookup
                    city = RentRollParser.get_city_from_zip(zip_code)

                # Create display_address (short format for UI: just street + unit)
                display_addr = street
                if final_unit:
                    display_addr = f"{street} {final_unit}"

                property_data = {
                    'address': unique_address,
                    'unit': final_unit,
                    'city': city,
                    'state': current_address_info['state'],
                    'zip_code': zip_code,
                    'display_address': display_addr,
                    'bedrooms': bedrooms,
                    'bathrooms': bathrooms,
                    'sqft': sqft,
                    'tags': tags,
                    'market_rent': market_rent,
                    'actual_rent': actual_rent,
                    'status': status,
                    'occupancy_type': occupancy_type
                }

                properties.append(property_data)

        return properties

    @staticmethod
    def get_effective_rent(property_data: Dict) -> Optional[float]:
        """
        Get effective rent for a property (actual rent if occupied, market rent if vacant)

        Args:
            property_data: Property dictionary with rent information

        Returns:
            Effective rent value
        """
        status = property_data.get('status', '').lower()
        actual_rent = property_data.get('actual_rent')
        market_rent = property_data.get('market_rent')

        # If property is vacant, use market rent
        if 'vacant' in status:
            return market_rent

        # Otherwise use actual rent, fallback to market rent
        return actual_rent if actual_rent else market_rent

    @staticmethod
    def is_vacant(property_data: Dict) -> bool:
        """Check if property is vacant"""
        status = property_data.get('status', '').lower()
        return 'vacant' in status
