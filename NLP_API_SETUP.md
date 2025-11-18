# SAHA-AI Conversational NLP Integration Guide

## Overview

Your SAHA-AI application now includes a sophisticated **Conversational AI** system powered by **Google Gemini API**. This enables agentic, context-aware conversations for financial advice and portfolio analysis.

## Architecture

### Components

1. **NLP Service** (`advisor/nlp_service.py`)
   - `ConversationalAI`: Core class for conversational interactions
   - `FinancialAdvisor`: Specialized financial advisory wrapper
   - Handles conversation history, context management, and message detection

2. **API Endpoints** (`advisor/nlp_views.py`)
   - Chat endpoints for conversational interactions
   - Financial advisor queries
   - Question type detection
   - Conversation history management

3. **URL Routes** (`advisor/urls.py`)
   - `/api/nlp/chat/` - Send chat messages
   - `/api/nlp/history/` - Retrieve conversation history
   - `/api/nlp/history/clear/` - Clear conversation history
   - `/api/nlp/advisor/` - Financial advisor queries
   - `/api/nlp/detect/` - Detect question type

## Setup

### 1. Get Google Gemini API Key

1. Visit: https://aistudio.google.com/apikey
2. Create a new API key (no payment required - free tier)
3. Copy your API key

### 2. Configure Environment Variable

Add to your `.env` file or system environment variables:

```bash
GEMINI_API_KEY=your_api_key_here
```

On Windows PowerShell:
```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

On Windows CMD:
```cmd
set GEMINI_API_KEY=your_api_key_here
```

### 3. Restart Django Server

```bash
python manage.py runserver
```

## API Usage

### 1. Send a Chat Message

**Endpoint:** `POST /api/nlp/chat/`

**Authentication:** Required (IsAuthenticated)

**Request Body:**
```json
{
    "message": "What are the latest market trends?",
    "include_context": true
}
```

**Response:**
```json
{
    "success": true,
    "user_message": "What are the latest market trends?",
    "ai_response": "Based on current market data...",
    "timestamp": "2025-11-13 19:55:00"
}
```

**Example (Python):**
```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}
data = {
    "message": "Should I invest in AAPL or MSFT?",
    "include_context": True
}

response = requests.post(
    "http://localhost:8000/api/nlp/chat/",
    json=data,
    headers=headers
)
print(response.json())
```

### 2. Get Conversation History

**Endpoint:** `GET /api/nlp/history/`

**Authentication:** Required

**Response:**
```json
{
    "success": true,
    "history": [
        {
            "role": "user",
            "content": "What is diversification?"
        },
        {
            "role": "assistant",
            "content": "Diversification is an investment strategy..."
        }
    ],
    "message_count": 2
}
```

### 3. Clear Conversation History

**Endpoint:** `POST /api/nlp/history/clear/`

**Authentication:** Required

**Response:**
```json
{
    "success": true,
    "message": "Conversation history cleared"
}
```

### 4. Financial Advisor Query

**Endpoint:** `POST /api/nlp/advisor/`

**Authentication:** Required

**Request Body (Multiple Options):**

**Option A: Stock Analysis**
```json
{
    "query": "Is AAPL a good buy now?",
    "ticker": "AAPL"
}
```

**Option B: Portfolio Suggestion**
```json
{
    "portfolio_summary": "I own 10 shares of AAPL, 5 shares of MSFT",
    "goals": "Long-term growth with moderate risk"
}
```

**Option C: General Market Insight**
```json
{
    "query": "What do you think about the current bull market?"
}
```

**Response:**
```json
{
    "success": true,
    "query": "Is AAPL a good buy now?",
    "advice": "Apple (AAPL) is a strong company...",
    "timestamp": "2025-11-13 19:55:00"
}
```

### 5. Detect Question Type

**Endpoint:** `POST /api/nlp/detect/`

**Authentication:** Required

**Request Body:**
```json
{
    "message": "I own AAPL and MSFT, should I diversify?"
}
```

**Response:**
```json
{
    "success": true,
    "message": "I own AAPL and MSFT, should I diversify?",
    "is_portfolio_question": true,
    "is_market_question": false,
    "is_stock_question": true,
    "timestamp": "2025-11-13 19:55:00"
}
```

## Frontend Implementation Example

### React Component

```jsx
import React, { useState, useEffect } from 'react';

export function ChatBot() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    const sendMessage = async () => {
        if (!input.trim()) return;

        setLoading(true);
        try {
            const response = await fetch('/api/nlp/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({
                    message: input,
                    include_context: true,
                }),
            });

            const data = await response.json();
            
            if (data.success) {
                setMessages([
                    ...messages,
                    { role: 'user', content: data.user_message },
                    { role: 'assistant', content: data.ai_response }
                ]);
                setInput('');
            }
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-container">
            <div className="messages">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`message ${msg.role}`}>
                        {msg.content}
                    </div>
                ))}
            </div>
            <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="Ask a financial question..."
            />
            <button onClick={sendMessage} disabled={loading}>
                {loading ? 'Sending...' : 'Send'}
            </button>
        </div>
    );
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
```

### JavaScript (Vanilla)

```javascript
async function sendChatMessage(message) {
    const response = await fetch('/api/nlp/chat/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
        body: JSON.stringify({
            message: message,
            include_context: true,
        }),
    });

    const data = await response.json();
    return data.ai_response;
}

// Usage
sendChatMessage("What's your opinion on tech stocks?").then(response => {
    console.log(response);
});
```

## Model Information

### Gemini 2.5 Flash

- **Cost**: Completely free (generous rate limits)
- **Token Window**: 1 million tokens
- **Performance**: Excellent for conversational AI
- **Speed**: Fast response times
- **Best For**: Agentic AI, real-time conversations

## Features

### Conversation Context Management

- Maintains last 10 exchanges per user
- Cached for 24 hours
- User-specific conversation history
- Automatic context pruning for performance

### Question Type Detection

- **Portfolio Questions**: Identifies portfolio-related queries
- **Market Questions**: Detects market trend inquiries
- **Stock Questions**: Recognizes specific stock symbols

### System Prompts

The AI is configured with specialized financial advisory prompts including:
- Investment analysis capabilities
- Market sentiment understanding
- Portfolio optimization guidance
- Risk management advice
- Complex financial concept explanations

## Limitations & Considerations

1. **API Rate Limits**
   - Free tier: 1,500 requests per minute (shared across all endpoints)
   - Use caching where appropriate

2. **Conversation History**
   - Stored in cache (not permanent database)
   - Clears after 24 hours
   - Per-user (not shared)

3. **API Key Security**
   - NEVER hardcode API key in source code
   - Use environment variables only
   - Regenerate if compromised

4. **Response Quality**
   - AI may not have real-time market data
   - Always recommend consulting qualified advisors
   - Model limitations acknowledged in responses

## Troubleshooting

### "GEMINI_API_KEY not set"

**Problem**: System warning about missing API key

**Solution**:
1. Create API key at https://aistudio.google.com/apikey
2. Set environment variable
3. Restart Django server

```bash
# Linux/Mac
export GEMINI_API_KEY="your_key"
python manage.py runserver

# Windows PowerShell
$env:GEMINI_API_KEY="your_key"
python manage.py runserver
```

### ModuleNotFoundError: google.generativeai

**Problem**: Package not installed

**Solution**:
```bash
pip install google-generativeai==0.8.3
```

### 401 Unauthorized

**Problem**: API key invalid

**Solution**:
1. Verify API key at https://aistudio.google.com/api-keys
2. Check if key is correctly set in environment
3. Regenerate new key if needed

### Empty Responses

**Problem**: AI returning empty or error responses

**Solution**:
1. Check API rate limits
2. Verify API key has no usage restrictions
3. Check Django logs for detailed errors
4. Ensure message is not empty

## Cost Analysis

### Current Setup (Free Tier)

- ✅ **No costs** for conversational AI
- ✅ 1,500 requests per day (approximate)
- ✅ Full access to Gemini 2.5 Flash
- ✅ Unlimited conversation history per user (24 hours)

### Future Scaling (Paid Tier)

When exceeding free tier limits:
- **Gemini 2.5 Flash**: $0.30/1M input tokens, $2.50/1M output tokens
- **Gemini 2.0 Flash**: $0.10/1M input, $0.40/1M output
- **Gemini 2.5 Flash-Lite**: $0.10/1M input, $0.40/1M output (most cost-effective)

## Next Steps

1. ✅ Add chat UI to dashboard
2. ✅ Integrate with portfolio data
3. ✅ Add real-time market data context
4. ✅ Implement conversation analytics
5. ✅ Add user preferences & chat settings

## Support & Resources

- **Gemini API Docs**: https://ai.google.dev/gemini-api/docs
- **API Reference**: https://ai.google.dev/api
- **Cookbook & Examples**: https://github.com/google-gemini/cookbook
- **Community**: https://discuss.ai.google.dev/c/gemini-api/

## Testing the API

### Using cURL

```bash
# Set your API key first
$apiKey = "your_key"

# Test chat endpoint
curl -X POST http://localhost:8000/api/nlp/chat/ `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" `
  -d '{
    "message": "What is a good investment strategy?",
    "include_context": true
  }'
```

### Using Postman

1. Set method to `POST`
2. URL: `http://localhost:8000/api/nlp/chat/`
3. Headers:
   - `Content-Type: application/json`
   - `Authorization: Bearer YOUR_TOKEN`
4. Body (JSON):
   ```json
   {
       "message": "Your question here",
       "include_context": true
   }
   ```

---

**Last Updated**: November 13, 2025
**Version**: 1.0
**Status**: Production Ready
