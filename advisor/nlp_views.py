"""
API endpoints for conversational AI chat functionality - SIMPLIFIED VERSION
Just Gemini + frontend routing. No complex orchestration.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import logging

from advisor.nlp_service import ConversationalAI
from .data_service import StockDataService as DataService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_message(request):
    """
    Simple chat endpoint. Gemini handles chat. Frontend handles routing.
    
    Request body:
    {
        "message": "hey what's up"
    }
    
    Response:
    {
        "success": true,
        "ai_response": "Gemini's response"
    }
    """
    try:
        message = request.data.get('message', '').strip()

        if not message:
            return Response(
                {"error": "Message cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get user ID for context
        user_id = request.user.id if request.user else None
        
        # Initialize Gemini conversational AI
        ai = ConversationalAI(user_id=user_id)
        
        # Get Gemini response
        response_data = ai.chat(message)
        gemini_response = response_data.get('ai_response', '')

        return Response({
            'success': True,
            'ai_response': gemini_response,
            'status': 'success'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in chat_message: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'status': 'error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def parse_intent(request):
    """
    Parse user intent from natural language input.
    Frontend uses this to decide: is this analysis? chat? portfolio?
    
    Request body:
    {
        "text": "analyze tata steel"
    }
    
    Response includes detected intent and confidence score.
    """
    try:
        text = request.data.get('text', '').strip()
        if not text:
            return Response({
                'intent': 'unknown',
                'confidence': 0,
                'message': 'No text provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Initialize NLU service
        data_service = DataService()
        
        # Detect intent using basic patterns
        intent, confidence, original_text = data_service.parse_intent(text)

        return Response({
            'intent': intent,
            'confidence': confidence,
            'original_text': original_text,
            'status': 'success'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error parsing intent: {str(e)}")
        return Response({
            'error': str(e),
            'status': 'error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def advisor_response(request):
    """
    Get a personalized advisor response for a user query.
    Falls back to Gemini if no specific context is available.
    
    Request body:
    {
        "question": "Should I buy reliance now?"
    }
    
    Response:
    {
        "response": "Advisor's response"
    }
    """
    try:
        question = request.data.get('question', '').strip()
        if not question:
            return Response({
                'response': 'Please ask a question',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

        user_id = request.user.id if request.user else None
        
        # Use Gemini for advisor response
        ai = ConversationalAI(user_id=user_id)
        response_data = ai.chat(question)
        advisor_response = response_data.get('ai_response', '')

        return Response({
            'response': advisor_response,
            'status': 'success'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in advisor_response: {str(e)}")
        return Response({
            'response': f'Error: {str(e)}',
            'status': 'error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
