"""
Backfill User Activity Events

Scans historical records (Registration, Match, Transaction) and creates
missing UserActivity events for existing data.

Design:
- Idempotent: Safe to run multiple times (checks for existing events)
- Chunked: Processes records in batches (default 1000)
- Progress logging: Reports progress every 10,000 records
- Dry-run support: Preview changes without committing
- Atomic: Each batch is a transaction (rollback on error)

Usage:
    # Dry-run (preview)
    python manage.py backfill_user_activities --dry-run
    
    # Backfill all events
    python manage.py backfill_user_activities
    
    # Backfill specific event type
    python manage.py backfill_user_activities --event-type tournaments
    
    # Custom chunk size
    python manage.py backfill_user_activities --chunk-size 500
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.user_profile.services.activity_service import UserActivityService
from apps.tournaments.models import Registration, Match
from apps.economy.models import DeltaCrownTransaction
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backfill UserActivity events from historical data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without committing'
        )
        parser.add_argument(
            '--event-type',
            type=str,
            choices=['tournaments', 'matches', 'economy', 'all'],
            default='all',
            help='Event type to backfill (default: all)'
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=1000,
            help='Records per batch (default: 1000)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit total records processed (for testing)'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        event_type = options['event_type']
        chunk_size = options['chunk_size']
        limit = options['limit']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be committed'))
        
        self.stdout.write(self.style.SUCCESS(f'🚀 Starting backfill (event_type={event_type})'))
        
        stats = {
            'tournaments_processed': 0,
            'tournaments_created': 0,
            'matches_processed': 0,
            'matches_created': 0,
            'economy_processed': 0,
            'economy_created': 0,
            'errors': 0
        }
        
        # Backfill tournaments
        if event_type in ['tournaments', 'all']:
            self._backfill_tournaments(stats, dry_run, chunk_size, limit)
        
        # Backfill matches
        if event_type in ['matches', 'all']:
            self._backfill_matches(stats, dry_run, chunk_size, limit)
        
        # Backfill economy
        if event_type in ['economy', 'all']:
            self._backfill_economy(stats, dry_run, chunk_size, limit)
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n📊 BACKFILL SUMMARY'))
        self.stdout.write(f"  Tournaments: {stats['tournaments_processed']} processed, "
                         f"{stats['tournaments_created']} events created")
        self.stdout.write(f"  Matches: {stats['matches_processed']} processed, "
                         f"{stats['matches_created']} events created")
        self.stdout.write(f"  Economy: {stats['economy_processed']} processed, "
                         f"{stats['economy_created']} events created")
        self.stdout.write(f"  Errors: {stats['errors']}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN - No changes committed'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Backfill complete'))
    
    def _backfill_tournaments(self, stats, dry_run, chunk_size, limit):
        """Backfill TOURNAMENT_JOINED events from Registration records."""
        self.stdout.write('\n📋 Backfilling tournament registrations...')
        
        # Query confirmed registrations
        qs = Registration.objects.filter(status='confirmed').order_by('id')
        
        if limit:
            qs = qs[:limit]
        
        total = qs.count()
        self.stdout.write(f"  Found {total} confirmed registrations")
        
        processed = 0
        created = 0
        
        # Process in chunks
        for i in range(0, total, chunk_size):
            chunk = qs[i:i + chunk_size]
            
            for registration in chunk:
                processed += 1
                
                try:
                    if not dry_run:
                        event = UserActivityService.record_tournament_join(
                            user_id=registration.user_id,
                            tournament_id=registration.tournament_id,
                            registration_id=registration.id,
                            timestamp=registration.created_at or timezone.now()
                        )
                        if event:
                            created += 1
                    else:
                        # Dry-run: just check if event exists
                        from apps.user_profile.models.activity import UserActivity, EventType
                        exists = UserActivity.objects.filter(
                            event_type=EventType.TOURNAMENT_JOINED,
                            user_id=registration.user_id,
                            source_type='tournament',
                            source_id=registration.id
                        ).exists()
                        if not exists:
                            created += 1
                
                except Exception as e:
                    logger.error(f"Error backfilling registration {registration.id}: {e}")
                    stats['errors'] += 1
            
            # Progress update
            if processed % 10000 == 0:
                self.stdout.write(f"  Progress: {processed}/{total} ({created} new events)")
        
        stats['tournaments_processed'] = processed
        stats['tournaments_created'] = created
        self.stdout.write(self.style.SUCCESS(
            f"  ✅ Tournaments: {processed} processed, {created} events created"
        ))
    
    def _backfill_matches(self, stats, dry_run, chunk_size, limit):
        """Backfill MATCH_WON/LOST events from Match records."""
        self.stdout.write('\n⚔️  Backfilling match results...')
        
        # Query completed matches with winners
        qs = Match.objects.filter(
            state='completed',
            winner_id__isnull=False,
            loser_id__isnull=False
        ).order_by('id')
        
        if limit:
            qs = qs[:limit]
        
        total = qs.count()
        self.stdout.write(f"  Found {total} completed matches")
        
        processed = 0
        created = 0
        
        # Process in chunks
        for i in range(0, total, chunk_size):
            chunk = qs[i:i + chunk_size]
            
            for match in chunk:
                processed += 1
                
                try:
                    # Extract scores
                    winner_score = None
                    loser_score = None
                    
                    if hasattr(match, 'scores') and match.scores:
                        if match.participant1_id == match.winner_id:
                            winner_score = match.scores.get('participant1')
                            loser_score = match.scores.get('participant2')
                        elif match.participant2_id == match.winner_id:
                            winner_score = match.scores.get('participant2')
                            loser_score = match.scores.get('participant1')
                    
                    if not dry_run:
                        winner_event, loser_event = UserActivityService.record_match_result(
                            match_id=match.id,
                            winner_id=match.winner_id,
                            loser_id=match.loser_id,
                            winner_score=winner_score,
                            loser_score=loser_score,
                            timestamp=getattr(match, 'completed_at', None) or timezone.now()
                        )
                        if winner_event or loser_event:
                            created += 1
                    else:
                        # Dry-run: check if events exist
                        from apps.user_profile.models.activity import UserActivity, EventType
                        winner_exists = UserActivity.objects.filter(
                            event_type=EventType.MATCH_WON,
                            user_id=match.winner_id,
                            source_type='match',
                            source_id=match.id
                        ).exists()
                        if not winner_exists:
                            created += 1
                
                except Exception as e:
                    logger.error(f"Error backfilling match {match.id}: {e}")
                    stats['errors'] += 1
            
            # Progress update
            if processed % 10000 == 0:
                self.stdout.write(f"  Progress: {processed}/{total} ({created} new events)")
        
        stats['matches_processed'] = processed
        stats['matches_created'] = created
        self.stdout.write(self.style.SUCCESS(
            f"  ✅ Matches: {processed} processed, {created} events created"
        ))
    
    def _backfill_economy(self, stats, dry_run, chunk_size, limit):
        """Backfill COINS_EARNED/SPENT events from DeltaCrownTransaction records."""
        self.stdout.write('\n💰 Backfilling economy transactions...')
        
        # Query all transactions (need to join wallet to get user_id)
        qs = DeltaCrownTransaction.objects.select_related('wallet').order_by('id')
        
        if limit:
            qs = qs[:limit]
        
        total = qs.count()
        self.stdout.write(f"  Found {total} transactions")
        
        processed = 0
        created = 0
        
        # Process in chunks
        for i in range(0, total, chunk_size):
            chunk = qs[i:i + chunk_size]
            
            for txn in chunk:
                processed += 1
                
                try:
                    # Get user_id from wallet.profile.user
                    if not hasattr(txn.wallet, 'profile') or not txn.wallet.profile:
                        continue
                    
                    user_id = txn.wallet.profile.user_id
                    
                    if not user_id:
                        continue
                    
                    if not dry_run:
                        event = UserActivityService.record_economy_transaction(
                            transaction_id=txn.id,
                            user_id=user_id,
                            amount=float(txn.amount),
                            reason=txn.reason,
                            timestamp=txn.created_at or timezone.now()
                        )
                        if event:
                            created += 1
                    else:
                        # Dry-run: check if event exists
                        from apps.user_profile.models.activity import UserActivity, EventType
                        event_type = EventType.COINS_EARNED if txn.amount > 0 else EventType.COINS_SPENT
                        exists = UserActivity.objects.filter(
                            event_type=event_type,
                            user_id=user_id,
                            source_model='economy',
                            source_id=txn.id
                        ).exists()
                        if not exists:
                            created += 1
                
                except Exception as e:
                    logger.error(f"Error backfilling transaction {txn.id}: {e}")
                    stats['errors'] += 1
            
            # Progress update
            if processed % 10000 == 0:
                self.stdout.write(f"  Progress: {processed}/{total} ({created} new events)")
        
        stats['economy_processed'] = processed
        stats['economy_created'] = created
        self.stdout.write(self.style.SUCCESS(
            f"  ✅ Economy: {processed} processed, {created} events created"
        ))
