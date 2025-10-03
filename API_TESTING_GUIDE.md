# Stock Market Chatbot API Testing Guide

## Overview
This guide provides comprehensive testing instructions for the Stock Market Chatbot API using Postman and manual testing methods.

## Prerequisites
1. Django development server running on `http://localhost:8000`
2. Postman installed
3. User account created for testing

## Postman Setup

### 1. Import Collection
- Import the `postman_collection.json` file into Postman
- The collection includes all API endpoints organized by functionality

### 2. Environment Variables
Set up the following environment variables in Postman:
- `base_url`: `http://localhost:8000`
- `auth_token`: (will be set after login)
- `stock_query`: `RELIANCE`
- `mf_query`: `HDFC`
- `ticker`: `RELIANCE`
- `buy_price`: `2500`
- `shares`: `10`
- `scheme_id`: `HDFC002`
- `buy_nav`: `75.50`
- `units`: `100`
- `category`: `Large Cap`

## Testing Workflow

### Phase 1: Authentication Testing
1. **Register New User**
   - Endpoint: `POST /users/register/`
   - Test with valid user data
   - Verify successful registration

2. **Login**
   - Endpoint: `POST /users/login/`
   - Test with registered credentials
   - Save auth token for subsequent requests

### Phase 2: Market Data Testing
1. **Market Snapshot**
   - Endpoint: `GET /advisor/market/snapshot/`
   - Verify NIFTY, SENSEX, BANKNIFTY data
   - Check market status

2. **Stock Search**
   - Test NSE search: `GET /advisor/search/NSE/RELIANCE`
   - Test BSE search: `GET /advisor/search/BSE/TCS`
   - Verify search results format

3. **Stock Analysis**
   - Endpoint: `GET /advisor/analyze/RELIANCE/2500/10`
   - Verify analysis data and recommendations

4. **Stock History**
   - Endpoint: `GET /advisor/history/RELIANCE/?period=1y`
   - Check historical data format

### Phase 3: Mutual Fund Testing
1. **Get All Mutual Funds**
   - Endpoint: `GET /advisor/mutual-fund/`
   - Verify fund list with all details

2. **Get Categories**
   - Endpoint: `GET /advisor/mutual-fund/categories/`
   - Verify available categories

3. **Search Mutual Funds**
   - Endpoint: `GET /advisor/search/MF/HDFC`
   - Test search functionality

4. **Fund Details**
   - Endpoint: `GET /advisor/mutual-fund/HDFC002/`
   - Verify detailed fund information

5. **Fund Analysis**
   - Endpoint: `GET /advisor/analyze_mf/HDFC002/75.50/100`
   - Check analysis results

6. **Fund History**
   - Endpoint: `GET /advisor/history_mf/HDFC002/?period=1y`
   - Verify NAV history

### Phase 4: Portfolio Management Testing
1. **Add to Portfolio**
   - Endpoint: `POST /advisor/portfolio/`
   - Add test holdings
   - Verify successful addition

2. **Get Portfolio**
   - Endpoint: `GET /advisor/portfolio/`
   - Verify holdings list

3. **Portfolio Details**
   - Endpoint: `GET /advisor/portfolio/details/`
   - Check current values and P&L

4. **Portfolio Health**
   - Endpoint: `GET /advisor/portfolio/health/`
   - Verify health analysis

5. **Remove from Portfolio**
   - Endpoint: `DELETE /advisor/portfolio/`
   - Test removal functionality

### Phase 5: Chat & AI Testing
1. **Parse Intent**
   - Endpoint: `POST /advisor/parse/`
   - Test various queries
   - Verify intent detection

2. **Chat**
   - Endpoint: `POST /advisor/chat/`
   - Test conversational AI
   - Verify responses

## Test Cases

### Positive Test Cases
1. Valid authentication
2. Successful stock search
3. Proper mutual fund data retrieval
4. Portfolio operations
5. Chat functionality

### Negative Test Cases
1. Invalid authentication
2. Non-existent stock symbols
3. Invalid mutual fund scheme IDs
4. Unauthorized portfolio access
5. Malformed requests

### Edge Cases
1. Empty search queries
2. Special characters in search
3. Large portfolio datasets
4. Network timeout scenarios

## Expected Response Formats

### Market Data
```json
{
  "indices": [
    {
      "name": "NIFTY",
      "price": 24836.30,
      "change": 225.20,
      "change_percent": 0.92
    }
  ],
  "market_status": {
    "status": "open",
    "message": "Market is LIVE"
  }
}
```

### Mutual Fund Data
```json
{
  "funds": [
    {
      "scheme_id": "HDFC002",
      "fund_name": "HDFC Top 100 Fund",
      "nav": 78.45,
      "change": -0.12,
      "change_pct": -0.15,
      "category": "Large Cap",
      "amc": "HDFC Mutual Fund",
      "aum": "₹12,456 Cr",
      "expense_ratio": 1.15,
      "min_sip": 500,
      "min_lumpsum": 5000
    }
  ]
}
```

### Portfolio Data
```json
{
  "holdings": [
    {
      "ticker": "RELIANCE",
      "quantity": 10,
      "average_buy_price": 2500.00,
      "current_price": 2550.00,
      "current_value": 25500.00,
      "net_profit": 500.00
    }
  ],
  "total_invested": 25000.00,
  "total_current_value": 25500.00,
  "net_profit": 500.00
}
```

## Performance Testing
1. Response time < 2 seconds for all endpoints
2. Concurrent user testing
3. Database query optimization
4. Cache effectiveness

## Security Testing
1. Authentication token validation
2. CSRF protection
3. Input sanitization
4. SQL injection prevention

## Deployment Testing Checklist
- [ ] All endpoints responding correctly
- [ ] Authentication working
- [ ] Data validation implemented
- [ ] Error handling proper
- [ ] Performance acceptable
- [ ] Security measures active
- [ ] Database connections stable
- [ ] Cache functioning
- [ ] Logging implemented

## Troubleshooting

### Common Issues
1. **Authentication Errors**: Check token format and expiration
2. **Data Not Found**: Verify symbol/scheme ID exists
3. **Slow Responses**: Check cache configuration
4. **CORS Issues**: Verify Django CORS settings

### Debug Steps
1. Check Django logs
2. Verify database connections
3. Test individual endpoints
4. Check environment variables
5. Validate request formats

## Contact
For issues or questions, refer to the application logs and Django admin panel.
