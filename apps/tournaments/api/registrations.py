# apps/tournaments/api/registrations.py
"""
Registration API endpoints for solo and team tournament registrations.
Module 3.x - Registration thin slice.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from apps.tournaments.models import Registration, Tournament, PaymentVerification
from apps.tournaments.services.registration import (
    SoloRegistrationInput,
    TeamRegistrationInput,
    register_efootball_player,
    register_valorant_team,
)
from apps.tournaments.api.permissions import IsOwnerOrOrganizer
from rest_framework import serializers


class PaymentVerificationSerializer(serializers.ModelSerializer):
    """Serializer for PaymentVerification nested in registration response."""
    class Meta:
        model = PaymentVerification
        fields = ['id', 'method', 'transaction_id', 'payer_account_number', 'amount_bdt', 'status']
        read_only_fields = ['id', 'status']


class RegistrationSerializer(serializers.ModelSerializer):
    """Base registration serializer."""
    payment_verification = PaymentVerificationSerializer(read_only=True)
    
    class Meta:
        model = Registration
        fields = ['id', 'tournament', 'user', 'team_id', 'status', 'created_at', 'payment_verification']
        read_only_fields = ['id', 'user', 'status', 'created_at', 'payment_verification']


class SoloRegistrationSerializer(serializers.Serializer):
    """Serializer for solo registration (e.g., eFootball)."""
    tournament_id = serializers.IntegerField()
    payment = serializers.DictField(child=serializers.CharField(), required=False)
    
    def validate_tournament_id(self, value):
        """Validate tournament exists and is open."""
        try:
            tournament = Tournament.objects.get(pk=value)
        except Tournament.DoesNotExist:
            raise serializers.ValidationError("Tournament not found.")
        
        # Check if registration is open (basic check)
        if hasattr(tournament, 'status') and tournament.status not in ['registration_open', 'draft']:
            raise serializers.ValidationError("Tournament registration is not open.")
        
        return value
    
    def validate_payment(self, value):
        """Validate payment fields."""
        if not value:
            return value
        
        required_fields = ['method', 'transaction_id', 'amount_bdt']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Payment field '{field}' is required.")
        
        amount = value.get('amount_bdt')
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                raise serializers.ValidationError("Amount must be greater than 0.")
        except (ValueError, TypeError):
            raise serializers.ValidationError("Invalid amount value.")
        
        return value
    
    def validate(self, data):
        """Check for duplicate registration."""
        user = self.context['request'].user
        tournament_id = data['tournament_id']
        
        if Registration.objects.filter(tournament_id=tournament_id, user=user).exists():
            raise serializers.ValidationError("You are already registered for this tournament.")
        
        return data
    
    def create(self, validated_data):
        """Create solo registration via service."""
        user = self.context['request'].user
        payment = validated_data.get('payment', {})
        
        input_data = SoloRegistrationInput(
            tournament_id=validated_data['tournament_id'],
            user_id=user.id,
            payment_method=payment.get('method'),
            payment_reference=payment.get('transaction_id'),
            payer_account_number=payment.get('payer_account_number'),
            amount_bdt=float(payment.get('amount_bdt', 0)) if payment.get('amount_bdt') else None,
        )
        
        registration = register_efootball_player(input_data)
        return registration


class TeamRegistrationSerializer(serializers.Serializer):
    """Serializer for team registration (e.g., Valorant)."""
    tournament_id = serializers.IntegerField()
    team_id = serializers.IntegerField()
    payment = serializers.DictField(child=serializers.CharField(), required=False)
    
    def validate_tournament_id(self, value):
        """Validate tournament exists and is open."""
        try:
            tournament = Tournament.objects.get(pk=value)
        except Tournament.DoesNotExist:
            raise serializers.ValidationError("Tournament not found.")
        
        if hasattr(tournament, 'status') and tournament.status not in ['registration_open', 'draft']:
            raise serializers.ValidationError("Tournament registration is not open.")
        
        return value
    
    def validate_team_id(self, value):
        """Validate team exists and caller is captain."""
        from apps.organizations.models import Team
        try:
            team = Team.objects.get(pk=value)
        except Team.DoesNotExist:
            raise serializers.ValidationError("Team not found.")
        
        user = self.context['request'].user
        # Check if user is team captain
        if team.captain != user and (not hasattr(team, 'captain_id') or team.captain_id != user.id):
            raise serializers.ValidationError("Only team captains can register teams.")
        
        return value
    
    def validate_payment(self, value):
        """Validate payment fields."""
        if not value:
            return value
        
        required_fields = ['method', 'transaction_id', 'amount_bdt']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Payment field '{field}' is required.")
        
        amount = value.get('amount_bdt')
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                raise serializers.ValidationError("Amount must be greater than 0.")
        except (ValueError, TypeError):
            raise serializers.ValidationError("Invalid amount value.")
        
        return value
    
    def validate(self, data):
        """Check for duplicate registration."""
        team_id = data['team_id']
        tournament_id = data['tournament_id']
        
        # Check if team already registered
        if Registration.objects.filter(tournament_id=tournament_id, team_id=team_id).exists():
            raise serializers.ValidationError("This team is already registered for this tournament.")
        
        return data
    
    def create(self, validated_data):
        """Create team registration via service."""
        user = self.context['request'].user
        payment = validated_data.get('payment', {})
        
        input_data = TeamRegistrationInput(
            tournament_id=validated_data['tournament_id'],
            team_id=validated_data['team_id'],
            created_by_user_id=user.id,
            payment_method=payment.get('method'),
            payment_reference=payment.get('transaction_id'),
            payer_account_number=payment.get('payer_account_number'),
            amount_bdt=float(payment.get('amount_bdt', 0)) if payment.get('amount_bdt') else None,
        )
        
        registration = register_valorant_team(input_data)
        return registration


class RegistrationViewSet(viewsets.GenericViewSet):
    """
    ViewSet for tournament registrations.
    
    Endpoints:
    - POST /api/tournaments/registrations/solo/ - Create solo registration
    - POST /api/tournaments/registrations/team/ - Create team registration
    - DELETE /api/tournaments/registrations/{id}/ - Cancel registration
    
    Optimization (Module 9.1): Added select_related to reduce N+1 queries.
    Planning ref: PART_5.2 Section 4.4 (Query Optimization)
    """
    queryset = Registration.objects.select_related(
        'tournament',
        'user',
        'team',
        'payment_verification'
    ).all()
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='solo')
    def create_solo(self, request):
        """Create a solo tournament registration."""
        serializer = SoloRegistrationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        registration = serializer.save()
        
        # Return full registration with payment verification
        response_serializer = RegistrationSerializer(registration)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], url_path='team')
    def create_team(self, request):
        """Create a team tournament registration."""
        serializer = TeamRegistrationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        registration = serializer.save()
        
        # Return full registration with payment verification
        response_serializer = RegistrationSerializer(registration)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, pk=None):
        """Cancel a registration (soft delete)."""
        try:
            registration = self.get_queryset().get(pk=pk)
        except Registration.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        # Check permission
        if registration.user != request.user and not request.user.is_staff:
            return Response(
                {"detail": "You can only cancel your own registration."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Soft cancel - mark as cancelled but keep payment verification intact
        if hasattr(registration, 'status'):
            registration.status = 'cancelled'
            registration.save(update_fields=['status'])
        
        return Response(status=status.HTTP_204_NO_CONTENT)
