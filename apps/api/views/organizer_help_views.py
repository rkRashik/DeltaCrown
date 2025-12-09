"""
DRF API Views for Help & Onboarding

Phase 7, Epic 7.6: Guidance & Help Overlays
Organizer-facing endpoints for help content, overlays, and onboarding wizard.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.tournament_ops.services.tournament_ops_service import get_tournament_ops_service
from apps.api.serializers.organizer_help_serializers import (
    HelpBundleSerializer,
    CompleteStepRequestSerializer,
    DismissStepRequestSerializer,
    OnboardingProgressSerializer,
    OnboardingStepSerializer,
)


class HelpBundleView(APIView):
    """
    Get complete help bundle for a page.
    
    GET /api/organizer/help/bundle/
    
    Query Parameters:
    - page_id (required): Page identifier (e.g., 'results_inbox', 'scheduling')
    - tournament_id (optional): Tournament ID for tournament-specific onboarding
    - audience (optional): Target audience (default: 'organizer')
    
    Returns:
    - HelpBundleDTO with help content, overlays, and onboarding state
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get help bundle for a page."""
        # Get query parameters
        page_id = request.query_params.get('page_id')
        tournament_id = request.query_params.get('tournament_id')
        audience = request.query_params.get('audience', 'organizer')
        
        # Validate required params
        if not page_id:
            return Response(
                {'error': 'page_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert tournament_id to int if provided
        if tournament_id:
            try:
                tournament_id = int(tournament_id)
            except ValueError:
                return Response(
                    {'error': 'tournament_id must be an integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get tournament ops service
        service = get_tournament_ops_service()
        
        # Fetch help bundle
        bundle = service.get_help_for_page(
            page_id=page_id,
            user_id=request.user.id,
            audience=audience,
            tournament_id=tournament_id
        )
        
        # Serialize and return
        serializer = HelpBundleSerializer(bundle)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompleteOnboardingStepView(APIView):
    """
    Mark an onboarding step as completed.
    
    POST /api/organizer/help/complete-step/
    
    Request Body:
    {
        "step_key": "results_inbox_intro",
        "tournament_id": 123  // optional
    }
    
    Returns:
    - OnboardingStepDTO with updated state
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Complete an onboarding step."""
        # Validate request data
        serializer = CompleteStepRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract data
        step_key = serializer.validated_data['step_key']
        tournament_id = serializer.validated_data.get('tournament_id')
        
        # Get tournament ops service
        service = get_tournament_ops_service()
        
        # Complete the step
        step_dto = service.complete_onboarding_step(
            user_id=request.user.id,
            step_key=step_key,
            tournament_id=tournament_id
        )
        
        # Serialize and return
        result_serializer = OnboardingStepSerializer(step_dto)
        return Response(result_serializer.data, status=status.HTTP_200_OK)


class DismissHelpItemView(APIView):
    """
    Dismiss/skip an onboarding step.
    
    POST /api/organizer/help/dismiss/
    
    Request Body:
    {
        "step_key": "results_inbox_intro",
        "tournament_id": 123  // optional
    }
    
    Returns:
    - OnboardingStepDTO with updated state
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Dismiss an onboarding step."""
        # Validate request data
        serializer = DismissStepRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract data
        step_key = serializer.validated_data['step_key']
        tournament_id = serializer.validated_data.get('tournament_id')
        
        # Get tournament ops service
        service = get_tournament_ops_service()
        
        # Dismiss the step
        step_dto = service.dismiss_help_item(
            user_id=request.user.id,
            step_key=step_key,
            tournament_id=tournament_id
        )
        
        # Serialize and return
        result_serializer = OnboardingStepSerializer(step_dto)
        return Response(result_serializer.data, status=status.HTTP_200_OK)


class OnboardingProgressView(APIView):
    """
    Get user's onboarding progress summary.
    
    GET /api/organizer/help/progress/
    
    Query Parameters:
    - tournament_id (optional): Tournament ID for tournament-specific progress
    
    Returns:
    - Progress summary with counts and completion percentage
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get onboarding progress."""
        # Get query parameters
        tournament_id = request.query_params.get('tournament_id')
        
        # Convert tournament_id to int if provided
        if tournament_id:
            try:
                tournament_id = int(tournament_id)
            except ValueError:
                return Response(
                    {'error': 'tournament_id must be an integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get tournament ops service
        service = get_tournament_ops_service()
        
        # Fetch progress
        progress = service.get_onboarding_progress(
            user_id=request.user.id,
            tournament_id=tournament_id
        )
        
        # Serialize and return
        serializer = OnboardingProgressSerializer(progress)
        return Response(serializer.data, status=status.HTTP_200_OK)
