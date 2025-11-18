"""
Conversational AI/NLP Service using Google Gemini API
Simple, clean approach: Gemini handles chat, frontend handles routing logic
"""

import os
import logging
from django.core.cache import cache
import google.generativeai as genai
import json

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not set in environment variables")


class ConversationalAI:
    """
    Handles conversational interactions using Google Gemini API.
    Simple, focused approach without complex orchestration.
    """

    def __init__(self, user_id: int = None):
        """Initialize conversational AI for a user."""
        self.user_id = user_id
        
        # --- PROMPT FIX ---
        # The system prompt has been significantly improved to be more "strict"
        # about entity extraction. This will fix the parsing error.
        system_prompt = """You are SAHA-AI, a financial advisor assistant. Your primary role is to act as an intent-based router. 
You MUST extract key entities and understand user intent. You MUST respond in JSON. When providing an overview or details about a company, your response should be data-driven and include specific financial numbers and metrics where possible.

Your goal is to populate this JSON structure:
{
  "intent": "...",
  "entity": "...",
  "response": "..."
}

## INTENTS ##
- "analyze_stock": User wants a detailed financial analysis of a SPECIFIC stock, including metrics, buy/sell recommendations, and price targets.
- "analyze_mutual_fund": User wants a detailed financial analysis of a SPECIFIC mutual fund.
- "request_stock_name": User wants to analyze a stock but did NOT provide a name.
- "request_mutual_fund_name": User wants to analyze a fund but did NOT provide a name.
- "general_chat": All other messages, including greetings, general questions about financial concepts, or requests for an overview/information about a company (e.g., "tell me about Apple").

## ENTITY RULES (CRITICAL) ##
- The 'entity' MUST be ONLY the name of the stock or fund (e.g., "tata steel", "reliance industries").
- The 'entity' MUST NOT include command words like "analyze", "show me", "what about", etc.
- If no specific entity is mentioned, 'entity' MUST be null.

## RESPONSE GUIDELINES ##
- For 'general_chat' about a company, provide a concise overview with key financial figures (e.g., revenue, profit, key ratios). Be quantitative.

## EXAMPLES ##
- User: "hello"
  -> {"intent": "general_chat", "entity": null, "response": "Hello! How can I assist you with your investments today?"}
- User: "analyze tata steel"
  -> {"intent": "analyze_stock", "entity": "tata steel", "response": "Sure, one moment while I analyze Tata Steel..."}
- User: "Could you analyze Reliance Industries for me?"
  -> {"intent": "analyze_stock", "entity": "Reliance Industries", "response": "Certainly, analyzing Reliance Industries for you."}
- User: "give me an overview on tata steel"
  -> {"intent": "general_chat", "entity": "tata steel", "response": "Tata Steel, a major player in the global steel industry, reported a consolidated revenue of ₹2,43,959 crore for FY23. Their net profit stood at ₹8,760 crore. Key metrics include a P/E ratio of around 10.5 and a book value per share of ₹850."}
- User: "what is a p/e ratio?"
  -> {"intent": "general_chat", "entity": null, "response": "The Price-to-Earnings (P/E) ratio is a valuation metric that compares a company's current share price to its per-share earnings."}
- User: "I want to analyze a stock"
  -> {"intent": "request_stock_name", "entity": null, "response": "Of course. Which stock would you like me to analyze?"}
- User: "show me sbi magnum equity fund"
  -> {"intent": "analyze_mutual_fund", "entity": "sbi magnum equity fund", "response": "Got it. Looking up the SBI Magnum Equity Fund."}
- User: "what about hdfc"
  -> {"intent": "analyze_stock", "entity": "hdfc", "response": "Sure, pulling up the analysis for HDFC."}
"""
        
        # --- THE FIX ---
        # Using a model name confirmed to be in your API key's list.
        self.model = genai.GenerativeModel(
            'models/gemini-flash-latest',
            system_instruction=system_prompt
        )
        self.conversation_history = self._load_conversation_history()

    def _load_conversation_history(self):
        """Load conversation history from cache if exists."""
        if not self.user_id:
            return []
        
        cache_key = f"conversation_history_{self.user_id}"
        history = cache.get(cache_key, [])
        return history

    def _save_conversation_history(self):
        """Save conversation history to cache."""
        if not self.user_id:
            return
        
        cache_key = f"conversation_history_{self.user_id}"
        # Store the last 20 messages (10 user, 10 model)
        cache.set(cache_key, self.conversation_history[-20:], timeout=86400) # 24 hours

    def add_to_history(self, role: str, content: str):
        """Add a message to conversation history."""
        # Ensure role is 'user' or 'model' as required by Gemini
        valid_role = 'user' if role == 'user' else 'model'
        self.conversation_history.append({"role": valid_role, "content": content})
        self._save_conversation_history()

    def get_response(self, user_message: str) -> dict:
        """
        Get an AI response to a user message, including intent and entities.
        
        Args:
            user_message: The user's input message
            
        Returns:
            A dictionary with intent, entity, and AI response string.
        """
        if not GEMINI_API_KEY:
            return {
                "intent": "error",
                "entity": None,
                "response": "Error: Gemini API key not configured."
            }

        try:
            # Add user message to history *before* sending
            self.add_to_history('user', user_message)
            
            # --- IMPROVEMENT ---
            # Using the stateless `generate_content` is simpler and more
            # compatible with our manual cache/history management.
            
            # Build the history in the format required by the API
            messages = [
                {"role": msg["role"], "parts": [{"text": msg["content"]}]}
                for msg in self.conversation_history
            ]

            # Send the new message along with all history
            response = self.model.generate_content(
                messages,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1, # Lowered temperature for more precise JSON output
                    response_mime_type="application/json"
                )
            )

            if response.text:
                try:
                    # Clean the response text if it's wrapped in markdown backticks
                    cleaned_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
                    
                    parsed_response = json.loads(cleaned_text)
                    ai_text_response = parsed_response.get("response", cleaned_text)
                    
                    # Add AI response to history
                    self.add_to_history('model', ai_text_response)
                    return parsed_response
                
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON response from Gemini: {response.text}")
                    # Even if JSON fails, save the raw text response
                    self.add_to_history('model', response.text)
                    return {"intent": "general_chat", "entity": None, "response": response.text}
            else:
                # Handle cases where the response was blocked or empty
                logger.error("Empty response from Gemini API (possibly blocked)")
                self.add_to_history('model', "I'm sorry, I can't respond to that.")
                return {
                    "intent": "error",
                    "entity": None,
                    "response": "I'm sorry, I am unable to respond to that prompt."
                }

        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}")
            # Check for common API key or model name errors
            if "404" in str(e) or "not found" in str(e).lower():
                return {"intent": "error", "entity": None, "response": f"Error: The model '{self.model.model_name}' was not found. Please check the model name."}
            if "permission" in str(e).lower() or "api key" in str(e).lower():
                return {"intent": "error", "entity": None, "response": "Error: Invalid API Key or insufficient permissions."}
            
            # Handle other potential errors like blocking
            error_response = f"An unexpected error occurred: {str(e)}"
            if "block" in str(e).lower():
                error_response = "I'm sorry, I am unable to respond to that."
            
            return {"intent": "error", "entity": None, "response": error_response}

    def chat(self, user_message: str) -> dict:
        """Main chat method that returns user and assistant messages."""
        ai_response = self.get_response(user_message)
        return {
            "user_message": user_message,
            "ai_response": ai_response,
            "success": True
        }

    def clear_history(self):
        """Clear the conversation history for this user."""
        self.conversation_history = []
        if self.user_id:
            cache_key = f"conversation_history_{self.user_id}"
            cache.delete(cache_key) # <-- Fixed a typo here, was cache_cache

    def get_history(self):
        """Get the full conversation history."""
        return self.conversation_history