"""
Unit tests for ResultVerificationService - Phase 6, Epic 6.4

Tests verification and finalization workflows with mocked adapters.

Reference: PHASE6_WORKPLAN_DRAFT.md - Epic 6.4 (Result Verification & Finalization)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from apps.tournament_ops.services.result_verification_service import (
    ResultVerificationService,
    ResultVerificationFailedError,
)
from apps.tournament_ops.dtos import (
    MatchResultSubmissionDTO,
    ResultVerificationResultDTO,
    MatchDTO,
    DisputeDTO,
)
from apps.tournament_ops.exceptions import SubmissionError, InvalidSubmissionStateError


class TestVerifySubmission:
    """
    Test verify_submission() method.
    
    Covers:
    - Schema validation integration
    - Verification logging
    - Event publishing
    - Error handling
    """
    
    def test_verify_submission_calls_schema_validation_and_logs_step(self):
        """Verify submission calls schema validation and logs verification step."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        event_bus = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=1,
            match_id=10,
            submitted_by_user_id=100,
            submitted_by_team_id=5,
            raw_result_payload={'winner_team_id': 5, 'loser_team_id': 6, 'score': '13-7'},
            proof_screenshot_url='https://example.com/proof.png',
            status='pending',
            submitted_at=datetime.now(),
            confirmed_at=None,
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=None,
            submitter_notes='We won',
            organizer_notes='',
        )
        
        verification_result = ResultVerificationResultDTO.create_valid(
            calculated_scores={'winner_team_id': 5, 'loser_team_id': 6, 'winner_score': 13, 'loser_score': 7},
            metadata={'game_slug': 'valorant'},
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        service.event_bus = event_bus
        
        # Mock _get_game_slug_for_submission
        with patch.object(service, '_get_game_slug_for_submission', return_value='valorant'):
            # Act
            result = service.verify_submission(1)
        
        # Assert
        assert result.is_valid is True
        submission_adapter.get_submission.assert_called_once_with(1)
        schema_validation_adapter.validate_payload.assert_called_once_with(
            game_slug='valorant',
            payload={'winner_team_id': 5, 'loser_team_id': 6, 'score': '13-7'},
        )
        dispute_adapter.log_verification_step.assert_called_once()
        log_call = dispute_adapter.log_verification_step.call_args
        assert log_call[1]['submission_id'] == 1
        assert log_call[1]['step'] == 'auto_verification'
        assert log_call[1]['status'] == 'success'
    
    def test_verify_submission_returns_verification_result_dto(self):
        """Verify submission returns ResultVerificationResultDTO."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=2,
            match_id=20,
            submitted_by_user_id=200,
            submitted_by_team_id=10,
            raw_result_payload={'winner_team_id': 10, 'loser_team_id': 11},
            proof_screenshot_url=None,
            status='confirmed',
            submitted_at=datetime.now(),
            confirmed_at=datetime.now(),
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=201,
            submitter_notes='',
            organizer_notes='',
        )
        
        verification_result = ResultVerificationResultDTO.create_valid(
            calculated_scores={'winner_team_id': 10, 'loser_team_id': 11, 'winner_score': 2, 'loser_score': 1},
            metadata={'game_slug': 'csgo'},
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='csgo'):
            # Act
            result = service.verify_submission(2)
        
        # Assert
        assert isinstance(result, ResultVerificationResultDTO)
        assert result.is_valid is True
        assert result.calculated_scores['winner_team_id'] == 10
        assert result.metadata['game_slug'] == 'csgo'
    
    def test_verify_submission_publishes_verified_event(self):
        """Verify submission publishes MatchResultVerifiedEvent."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        event_bus = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=3,
            match_id=30,
            submitted_by_user_id=300,
            submitted_by_team_id=15,
            raw_result_payload={'winner_team_id': 15, 'loser_team_id': 16, 'score': '25-23'},
            proof_screenshot_url='https://example.com/proof3.png',
            status='pending',
            submitted_at=datetime.now(),
            confirmed_at=None,
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=None,
            submitter_notes='Close game',
            organizer_notes='',
        )
        
        verification_result = ResultVerificationResultDTO.create_valid(
            calculated_scores={'winner_team_id': 15, 'loser_team_id': 16, 'winner_score': 25, 'loser_score': 23},
            metadata={'game_slug': 'valorant', 'validation_method': 'jsonschema'},
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        service.event_bus = event_bus
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='valorant'):
            # Act
            service.verify_submission(3)
        
        # Assert
        event_bus.publish.assert_called_once()
        event_call = event_bus.publish.call_args[0][0]
        assert event_call.name == 'MatchResultVerifiedEvent'
        assert event_call.payload['submission_id'] == 3
        assert event_call.payload['match_id'] == 30
        assert event_call.payload['is_valid'] is True
        assert event_call.payload['errors_count'] == 0
        assert event_call.payload['game_slug'] == 'valorant'
    
    def test_verify_submission_handles_missing_schema_as_invalid(self):
        """Verify submission handles missing schema as invalid."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        event_bus = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=4,
            match_id=40,
            submitted_by_user_id=400,
            submitted_by_team_id=20,
            raw_result_payload={'winner_team_id': 20, 'loser_team_id': 21},
            proof_screenshot_url=None,
            status='pending',
            submitted_at=datetime.now(),
            confirmed_at=None,
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=None,
            submitter_notes='',
            organizer_notes='',
        )
        
        # Schema validation returns invalid (missing schema)
        verification_result = ResultVerificationResultDTO.create_invalid(
            errors=['Missing match result schema for game'],
            metadata={'game_slug': 'unknown_game', 'validation_method': 'schema_missing'},
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        service.event_bus = event_bus
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='unknown_game'):
            # Act
            result = service.verify_submission(4)
        
        # Assert
        assert result.is_valid is False
        assert 'Missing match result schema for game' in result.errors
        dispute_adapter.log_verification_step.assert_called_once()
        log_call = dispute_adapter.log_verification_step.call_args
        assert log_call[1]['status'] == 'failure'


class TestFinalizeSubmissionAfterVerification:
    """
    Test finalize_submission_after_verification() method.
    
    Covers:
    - Full verification pipeline
    - Match service integration
    - Dispute resolution
    - Event publishing
    - Error handling
    """
    
    def test_finalize_submission_calls_verify_first(self):
        """Finalize submission calls verify_submission first."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=5,
            match_id=50,
            submitted_by_user_id=500,
            submitted_by_team_id=25,
            raw_result_payload={'winner_team_id': 25, 'loser_team_id': 26, 'score': '16-14'},
            proof_screenshot_url='https://example.com/proof5.png',
            status='confirmed',
            submitted_at=datetime.now(),
            confirmed_at=datetime.now(),
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=501,
            submitter_notes='',
            organizer_notes='',
        )
        
        finalized_dto = MatchResultSubmissionDTO(**{**submission_dto.__dict__, 'status': 'finalized', 'finalized_at': datetime.now()})
        
        verification_result = ResultVerificationResultDTO.create_valid(
            calculated_scores={'winner_team_id': 25, 'loser_team_id': 26, 'winner_score': 16, 'loser_score': 14},
            metadata={'game_slug': 'csgo'},
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        submission_adapter.update_submission_status.return_value = finalized_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        dispute_adapter.get_open_dispute_for_submission.return_value = None
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='csgo'):
            with patch.object(service, '_apply_final_scores_to_match'):
                # Act
                service.finalize_submission_after_verification(5, 999)
        
        # Assert
        schema_validation_adapter.validate_payload.assert_called_once()
    
    def test_finalize_submission_raises_if_verification_invalid(self):
        """Finalize submission raises ResultVerificationFailedError if verification fails."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=6,
            match_id=60,
            submitted_by_user_id=600,
            submitted_by_team_id=30,
            raw_result_payload={'winner_team_id': 30},  # Missing loser_team_id
            proof_screenshot_url=None,
            status='confirmed',
            submitted_at=datetime.now(),
            confirmed_at=datetime.now(),
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=601,
            submitter_notes='',
            organizer_notes='',
        )
        
        # Verification fails
        verification_result = ResultVerificationResultDTO.create_invalid(
            errors=['Missing required field: loser_team_id'],
            metadata={'game_slug': 'valorant'},
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='valorant'):
            # Act & Assert
            with pytest.raises(ResultVerificationFailedError) as exc_info:
                service.finalize_submission_after_verification(6, 999)
            
            assert 'failed verification' in str(exc_info.value)
            assert 'Missing required field: loser_team_id' in str(exc_info.value)
    
    def test_finalize_submission_updates_match_via_match_service(self):
        """Finalize submission updates match via MatchService.accept_match_result."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=7,
            match_id=70,
            submitted_by_user_id=700,
            submitted_by_team_id=35,
            raw_result_payload={'winner_team_id': 35, 'loser_team_id': 36, 'score': '13-9'},
            proof_screenshot_url='https://example.com/proof7.png',
            status='confirmed',
            submitted_at=datetime.now(),
            confirmed_at=datetime.now(),
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=701,
            submitter_notes='',
            organizer_notes='',
        )
        
        finalized_dto = MatchResultSubmissionDTO(**{**submission_dto.__dict__, 'status': 'finalized', 'finalized_at': datetime.now()})
        
        verification_result = ResultVerificationResultDTO.create_valid(
            calculated_scores={'winner_team_id': 35, 'loser_team_id': 36, 'winner_score': 13, 'loser_score': 9},
            metadata={'game_slug': 'valorant'},
        )
        
        match_dto = MatchDTO(
            id=70,
            tournament_id=1,
            stage_id=2,
            round_number=1,
            match_number=1,
            team1_id=35,
            team2_id=36,
            winner_team_id=35,
            loser_team_id=36,
            status='completed',
            scheduled_time=None,
            result={'winner_team_id': 35, 'loser_team_id': 36, 'score': '13-9'},
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        submission_adapter.update_submission_status.return_value = finalized_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        dispute_adapter.get_open_dispute_for_submission.return_value = None
        match_service.accept_match_result.return_value = match_dto
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='valorant'):
            # Act
            service.finalize_submission_after_verification(7, 999)
        
        # Assert
        match_service.accept_match_result.assert_called_once_with(
            match_id=70,
            winner_team_id=35,
            loser_team_id=36,
            result_payload={'winner_team_id': 35, 'loser_team_id': 36, 'score': '13-9'},
            metadata={
                'source': 'result_verification_service',
                'calculated_scores': {'winner_team_id': 35, 'loser_team_id': 36, 'winner_score': 13, 'loser_score': 9},
            }
        )
    
    def test_finalize_submission_updates_submission_status_to_finalized(self):
        """Finalize submission updates submission status to 'finalized'."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=8,
            match_id=80,
            submitted_by_user_id=800,
            submitted_by_team_id=40,
            raw_result_payload={'winner_team_id': 40, 'loser_team_id': 41, 'score': '2-0'},
            proof_screenshot_url=None,
            status='auto_confirmed',
            submitted_at=datetime.now() - timedelta(hours=25),
            confirmed_at=None,
            finalized_at=None,
            auto_confirm_deadline=datetime.now() - timedelta(hours=1),
            confirmed_by_user_id=None,
            submitter_notes='',
            organizer_notes='',
        )
        
        finalized_dto = MatchResultSubmissionDTO(**{**submission_dto.__dict__, 'status': 'finalized', 'finalized_at': datetime.now()})
        
        verification_result = ResultVerificationResultDTO.create_valid(
            calculated_scores={'winner_team_id': 40, 'loser_team_id': 41, 'winner_score': 2, 'loser_score': 0},
            metadata={'game_slug': 'csgo'},
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        submission_adapter.update_submission_status.return_value = finalized_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        dispute_adapter.get_open_dispute_for_submission.return_value = None
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='csgo'):
            with patch.object(service, '_apply_final_scores_to_match'):
                # Act
                result = service.finalize_submission_after_verification(8, 999)
        
        # Assert
        submission_adapter.update_submission_status.assert_called_once_with(
            submission_id=8,
            status='finalized',
        )
        assert result.status == 'finalized'
    
    def test_finalize_submission_resolves_open_dispute_for_submitter(self):
        """Finalize submission resolves open dispute when submitter wins."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        event_bus = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=9,
            match_id=90,
            submitted_by_user_id=900,
            submitted_by_team_id=45,
            raw_result_payload={'winner_team_id': 45, 'loser_team_id': 46, 'score': '13-11'},
            proof_screenshot_url='https://example.com/proof9.png',
            status='disputed',
            submitted_at=datetime.now(),
            confirmed_at=None,
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=None,
            submitter_notes='We won',
            organizer_notes='',
        )
        
        finalized_dto = MatchResultSubmissionDTO(**{**submission_dto.__dict__, 'status': 'finalized', 'finalized_at': datetime.now()})
        
        dispute_dto = DisputeDTO(
            id=5,
            submission_id=9,
            match_id=90,
            disputed_by_user_id=901,
            disputed_by_team_id=46,
            reason_code='incorrect_score',
            reason='Wrong score reported',
            status='open',
            escalated_at=None,
            resolved_by_user_id=None,
            resolved_at=None,
            resolution_notes='',
            opened_at=datetime.now(),
        )
        
        resolved_dispute_dto = DisputeDTO(**{**dispute_dto.__dict__, 'status': 'resolved_for_submitter', 'resolved_by_user_id': 999, 'resolved_at': datetime.now()})
        
        verification_result = ResultVerificationResultDTO.create_valid(
            calculated_scores={'winner_team_id': 45, 'loser_team_id': 46, 'winner_score': 13, 'loser_score': 11},
            metadata={'game_slug': 'valorant'},
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        submission_adapter.update_submission_status.return_value = finalized_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        dispute_adapter.get_open_dispute_for_submission.return_value = dispute_dto
        dispute_adapter.update_dispute_status.return_value = resolved_dispute_dto
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        service.event_bus = event_bus
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='valorant'):
            with patch.object(service, '_apply_final_scores_to_match'):
                # Act
                service.finalize_submission_after_verification(9, 999)
        
        # Assert
        dispute_adapter.update_dispute_status.assert_called_once_with(
            dispute_id=5,
            status='resolved_for_submitter',
            resolved_by_user_id=999,
            resolution_notes='Verification confirmed submitter result (submitter wins)',
        )
    
    def test_finalize_submission_resolves_open_dispute_for_opponent(self):
        """Finalize submission resolves open dispute when opponent wins."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        event_bus = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=10,
            match_id=100,
            submitted_by_user_id=1000,
            submitted_by_team_id=50,
            raw_result_payload={'winner_team_id': 51, 'loser_team_id': 50, 'score': '13-7'},  # Opponent won
            proof_screenshot_url='https://example.com/proof10.png',
            status='disputed',
            submitted_at=datetime.now(),
            confirmed_at=None,
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=None,
            submitter_notes='We won',
            organizer_notes='',
        )
        
        finalized_dto = MatchResultSubmissionDTO(**{**submission_dto.__dict__, 'status': 'finalized', 'finalized_at': datetime.now()})
        
        dispute_dto = DisputeDTO(
            id=6,
            submission_id=10,
            match_id=100,
            disputed_by_user_id=1001,
            disputed_by_team_id=51,
            reason_code='incorrect_winner',
            reason='We actually won',
            status='open',
            escalated_at=None,
            resolved_by_user_id=None,
            resolved_at=None,
            resolution_notes='',
            opened_at=datetime.now(),
        )
        
        resolved_dispute_dto = DisputeDTO(**{**dispute_dto.__dict__, 'status': 'resolved_for_opponent', 'resolved_by_user_id': 999, 'resolved_at': datetime.now()})
        
        verification_result = ResultVerificationResultDTO.create_valid(
            calculated_scores={'winner_team_id': 51, 'loser_team_id': 50, 'winner_score': 13, 'loser_score': 7},
            metadata={'game_slug': 'csgo'},
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        submission_adapter.update_submission_status.return_value = finalized_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        dispute_adapter.get_open_dispute_for_submission.return_value = dispute_dto
        dispute_adapter.update_dispute_status.return_value = resolved_dispute_dto
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        service.event_bus = event_bus
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='csgo'):
            with patch.object(service, '_apply_final_scores_to_match'):
                # Act
                service.finalize_submission_after_verification(10, 999)
        
        # Assert
        dispute_adapter.update_dispute_status.assert_called_once_with(
            dispute_id=6,
            status='resolved_for_opponent',
            resolved_by_user_id=999,
            resolution_notes='Verification confirmed opponent result (opponent wins)',
        )
    
    def test_finalize_submission_logs_finalization_step(self):
        """Finalize submission logs finalization step to audit trail."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=11,
            match_id=110,
            submitted_by_user_id=1100,
            submitted_by_team_id=55,
            raw_result_payload={'winner_team_id': 55, 'loser_team_id': 56, 'score': '16-12'},
            proof_screenshot_url=None,
            status='confirmed',
            submitted_at=datetime.now(),
            confirmed_at=datetime.now(),
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=1101,
            submitter_notes='',
            organizer_notes='',
        )
        
        finalized_dto = MatchResultSubmissionDTO(**{**submission_dto.__dict__, 'status': 'finalized', 'finalized_at': datetime.now()})
        
        verification_result = ResultVerificationResultDTO.create_valid(
            calculated_scores={'winner_team_id': 55, 'loser_team_id': 56, 'winner_score': 16, 'loser_score': 12},
            metadata={'game_slug': 'csgo'},
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        submission_adapter.update_submission_status.return_value = finalized_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        dispute_adapter.get_open_dispute_for_submission.return_value = None
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='csgo'):
            with patch.object(service, '_apply_final_scores_to_match'):
                # Act
                service.finalize_submission_after_verification(11, 999)
        
        # Assert
        # Should log twice: once for verify_submission, once for finalization
        assert dispute_adapter.log_verification_step.call_count == 2
        finalization_log_call = [call for call in dispute_adapter.log_verification_step.call_args_list if call[1]['step'] == 'finalization'][0]
        assert finalization_log_call[1]['submission_id'] == 11
        assert finalization_log_call[1]['status'] == 'success'
        assert finalization_log_call[1]['performed_by_user_id'] == 999
    
    def test_finalize_submission_publishes_finalized_event_with_scores(self):
        """Finalize submission publishes MatchResultFinalizedEvent with verification context."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        event_bus = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=12,
            match_id=120,
            submitted_by_user_id=1200,
            submitted_by_team_id=60,
            raw_result_payload={'winner_team_id': 60, 'loser_team_id': 61, 'score': '13-10', 'map': 'Dust2'},
            proof_screenshot_url='https://example.com/proof12.png',
            status='confirmed',
            submitted_at=datetime.now(),
            confirmed_at=datetime.now(),
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=1201,
            submitter_notes='',
            organizer_notes='',
        )
        
        finalized_dto = MatchResultSubmissionDTO(**{**submission_dto.__dict__, 'status': 'finalized', 'finalized_at': datetime.now()})
        
        verification_result = ResultVerificationResultDTO.create_valid(
            calculated_scores={'winner_team_id': 60, 'loser_team_id': 61, 'winner_score': 13, 'loser_score': 10, 'map': 'Dust2'},
            metadata={'game_slug': 'csgo', 'validation_method': 'jsonschema'},
        )
        verification_result.warnings = ['Suspiciously short match duration: 45s']
        
        submission_adapter.get_submission.return_value = submission_dto
        submission_adapter.update_submission_status.return_value = finalized_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        dispute_adapter.get_open_dispute_for_submission.return_value = None
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        service.event_bus = event_bus
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='csgo'):
            with patch.object(service, '_apply_final_scores_to_match'):
                # Act
                service.finalize_submission_after_verification(12, 999)
        
        # Assert
        # Should publish 2 events: MatchResultVerifiedEvent + MatchResultFinalizedEvent
        assert event_bus.publish.call_count == 2
        finalized_event_call = [call for call in event_bus.publish.call_args_list if call[0][0].name == 'MatchResultFinalizedEvent'][0]
        event = finalized_event_call[0][0]
        assert event.payload['submission_id'] == 12
        assert event.payload['match_id'] == 120
        assert event.payload['winner_team_id'] == 60
        assert event.payload['loser_team_id'] == 61
        assert event.payload['resolved_by_user_id'] == 999
        assert event.metadata['calculated_scores']['map'] == 'Dust2'
        assert event.metadata['verification_warnings_count'] == 1
    
    def test_verify_submission_handles_validation_exceptions_gracefully(self):
        """Verify submission handles validation exceptions gracefully."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=13,
            match_id=130,
            submitted_by_user_id=1300,
            submitted_by_team_id=65,
            raw_result_payload={'winner_team_id': 65, 'loser_team_id': 66},
            proof_screenshot_url=None,
            status='pending',
            submitted_at=datetime.now(),
            confirmed_at=None,
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=None,
            submitter_notes='',
            organizer_notes='',
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        schema_validation_adapter.validate_payload.side_effect = Exception("Unexpected validation error")
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='valorant'):
            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                service.verify_submission(13)
            
            assert 'Unexpected validation error' in str(exc_info.value)


class TestDryRunVerification:
    """Test dry_run_verification() method."""
    
    def test_dry_run_verification_does_not_log_or_change_state(self):
        """Dry run verification does not log or publish events."""
        # Arrange
        submission_adapter = Mock()
        dispute_adapter = Mock()
        schema_validation_adapter = Mock()
        match_service = Mock()
        event_bus = Mock()
        
        submission_dto = MatchResultSubmissionDTO(
            id=14,
            match_id=140,
            submitted_by_user_id=1400,
            submitted_by_team_id=70,
            raw_result_payload={'winner_team_id': 70, 'loser_team_id': 71, 'score': '13-8'},
            proof_screenshot_url='https://example.com/proof14.png',
            status='pending',
            submitted_at=datetime.now(),
            confirmed_at=None,
            finalized_at=None,
            auto_confirm_deadline=datetime.now() + timedelta(hours=24),
            confirmed_by_user_id=None,
            submitter_notes='',
            organizer_notes='',
        )
        
        verification_result = ResultVerificationResultDTO.create_valid(
            calculated_scores={'winner_team_id': 70, 'loser_team_id': 71, 'winner_score': 13, 'loser_score': 8},
            metadata={'game_slug': 'valorant'},
        )
        
        submission_adapter.get_submission.return_value = submission_dto
        schema_validation_adapter.validate_payload.return_value = verification_result
        
        service = ResultVerificationService(
            result_submission_adapter=submission_adapter,
            dispute_adapter=dispute_adapter,
            schema_validation_adapter=schema_validation_adapter,
            match_service=match_service,
        )
        service.event_bus = event_bus
        
        with patch.object(service, '_get_game_slug_for_submission', return_value='valorant'):
            # Act
            result = service.dry_run_verification(14)
        
        # Assert
        assert result.is_valid is True
        dispute_adapter.log_verification_step.assert_not_called()
        event_bus.publish.assert_not_called()


class TestArchitectureCompliance:
    """Test architecture compliance (no ORM imports)."""
    
    def test_result_verification_service_never_imports_orm_directly(self):
        """ResultVerificationService must never import ORM models directly."""
        import inspect
        from apps.tournament_ops.services import result_verification_service
        
        source = inspect.getsource(result_verification_service)
        
        # Should not contain module-level ORM imports
        assert 'from apps.tournaments.models import' not in source
        assert 'from apps.organizations.models import' not in source
        assert 'from django.db import models' not in source
        
        # Method-level imports in _get_game_slug_for_submission are OK
        # (They're inside a method, not at module level)
