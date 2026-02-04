"""
CMA Generator - Streamlit Application
Main application for generating Comparative Market Analysis reports
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import os
from pathlib import Path

from database import Database
from parsers import RentRollParser
from geocoder import Geocoder, CensusGeocoder, calculate_distance_miles
from reports import CMAReportGenerator
from rentcast_client import RentCastClient
from address_cleaner import AddressCleaner
from google_drive_exporter import GoogleDriveExporter
import re
from urllib.parse import quote

# Conditional import for Google Auth
try:
    from streamlit_google_auth import Authenticate
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

# Helper Functions
def generate_zillow_url(address: str, city: str = "", state: str = "", zip_code: str = "") -> str:
    """
    Generate Zillow search URL from address components.
    Format: https://www.zillow.com/homes/{address-city-state-zip}_rb/

    Args:
        address: Street address (e.g., "123 Main St")
        city: City name (optional if included in address)
        state: State abbreviation (optional if included in address)
        zip_code: ZIP code (optional if included in address)

    Returns:
        Formatted Zillow search URL
    """
    # If full address provided as single string, try to parse it
    if not city and not state and not zip_code:
        # Try to extract components from full address
        # Format: "123 Main St, Durham, NC 27701"
        parts = [p.strip() for p in address.split(',')]
        if len(parts) >= 3:
            address = parts[0]
            city = parts[1] if len(parts) > 1 else ""
            # Parse "NC 27701" or just "NC"
            state_zip = parts[2].split() if len(parts) > 2 else []
            state = state_zip[0] if len(state_zip) > 0 else ""
            zip_code = state_zip[1] if len(state_zip) > 1 else ""
        elif len(parts) == 2:
            address = parts[0]
            # Assume second part is "City State" or "City"
            city_state = parts[1].split()
            city = ' '.join(city_state[:-1]) if len(city_state) > 1 else city_state[0]
            state = city_state[-1] if len(city_state) > 1 else ""

    # Build formatted address string
    formatted_parts = [address]
    if city:
        formatted_parts.append(city)
    if state:
        formatted_parts.append(state)
    if zip_code:
        formatted_parts.append(str(zip_code))

    # Join with hyphens and clean up
    formatted_address = '-'.join(formatted_parts)

    # Remove special characters and clean up
    formatted_address = re.sub(r'[^\w\s-]', '', formatted_address)  # Remove punctuation except hyphens
    formatted_address = re.sub(r'\s+', '-', formatted_address)  # Replace spaces with hyphens
    formatted_address = re.sub(r'-+', '-', formatted_address)  # Collapse multiple hyphens
    formatted_address = formatted_address.strip('-')  # Remove leading/trailing hyphens

    # Build Zillow URL
    zillow_url = f"https://www.zillow.com/homes/{formatted_address}_rb/"

    return zillow_url

def calculate_age_display(date_str: str) -> str:
    """
    Convert retrieved_date timestamp to human-readable age.

    Args:
        date_str: ISO format datetime string

    Returns:
        Human-readable age string (e.g., "2 days", "3 weeks")
    """
    if not date_str:
        return "N/A"

    try:
        # Parse the datetime string
        retrieved = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        age_days = (datetime.now() - retrieved.replace(tzinfo=None)).days

        if age_days == 0:
            return "Today"
        elif age_days == 1:
            return "1 day"
        elif age_days < 7:
            return f"{age_days} days"
        elif age_days < 30:
            weeks = age_days // 7
            return f"{weeks} week" if weeks == 1 else f"{weeks} weeks"
        else:
            months = age_days // 30
            return f"{months} month" if months == 1 else f"{months} months"
    except Exception:
        return "N/A"

# Page configuration
st.set_page_config(
    page_title="CMA Generator",
    page_icon="🏠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Authentication check
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Get password from environment variable or Streamlit secrets
        correct_password = os.getenv("APP_PASSWORD") or st.secrets.get("APP_PASSWORD", "")

        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    # Return True if password already validated
    if st.session_state.get("password_correct", False):
        return True

    # Show password input
    st.title("🔐 CMA Generator - Access Required")
    st.markdown("---")
    st.info("Please enter the access password to continue.")

    st.text_input(
        "Password",
        type="password",
        on_change=password_entered,
        key="password",
        help="Contact the administrator if you need access"
    )

    # Show error if password was incorrect
    if st.session_state.get("password_correct", None) == False:
        st.error("😕 Incorrect password. Please try again.")

    return False

# Check authentication before loading app
if not check_password():
    st.stop()  # Do not continue if password is incorrect

# Mobile-optimized CSS
st.markdown("""
<style>
    /* Mobile-friendly improvements */
    @media (max-width: 768px) {
        /* Increase touch target sizes */
        .stButton button {
            min-height: 44px;
            padding: 12px 24px;
            font-size: 16px;
        }

        /* Better spacing for mobile */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 3rem;
        }

        /* Truncate long addresses in tables */
        .stDataFrame td {
            max-width: 150px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        /* Stack metrics vertically on mobile */
        [data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }

        /* Improve input field sizes */
        .stTextInput input, .stSelectbox select, .stNumberInput input {
            font-size: 16px;
            min-height: 44px;
        }

        /* Better table scrolling */
        .stDataFrame {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
    }

    /* Always apply better spacing */
    .stButton button {
        min-height: 40px;
    }

    /* Disable Streamlit's rerun fade animation to prevent grey page flash */
    .main .block-container {
        transition: none !important;
    }

    .stApp > div {
        transition: none !important;
    }

    div[data-testid="stStatusWidget"] {
        transition: none !important;
    }

    /* Prevent grey overlay during reruns */
    .stApp [data-testid="stAppViewContainer"] {
        transition: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize cached resources
@st.cache_resource
def get_database():
    """Get cached database instance"""
    return Database()

@st.cache_resource
def get_geocoder():
    """Get cached geocoder instance"""
    return Geocoder()

@st.cache_resource
def get_report_generator():
    """Get cached report generator instance"""
    return CMAReportGenerator()

@st.cache_resource
def get_rentcast_client():
    """Get cached RentCast API client instance"""
    return RentCastClient()

# Initialize session state with loading indicator
if 'initialized' not in st.session_state:
    with st.spinner("🔧 Initializing CMA Generator..."):
        st.session_state.db = get_database()
        st.session_state.geocoder = get_geocoder()
        st.session_state.report_generator = get_report_generator()
        st.session_state.rentcast = get_rentcast_client()
        st.session_state.initialized = True

if 'db' not in st.session_state:
    st.session_state.db = get_database()

if 'geocoder' not in st.session_state:
    st.session_state.geocoder = get_geocoder()

if 'report_generator' not in st.session_state:
    st.session_state.report_generator = get_report_generator()

if 'rentcast' not in st.session_state:
    st.session_state.rentcast = get_rentcast_client()

if 'external_comps' not in st.session_state:
    st.session_state.external_comps = []

if 'comparables' not in st.session_state:
    st.session_state.comparables = []

if 'search_params' not in st.session_state:
    st.session_state.search_params = None

if 'selected_comps' not in st.session_state:
    st.session_state.selected_comps = []

if 'subject_coords' not in st.session_state:
    st.session_state.subject_coords = None

if 'import_status' not in st.session_state:
    st.session_state.import_status = None  # None, 'in_progress', 'completed', 'error'

if 'import_summary' not in st.session_state:
    st.session_state.import_summary = None


# Sidebar navigation
st.sidebar.title("🏠 CMA Generator")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["🔍 Generate CMA", "⚙️ Data Management"],
    index=0
)

st.sidebar.markdown("---")

# Global import status indicator
if st.session_state.import_status == 'in_progress':
    st.sidebar.warning("⏳ **Import in progress...**\nPlease stay on this page")
elif st.session_state.import_status == 'completed' and st.session_state.import_summary:
    with st.sidebar:
        st.success("✅ **Last Import Successful**")
        summary = st.session_state.import_summary
        st.caption(f"{summary.get('new', 0)} new, {summary.get('updated', 0)} updated")

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info(
    "This tool generates Comparative Market Analysis reports "
    "based on your rent roll data and market comparables."
)


# ============================================================================
# PAGE 2: Data Management - Upload Rent Roll Tab
# ============================================================================
if page == "⚙️ Data Management":
    st.title("⚙️ Data Management")

    # Create tabs for the workflow
    tab1, tab2, tab3 = st.tabs(["📤 Step 1: Upload Rent Roll", "🗺️ Step 2: Geocode Properties", "📊 Step 3: View Properties"])

    with tab1:
        st.markdown("### Step 1: Upload Rent Roll")
        st.markdown("Upload your latest AppFolio rent roll export CSV file. **Import starts automatically.**")

        uploaded_file = st.file_uploader(
            "Choose rent roll CSV file",
            type=['csv'],
            help="Export from AppFolio: Reports > Rent Roll",
            key="rent_roll_uploader"
        )
        
        if uploaded_file is not None:
            # Save uploaded file with a consistent name
            temp_path = f"data/temp_rent_roll_latest.csv"

            # Check if this is a new file upload (compare with session state)
            is_new_upload = (
                'last_uploaded_file' not in st.session_state or
                st.session_state.last_uploaded_file != uploaded_file.name
            )

            if is_new_upload:
                # Save file
                with open(temp_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())

                # Mark as new upload
                st.session_state.last_uploaded_file = uploaded_file.name
                st.session_state.import_status = None  # Reset status for new upload

            st.success(f"✅ File uploaded: {uploaded_file.name}")

            # Show import status
            if st.session_state.import_status == 'in_progress':
                st.warning("⚠️ **Import was interrupted.** The file will be re-imported automatically. Please wait and don't navigate away.")

            elif st.session_state.import_status == 'completed' and st.session_state.import_summary:
                summary = st.session_state.import_summary
                st.success(f"✅ Import completed in {summary['elapsed']:.1f}s!")

                col1, col2, col3 = st.columns(3)
                col1.metric("New Properties", summary['new'])
                col2.metric("Updated Properties", summary['updated'])
                col3.metric("Needs Geocoding", summary['pending_geocode'])

                if summary['pending_geocode'] > 0:
                    st.info(f"💡 {summary['pending_geocode']} properties need geocoding. Go to **Tab 2: Geocode Properties** to geocode them.")

            # Preview
            with st.expander("📄 Preview Raw CSV"):
                preview_df = pd.read_csv(temp_path, nrows=20)
                st.dataframe(preview_df)

            # AUTO-IMPORT: Trigger on new file upload OR if import was interrupted
            should_import = (
                is_new_upload or
                (st.session_state.import_status == 'in_progress' and not is_new_upload)
            )

            if should_import:
                # Set status to in_progress
                st.session_state.import_status = 'in_progress'

                with st.spinner("Parsing rent roll data..."):
                    try:
                        import time

                        # Parse CSV
                        properties = RentRollParser.parse_csv(temp_path)

                        st.info(f"Found {len(properties)} properties in rent roll")

                        # Check for duplicates in parsed data
                        from collections import Counter
                        addresses = [p['address'] for p in properties]
                        address_counts = Counter(addresses)
                        duplicates = {addr: count for addr, count in address_counts.items() if count > 1}

                        if duplicates:
                            st.warning(f"⚠️ Found {len(duplicates)} duplicate addresses in CSV (will keep last occurrence):")
                            with st.expander(f"View {len(duplicates)} duplicate addresses"):
                                for addr, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True):
                                    st.caption(f"• {count}x: {addr}")

                        # Progress bar
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        start_time = time.time()

                        # Step 1: Prepare all properties for batch insert
                        status_text.text("Preparing properties for import...")
                        for prop in properties:
                            # Store original address (from parser)
                            prop['original_address'] = prop['address']

                            # display_address already set by parser (street + unit only)
                            # Don't override it here!

                            # Standardized address will be populated by Census geocoder
                            # For now, leave empty - Census provides authoritative USPS standard
                            prop['standardized_address'] = None

                            # Check if property already exists
                            existing = st.session_state.db.get_property_by_address(prop['address'])

                            if existing:
                                # Property exists - preserve geocoding data if available
                                prop['latitude'] = existing.get('latitude')
                                prop['longitude'] = existing.get('longitude')
                                prop['geocode_quality'] = existing.get('geocode_quality')
                                prop['geocode_variant'] = existing.get('geocode_variant')
                                prop['geocoding_status'] = existing.get('geocoding_status', 'pending')
                                prop['standardized_address'] = existing.get('standardized_address')
                            else:
                                # New property - mark for geocoding
                                prop['latitude'] = None
                                prop['longitude'] = None
                                prop['geocode_quality'] = None
                                prop['geocode_variant'] = None
                                prop['geocoding_status'] = 'pending'

                        progress_bar.progress(0.3)

                        # Step 2: Batch insert all properties
                        status_text.text(f"Inserting {len(properties)} properties...")
                        batch_result = st.session_state.db.insert_properties_batch(properties)
                        imported_count = batch_result['inserted']
                        updated_count = batch_result['updated']
                        property_ids = batch_result['property_ids']

                        progress_bar.progress(0.6)

                        # Step 3: Prepare rent history records (PII removed)
                        status_text.text("Preparing rent history...")
                        rent_records = []
                        for idx, prop in enumerate(properties):
                            rent_records.append({
                                'property_id': property_ids[idx],
                                'market_rent': prop.get('market_rent'),
                                'actual_rent': prop.get('actual_rent'),
                                'status': prop.get('status'),
                                'occupancy_type': prop.get('occupancy_type')
                            })

                        progress_bar.progress(0.8)

                        # Step 4: Batch insert rent history
                        status_text.text(f"Inserting {len(rent_records)} rent history records...")
                        st.session_state.db.insert_rent_history_batch(rent_records)

                        progress_bar.progress(1.0)
                        status_text.empty()
                        progress_bar.empty()

                        # Get geocoding statistics
                        geocode_stats = st.session_state.db.get_geocoding_stats()
                        pending_count = geocode_stats.get('pending', 0)
                        completed_count = geocode_stats.get('completed', 0)

                        # Summary
                        elapsed = time.time() - start_time
                        st.success(f"✅ Import Complete in {elapsed:.1f} seconds!")

                        col1, col2, col3 = st.columns(3)
                        col1.metric("New Properties", imported_count)
                        col2.metric("Updated Properties", updated_count)
                        col3.metric("Needs Geocoding", pending_count)

                        if pending_count > 0:
                            st.info(f"💡 {pending_count} properties need geocoding. Go to **Tab 2: Geocode Properties** to geocode them.")

                        # Update session state with completion status
                        st.session_state.import_status = 'completed'
                        st.session_state.import_summary = {
                            'new': imported_count,
                            'updated': updated_count,
                            'pending_geocode': pending_count,
                            'elapsed': elapsed
                        }

                        # Clean up temp file
                        os.remove(temp_path)

                    except Exception as e:
                        st.error(f"❌ Error parsing rent roll: {e}")
                        st.session_state.import_status = 'error'
                        import traceback
                        st.code(traceback.format_exc())

    # Tab 2: Geocoding
    with tab2:
        st.markdown("### Step 2: Geocode Properties")

        all_props_geo = st.session_state.db.get_all_properties()

        if not all_props_geo:
            st.warning("⚠️ No properties in database. Please upload a rent roll in Tab 1 first.")
        else:
            # Geocoding Statistics
            geocode_stats = st.session_state.db.get_geocoding_stats()

            # Handle both 'geocoded' and 'completed' status values
            geocoded_count = geocode_stats.get('geocoded', 0) + geocode_stats.get('completed', 0)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Properties", geocode_stats.get('total', 0))
            col2.metric("✅ Geocoded", geocoded_count)
            col3.metric("⏳ Pending", geocode_stats.get('pending', 0))
            col4.metric("❌ Failed", geocode_stats.get('failed', 0))

            # Geocoding Section
            if geocode_stats.get('pending', 0) > 0:
                st.markdown("---")
                st.subheader("🗺️ Geocode Pending Properties")

                pending_count = geocode_stats.get('pending', 0)

                st.info(f"**{pending_count} properties** need geocoding. This will use the Census Batch API (free, fast, accurate).")

                # Geocoding button
                col_btn1, col_btn2 = st.columns([1, 3])
                with col_btn1:
                    if st.button("🗺️ Start Geocoding", type="primary", key="geocode_button"):
                        st.session_state.geocoding_in_progress_tab2 = True

                with col_btn2:
                    st.caption("Estimated time: ~30 seconds for all properties")

                # Geocoding process
                if st.session_state.get('geocoding_in_progress_tab2', False):
                    import time
                    from address_cleaner import AddressCleaner

                    st.markdown("---")
                    st.markdown("### 🚀 Geocoding in Progress")

                    # Get pending properties
                    pending_props = st.session_state.db.get_properties_by_geocoding_status('pending')

                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    success_count = 0
                    failed_count = 0
                    start_time = time.time()

                    # Use Census Batch API
                    geocoder = CensusGeocoder()
                    status_text.text(f"🇺🇸 Preparing {len(pending_props)} addresses for Census Batch API...")

                    # Prepare addresses with cleaning
                    batch_addresses = []
                    for prop in pending_props:
                        full_addr = prop.get('address', '')
                        street = full_addr

                        # Remove city, state, zip from end to get just street
                        if prop.get('city'):
                            street = street.replace(f", {prop['city']}", "")
                        if prop.get('state') and prop.get('zip_code'):
                            street = street.replace(f", {prop['state']} {prop['zip_code']}", "")
                        elif prop.get('state'):
                            street = street.replace(f", {prop['state']}", "")

                        street = street.strip().rstrip(',').strip()

                        batch_addresses.append({
                            'id': str(prop['id']),
                            'street': street,
                            'city': prop.get('city', ''),
                            'state': prop.get('state', ''),
                            'zip_code': prop.get('zip_code', '')
                        })

                    progress_bar.progress(0.2)
                    status_text.text(f"📤 Sending {len(batch_addresses)} addresses to Census API...")

                    # Call Census batch API
                    batch_results = geocoder.geocode_batch(batch_addresses)

                    progress_bar.progress(0.6)
                    status_text.text(f"💾 Updating database with {len(batch_results)} results...")

                    # Update database
                    for result in batch_results:
                        prop_id = int(result.get('id', 0))
                        matching_prop = next((p for p in pending_props if p['id'] == prop_id), None)

                        if matching_prop:
                            st.session_state.db.update_geocoding(
                                address=matching_prop['address'],
                                latitude=result.get('latitude'),
                                longitude=result.get('longitude'),
                                geocode_quality=result.get('quality', 'failed'),
                                geocode_variant=result.get('input_address'),
                                standardized_address=result.get('matched_address', '')
                            )

                            if result.get('latitude'):
                                success_count += 1
                            else:
                                failed_count += 1

                    progress_bar.progress(1.0)
                    elapsed = time.time() - start_time

                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()

                    # Show results
                    st.success(f"✅ **Geocoding Complete!** Processed {len(pending_props)} properties in {elapsed:.1f} seconds")

                    col_r1, col_r2 = st.columns(2)
                    col_r1.metric("✅ Successfully Geocoded", success_count)
                    col_r2.metric("❌ Failed", failed_count)

                    if failed_count > 0:
                        st.warning(f"⚠️ {failed_count} addresses could not be geocoded. These may have malformed addresses or not exist in the Census database.")

                    # Reset state and rerun to show updated stats
                    st.session_state.geocoding_in_progress_tab2 = False
                    time.sleep(1)
                    st.rerun()

            else:
                st.success("✅ All properties have been geocoded!")
                st.info("💡 Go to **Tab 3: View Properties** to see your geocoded data")

    # Tab 3: View Properties
    with tab3:
        st.markdown("### Step 3: View Properties")

        # ============================================================
        # DATABASE STATISTICS - MOVED TO TOP FOR IMMEDIATE VISIBILITY
        # ============================================================

        # Section 1: Rent Roll Properties Database
        st.markdown("#### 🏠 Rent Roll Properties Database")

        geocode_stats = st.session_state.db.get_geocoding_stats()
        geocoded_count = geocode_stats.get('geocoded', 0) + geocode_stats.get('completed', 0)
        geocode_pct = (geocoded_count / geocode_stats.get('total', 1)) * 100 if geocode_stats.get('total', 0) > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 Properties", geocode_stats.get('total', 0))
        col2.metric("🗺️ Geocoded", f"{geocode_pct:.0f}%")
        col3.metric("✅ Ready", geocoded_count)
        col4.metric("❌ Failed", geocode_stats.get('failed', 0))

        st.markdown("")  # Spacing

        # Section 2: RentCast External Database
        st.markdown("#### 🌐 RentCast External Database")

        rentcast_stats = st.session_state.db.get_external_comps_stats('RentCast')

        if rentcast_stats and rentcast_stats.get('total_count', 0) > 0:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📊 Cached Comps", rentcast_stats.get('total_count', 0))

            # Calculate age displays
            newest_age = calculate_age_display(rentcast_stats.get('newest_date'))
            oldest_age = calculate_age_display(rentcast_stats.get('oldest_date'))
            avg_age = rentcast_stats.get('avg_age_days', 0)

            col2.metric("📅 Newest", newest_age)
            col3.metric("📅 Oldest", oldest_age)
            col4.metric("⏰ Avg Age", f"{avg_age:.1f} days")
        else:
            st.info("💡 No RentCast comparables cached yet. Generate a CMA to fetch data!")

        st.markdown("---")

        # ============================================================
        # PROPERTY DATA TABLE (existing code continues below)
        # ============================================================

        all_props = st.session_state.db.get_all_properties()

        if not all_props:
            st.warning("⚠️ No properties in database. Please upload a rent roll in Tab 1 first.")
        else:

            # Create display dataframe
            display_data = []
            for prop in all_props:
                # Handle display_address with fallback for NULL/legacy values
                display_addr = prop.get('display_address')
                if not display_addr or display_addr == 'None':
                    # Fallback: extract street from full address
                    full_addr = prop.get('address', '')
                    # Take everything before first comma (street portion)
                    display_addr = full_addr.split(',')[0] if ',' in full_addr else full_addr
                    # Add unit if exists
                    if prop.get('unit'):
                        display_addr = f"{display_addr} {prop['unit']}"
                    display_addr = display_addr or 'N/A'

                display_data.append({
                    'Address': display_addr,
                    'City': prop.get('city', 'N/A'),
                    'Beds': prop.get('bedrooms', 'N/A'),
                    'Baths': prop.get('bathrooms', 'N/A'),
                    'Sqft': prop.get('sqft', 'N/A'),
                    'Market Rent': f"${prop.get('market_rent', 0):,.2f}" if prop.get('market_rent') else 'N/A',
                    'Actual Rent': f"${prop.get('actual_rent', 0):,.2f}" if prop.get('actual_rent') else 'N/A',
                    'Status': prop.get('status', 'N/A'),
                    'Geocoded': '✅' if prop.get('latitude') else '❌'
                })

            df = pd.DataFrame(display_data)

            # Filters
            st.markdown("### 🔍 Filters")
            col1, col2, col3 = st.columns(3)

            with col1:
                city_filter = st.multiselect(
                    "Filter by City",
                    options=sorted([c for c in df['City'].unique().tolist() if c and c != 'N/A'])
                )

            with col2:
                status_filter = st.multiselect(
                    "Filter by Status",
                    options=sorted([s for s in df['Status'].unique().tolist() if s and s != 'N/A'])
                )

            with col3:
                geocoded_filter = st.selectbox(
                    "Geocoded Status",
                    options=["All", "Geocoded Only", "Not Geocoded"]
                )

            # Apply filters
            filtered_df = df.copy()

            if city_filter:
                filtered_df = filtered_df[filtered_df['City'].isin(city_filter)]

            if status_filter:
                filtered_df = filtered_df[filtered_df['Status'].isin(status_filter)]

            if geocoded_filter == "Geocoded Only":
                filtered_df = filtered_df[filtered_df['Geocoded'] == '✅']
            elif geocoded_filter == "Not Geocoded":
                filtered_df = filtered_df[filtered_df['Geocoded'] == '❌']

            # Show count with RentCast total
            st.markdown(f"### 📊 Rent Roll: Showing {len(filtered_df)} of {len(df)} properties")
            if rentcast_stats and rentcast_stats.get('total_count', 0) > 0:
                st.info(f"💡 Plus **{rentcast_stats.get('total_count', 0)} RentCast comparables** in cache (used in CMA generation)")

            st.dataframe(filtered_df, hide_index=True, width='stretch')

            # Export current view
            st.markdown("---")
            col_export1, col_export2, col_export3 = st.columns([1, 1, 2])

            with col_export1:
                if st.button("📥 Export to CSV"):
                    csv_path = f"exports/properties_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    os.makedirs("exports", exist_ok=True)
                    filtered_df.to_csv(csv_path, index=False)
                    st.success(f"✅ Exported to {csv_path}")

            with col_export2:
                # Provide download button
                csv_data = filtered_df.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv_data,
                    file_name=f"properties_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )


# ============================================================================
# PAGE 1: Generate CMA (Primary page)
# ============================================================================
if page == "🔍 Generate CMA":
    st.title("🔍 Generate CMA Report")

    # Check if database has properties
    all_props_check = st.session_state.db.get_all_properties()

    if not all_props_check:
        st.warning("⚠️ **No properties in database yet**")
        st.info("👉 Go to **Data Management** to upload your rent roll and get started")
        st.stop()

    # Input form
    st.markdown("### Subject Property")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Get all properties for dropdown
        all_props = st.session_state.db.get_all_properties()

        if not all_props:
            st.warning("⚠️ No properties in database. Please upload a rent roll first.")
            st.stop()

        # Create address options
        address_options = [prop['address'] for prop in all_props if prop['address']]

        subject_address = st.selectbox(
            "Select Subject Property",
            options=[""] + address_options,
            help="Choose a property from your rent roll or enter manually below"
        )

        # Or manual entry
        manual_address = st.text_input(
            "Or Enter Address Manually",
            placeholder="123 Main St, Durham, NC 27701"
        )

        # Use manual if provided, otherwise use selected
        final_address = manual_address if manual_address else subject_address

        # Add Zillow Rent Zestimate link if address is entered
        if final_address:
            if subject_address and not manual_address:
                # Dropdown selected: Use database fields for better URL formatting
                selected_prop = next((p for p in all_props if p['address'] == subject_address), None)
                if selected_prop:
                    zillow_url = generate_zillow_url(
                        selected_prop.get('address', final_address),
                        selected_prop.get('city', ''),
                        selected_prop.get('state', ''),
                        selected_prop.get('zip_code', '')
                    )
                else:
                    # Fallback to parsing full address string
                    zillow_url = generate_zillow_url(final_address)
            else:
                # Manual entry: Parse full address string
                zillow_url = generate_zillow_url(final_address)

            st.markdown(f"[📊 View Rent Zestimate on Zillow ↗]({zillow_url})", unsafe_allow_html=True)

    with col2:
        st.markdown("#### Property Details")

        # Auto-fill if property selected
        if subject_address and not manual_address:
            selected_prop = next((p for p in all_props if p['address'] == subject_address), None)
            if selected_prop:
                default_beds = selected_prop.get('bedrooms') or 0
                default_baths = selected_prop.get('bathrooms') or 0
                default_sqft = selected_prop.get('sqft') or 0
        else:
            default_beds = 0
            default_baths = 0
            default_sqft = 0

        subject_beds = st.number_input("Bedrooms", min_value=0.0, max_value=10.0, value=float(default_beds), step=0.5)
        subject_baths = st.number_input("Bathrooms", min_value=0.0, max_value=10.0, value=float(default_baths), step=0.5)
        subject_sqft = st.number_input("Square Feet", min_value=0, max_value=10000, value=int(default_sqft), step=50)

    # Search criteria
    st.markdown("### Search Criteria")

    col1, col2, col3 = st.columns(3)

    with col1:
        search_radius = st.slider("Search Radius (miles)", min_value=0.5, max_value=20.0, value=3.0, step=0.5)

    with col2:
        sqft_tolerance = st.slider("Sqft Tolerance (±)", min_value=0, max_value=1000, value=200, step=50)

    with col3:
        exact_match = st.checkbox("Exact Bed/Bath Match Only", value=True)

    # Advanced filters
    with st.expander("🔧 Advanced Filters"):
        col1, col2 = st.columns(2)

        with col1:
            property_type_filter = st.multiselect(
                "Property Type",
                options=["Single Family", "Townhouse", "Condo", "Duplex"],
                default=None
            )

            status_filter = st.multiselect(
                "Occupancy Status",
                options=["Current", "Vacant-Unrented", "Notice", "Evict"],
                default=None
            )

        with col2:
            year_built_min = st.number_input("Year Built (Min)", min_value=1900, max_value=2030, value=1900, step=1)
            year_built_max = st.number_input("Year Built (Max)", min_value=1900, max_value=2030, value=2030, step=1)

    # Search button
    if st.button("🔍 Find Comparables", type="primary"):
        # Clear external comps when starting a new CMA search
        st.session_state.external_comps = []

        # Mark that a search has been performed
        st.session_state.cma_search_active = True

        if not final_address:
            st.error("❌ Please select or enter a subject property address")
            st.stop()

        with st.spinner("Searching for comparables..."):
            # Geocode subject property if needed
            if subject_address and not manual_address:
                # Use existing coordinates
                selected_prop = next((p for p in all_props if p['address'] == subject_address), None)
                if selected_prop and selected_prop.get('latitude'):
                    subject_lat = selected_prop['latitude']
                    subject_lon = selected_prop['longitude']
                    st.success(f"✅ Using coordinates from database")
                else:
                    # Property exists but not geocoded yet
                    geocode_result = st.session_state.geocoder.geocode_with_quality(final_address)
                    if geocode_result['latitude']:
                        subject_lat = geocode_result['latitude']
                        subject_lon = geocode_result['longitude']
                        st.success(f"✅ Geocoded: {geocode_result['standardized_address']} (Quality: {geocode_result['quality']})")
                    else:
                        st.error(f"❌ Could not geocode subject property address: {final_address}")
                        st.info("💡 Try entering the address in a different format or check for typos")
                        st.stop()
            else:
                # Geocode manual address with enhanced fallback
                st.info(f"🔍 Geocoding address: {final_address}")

                geocode_result = st.session_state.geocoder.geocode_with_quality(final_address)

                if geocode_result['latitude']:
                    subject_lat = geocode_result['latitude']
                    subject_lon = geocode_result['longitude']

                    # Show standardization and quality info
                    st.success(f"✅ Successfully geocoded!")
                    st.info(f"**Standardized:** {geocode_result['standardized_address']}")
                    st.info(f"**Quality:** {geocode_result['quality'].upper()}")

                    if geocode_result['quality'] == 'city' or geocode_result['quality'] == 'zip':
                        st.warning(f"⚠️ Only {geocode_result['quality']}-level match found. Results may be less precise.")
                else:
                    st.error(f"❌ Could not geocode address: {final_address}")
                    st.info("💡 **Troubleshooting tips:**")
                    st.markdown("""
                    - Verify the address format: `123 Main Street, Durham, NC 27701`
                    - Check for typos in street name or city
                    - Try with just: `City, State ZIP` for city-level search
                    - Ensure the address exists in the Durham/Chapel Hill area
                    """)
                    st.stop()

            st.session_state.subject_coords = (subject_lat, subject_lon)

            # Build filters
            filters = {}

            if exact_match:
                if subject_beds > 0:
                    filters['bedrooms'] = subject_beds
                if subject_baths > 0:
                    filters['bathrooms'] = subject_baths

            if subject_sqft > 0:
                filters['sqft_min'] = subject_sqft - sqft_tolerance
                filters['sqft_max'] = subject_sqft + sqft_tolerance

            if year_built_min > 1900:
                filters['year_built_min'] = year_built_min
            if year_built_max < 2030:
                filters['year_built_max'] = year_built_max

            if status_filter:
                # For simplicity, just use first status
                # In production, would need to handle multiple
                filters['status'] = status_filter[0] if len(status_filter) == 1 else None

            # Save search parameters to session state for RentCast UI
            st.session_state.search_params = {
                'subject_lat': subject_lat,
                'subject_lon': subject_lon,
                'search_radius': search_radius,
                'filters': filters,
                'subject_beds': subject_beds,
                'subject_baths': subject_baths,
                'subject_sqft': subject_sqft
            }

            # Find comparables
            comparables = st.session_state.db.find_comparables(
                subject_lat,
                subject_lon,
                search_radius,
                filters
            )

            # Calculate effective rent for each comparable
            for comp in comparables:
                if comp.get('status') and 'vacant' in comp['status'].lower():
                    comp['rent'] = comp.get('market_rent', 0)
                    comp['rent_source'] = 'Market Rent (Vacant)'
                else:
                    comp['rent'] = comp.get('actual_rent', 0) or comp.get('market_rent', 0)
                    comp['rent_source'] = 'Actual Rent'

                comp['source'] = 'Internal'

            # Exclude subject property itself
            comparables = [c for c in comparables if c['address'] != final_address]

            # Merge internal and external comps
            all_comparables = comparables.copy()

            # Read external comps from session state
            external_comps = st.session_state.get('external_comps', [])

            if external_comps:
                # Normalize external comps format to match internal
                for ext_comp in external_comps:
                    ext_comp['rent'] = ext_comp.get('rent_price', 0)
                    ext_comp['rent_source'] = 'RentCast Market Data'
                    ext_comp['source'] = 'RentCast'

                all_comparables.extend(external_comps)
                all_comparables.sort(key=lambda x: x.get('distance_miles', 999))

            st.session_state.comparables = all_comparables

            # Summary
            internal_count = len(comparables)
            external_count = len(external_comps)
            if external_count > 0:
                st.success(f"✅ Total: {len(all_comparables)} comparables ({internal_count} internal + {external_count} RentCast)")
            else:
                st.success(f"✅ Found {internal_count} internal comparable properties")

    # RentCast External Data Section (outside Find Comparables button)
    # This section persists across button clicks using session state
    if st.session_state.search_params is not None:
        params = st.session_state.search_params

        st.markdown("---")
        st.markdown("### 🌐 External Market Data (RentCast)")

        # Check for cached data
        cached_external = st.session_state.db.find_external_comps(
            params['subject_lat'],
            params['subject_lon'],
            params['search_radius'],
            params['filters'],
            max_age_days=30,
            source='RentCast'
        )

        if cached_external:
            # Show cached data info
            age_days = int(cached_external[0].get('age_days', 0)) if cached_external[0].get('age_days') is not None else 0

            if age_days < 7:
                st.success(f"🟢 Found {len(cached_external)} cached RentCast comps (retrieved {age_days} days ago - fresh!)")
            elif age_days < 30:
                st.info(f"🟡 Found {len(cached_external)} cached RentCast comps (retrieved {age_days} days ago)")
            else:
                st.warning(f"🟠 Found {len(cached_external)} cached RentCast comps (retrieved {age_days} days ago - consider refreshing)")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Use Cached Data (free)", key="use_cached_btn"):
                    st.session_state.external_comps = cached_external
                    st.rerun()
            with col2:
                if st.button("🔄 Refresh from RentCast (1 API call)", key="refresh_btn"):
                    with st.spinner("Fetching fresh data from RentCast API..."):
                        try:
                            response = st.session_state.rentcast.get_rent_estimate(
                                latitude=params['subject_lat'],
                                longitude=params['subject_lon'],
                                bedrooms=int(params['subject_beds']) if params['subject_beds'] > 0 else None,
                                bathrooms=params['subject_baths'] if params['subject_baths'] > 0 else None,
                                sqft=params['subject_sqft'] if params['subject_sqft'] > 0 else None,
                                comp_count=25
                            )

                            normalized_comps = st.session_state.rentcast.normalize_comparables(response)
                            api_count = len(normalized_comps)
                            saved_count = st.session_state.db.save_external_comps(normalized_comps, source='RentCast')

                            st.session_state.external_comps = st.session_state.db.find_external_comps(
                                params['subject_lat'],
                                params['subject_lon'],
                                params['search_radius'],
                                params['filters'],
                                max_age_days=30,
                                source='RentCast'
                            )

                            # Show detailed fetch results
                            filtered_count = len(st.session_state.external_comps)
                            if saved_count > 0:
                                st.success(f"✅ Retrieved {api_count} RentCast comps from API")
                                st.info(f"💾 Saved {saved_count} new comps to database (rest were already cached)")
                            else:
                                st.info(f"✅ Retrieved {api_count} RentCast comps from API")
                                st.info(f"💡 All {api_count} comps were already in cache (no API quota used)")

                            if filtered_count < api_count:
                                st.info(f"📊 {filtered_count} match your search criteria ({params['search_radius']} mi radius, {params['subject_beds']}bd/{params['subject_baths']}ba)")

                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ RentCast API Error: {str(e)}")
                            st.session_state.external_comps = []
        else:
            # No cached data
            st.info("No cached RentCast data found for this area")

            if st.button("🔄 Fetch RentCast Comparables (1 API call)", key="fetch_new_btn"):
                with st.spinner("Fetching data from RentCast API..."):
                    try:
                        response = st.session_state.rentcast.get_rent_estimate(
                            latitude=params['subject_lat'],
                            longitude=params['subject_lon'],
                            bedrooms=int(params['subject_beds']) if params['subject_beds'] > 0 else None,
                            bathrooms=params['subject_baths'] if params['subject_baths'] > 0 else None,
                            sqft=params['subject_sqft'] if params['subject_sqft'] > 0 else None,
                            comp_count=25
                        )

                        normalized_comps = st.session_state.rentcast.normalize_comparables(response)
                        api_count = len(normalized_comps)
                        saved_count = st.session_state.db.save_external_comps(normalized_comps, source='RentCast')

                        st.session_state.external_comps = st.session_state.db.find_external_comps(
                            params['subject_lat'],
                            params['subject_lon'],
                            params['search_radius'],
                            params['filters'],
                            max_age_days=30,
                            source='RentCast'
                        )

                        # Show detailed fetch results
                        filtered_count = len(st.session_state.external_comps)
                        st.success(f"✅ Retrieved {api_count} RentCast comps from API")
                        st.info(f"💾 Saved {saved_count} new comps to database • 💡 These are cached for future use (free)")

                        if filtered_count < api_count:
                            st.info(f"📊 {filtered_count} match your search criteria ({params['search_radius']} mi radius, {params['subject_beds']}bd/{params['subject_baths']}ba)")

                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ RentCast API Error: {str(e)}")
                        if "not configured" in str(e):
                            st.info("💡 To use RentCast: Set RENTCAST_API_KEY environment variable. Get your free key at https://app.rentcast.io/app/api")
                        st.session_state.external_comps = []

        # Re-merge comparables when external comps change
        # This ensures the table updates after fetching RentCast data
        if st.session_state.get('comparables'):
            # Get current internal comps from session state
            current_comps = st.session_state.comparables
            internal_comps = [c for c in current_comps if c.get('source') != 'RentCast']

            # Get external comps
            external_comps = st.session_state.get('external_comps', [])

            # Rebuild merged list
            all_comparables = internal_comps.copy()

            if external_comps:
                # Normalize external comps
                for ext_comp in external_comps:
                    ext_comp['rent'] = ext_comp.get('rent_price', 0)
                    ext_comp['rent_source'] = 'RentCast Market Data'
                    ext_comp['source'] = 'RentCast'

                all_comparables.extend(external_comps)
                all_comparables.sort(key=lambda x: x.get('distance_miles', 999))

            # Update session state
            st.session_state.comparables = all_comparables

    # Display comparables
    if st.session_state.comparables:
        st.markdown("### 📋 Comparable Properties")

        # Create dataframe for display
        comp_data = []
        for idx, comp in enumerate(st.session_state.comparables):
            # Determine data source badge
            data_source = comp.get('source', 'Internal')
            if data_source == 'RentCast':
                source_badge = '🌐 RentCast'
            else:
                source_badge = '🏠 Internal'

            # Generate Zillow URL for this comparable
            comp_address = comp.get('address', '')
            comp_city = comp.get('city', '')
            comp_state = comp.get('state', '')
            comp_zip = comp.get('zip_code', '')
            zillow_url = generate_zillow_url(comp_address, comp_city, comp_state, comp_zip)

            comp_data.append({
                'Select': False,
                'Address': comp.get('address', 'N/A'),
                'Beds': comp.get('bedrooms', 'N/A'),
                'Baths': comp.get('bathrooms', 'N/A'),
                'Sqft': comp.get('sqft', 'N/A'),
                'Rent': f"${comp.get('rent', 0):,.2f}" if comp.get('rent') else 'N/A',
                'Zillow': zillow_url,
                'Source': source_badge,
                'Status': comp.get('status', 'N/A'),
                'Distance': f"{comp.get('distance_miles', 0):.2f} mi",
                'Index': idx
            })

        comp_df = pd.DataFrame(comp_data)

        # Display editable dataframe
        st.markdown("**Select comparables to include in your CMA report:**")

        edited_df = st.data_editor(
            comp_df[['Select', 'Address', 'Beds', 'Baths', 'Sqft', 'Rent', 'Zillow', 'Source', 'Status', 'Distance']],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "✓",
                    help="Select to include in CMA",
                    default=False,
                    width="small"
                ),
                "Address": st.column_config.TextColumn(
                    "Address",
                    width="medium"
                ),
                "Beds": st.column_config.NumberColumn(
                    "Beds",
                    width="small"
                ),
                "Baths": st.column_config.NumberColumn(
                    "Baths",
                    width="small"
                ),
                "Sqft": st.column_config.NumberColumn(
                    "Sqft",
                    width="small"
                ),
                "Rent": st.column_config.TextColumn(
                    "Rent",
                    width="small"
                ),
                "Zillow": st.column_config.LinkColumn(
                    "Zillow",
                    help="View property on Zillow",
                    display_text="🔍 View",
                    width="small"
                ),
                "Source": st.column_config.TextColumn(
                    "Source",
                    width="small"
                ),
                "Status": st.column_config.TextColumn(
                    "Status",
                    width="small"
                ),
                "Distance": st.column_config.TextColumn(
                    "Dist",
                    width="small"
                )
            }
        )

        # Get selected comparables
        selected_indices = edited_df[edited_df['Select'] == True].index.tolist()
        st.session_state.selected_comps = [st.session_state.comparables[i] for i in selected_indices]

        st.info(f"📌 {len(st.session_state.selected_comps)} comparables selected")

        # Generate report button
        if st.session_state.selected_comps:
            st.markdown("---")
            st.markdown("### 📊 Generate Report")

            col1, col2, col3 = st.columns(3)

            report_name = st.text_input(
                "Report Name",
                value=f"CMA_{final_address.split(',')[0]}_{datetime.now().strftime('%Y%m%d')}"
            )

            # Google Docs Export
            st.markdown("---")
            st.markdown("### 📝 Export to Google Docs")

            if GOOGLE_AUTH_AVAILABLE:
                # Initialize Google Auth
                if 'google_auth' not in st.session_state:
                    try:
                        google_client_id = os.getenv("GOOGLE_CLIENT_ID") or st.secrets.get("GOOGLE_CLIENT_ID", "")
                        google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or st.secrets.get("GOOGLE_CLIENT_SECRET", "")
                        google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI") or st.secrets.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")

                        if google_client_id and google_client_secret:
                            st.session_state.google_auth = Authenticate(
                                secret_credentials_path=None,
                                cookie_name='google_auth_cookie',
                                cookie_key='this_is_secret',
                                redirect_uri=google_redirect_uri,
                            )
                        else:
                            st.session_state.google_auth = None
                    except Exception as e:
                        st.session_state.google_auth = None
                        st.error(f"⚠️ Google OAuth initialization error: {e}")

                if st.session_state.get('google_auth') is None:
                    st.info("💡 Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable Google Docs export")
                else:
                    authenticator = st.session_state.google_auth

                    col_left, col_right = st.columns([3, 1])

                    with col_left:
                        if authenticator.check_authentification():
                            st.success(f"✅ Connected as {authenticator.get_username()}")

                            if st.button("📝 Create Google Doc", type="primary"):
                                try:
                                    # Prepare report data
                                    selected_comps = st.session_state.selected_comps
                                    rents_temp = [c.get('rent', 0) for c in selected_comps if c.get('rent')]

                                    if rents_temp:
                                        avg_rent = sum(rents_temp) / len(rents_temp)
                                        median_rent = sorted(rents_temp)[len(rents_temp) // 2]
                                        min_rent = min(rents_temp)
                                        max_rent = max(rents_temp)
                                        suggested_low = median_rent * 0.95
                                        suggested_high = median_rent * 1.05
                                    else:
                                        avg_rent = median_rent = min_rent = max_rent = suggested_low = suggested_high = 0

                                    cma_data = {
                                        'cma_name': report_name,
                                        'subject_address': final_address,
                                        'subject_beds': subject_beds,
                                        'subject_baths': subject_baths,
                                        'subject_sqft': subject_sqft,
                                        'rent_stats': {
                                            'avg_rent': avg_rent,
                                            'median_rent': median_rent,
                                            'min_rent': min_rent,
                                            'max_rent': max_rent,
                                            'suggested_low': suggested_low,
                                            'suggested_high': suggested_high
                                        },
                                        'comparables': selected_comps
                                    }

                                    with st.spinner("Uploading to Google Drive..."):
                                        # Generate HTML
                                        exports_dir = Path("exports")
                                        exports_dir.mkdir(exist_ok=True)
                                        html_path = exports_dir / f"{report_name}.html"

                                        # Create map if coords available
                                        if st.session_state.subject_coords:
                                            map_html = report_gen.create_map_html(
                                                final_address,
                                                st.session_state.subject_coords[0],
                                                st.session_state.subject_coords[1],
                                                selected_comps
                                            )
                                        else:
                                            map_html = None

                                        report_gen.generate_html(cma_data, str(html_path), map_html)

                                        # Upload to Drive
                                        credentials = authenticator.get_credentials()
                                        drive_exporter = GoogleDriveExporter(credentials)
                                        result = drive_exporter.upload_html_as_doc(
                                            str(html_path),
                                            f"{report_name} - CMA Report"
                                        )

                                        st.success("✅ Successfully uploaded to Google Drive!")
                                        st.markdown(f"**[📝 Open in Google Docs ↗]({result['web_view_link']})**")

                                except Exception as e:
                                    st.error(f"❌ Upload failed: {e}")
                        else:
                            st.info("🔐 Connect your Google account to export")
                            authenticator.login()

                    with col_right:
                        if authenticator.check_authentification():
                            if st.button("🚪 Logout"):
                                authenticator.logout()
                                st.rerun()
            else:
                st.warning("⚠️ Install `streamlit-google-auth` to enable Google Docs export")

            # Calculate statistics
            rents = [comp.get('rent', 0) for comp in st.session_state.selected_comps if comp.get('rent')]

            if rents:
                avg_rent = sum(rents) / len(rents)
                median_rent = sorted(rents)[len(rents) // 2]
                min_rent = min(rents)
                max_rent = max(rents)
                suggested_low = median_rent * 0.95
                suggested_high = median_rent * 1.05

                # Display statistics
                st.markdown("#### Rent Analysis")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Average Rent", f"${avg_rent:,.2f}")
                col2.metric("Median Rent", f"${median_rent:,.2f}")
                col3.metric("Min Rent", f"${min_rent:,.2f}")
                col4.metric("Max Rent", f"${max_rent:,.2f}")

                st.markdown(f"**Suggested Rent Range:** ${suggested_low:,.2f} - ${suggested_high:,.2f}")

                # Export buttons
                st.markdown("#### Export Options")

                col1, col2, col3 = st.columns(3)

                # Create export directory
                export_dir = Path("exports")
                export_dir.mkdir(exist_ok=True)

                # Prepare CMA data
                cma_data = {
                    'cma_name': report_name,
                    'subject_address': final_address,
                    'subject_beds': subject_beds,
                    'subject_baths': subject_baths,
                    'subject_sqft': subject_sqft,
                    'rent_stats': {
                        'avg_rent': avg_rent,
                        'median_rent': median_rent,
                        'min_rent': min_rent,
                        'max_rent': max_rent,
                        'suggested_low': suggested_low,
                        'suggested_high': suggested_high,
                        'comp_count': len(st.session_state.selected_comps)
                    },
                    'comparables': st.session_state.selected_comps
                }

                report_gen = st.session_state.report_generator

                with col1:
                    if st.button("📄 Export PDF"):
                        pdf_path = export_dir / f"{report_name}.pdf"
                        try:
                            report_gen.generate_pdf(cma_data, str(pdf_path))
                            st.success(f"✅ PDF saved to: {pdf_path}")

                            with open(pdf_path, 'rb') as f:
                                st.download_button(
                                    "⬇️ Download PDF",
                                    f,
                                    file_name=f"{report_name}.pdf",
                                    mime="application/pdf"
                                )
                        except Exception as e:
                            st.error(f"Error generating PDF: {e}")

                with col2:
                    if st.button("📊 Export Excel"):
                        excel_path = export_dir / f"{report_name}.xlsx"
                        try:
                            report_gen.generate_excel(cma_data, str(excel_path))
                            st.success(f"✅ Excel saved to: {excel_path}")

                            with open(excel_path, 'rb') as f:
                                st.download_button(
                                    "⬇️ Download Excel",
                                    f,
                                    file_name=f"{report_name}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                        except Exception as e:
                            st.error(f"Error generating Excel: {e}")

                with col3:
                    if st.button("🌐 Export HTML"):
                        html_path = export_dir / f"{report_name}.html"
                        try:
                            # Create map if coordinates available
                            if st.session_state.subject_coords:
                                subject_for_map = {
                                    'address': final_address,
                                    'latitude': st.session_state.subject_coords[0],
                                    'longitude': st.session_state.subject_coords[1]
                                }
                                map_html = report_gen.create_map(subject_for_map, st.session_state.selected_comps)
                            else:
                                map_html = None

                            report_gen.generate_html(cma_data, str(html_path), map_html)
                            st.success(f"✅ HTML saved to: {html_path}")

                            with open(html_path, 'r', encoding='utf-8') as f:
                                st.download_button(
                                    "⬇️ Download HTML",
                                    f,
                                    file_name=f"{report_name}.html",
                                    mime="text/html"
                                )
                        except Exception as e:
                            st.error(f"Error generating HTML: {e}")



# ============================================================================
# PAGE 3: View Properties (DEPRECATED - NOW IN DATA MANAGEMENT TAB 2 & 3)
# ============================================================================
# elif page == "📊 View Properties":
#     st.title("📊 View Properties Database")

