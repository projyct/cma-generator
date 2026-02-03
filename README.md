# CMA Generator

A comprehensive tool for generating Comparative Market Analysis (CMA) reports based on AppFolio rent roll exports and market comparables.

## Features

- 📤 **Import AppFolio Rent Roll** - Automatically parse CSV exports
- 🗺️ **Automatic Geocoding** - Convert addresses to coordinates using OpenStreetMap
- 🔍 **Smart Comparable Search** - Find properties within custom radius with filters
- 📊 **Multiple Export Formats** - PDF, Excel, and interactive HTML reports
- 💾 **Historical Tracking** - Track rent changes over time
- 🎯 **Flexible Filtering** - Beds, baths, sqft, year built, property type, occupancy status
- 🗃️ **SQLite Database** - Local storage for all property data

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup Instructions

1. **Clone or download this repository**

```bash
cd CMA_Generator
```

2. **Install required packages**

```bash
pip install -r requirements.txt
```

3. **Configure environment variables** (optional)

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your email for geocoding:

```
GEOCODING_EMAIL=your_email@example.com
```

4. **Create necessary directories**

The app will automatically create these, but you can create them manually:

```bash
mkdir -p data exports
```

## Usage

### Starting the Application

Run the Streamlit app:

```bash
streamlit run app.py
```

The app will open in your default browser (typically at `http://localhost:8501`)

### Workflow

#### 1. Upload Rent Roll

- Navigate to **"📤 Upload Rent Roll"**
- Click "Choose rent roll CSV file" and select your AppFolio export
- Preview the data
- Click **"🔄 Parse and Import"**
- Wait for geocoding to complete (this respects rate limits - approximately 1 address per second)

**Note:** The first upload will take longer as all addresses need to be geocoded. Subsequent uploads will use cached coordinates.

#### 2. Generate CMA Report

- Navigate to **"🔍 Generate CMA"**
- Select or enter subject property address
- Enter property details (beds, baths, sqft)
- Set search radius (default 3 miles)
- Configure filters:
  - Square footage tolerance
  - Exact bed/bath match
  - Advanced filters (property type, year built, occupancy status)
- Click **"🔍 Find Comparables"**
- Review comparable properties in the table
- **Check the boxes** next to properties you want to include
- Enter a report name
- Click **"📄 Export PDF"**, **"📊 Export Excel"**, or **"🌐 Export HTML"**
- Download the generated report

#### 3. View Properties Database

- Navigate to **"📊 View Properties"**
- View all properties in your database
- Filter by city, status, or geocoding status
- Export filtered data to CSV

## File Structure

```
CMA_Generator/
├── app.py                  # Main Streamlit application
├── database.py             # SQLite database operations
├── parsers.py              # AppFolio CSV parser
├── geocoder.py             # Nominatim geocoding integration
├── reports.py              # PDF/Excel/HTML report generation
├── zillow_scraper.py       # Placeholder for Zillow integration
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .env                   # Your environment config (not in git)
├── .gitignore            # Git ignore rules
├── data/
│   └── cma_generator.db  # SQLite database (auto-created)
└── exports/              # Generated reports saved here
```

## AppFolio Export Format

The tool expects AppFolio rent roll CSV exports with the following structure:

- **Unit column** containing addresses in format: `-> ADDRESS - FULL_ADDRESS City, State Zip`
- **BD/BA column** in format: `3/2.50`
- **Sqft column** with square footage
- **Market Rent column** (for vacant units)
- **Rent column** (actual rent for occupied units)
- **Status column** (e.g., "Current", "Vacant-Unrented", "Notice", "Evict")

### Example Export Steps in AppFolio:

1. Go to **Reports** → **Rent Roll**
2. Select date range
3. Export to CSV
4. Save and upload to CMA Generator

## Rent Calculation Logic

The tool uses the following logic to determine comparable rent values:

- **Occupied units**: Uses actual rent charged
- **Vacant units**: Uses market rent
- The source is noted in the report for transparency

## Geocoding

The application uses **OpenStreetMap's Nominatim** service for geocoding:

- **Free** and open-source
- **Rate limited** to 1 request per second
- Coordinates are **cached** in the database
- Failed geocoding is logged but won't block import

### Geocoding Best Practices

- First import will be slow (1 address/second)
- Subsequent imports use cached coordinates
- Check "Geocoded" status in "View Properties" page
- Properties without coordinates won't appear in CMA searches

## Zillow Integration (Future)

The `zillow_scraper.py` module is a placeholder for future Zillow integration:

### Option 1: Zillow API
- Obtain API key from Zillow Bridge Interactive
- Add to `.env`: `ZILLOW_API_KEY=your_key_here`
- Implement API calls in `zillow_scraper.py`

### Option 2: Manual Import
- Export Zillow comparables to CSV
- Use `manual_import_csv()` function
- Required columns: address, city, state, zip_code, bedrooms, bathrooms, sqft, rent_price, date_closed

### Option 3: Web Scraping
- ⚠️ Check Zillow's Terms of Service
- Implement in `ZillowWebScraper` class
- Use respectful scraping practices

## Report Outputs

### PDF Report
- Professional formatted document
- Professional formatting
- Subject property details
- Rent analysis statistics
- Comparables table
- Disclaimer

### Excel Report
- **Summary sheet**: Subject property and rent analysis
- **Comparables sheet**: Full data table with all properties
- Formatted with colors and styling
- Ready for further analysis

### HTML Report
- Interactive web page
- Embedded map showing subject + comparables
- Responsive design
- Share-friendly format

## Troubleshooting

### Geocoding Fails
- Check internet connection
- Verify address format is correct
- Try manual geocoding at [OpenStreetMap](https://www.openstreetmap.org/)
- Check rate limiting (only 1 request per second allowed)

### No Comparables Found
- Increase search radius
- Reduce square footage tolerance
- Uncheck "Exact Bed/Bath Match Only"
- Check if properties have been geocoded

### Import Errors
- Verify CSV is from AppFolio rent roll export
- Check CSV encoding (should be UTF-8)
- Look for special characters in addresses
- Review error messages for specific issues

### Database Issues
- Database is stored in `data/cma_generator.db`
- To reset: delete the database file and restart app
- Backup before major operations

## Technical Details

### Database Schema

**properties table**
- Stores unique properties with geocoded coordinates
- Tracks beds, baths, sqft, property type, year built

**rent_history table**
- Historical rent data for each upload
- Links to properties via foreign key
- Tracks market rent, actual rent, occupancy status

**saved_cmas table**
- Stores generated CMA reports for reference
- Includes all search parameters and selected comps

**zillow_comps table**
- Cache for Zillow API results (when implemented)

### Dependencies

- **streamlit**: Web UI framework
- **pandas**: Data manipulation
- **plotly**: Interactive charts
- **reportlab**: PDF generation
- **openpyxl**: Excel generation
- **geopy**: Geocoding (Nominatim)
- **folium**: Interactive maps
- **requests**: HTTP requests
- **Pillow**: Image handling
- **python-dotenv**: Environment variables

## Development

### Adding Features

To add new features:

1. **Database changes**: Modify schema in `database.py`
2. **New filters**: Add to search form in `app.py`
3. **Report customization**: Edit templates in `reports.py`
4. **Additional data sources**: Implement in new module

### Contributing

For internal modifications:

1. Test changes with sample data first
2. Backup database before schema changes
3. Document new features in this README
4. Update requirements.txt if adding dependencies

## Support

For issues or questions:
- Check troubleshooting section above
- Review error messages carefully
- Check that all dependencies are installed
- Verify CSV format matches expected structure

## License

MIT License

## Version History

- **v1.0** - Initial release
  - AppFolio rent roll import
  - Geocoding with Nominatim
  - Comparable property search
  - PDF, Excel, HTML report generation
  - SQLite database storage
