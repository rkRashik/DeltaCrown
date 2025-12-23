# apps/user_profile/management/commands/reconcile_economy.py
"""
Reconcile Economy Command (UP-M3)

Reconciles profile economy fields with wallet/ledger (fixes drift).

Usage:
    python manage.py reconcile_economy --dry-run              # Preview changes
    python manage.py reconcile_economy --user-id 123          # Reconcile single user
    python manage.py reconcile_economy --all                  # Reconcile all users
    python manage.py reconcile_economy --all --batch-size 100 # Batch processing

Safety:
- Idempotent: Safe to rerun multiple times
- Atomic: Each user reconciled in separate transaction
- Never destructive: Only updates profile caches from ledger (source of truth)

Related: apps/user_profile/services/economy_sync.py
"""
from __future__ import annotations

import sys
from decimal import Decimal
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.apps import apps


class Command(BaseCommand):
    help = "Reconcile profile economy fields with wallet/ledger (UP-M3)"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without committing'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Reconcile single user by ID'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reconcile all users with wallets'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of users to process in each batch (default: 1000)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Max users to reconcile (for testing)'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_id = options.get('user_id')
        process_all = options.get('all')
        batch_size = options['batch_size']
        limit = options.get('limit')
        
        if not (user_id or process_all):
            raise CommandError('Must specify --user-id or --all')
        
        if user_id and process_all:
            raise CommandError('Cannot specify both --user-id and --all')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be committed\n'))
        
        # Import models
        DeltaCrownWallet = apps.get_model('economy', 'DeltaCrownWallet')
        UserProfile = apps.get_model('user_profile', 'UserProfile')
        
        # Get wallets to process
        if user_id:
            wallets = DeltaCrownWallet.objects.filter(
                profile__user_id=user_id
            ).select_related('profile')
            
            if not wallets.exists():
                self.stdout.write(self.style.ERROR(f'❌ User {user_id} has no wallet'))
                return
        else:
            wallets = DeltaCrownWallet.objects.select_related('profile').order_by('id')
            if limit:
                wallets = wallets[:limit]
        
        total = wallets.count()
        self.stdout.write(f'📋 Processing {total} wallets...\n')
        
        # Counters
        processed = 0
        balance_synced = 0
        earnings_synced = 0
        errors = 0
        
        # Process in batches
        wallet_ids = list(wallets.values_list('id', flat=True))
        
        for i in range(0, len(wallet_ids), batch_size):
            batch_ids = wallet_ids[i:i + batch_size]
            
            for wallet_id in batch_ids:
                try:
                    result = self._reconcile_wallet(wallet_id, dry_run=dry_run)
                    processed += 1
                    
                    if result['balance_synced']:
                        balance_synced += 1
                        self.stdout.write(
                            f"  💰 User {result['profile_id']}: "
                            f"Balance {result['balance_before']:.2f} → {result['balance_after']:.2f}"
                        )
                    
                    if result['earnings_synced']:
                        earnings_synced += 1
                        self.stdout.write(
                            f"  🏆 User {result['profile_id']}: "
                            f"Earnings {result['earnings_before']:.2f} → {result['earnings_after']:.2f}"
                        )
                    
                    # Progress every 100 wallets
                    if processed % 100 == 0:
                        self.stdout.write(f'  ... {processed}/{total} processed')
                
                except Exception as e:
                    errors += 1
                    self.stderr.write(self.style.ERROR(f'❌ Error processing wallet {wallet_id}: {e}'))
        
        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(f'📊 SUMMARY:')
        self.stdout.write(f'  Processed: {processed}')
        self.stdout.write(f'  Balance synced: {balance_synced}')
        self.stdout.write(f'  Earnings synced: {earnings_synced}')
        self.stdout.write(f'  Errors: {errors}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN - No changes committed'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Reconciliation complete'))
    
    def _reconcile_wallet(self, wallet_id: int, dry_run: bool) -> dict:
        """
        Reconcile a single wallet.
        
        Returns:
            dict with keys: profile_id, balance_synced, earnings_synced, balance_before, balance_after
        """
        from apps.user_profile.services.economy_sync import sync_wallet_to_profile, get_balance_drift
        
        if dry_run:
            # Read-only: Check drift without modifying
            DeltaCrownWallet = apps.get_model('economy', 'DeltaCrownWallet')
            DeltaCrownTransaction = apps.get_model('economy', 'DeltaCrownTransaction')
            
            wallet = DeltaCrownWallet.objects.select_related('profile').get(pk=wallet_id)
            profile = wallet.profile
            
            # Check balance drift
            drift_info = get_balance_drift(wallet_id)
            balance_synced = drift_info['has_drift']
            
            # Check earnings drift
            from django.db.models import Sum
            ledger_earnings = DeltaCrownTransaction.objects.filter(
                wallet=wallet,
                amount__gt=0
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            profile_earnings = float(profile.lifetime_earnings)
            earnings_synced = (abs(ledger_earnings - profile_earnings) > 0.01)
            
            return {
                'profile_id': profile.id,
                'balance_synced': balance_synced,
                'earnings_synced': earnings_synced,
                'balance_before': drift_info['profile_balance'],
                'balance_after': drift_info['wallet_balance'],
                'earnings_before': profile_earnings,
                'earnings_after': ledger_earnings,
            }
        else:
            # Write: Actually sync
            return sync_wallet_to_profile(wallet_id)
