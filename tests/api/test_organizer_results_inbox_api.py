"""
Epic 7.1: Organizer Results Inbox API Tests

Comprehensive API test suite for organizer results inbox endpoints.

Test Coverage:
- GET /api/v1/organizer/results-inbox/ - 7 tests
- POST /api/v1/organizer/results-inbox/bulk-action/ - 5 tests

Total: 12 tests

Reference: ROADMAP_AND_EPICS_PART_4.md - Epic 7.1, Results Inbox & Queue Management
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.tournament_ops.dtos import OrganizerReviewItemDTO

User = get_user_model()


@pytest.fixture
def organizer_user(db):
    """Create organizer user."""
    return User.objects.create_user(
        username="organizer1",
        email="organizer@test.com",
        password="pass123"
    )


@pytest.fixture
def api_client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, organizer_user):
    """Create authenticated API client."""
    api_client.force_authenticate(user=organizer_user)
    return api_client


@pytest.fixture
def sample_review_items():
    """Sample OrganizerReviewItemDTO list for testing."""
    now = datetime.now(timezone.utc)
    return [
        OrganizerReviewItemDTO(
            submission_id=101,
            match_id=201,
            tournament_id=1,
            tournament_name='Summer Championship 2025',
            stage_id=None,
            submitted_by_user_id=100,
            status='pending',
            dispute_id=None,
            dispute_status=None,
            created_at=now - timedelta(hours=12),
            auto_confirm_deadline=now + timedelta(hours=12),
            opened_at=None,
            is_overdue=False,
            priority=85,
        ),
        OrganizerReviewItemDTO(
            submission_id=102,
            match_id=202,
            tournament_id=2,
            tournament_name='Winter League 2025',
            stage_id=None,
            submitted_by_user_id=101,
            status='disputed',
            dispute_id=501,
            dispute_status='open',
            created_at=now - timedelta(hours=48),
            auto_confirm_deadline=now - timedelta(hours=24),
            opened_at=now - timedelta(hours=48),
            is_overdue=True,
            priority=95,
        ),
        OrganizerReviewItemDTO(
            submission_id=103,
            match_id=203,
            tournament_id=1,
            tournament_name='Summer Championship 2025',
            stage_id=None,
            submitted_by_user_id=100,
            status='pending',
            dispute_id=None,
            dispute_status=None,
            created_at=now - timedelta(hours=6),
            auto_confirm_deadline=now + timedelta(hours=18),
            opened_at=None,
            is_overdue=False,
            priority=70,
        ),
    ]


class TestOrganizerResultsInboxAPI:
    """Test suite for GET /api/v1/organizer/results-inbox/ endpoint."""

    @patch('apps.tournament_ops.services.tournament_ops_service.TournamentOpsService.list_results_inbox_for_organizer')
    def test_get_results_inbox_returns_paginated_items_for_organizer(
        self,
        mock_list_inbox,
        authenticated_client,
        organizer_user,
        sample_review_items,
    ):
        """Test GET /api/v1/organizer/results-inbox/ returns paginated items."""
        # Arrange
        mock_list_inbox.return_value = sample_review_items

        # Act
        response = authenticated_client.get('/api/tournaments/v1/organizer/results-inbox/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'results' in response.data
        assert len(response.data['results']) == 3
        
        # Verify service was called with correct organizer_user_id
        mock_list_inbox.assert_called_once()
        call_args = mock_list_inbox.call_args
        assert call_args[1]['organizer_user_id'] == organizer_user.id

    @patch('apps.tournament_ops.services.tournament_ops_service.TournamentOpsService.list_results_inbox_for_organizer')
    def test_get_results_inbox_filters_by_tournament_id_query_param(
        self,
        mock_list_inbox,
        authenticated_client,
        sample_review_items,
    ):
        """Test filtering by tournament_id query parameter."""
        # Arrange
        filtered_items = [sample_review_items[0], sample_review_items[2]]
        mock_list_inbox.return_value = filtered_items

        # Act
        response = authenticated_client.get('/api/tournaments/v1/organizer/results-inbox/?tournament_id=1')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
        
        # Verify filter was passed to service
        call_args = mock_list_inbox.call_args
        assert call_args[1]['filters'].get('tournament_id') == 1

    @patch('apps.tournament_ops.services.tournament_ops_service.TournamentOpsService.list_results_inbox_for_organizer')
    def test_get_results_inbox_filters_by_status(
        self,
        mock_list_inbox,
        authenticated_client,
        sample_review_items,
    ):
        """Test filtering by status query parameter."""
        # Arrange
        filtered_items = [sample_review_items[0], sample_review_items[2]]
        mock_list_inbox.return_value = filtered_items

        # Act
        response = authenticated_client.get('/api/tournaments/v1/organizer/results-inbox/?status=pending')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
        
        # Verify filter was passed to service
        call_args = mock_list_inbox.call_args
        assert 'pending' in call_args[1]['filters'].get('status', [])

    @patch('apps.tournament_ops.services.tournament_ops_service.TournamentOpsService.list_results_inbox_for_organizer')
    def test_get_results_inbox_filters_by_date_range(
        self,
        mock_list_inbox,
        authenticated_client,
        sample_review_items,
    ):
        """Test filtering by date range query parameters."""
        # Arrange
        filtered_items = [sample_review_items[0]]
        mock_list_inbox.return_value = filtered_items
        
        date_from = '2025-12-08T00:00:00Z'
        date_to = '2025-12-09T23:59:59Z'

        # Act
        response = authenticated_client.get(
            f'/api/tournaments/v1/organizer/results-inbox/?date_from={date_from}&date_to={date_to}'
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        # Verify filter was passed to service
        call_args = mock_list_inbox.call_args
        assert 'date_from' in call_args[1]['filters']
        assert 'date_to' in call_args[1]['filters']

    @patch('apps.tournament_ops.services.tournament_ops_service.TournamentOpsService.list_results_inbox_for_organizer')
    def test_get_results_inbox_uses_priority_ordering_by_default(
        self,
        mock_list_inbox,
        authenticated_client,
        sample_review_items,
    ):
        """Test default ordering by priority."""
        # Arrange
        mock_list_inbox.return_value = sample_review_items

        # Act
        response = authenticated_client.get('/api/tournaments/v1/organizer/results-inbox/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        # Results should be ordered by priority (descending)
        priorities = [item['priority'] for item in response.data['results']]
        assert priorities == sorted(priorities, reverse=True)

    def test_results_inbox_requires_authenticated_user(
        self,
        api_client,
    ):
        """Test that endpoint requires authentication."""
        # Act
        response = api_client.get('/api/tournaments/v1/organizer/results-inbox/')

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('apps.tournament_ops.services.tournament_ops_service.TournamentOpsService.list_results_inbox_for_organizer')
    def test_results_inbox_api_uses_tournament_ops_service_facade(
        self,
        mock_list_inbox,
        authenticated_client,
        sample_review_items,
    ):
        """Test that API uses TournamentOpsService façade, not internal services."""
        # Arrange
        mock_list_inbox.return_value = sample_review_items

        # Act
        response = authenticated_client.get('/api/tournaments/v1/organizer/results-inbox/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        
        # Verify TournamentOpsService.list_results_inbox_for_organizer was called
        mock_list_inbox.assert_called_once()


class TestOrganizerResultsInboxBulkActionAPI:
    """Test suite for POST /api/v1/organizer/results-inbox/bulk-action/ endpoint."""

    @patch('apps.tournament_ops.services.tournament_ops_service.TournamentOpsService.bulk_finalize_submissions')
    def test_bulk_action_finalize_calls_service_and_returns_summary(
        self,
        mock_bulk_finalize,
        authenticated_client,
        organizer_user,
        sample_review_items,
    ):
        """Test bulk finalize action calls service and returns summary."""
        # Arrange
        submission_ids = [101, 102]
        mock_bulk_finalize.return_value = {
            'processed': 2,
            'failed': [],
            'items': sample_review_items[:2],
        }

        # Act
        response = authenticated_client.post(
            '/api/tournaments/v1/organizer/results-inbox/bulk-action/',
            {
                'action': 'finalize',
                'submission_ids': submission_ids,
            },
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['processed'] == 2
        assert len(response.data['items']) == 2
        assert len(response.data['failed']) == 0
        
        # Verify service was called correctly
        mock_bulk_finalize.assert_called_once_with(
            submission_ids=submission_ids,
            resolved_by_user_id=organizer_user.id
        )

    @patch('apps.tournament_ops.services.tournament_ops_service.TournamentOpsService.bulk_reject_submissions')
    def test_bulk_action_reject_calls_service_and_returns_summary(
        self,
        mock_bulk_reject,
        authenticated_client,
        organizer_user,
        sample_review_items,
    ):
        """Test bulk reject action calls service and returns summary."""
        # Arrange
        submission_ids = [101, 102]
        notes = 'Invalid proof screenshot'
        mock_bulk_reject.return_value = {
            'processed': 2,
            'failed': [],
            'items': sample_review_items[:2],
        }

        # Act
        response = authenticated_client.post(
            '/api/tournaments/v1/organizer/results-inbox/bulk-action/',
            {
                'action': 'reject',
                'submission_ids': submission_ids,
                'notes': notes,
            },
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data['processed'] == 2
        
        # Verify service was called with notes
        mock_bulk_reject.assert_called_once_with(
            submission_ids=submission_ids,
            resolved_by_user_id=organizer_user.id,
            notes=notes
        )

    def test_bulk_action_missing_submission_ids_returns_400(
        self,
        authenticated_client,
    ):
        """Test bulk action without submission_ids returns 400."""
        # Act
        response = authenticated_client.post(
            '/api/tournaments/v1/organizer/results-inbox/bulk-action/',
            {
                'action': 'finalize',
            },
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_action_invalid_action_returns_400(
        self,
        authenticated_client,
    ):
        """Test bulk action with invalid action type returns 400."""
        # Act
        response = authenticated_client.post(
            '/api/tournaments/v1/organizer/results-inbox/bulk-action/',
            {
                'action': 'invalid_action',
                'submission_ids': [101, 102],
            },
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_action_reject_without_notes_returns_400(
        self,
        authenticated_client,
    ):
        """Test bulk reject action without notes returns 400."""
        # Act
        response = authenticated_client.post(
            '/api/tournaments/v1/organizer/results-inbox/bulk-action/',
            {
                'action': 'reject',
                'submission_ids': [101, 102],
            },
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'notes' in str(response.data).lower() or 'error' in response.data
