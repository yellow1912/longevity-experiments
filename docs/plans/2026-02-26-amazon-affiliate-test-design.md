# Amazon Affiliate API Test Script Design

**Date:** 2026-02-26
**Purpose:** Test Amazon Product Advertising API credentials and pull supplement product data
**Target:** Simple Python test script for longevity/health affiliate website

## Overview

Create a Python test script that verifies Amazon affiliate credentials work correctly and retrieves supplement product data from the Product Advertising API 5.0. This is the foundation for a future affiliate website that will store product data in a database.

### Goals
- Verify API credentials are valid and working
- Pull sample supplement/vitamin product data
- Display product information including affiliate links
- Provide foundation for future database integration

### Non-Goals
- Database integration (future phase)
- Web scraping or alternative data sources
- Full website implementation
- Automated data synchronization

## Architecture

### Selected Approach
**Official Amazon PA-API SDK** (`paapi5-python-sdk`)

**Rationale:**
- Official support from Amazon
- Complete feature set for production use
- Well-documented with type hints
- Best long-term maintainability for scaling to full website
- Better error handling than alternatives

### Project Structure
```
longevity-experiments/
├── Longevity-credentials.csv      # API credentials (gitignored)
├── test_amazon_api.py             # Main test script
├── requirements.txt               # Python dependencies
├── .gitignore                     # Ignore credentials and env files
└── docs/
    └── plans/
        └── 2026-02-26-amazon-affiliate-test-design.md
```

## Components

### 1. Credential Loader (`load_credentials()`)
Reads and parses the CSV credentials file.

**Input:** `Longevity-credentials.csv` file path
**Output:** Dictionary with `partner_tag`, `access_key`, `secret_key`
**Error Handling:** File not found, parsing errors, missing fields

### 2. API Client Initializer (`initialize_api_client()`)
Sets up the PA-API client with credentials.

**Configuration:**
- Partner Tag: `longevityhe09-20.longevity`
- Access Key: From CSV (Credential Id)
- Secret Key: From CSV (Secret)
- Region: US (amazon.com marketplace)
- API Version: 5.0

**Output:** Configured API client instance

### 3. Product Search (`search_supplements()`)
Performs SearchItems operation for supplements.

**Parameters:**
- `keyword`: Search term (default: "vitamin D supplement")
- `item_count`: Number of results (default: 10)

**Requested Resources:**
- `Images.Primary.Large` - Product images
- `ItemInfo.Title` - Product names
- `ItemInfo.Features` - Product descriptions
- `Offers.Listings.Price` - Pricing information
- `ItemInfo.ByLineInfo` - Brand information
- `BrowseNodeInfo.BrowseNodes` - Categories

**Output:** Raw API response with product items

### 4. Data Formatter (`format_product_data()`)
Transforms API response into readable format.

**Extracted Fields:**
- ASIN (Amazon Standard Identification Number)
- Product title
- Brand
- Price (with currency)
- Star rating and review count
- Affiliate URL (with partner tag)
- Primary image URL
- Key features (first 3)

**Output:** List of formatted product dictionaries

### 5. Main Orchestrator (`main()`)
Coordinates the entire workflow.

**Flow:**
1. Load credentials from CSV
2. Initialize API client
3. Search for supplements
4. Format results
5. Display to console

## Data Flow

### Authentication Process
```
CSV File → Parse Credentials → PA-API Client Configuration
   ↓
Partner Tag: longevityhe09-20.longevity
Access Key: 8mb4mfke5vjebkutlvctlbqjo
Secret Key: e9vjh8ogigqiqh8ek0ftg7prakk02kfntjnjv9mnrhim6k5akb
Region: US
```

### Request Flow
```
Python Script
    ↓
SearchItems API Call
    - Keywords: "vitamin D supplement"
    - ItemCount: 10
    - Resources: [Images, ItemInfo, Offers]
    - PartnerTag: longevityhe09-20.longevity
    ↓
Amazon PA-API 5.0
    ↓
JSON Response
    - SearchResult.Items[]
    - Each item with ASIN, title, price, images, etc.
    ↓
Parse & Format
    ↓
Console Output (formatted product list)
```

### Response Data Structure
Each product item contains:
- **ASIN**: Unique product identifier
- **DetailPageURL**: Affiliate link with partner tag embedded
- **ItemInfo**: Title, brand, features, product group
- **Offers**: Pricing, savings, availability, condition
- **Images**: Product photos in various sizes

## Error Handling

### Credential Errors
- **Missing CSV file**: Display file path error, guide to correct location
- **Invalid credentials**: Show authentication failure message
- **Malformed CSV**: Report parsing error with line number

### API Errors
- **TooManyRequests** (429): Rate limiting, suggest waiting 1 second and retry
- **InvalidPartnerTag**: Check affiliate account approval status
- **Unauthorized** (401): Invalid or expired credentials
- **No results found**: Inform user, suggest alternative keywords
- **Network timeout**: Connection error handling with retry suggestion

### Data Parsing Errors
- **Missing fields**: Use defaults or skip individual item
- **Malformed response**: Log error, continue processing other items
- **Image URL not available**: Mark as "No image"
- **Price not available**: Show "Price unavailable"

### Error Handling Strategy
- Use try-except blocks around all API calls
- Provide clear, actionable error messages
- Graceful degradation (don't crash on single item failures)
- Log errors for debugging without exposing sensitive data

## Testing & Verification

### Installation Verification
```bash
pip install -r requirements.txt
pip show paapi5-python-sdk
```

### Success Criteria
✓ Script runs without crashes
✓ Credentials load successfully from CSV
✓ API authentication succeeds
✓ Returns 5-10 supplement products
✓ Each product displays:
  - Title
  - Price
  - Star rating
  - Affiliate link with correct partner tag
  - At least one image URL
✓ Affiliate URLs contain `longevityhe09-20`

### Running the Test
```bash
python test_amazon_api.py
```

**Expected Output:**
```
Loading credentials...
Initializing Amazon PA-API client...
Searching for supplements...

Found 10 products:

1. Vitamin D3 5000 IU - Brand Name
   Price: $19.99
   Rating: 4.5 stars (2,341 reviews)
   ASIN: B01234ABCD
   Link: https://www.amazon.com/dp/B01234ABCD?tag=longevityhe09-20
   Image: https://m.media-amazon.com/images/I/...

[... 9 more products ...]

Test completed successfully!
```

### Validation Checks
1. **Credential parsing**: No errors loading CSV
2. **API connection**: Successful authentication
3. **Data retrieval**: Non-empty results
4. **Affiliate tagging**: Partner tag present in all URLs
5. **Data completeness**: All expected fields populated

## Future Considerations

### Database Integration (Next Phase)
- Choose database (PostgreSQL, MySQL, MongoDB)
- Design product schema
- Add data persistence layer
- Implement update/sync logic

### Rate Limiting
- PA-API has usage limits (check affiliate account tier)
- Implement request throttling for production
- Add caching to reduce API calls

### Product Categories
- Expand beyond vitamin D to other supplements
- Add category-based searches
- Support multiple search terms

### Monitoring
- Log API usage and errors
- Track successful vs failed requests
- Monitor affiliate link click-through (Amazon reports)

## Dependencies

```
paapi5-python-sdk>=1.3.0
```

## Security Considerations

- **Never commit credentials**: Add CSV file to `.gitignore`
- **Environment variables**: Consider moving to `.env` for production
- **Secret rotation**: API secrets should be rotated periodically
- **Access control**: Restrict file permissions on credentials file

## References

- [Amazon Product Advertising API Documentation](https://webservices.amazon.com/paapi5/documentation/)
- [paapi5-python-sdk GitHub](https://github.com/seratch/paapi5-python-sdk)
- PA-API Version: 2.1 (from credentials file)
