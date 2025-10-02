# API Keys Setup Guide for SAHA-AI

This guide will help you configure API keys for real-time stock data in your SAHA-AI application.

## Required API Keys

### 1. Alpha Vantage API (Primary - Free Tier)
- **Website**: https://www.alphavantage.co/support/#api-key
- **Free Tier**: 5 API requests per minute, 500 requests per day
- **Registration**: Free account required
- **Best for**: US and international stocks

**Steps to get Alpha Vantage API Key:**
1. Visit https://www.alphavantage.co/support/#api-key
2. Fill out the form with your email and purpose
3. You'll receive your API key via email
4. Add it to your environment variables as `ALPHA_VANTAGE_API_KEY`

### 2. IEX Cloud API (Secondary - Free Tier)
- **Website**: https://iexcloud.io/
- **Free Tier**: 50,000 core data credits per month
- **Registration**: Free account required
- **Best for**: US stocks, real-time data

**Steps to get IEX Cloud API Key:**
1. Visit https://iexcloud.io/
2. Sign up for a free account
3. Go to your account dashboard
4. Copy your publishable token
5. Add it to your environment variables as `IEX_CLOUD_API_KEY`

### 3. Yahoo Finance (Fallback - No Key Required)
- **Website**: https://finance.yahoo.com/
- **Access**: Public API, no registration required
- **Limitations**: Rate limited, may be unreliable
- **Best for**: Backup data source

## Environment Variables Setup

### Local Development
1. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` and add your API keys:
   ```env
   ALPHA_VANTAGE_API_KEY=your_actual_api_key_here
   IEX_CLOUD_API_KEY=your_actual_iex_key_here
   ```

### Production Deployment

#### For Railway:
1. Go to your Railway project dashboard
2. Click on "Variables" tab
3. Add the following environment variables:
   - `ALPHA_VANTAGE_API_KEY` = your_actual_api_key_here
   - `IEX_CLOUD_API_KEY` = your_actual_iex_key_here

#### For Render:
1. Go to your Render service dashboard
2. Click on "Environment" tab
3. Add the following environment variables:
   - `ALPHA_VANTAGE_API_KEY` = your_actual_api_key_here
   - `IEX_CLOUD_API_KEY` = your_actual_iex_key_here

#### For Heroku:
1. Go to your Heroku app dashboard
2. Click on "Settings" tab
3. Click "Reveal Config Vars"
4. Add the following environment variables:
   - `ALPHA_VANTAGE_API_KEY` = your_actual_api_key_here
   - `IEX_CLOUD_API_KEY` = your_actual_iex_key_here

## Testing Your API Keys

After setting up your API keys, test them using the Django shell:

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Test Alpha Vantage
python manage.py shell -c "from advisor.data_service import stock_data_service; print('Alpha Vantage test:', stock_data_service._fetch_alpha_vantage('RELIANCE'))"

# Test IEX Cloud
python manage.py shell -c "from advisor.data_service import stock_data_service; print('IEX Cloud test:', stock_data_service._fetch_iex_cloud('RELIANCE'))"

# Test overall service
python manage.py shell -c "from advisor.data_service import stock_data_service; print('Stock price:', stock_data_service.get_stock_price('RELIANCE'))"
```

## API Usage Limits and Best Practices

### Alpha Vantage
- **Free Tier**: 5 requests/minute, 500 requests/day
- **Best Practice**: Cache results for 5+ minutes
- **Upgrade**: $25/month for 75 requests/minute, 30,000 requests/day

### IEX Cloud
- **Free Tier**: 50,000 core data credits/month
- **Best Practice**: Cache results for 1+ minute
- **Upgrade**: $9/month for 1M core data credits

### Caching Strategy
The application automatically caches API responses for 5 minutes to minimize API calls and stay within free tier limits.

## Troubleshooting

### Common Issues:

1. **"API key not found" error**
   - Check if environment variable is set correctly
   - Restart your application after setting environment variables

2. **"Rate limit exceeded" error**
   - Wait for the rate limit to reset
   - Implement better caching
   - Consider upgrading to paid tier

3. **"Invalid API key" error**
   - Verify the API key is correct
   - Check if the API key is active
   - Ensure no extra spaces or characters

4. **"No data returned" error**
   - Check if the stock symbol is correct
   - Verify the API service is working
   - Check API documentation for symbol format

### Testing Commands:

```bash
# Test environment variables
python manage.py shell -c "import os; print('Alpha Vantage Key:', 'SET' if os.getenv('ALPHA_VANTAGE_API_KEY') else 'NOT SET')"

# Test API connectivity
python manage.py shell -c "from advisor.data_service import stock_data_service; print('Market indices:', stock_data_service.get_market_indices())"
```

## Production Recommendations

1. **Monitor API Usage**: Keep track of your API usage to avoid hitting limits
2. **Implement Fallbacks**: The app has multiple fallback mechanisms
3. **Cache Aggressively**: Cache results for longer periods in production
4. **Error Handling**: The app gracefully handles API failures
5. **Upgrade When Needed**: Consider paid tiers for high-traffic applications

## Support

If you encounter issues:
1. Check the API provider's documentation
2. Verify your API key is active
3. Test with a simple API call
4. Check the application logs for detailed error messages
