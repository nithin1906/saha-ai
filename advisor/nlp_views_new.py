"""
API endpoints for conversational AI chat functionality
Simple marker-based redirection (no function calling complexity)
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import logging
import re

from advisor.nlp_service import ConversationalAI
from .data_service import StockDataService as DataService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_message(request):
    """
    Handle chat messages with Gemini, using its intent parsing capabilities.
    """
    try:
        message = request.data.get('message', '').strip()
        if not message:
            return Response(
                {"error": "Message cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Initialize conversational AI to get structured response
        ai = ConversationalAI(user_id=request.user.id)
        gemini_result = ai.get_response(message)

        intent = gemini_result.get('intent', 'general_chat')
        entity = gemini_result.get('entity')

        # Default response values
        has_redirection = False
        redirection_type = 'none'
        redirection_target = None
        response_data = gemini_result  # By default, return the whole object

        if intent == 'analyze_stock' and entity:
            has_redirection = True
            redirection_type = 'stock'
            redirection_target = entity
            response_data = f"Looking up stock \"{entity}\"..."  # For redirection, a simple string is fine

        elif intent == 'analyze_mutual_fund' and entity:
            has_redirection = True
            redirection_type = 'mutual_fund'
            redirection_target = entity
            response_data = f"Analyzing mutual fund: \"{entity}\"..."  # For redirection, a simple string is fine

        return Response({
            "success": True,
            "user_message": message,
            "ai_response": response_data,
            "has_redirection": has_redirection,
            "redirection_type": redirection_type,
            "redirection_target": redirection_target,
            "timestamp": str(__import__('datetime').datetime.now())
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in chat_message: {str(e)}")
        return Response(
            {"error": f"Error processing message: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def advisor_response(request):
    """
    Get a personalized advisor response for a user query.
    
    Request body:
    {
        "question": "Should I buy reliance now?"
    }
    
    Response:
    {
        "response": "Advisor's response",
        "has_redirection": true/false,
        "redirection_type": "stock|mutual_fund|none",
        "redirection_target": "RELIANCE|null"
    }
    """
    try:
        question = request.data.get('question', '').strip()
        if not question:
            return Response({
                'response': 'Please ask a question',
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Use Gemini for advisor response
        ai = ConversationalAI(user_id=request.user.id)
        advisor_response = ai.get_response(question)

        # Parse redirection markers
        redirection_type = 'none'
        redirection_target = None
        has_redirection = False

        stock_match = re.search(r'\[STOCK_ANALYSIS:([^\]]+)\]', advisor_response)
        if stock_match:
            redirection_type = 'stock'
            redirection_target = stock_match.group(1).strip()
            has_redirection = True
            advisor_response = re.sub(r'\[STOCK_ANALYSIS:[^\]]+\]\s*', '', advisor_response).strip()

        mf_match = re.search(r'\[MF_ANALYSIS:([^\]]+)\]', advisor_response)
        if mf_match:
            redirection_type = 'mutual_fund'
            redirection_target = mf_match.group(1).strip()
            has_redirection = True
            advisor_response = re.sub(r'\[MF_ANALYSIS:[^\]]+\]\s*', '', advisor_response).strip()

        return Response({
            'response': advisor_response,
            'status': 'success',
            'has_redirection': has_redirection,
            'redirection_type': redirection_type,
            'redirection_target': redirection_target
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in advisor_response: {str(e)}")
        return Response({
            'response': f'Error: {str(e)}',
            'status': 'error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
