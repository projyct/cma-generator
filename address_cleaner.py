"""
Address Standardization and Normalization Module
Cleans and standardizes US addresses before geocoding to improve success rate
"""

import re
from typing import Dict, Optional, Tuple


class AddressCleaner:
    """Clean and standardize US addresses"""

    # Common street type abbreviations
    STREET_TYPES = {
        'ST': 'STREET', 'STR': 'STREET', 'ST.': 'STREET',
        'AVE': 'AVENUE', 'AV': 'AVENUE', 'AVE.': 'AVENUE',
        'BLVD': 'BOULEVARD', 'BL': 'BOULEVARD', 'BLVD.': 'BOULEVARD',
        'RD': 'ROAD', 'RD.': 'ROAD',
        'DR': 'DRIVE', 'DR.': 'DRIVE', 'DRV': 'DRIVE',
        'LN': 'LANE', 'LN.': 'LANE',
        'CT': 'COURT', 'CT.': 'COURT', 'CRT': 'COURT',
        'CIR': 'CIRCLE', 'CIRC': 'CIRCLE', 'CIR.': 'CIRCLE',
        'PL': 'PLACE', 'PL.': 'PLACE',
        'TRL': 'TRAIL', 'TR': 'TRAIL', 'TRL.': 'TRAIL',
        'WAY': 'WAY', 'WY': 'WAY',
        'PKWY': 'PARKWAY', 'PKY': 'PARKWAY', 'PKWY.': 'PARKWAY',
        'TER': 'TERRACE', 'TERR': 'TERRACE', 'TER.': 'TERRACE',
        'HWY': 'HIGHWAY', 'HW': 'HIGHWAY', 'HWY.': 'HIGHWAY',
    }

    # Common directional abbreviations
    DIRECTIONALS = {
        'N': 'NORTH', 'N.': 'NORTH',
        'S': 'SOUTH', 'S.': 'SOUTH',
        'E': 'EAST', 'E.': 'EAST',
        'W': 'WEST', 'W.': 'WEST',
        'NE': 'NORTHEAST', 'N.E.': 'NORTHEAST',
        'NW': 'NORTHWEST', 'N.W.': 'NORTHWEST',
        'SE': 'SOUTHEAST', 'S.E.': 'SOUTHEAST',
        'SW': 'SOUTHWEST', 'S.W.': 'SOUTHWEST',
    }

    # Common unit designators
    UNIT_TYPES = {
        'APT': 'APARTMENT', 'APT.': 'APARTMENT', '#': 'APARTMENT',
        'STE': 'SUITE', 'STE.': 'SUITE',
        'UNIT': 'UNIT', 'UN': 'UNIT',
        'BLDG': 'BUILDING', 'BLDG.': 'BUILDING',
        'FL': 'FLOOR', 'FLR': 'FLOOR',
        'RM': 'ROOM', 'ROOM': 'ROOM',
    }

    # Valid US state codes for validation
    VALID_STATES = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
        'DC'  # District of Columbia
    }

    # Common typos/misspellings for Durham, Chapel Hill area
    CITY_CORRECTIONS = {
        'DRIHAM': 'DURHAM',
        'DURHM': 'DURHAM',
        'CAHPEL': 'CHAPEL',
        'CHAPEL HILL': 'CHAPEL HILL',
        'CHAPELHILL': 'CHAPEL HILL',
        'PITTSBORO': 'PITTSBORO',
        'PITTSBOROUGH': 'PITTSBORO',
    }

    @staticmethod
    def clean_whitespace(text: str) -> str:
        """Remove extra whitespace and normalize spacing"""
        if not text:
            return ""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        return text.strip()

    @staticmethod
    def remove_unit_designators(street: str) -> str:
        """
        Remove unit/apartment/suite designators from street address

        Args:
            street: Street address that may contain unit numbers

        Returns:
            Street address with unit designators removed
        """
        if not street:
            return street

        # Pattern matches: APT 4, UNIT B, SUITE 100, #205, etc.
        # Handles: APT, APARTMENT, UNIT, SUITE, STE, BLDG, FL, ROOM, RM, #
        # Note: # doesn't need \b word boundary
        pattern = r'(\bAPT\.?|\bAPARTMENT|\bUNIT|\bUN|\bSUITE|\bSTE\.?|\bBLDG\.?|\bBUILDING|\bFL\.?|\bFLOOR|\bFLR|\bROOM|\bRM|#)\s*[A-Z0-9\-]+\b'

        # Remove unit designators (case insensitive)
        cleaned = re.sub(pattern, '', street, flags=re.IGNORECASE)

        # Clean up extra whitespace left behind
        cleaned = AddressCleaner.clean_whitespace(cleaned)

        return cleaned

    @staticmethod
    def is_po_box(address: str) -> bool:
        """
        Check if address is a PO Box (cannot be geocoded)

        Args:
            address: Address string to check

        Returns:
            True if address is a PO Box
        """
        if not address:
            return False

        # Pattern matches: PO BOX, P.O. BOX, P O BOX, etc.
        pattern = r'\bP\.?\s*O\.?\s*BOX\s+\d+\b'
        return bool(re.search(pattern, address.upper()))

    @staticmethod
    def normalize_street_type(address_parts: list) -> list:
        """Normalize street type abbreviations"""
        normalized = []
        for part in address_parts:
            upper_part = part.upper()
            if upper_part in AddressCleaner.STREET_TYPES:
                normalized.append(AddressCleaner.STREET_TYPES[upper_part])
            else:
                normalized.append(part)
        return normalized

    @staticmethod
    def normalize_directionals(address_parts: list) -> list:
        """Normalize directional abbreviations"""
        normalized = []
        for part in address_parts:
            upper_part = part.upper()
            if upper_part in AddressCleaner.DIRECTIONALS:
                normalized.append(AddressCleaner.DIRECTIONALS[upper_part])
            else:
                normalized.append(part)
        return normalized

    @staticmethod
    def fix_city_typos(city: str) -> str:
        """Fix common city name typos"""
        if not city:
            return city

        upper_city = city.upper()
        for typo, correction in AddressCleaner.CITY_CORRECTIONS.items():
            if typo in upper_city:
                upper_city = upper_city.replace(typo, correction)

        # Return in title case
        return upper_city.title()

    @staticmethod
    def parse_components(address: str) -> Dict[str, Optional[str]]:
        """
        Parse address into components: street, city, state, zip

        Args:
            address: Full address string

        Returns:
            Dictionary with street, city, state, zip_code
        """
        components = {
            'street': None,
            'city': None,
            'state': None,
            'zip_code': None
        }

        if not address:
            return components

        # Try to extract zip code (including Zip+4 format)
        zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', address)
        if zip_match:
            components['zip_code'] = zip_match.group(1)
            # Remove zip from address for further parsing
            address = address[:zip_match.start()] + address[zip_match.end():]

        # Try to extract state (2-letter code, case-insensitive with validation)
        # Look for all 2-letter words and validate them
        state_matches = re.finditer(r'\b([A-Za-z]{2})\b', address)
        for match in state_matches:
            state_candidate = match.group(1).upper()
            # Validate it's a real US state code
            if state_candidate in AddressCleaner.VALID_STATES:
                components['state'] = state_candidate
                # Remove state from address
                address = address[:match.start()] + address[match.end():]
                break  # Only take first valid state match

        # Split remaining by comma and filter empty parts
        parts = [p.strip() for p in address.split(',') if p.strip()]

        if len(parts) >= 2:
            # Assume: "street, city" or "street, city, state"
            components['street'] = parts[0]
            components['city'] = parts[1]
        elif len(parts) == 1:
            # Just street address
            components['street'] = parts[0]

        return components

    @staticmethod
    def standardize(address: str) -> str:
        """
        Standardize an address string

        Args:
            address: Raw address string

        Returns:
            Standardized address string
        """
        if not address:
            return ""

        # Check if PO Box (return as-is, cannot be geocoded)
        if AddressCleaner.is_po_box(address):
            return AddressCleaner.clean_whitespace(address).upper()

        # Clean whitespace
        address = AddressCleaner.clean_whitespace(address)

        # Parse components
        components = AddressCleaner.parse_components(address)

        # Standardize street component
        street = components.get('street', '')
        if street:
            # CRITICAL FIX: Remove unit designators FIRST
            street = AddressCleaner.remove_unit_designators(street)

            # Split street into words
            street_parts = street.split()

            # Normalize street types and directionals
            street_parts = AddressCleaner.normalize_street_type(street_parts)
            street_parts = AddressCleaner.normalize_directionals(street_parts)

            # Apply smart title casing
            titled_parts = []
            for part in street_parts:
                upper_part = part.upper()
                # Preserve all-caps words (like US, NC)
                if len(part) == 2 and upper_part in AddressCleaner.VALID_STATES:
                    titled_parts.append(upper_part)
                # Preserve ordinals (1st, 2nd, 3rd, etc.)
                elif re.match(r'^\d+(st|nd|rd|th)$', part.lower()):
                    titled_parts.append(part.lower())
                # Handle hyphenated words properly
                elif '-' in part:
                    titled_parts.append('-'.join([w.capitalize() for w in part.split('-')]))
                # Handle apostrophes (O'Brien, etc.)
                elif "'" in part:
                    titled_parts.append(part.title())
                else:
                    titled_parts.append(part.title())

            street = ' '.join(titled_parts)

        # Standardize city
        city = components.get('city', '')
        if city:
            city = AddressCleaner.fix_city_typos(city)

        # Standardize state (already uppercase from parse_components)
        state = components.get('state', '')

        # Get zip code (preserves Zip+4)
        zip_code = components.get('zip_code', '')

        # Reconstruct standardized address
        standardized_parts = []

        if street:
            standardized_parts.append(street)

        if city:
            standardized_parts.append(city)

        if state and zip_code:
            standardized_parts.append(f"{state} {zip_code}")
        elif state:
            standardized_parts.append(state)
        elif zip_code:
            standardized_parts.append(zip_code)

        return ', '.join(standardized_parts)

    @staticmethod
    def standardize_components(street: str = None, city: str = None,
                              state: str = None, zip_code: str = None,
                              remove_units: bool = False) -> str:
        """
        Standardize address from individual components

        Args:
            street: Street address
            city: City name
            state: State code (2 letters)
            zip_code: ZIP code
            remove_units: Whether to remove unit designators from street

        Returns:
            Standardized full address string
        """
        # Build address from components
        parts = []

        if street:
            street = AddressCleaner.clean_whitespace(street)

            # Remove units if requested
            if remove_units:
                street = AddressCleaner.remove_unit_designators(street)

            street_parts = street.split()
            street_parts = AddressCleaner.normalize_street_type(street_parts)
            street_parts = AddressCleaner.normalize_directionals(street_parts)
            street = ' '.join([p.title() for p in street_parts])
            parts.append(street)

        if city:
            city = AddressCleaner.fix_city_typos(AddressCleaner.clean_whitespace(city))
            parts.append(city)

        if state:
            state = state.upper().strip()

        if state and zip_code:
            parts.append(f"{state} {zip_code.strip()}")
        elif state:
            parts.append(state)
        elif zip_code:
            parts.append(zip_code.strip())

        return ', '.join(parts)

    @staticmethod
    def format_for_display(street: str = None, unit: str = None, city: str = None,
                          state: str = None, zip_code: str = None) -> str:
        """
        Format address according to USPS standards for professional display

        USPS Standard Format:
        [House Number] [Street Name] [Street Type] [Unit], [City], [State] [ZIP]

        Examples:
            123 Main St Unit A, Durham, NC 27701
            1 Autumn Woods Dr, Durham, NC 27713
            10 Brandywine Ct Unit A, Durham, NC 27705

        Args:
            street: Street address (e.g., "123 Main St")
            unit: Unit designator (e.g., "Unit A", "Apt 5")
            city: City name
            state: State code (2 letters)
            zip_code: ZIP code

        Returns:
            Professionally formatted address string
        """
        parts = []

        # Street address - no comma after house number
        if street:
            street = street.strip()

            # Remove any trailing commas from street
            street = street.rstrip(',').strip()

            # Append unit to street if present (before comma)
            if unit and unit.strip():
                street = f"{street} {unit.strip()}"

            parts.append(street)
        elif unit:
            # Edge case: only unit provided
            parts.append(unit.strip())

        # City (after first comma)
        if city:
            parts.append(city.strip())

        # State and ZIP (space separated, after city)
        if state and zip_code:
            parts.append(f"{state.strip()} {zip_code.strip()}")
        elif state:
            parts.append(state.strip())
        elif zip_code:
            parts.append(zip_code.strip())

        # Join with commas between major components
        return ', '.join(parts) if parts else ''

    @staticmethod
    def create_geocoding_variants(address: str) -> list:
        """
        Create multiple variants of an address for geocoding attempts
        Optimized order to maximize exact matches first

        Args:
            address: Address string

        Returns:
            List of address variants to try, in order of specificity
        """
        variants = []

        # Parse components
        components = AddressCleaner.parse_components(address)

        # VARIANT 1: Street + City + State + Zip (NO unit) - Most likely to work with Nominatim
        if components.get('street'):
            variant = AddressCleaner.standardize_components(
                components['street'],
                components.get('city'),
                components.get('state'),
                components.get('zip_code'),
                remove_units=True  # Use new remove_units flag
            )
            if variant:
                variants.append(variant)

        # VARIANT 2: Full standardized address (with unit if present)
        full_standardized = AddressCleaner.standardize(address)
        if full_standardized and full_standardized not in variants:
            variants.append(full_standardized)

        # VARIANT 3: Street + City + State (no ZIP, no unit) - For addresses with bad ZIP
        if components.get('street') and components.get('city') and components.get('state'):
            variant = AddressCleaner.standardize_components(
                components['street'],
                components.get('city'),
                components.get('state'),
                None,  # No ZIP
                remove_units=True
            )
            if variant and variant not in variants:
                variants.append(variant)

        # VARIANT 4: City + State + Zip (for city-level geocoding)
        if components.get('city') and (components.get('state') or components.get('zip_code')):
            city_variant = AddressCleaner.standardize_components(
                None,
                components.get('city'),
                components.get('state'),
                components.get('zip_code')
            )
            if city_variant and city_variant not in variants:
                variants.append(city_variant)

        # VARIANT 5: Just Zip code (as last resort)
        if components.get('zip_code'):
            zip_variant = components['zip_code']
            if zip_variant not in variants:
                variants.append(zip_variant)

        return variants


def standardize_address(address: str) -> str:
    """
    Convenience function to standardize an address

    Args:
        address: Raw address string

    Returns:
        Standardized address string
    """
    return AddressCleaner.standardize(address)


def get_geocoding_variants(address: str) -> list:
    """
    Convenience function to get geocoding variants

    Args:
        address: Address string

    Returns:
        List of address variants to try for geocoding
    """
    return AddressCleaner.create_geocoding_variants(address)
