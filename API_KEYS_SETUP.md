# API Keys Setup Guide

## Where to Put API Keys

All API keys should be set as **environment variables** in your system. The application will automatically read them.

### Option 1: Create a `.env` file (Recommended for Development)

Create a `.env` file in the project root directory (`/Users/akshit/Documents/Codes/saha-ai/.env`) with the following content:

```bash
# Finnhub API Key (Optional - for stock data fallback)
# Get your free API key from: https://finnhub.io/register
FINNHUB_API_KEY=your_finnhub_api_key_here

# MFapi Key (Optional - for mutual fund data fallback)
# Get your API key from: https://www.mfapi.in/
MFAPI_KEY=your_mfapi_key_here

# Gemini API Key (Optional - for NLP and general conversation only)
# Get your API key from: https://makersuite.google.com/app/apikey
# NOTE: Gemini is STRICTLY used only for general queries like "hi", "what can you do", etc.
# It is NEVER used for financial queries or data.
GEMINI_API_KEY=your_gemini_api_key_here
```

### Option 2: Set Environment Variables in Your Shell

**For macOS/Linux:**
```bash
export FINNHUB_API_KEY="your_finnhub_api_key_here"
export MFAPI_KEY="your_mfapi_key_here"
export GEMINI_API_KEY="your_gemini_api_key_here"
```

**For Windows (PowerShell):**
```powershell
$env:FINNHUB_API_KEY="your_finnhub_api_key_here"
$env:MFAPI_KEY="your_mfapi_key_here"
$env:GEMINI_API_KEY="your_gemini_api_key_here"
```

## API Priority and Usage

### Stocks
1. **Primary:** Yahoo Finance (No API key required - FREE)
2. **Fallback:** Finnhub API (Requires API key - FREE tier available)

### Mutual Funds
1. **Primary:** Yahoo Finance (No API key required - FREE)
2. **Fallback:** MFapi (Requires API key)

### Gemini (NLP Only)
- **Usage:** STRICTLY for general non-financial queries only
- **Examples:** "hi", "hello", "what can you do", "help", "thanks"
- **NOT Used For:** Any financial queries, stock analysis, portfolio data, market data
- **Note:** If you don't set this key, the app will use rule-based responses for general queries

## Getting API Keys

### Finnhub API Key
1. Visit: https://finnhub.io/register
2. Sign up for a free account
3. Go to your dashboard
4. Copy your API key
5. Set it as `FINNHUB_API_KEY` environment variable

### MFapi Key
1. Visit: https://www.mfapi.in/
2. Sign up for an account
3. Get your API key from the dashboard
4. Set it as `MFAPI_KEY` environment variable

### Gemini API Key
1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Create a new API key
4. Set it as `GEMINI_API_KEY` environment variable

## Important Notes

- **Yahoo Finance is the primary API** for both stocks and mutual funds - it's free and doesn't require an API key
- **Fallback APIs are optional** - the app will work without them, but may have reduced reliability
- **Gemini is completely optional** - the app works fine without it using rule-based responses
- **Never commit your `.env` file** to version control - it should be in `.gitignore`

## Verification

After setting up your API keys, restart your Django development server:

```bash
python manage.py runserver
```

The application will log which APIs are configured when it starts. Check the console output for messages like:
- "Finnhub API: Configured" or "Finnhub API: Not configured (optional fallback)"
- "MFapi: Configured" or "MFapi: Not configured (optional fallback)"

