"""
REST API ViewSets for Tournament Models

This module provides comprehensive API endpoints for all tournament-related models
including the 6 new Phase 1 models.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django.utils import timezone

from .models import (
    Tournament,
    TournamentSchedule,
    TournamentCapacity,
    TournamentFinance,
    TournamentMedia,
    TournamentRules,
    TournamentArchive
)
from .serializers import (
    TournamentDetailSerializer,
    TournamentListSerializer,
    TournamentScheduleSerializer,
    TournamentCapacitySerializer,
    TournamentFinanceSerializer,
    TournamentMediaSerializer,
    TournamentRulesSerializer,
    TournamentArchiveSerializer,
)


# ============================================================================
# CORE MODEL VIEWSETS
# ============================================================================

class TournamentScheduleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Tournament Schedules
    
    list: Get all tournament schedules
    retrieve: Get a specific tournament schedule
    create: Create a new tournament schedule
    update: Update a tournament schedule
    partial_update: Partially update a tournament schedule
    destroy: Delete a tournament schedule
    """
    
    queryset = TournamentSchedule.objects.select_related('tournament').all()
    serializer_class = TournamentScheduleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = {
        'tournament': ['exact'],
        'timezone': ['exact'],
        'auto_close_registration': ['exact'],
        'auto_start_checkin': ['exact'],
        'registration_start': ['gte', 'lte'],
        'registration_end': ['gte', 'lte'],
        'tournament_start': ['gte', 'lte'],
        'tournament_end': ['gte', 'lte'],
    }
    search_fields = ['tournament__name']
    ordering_fields = ['tournament_start', 'registration_start', 'created_at']
    ordering = ['-tournament_start']
    
    @action(detail=False, methods=['get'])
    def registration_open(self, request):
        """Get schedules with open registration"""
        now = timezone.now()
        schedules = self.queryset.filter(
            registration_start__lte=now,
            registration_end__gte=now
        )
        serializer = self.get_serializer(schedules, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming tournaments"""
        now = timezone.now()
        schedules = self.queryset.filter(
            tournament_start__gt=now
        ).order_by('tournament_start')
        serializer = self.get_serializer(schedules, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def in_progress(self, request):
        """Get tournaments currently in progress"""
        now = timezone.now()
        schedules = self.queryset.filter(
            tournament_start__lte=now,
            tournament_end__gte=now
        )
        serializer = self.get_serializer(schedules, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get detailed status of a tournament schedule"""
        schedule = self.get_object()
        return Response({
            'is_registration_open': schedule.is_registration_open(),
            'is_registration_upcoming': schedule.is_registration_upcoming(),
            'is_checkin_open': schedule.is_checkin_open(),
            'is_in_progress': schedule.is_in_progress(),
            'has_ended': schedule.has_ended(),
            'days_until_start': schedule.get_days_until_start(),
            'days_until_registration_end': schedule.get_days_until_registration_end(),
        })


class TournamentCapacityViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Tournament Capacity
    
    Provides CRUD operations and capacity management endpoints.
    """
    
    queryset = TournamentCapacity.objects.select_related('tournament').all()
    serializer_class = TournamentCapacitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = {
        'tournament': ['exact'],
        'capacity_status': ['exact'],
        'is_full': ['exact'],
        'enable_waitlist': ['exact'],
        'waitlist_full': ['exact'],
        'current_teams': ['gte', 'lte'],
        'max_teams': ['gte', 'lte'],
    }
    search_fields = ['tournament__name']
    ordering_fields = ['current_teams', 'max_teams', 'fill_percentage']
    ordering = ['-current_teams']
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get tournaments with available capacity"""
        capacities = self.queryset.filter(is_full=False)
        serializer = self.get_serializer(capacities, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def full(self, request):
        """Get full tournaments"""
        capacities = self.queryset.filter(is_full=True)
        serializer = self.get_serializer(capacities, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def increment(self, request, pk=None):
        """Increment team count (e.g., when a team registers)"""
        capacity = self.get_object()
        
        if capacity.is_full and not capacity.enable_waitlist:
            return Response(
                {'error': 'Tournament is full'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        capacity.increment_teams()
        serializer = self.get_serializer(capacity)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def decrement(self, request, pk=None):
        """Decrement team count (e.g., when a team withdraws)"""
        capacity = self.get_object()
        capacity.decrement_teams()
        serializer = self.get_serializer(capacity)
        return Response(serializer.data)


class TournamentFinanceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Tournament Finance
    
    Provides CRUD operations and financial calculations.
    """
    
    queryset = TournamentFinance.objects.select_related('tournament').all()
    serializer_class = TournamentFinanceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = {
        'tournament': ['exact'],
        'currency': ['exact'],
        'prize_currency': ['exact'],
        'entry_fee': ['gte', 'lte'],
        'prize_pool': ['gte', 'lte'],
        'total_revenue': ['gte', 'lte'],
    }
    search_fields = ['tournament__name']
    ordering_fields = ['entry_fee', 'prize_pool', 'total_revenue']
    ordering = ['-prize_pool']
    
    @action(detail=False, methods=['get'])
    def free(self, request):
        """Get free tournaments (no entry fee)"""
        finances = self.queryset.filter(entry_fee=0)
        serializer = self.get_serializer(finances, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def paid(self, request):
        """Get paid tournaments"""
        finances = self.queryset.filter(entry_fee__gt=0)
        serializer = self.get_serializer(finances, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def record_payment(self, request, pk=None):
        """Record a payment"""
        finance = self.get_object()
        amount = request.data.get('amount')
        
        if not amount:
            return Response(
                {'error': 'Amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = float(amount)
            finance.record_payment(amount)
            serializer = self.get_serializer(finance)
            return Response(serializer.data)
        except ValueError:
            return Response(
                {'error': 'Invalid amount'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def record_payout(self, request, pk=None):
        """Record a prize payout"""
        finance = self.get_object()
        amount = request.data.get('amount')
        
        if not amount:
            return Response(
                {'error': 'Amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = float(amount)
            finance.record_payout(amount)
            serializer = self.get_serializer(finance)
            return Response(serializer.data)
        except ValueError:
            return Response(
                {'error': 'Invalid amount'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get financial summary"""
        finance = self.get_object()
        return Response({
            'entry_fee': finance.get_formatted_entry_fee(),
            'prize_pool': finance.get_formatted_prize_pool(),
            'total_revenue': finance.get_formatted_total_revenue(),
            'total_paid_out': finance.get_formatted_total_paid_out(),
            'profit': finance.calculate_profit(),
            'estimated_revenue': finance.calculate_estimated_revenue(),
            'revenue_per_team': finance.calculate_revenue_per_team(),
        })


class TournamentMediaViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Tournament Media
    
    Provides CRUD operations for tournament media assets.
    """
    
    queryset = TournamentMedia.objects.select_related('tournament').all()
    serializer_class = TournamentMediaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    
    filterset_fields = {
        'tournament': ['exact'],
        'show_logo_on_card': ['exact'],
        'show_banner_on_card': ['exact'],
    }
    search_fields = ['tournament__name', 'logo_alt_text', 'banner_alt_text']
    
    @action(detail=False, methods=['get'])
    def with_logos(self, request):
        """Get media entries that have logos"""
        media = self.queryset.exclude(logo='')
        serializer = self.get_serializer(media, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def with_banners(self, request):
        """Get media entries that have banners"""
        media = self.queryset.exclude(banner='')
        serializer = self.get_serializer(media, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def with_streams(self, request):
        """Get media entries that have stream URLs"""
        media = self.queryset.exclude(stream_url='')
        serializer = self.get_serializer(media, many=True)
        return Response(serializer.data)


class TournamentRulesViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Tournament Rules
    
    Provides CRUD operations for tournament rules and requirements.
    """
    
    queryset = TournamentRules.objects.select_related('tournament').all()
    serializer_class = TournamentRulesSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    
    filterset_fields = {
        'tournament': ['exact'],
        'require_discord': ['exact'],
        'require_game_id': ['exact'],
        'require_team_logo': ['exact'],
        'min_age': ['gte', 'lte'],
        'max_age': ['gte', 'lte'],
    }
    search_fields = [
        'tournament__name',
        'general_rules',
        'eligibility_requirements',
        'match_rules',
    ]
    
    @action(detail=False, methods=['get'])
    def with_age_restriction(self, request):
        """Get rules with age restrictions"""
        from django.db.models import Q
        rules = self.queryset.filter(
            Q(min_age__isnull=False) | Q(max_age__isnull=False)
        )
        serializer = self.get_serializer(rules, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def with_region_restriction(self, request):
        """Get rules with region restrictions"""
        rules = self.queryset.exclude(region_restriction='')
        serializer = self.get_serializer(rules, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def check_eligibility(self, request, pk=None):
        """Check eligibility based on provided data"""
        rules = self.get_object()
        
        # Get query parameters
        age = request.query_params.get('age')
        region = request.query_params.get('region')
        rank = request.query_params.get('rank')
        
        eligibility = {
            'eligible': True,
            'reasons': []
        }
        
        # Check age restriction
        if age:
            try:
                age = int(age)
                if not rules.check_age_eligibility(age):
                    eligibility['eligible'] = False
                    eligibility['reasons'].append(
                        f"Age {age} does not meet requirements "
                        f"({rules.min_age or '?'}-{rules.max_age or '?'})"
                    )
            except ValueError:
                pass
        
        # Check region restriction
        if region and not rules.check_region_eligibility(region):
            eligibility['eligible'] = False
            eligibility['reasons'].append(
                f"Region '{region}' is not allowed (allowed: {rules.region_restriction})"
            )
        
        # Check rank restriction
        if rank and not rules.check_rank_eligibility(rank):
            eligibility['eligible'] = False
            eligibility['reasons'].append(
                f"Rank '{rank}' does not meet requirements ({rules.rank_restriction})"
            )
        
        return Response(eligibility)


class TournamentArchiveViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Tournament Archive
    
    Provides CRUD operations and archive management.
    """
    
    queryset = TournamentArchive.objects.select_related(
        'tournament',
        'source_tournament',
        'archived_by',
        'cloned_by',
        'restored_by'
    ).all()
    serializer_class = TournamentArchiveSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = {
        'tournament': ['exact'],
        'archive_type': ['exact'],
        'is_archived': ['exact'],
        'can_restore': ['exact'],
        'source_tournament': ['exact'],
        'preserve_participants': ['exact'],
        'preserve_matches': ['exact'],
        'preserve_media': ['exact'],
    }
    search_fields = [
        'tournament__name',
        'archive_reason',
        'notes',
    ]
    ordering_fields = ['archived_at', 'cloned_at', 'restored_at']
    ordering = ['-archived_at']
    
    @action(detail=False, methods=['get'])
    def archived(self, request):
        """Get archived tournaments"""
        archives = self.queryset.filter(is_archived=True)
        serializer = self.get_serializer(archives, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active (non-archived) tournaments"""
        archives = self.queryset.filter(is_archived=False)
        serializer = self.get_serializer(archives, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def clones(self, request):
        """Get cloned tournaments"""
        archives = self.queryset.filter(source_tournament__isnull=False)
        serializer = self.get_serializer(archives, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def archive_tournament(self, request, pk=None):
        """Archive a tournament"""
        archive = self.get_object()
        
        if archive.is_archived:
            return Response(
                {'error': 'Tournament is already archived'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', '')
        archive.archive_tournament(request.user, reason)
        
        serializer = self.get_serializer(archive)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def restore_tournament(self, request, pk=None):
        """Restore an archived tournament"""
        archive = self.get_object()
        
        if not archive.is_archived:
            return Response(
                {'error': 'Tournament is not archived'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not archive.can_restore:
            return Response(
                {'error': 'Tournament cannot be restored'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        archive.restore_tournament(request.user)
        
        serializer = self.get_serializer(archive)
        return Response(serializer.data)


class TournamentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Tournaments
    
    Provides comprehensive tournament management with all related data.
    Uses different serializers for list and detail views.
    """
    
    queryset = Tournament.objects.select_related(
        'game',
        'organizer',
        'schedule',
        'capacity',
        'finance',
        'media',
        'rules',
        'archive',
    ).all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = {
        'game': ['exact'],
        'organizer': ['exact'],
        'tournament_type': ['exact'],
        'status': ['exact'],
        'format': ['exact'],
        'platform': ['exact'],
        'created_at': ['gte', 'lte'],
    }
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name', 'tournament_start']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'list':
            return TournamentListSerializer
        return TournamentDetailSerializer
    
    @action(detail=False, methods=['get'])
    def published(self, request):
        """Get published tournaments"""
        tournaments = self.queryset.filter(status='PUBLISHED')
        serializer = self.get_serializer(tournaments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming tournaments"""
        now = timezone.now()
        tournaments = self.queryset.filter(
            schedule__tournament_start__gt=now,
            status='PUBLISHED'
        ).order_by('schedule__tournament_start')
        serializer = self.get_serializer(tournaments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def in_progress(self, request):
        """Get tournaments in progress"""
        now = timezone.now()
        tournaments = self.queryset.filter(
            schedule__tournament_start__lte=now,
            schedule__tournament_end__gte=now,
            status='PUBLISHED'
        )
        serializer = self.get_serializer(tournaments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Get completed tournaments"""
        tournaments = self.queryset.filter(status='COMPLETED')
        serializer = self.get_serializer(tournaments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def registration_open(self, request):
        """Get tournaments with open registration"""
        now = timezone.now()
        tournaments = self.queryset.filter(
            schedule__registration_start__lte=now,
            schedule__registration_end__gte=now,
            status='PUBLISHED',
            capacity__is_full=False
        )
        serializer = self.get_serializer(tournaments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def full_details(self, request, pk=None):
        """Get complete tournament details with all related data"""
        tournament = self.get_object()
        serializer = TournamentDetailSerializer(tournament, context={'request': request})
        return Response(serializer.data)
