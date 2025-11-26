# Generated migration for registration system constraints and indexes
# Based on Documents/Planning/PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0012_create_webhook_models'),
    ]

    operations = [
        # Add waitlist fields to Registration
        migrations.AddField(
            model_name='registration',
            name='waitlist_position',
            field=models.IntegerField(null=True, blank=True, help_text='Position in waitlist queue'),
        ),
        
        # Add fee waiver status to Payment
        migrations.AddField(
            model_name='payment',
            name='waived',
            field=models.BooleanField(default=False, help_text='Fee waived by organizer'),
        ),
        migrations.AddField(
            model_name='payment',
            name='waive_reason',
            field=models.TextField(blank=True, help_text='Reason for fee waiver'),
        ),
        
        # Add resubmission tracking to Payment
        migrations.AddField(
            model_name='payment',
            name='resubmission_count',
            field=models.IntegerField(default=0, help_text='Number of times payment was resubmitted'),
        ),
        
        # NOTE: file_type column already exists on Payment (created in initial migration)
        # No-op: historical duplication removed to prevent duplicate column creation.
        
        # Add waitlist status to Registration.STATUS_CHOICES
        migrations.AlterField(
            model_name='registration',
            name='status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('pending', 'Pending'),
                    ('payment_submitted', 'Payment Submitted'),
                    ('confirmed', 'Confirmed'),
                    ('rejected', 'Rejected'),
                    ('cancelled', 'Cancelled'),
                    ('waitlisted', 'Waitlisted'),
                    ('no_show', 'No Show'),
                ],
                default='pending',
                db_index=True,
                help_text='Current registration status'
            ),
        ),
        
        # Add waived status to Payment.STATUS_CHOICES
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('pending', 'Pending'),
                    ('submitted', 'Submitted'),
                    ('verified', 'Verified'),
                    ('rejected', 'Rejected'),
                    ('refunded', 'Refunded'),
                    ('waived', 'Fee Waived'),
                ],
                default='pending',
                db_index=True,
                help_text='Payment verification status'
            ),
        ),
        
        # Add database constraints using raw SQL
        migrations.RunSQL(
            sql="""
            -- Constraint 1: User XOR Team (must have one, not both)
            ALTER TABLE tournaments_registration 
            ADD CONSTRAINT chk_registration_participant_type 
            CHECK (
                (user_id IS NOT NULL AND team_id IS NULL) OR 
                (user_id IS NULL AND team_id IS NOT NULL)
            );
            
            -- Constraint 2: Unique user registration per tournament (excluding deleted)
            CREATE UNIQUE INDEX idx_registration_user_tournament 
            ON tournaments_registration(tournament_id, user_id) 
            WHERE user_id IS NOT NULL AND is_deleted = false;
            
            -- Constraint 3: Unique team registration per tournament (excluding deleted)
            CREATE UNIQUE INDEX idx_registration_team_tournament 
            ON tournaments_registration(tournament_id, team_id) 
            WHERE team_id IS NOT NULL AND is_deleted = false;
            
            -- Constraint 4: Unique slot number per tournament (excluding deleted and null slots)
            CREATE UNIQUE INDEX idx_registration_slot_tournament 
            ON tournaments_registration(tournament_id, slot_number) 
            WHERE slot_number IS NOT NULL AND is_deleted = false;
            
            -- Constraint 5: Payment verification constraint
            ALTER TABLE tournaments_payment 
            ADD CONSTRAINT chk_payment_verification 
            CHECK (
                (status = 'verified' AND verified_by_id IS NOT NULL AND verified_at IS NOT NULL) OR 
                (status != 'verified')
            );
            
            -- Constraint 6: Payment amount must be positive (unless waived)
            ALTER TABLE tournaments_payment 
            ADD CONSTRAINT chk_payment_amount_positive 
            CHECK (amount >= 0);
            
            -- Index 1: GIN index on registration_data JSONB for efficient queries
            CREATE INDEX idx_registration_data_gin 
            ON tournaments_registration USING GIN(registration_data);
            
            -- Index 2: Composite index for waitlist queries
            CREATE INDEX idx_registration_waitlist 
            ON tournaments_registration(tournament_id, waitlist_position) 
            WHERE status = 'waitlisted' AND is_deleted = false;
            
            -- Index 3: Index on payment method for analytics
            CREATE INDEX idx_payment_method 
            ON tournaments_payment(payment_method);
            
            -- Index 4: Index on payment submitted_at for deadline tracking
            CREATE INDEX idx_payment_created_at 
            ON tournaments_payment(submitted_at);
            
            -- Index 5: Composite index for payment verification queue (by status and submitted_at)
            CREATE INDEX idx_payment_verification_queue 
            ON tournaments_payment(status, submitted_at) 
            WHERE status IN ('pending', 'submitted');
            """,
            reverse_sql="""
            -- Drop constraints
            ALTER TABLE tournaments_registration DROP CONSTRAINT IF EXISTS chk_registration_participant_type;
            ALTER TABLE tournaments_payment DROP CONSTRAINT IF EXISTS chk_payment_verification;
            ALTER TABLE tournaments_payment DROP CONSTRAINT IF EXISTS chk_payment_amount_positive;
            
            -- Drop indexes
            DROP INDEX IF EXISTS idx_registration_user_tournament;
            DROP INDEX IF EXISTS idx_registration_team_tournament;
            DROP INDEX IF EXISTS idx_registration_slot_tournament;
            DROP INDEX IF EXISTS idx_registration_data_gin;
            DROP INDEX IF EXISTS idx_registration_waitlist;
            DROP INDEX IF EXISTS idx_payment_method;
            DROP INDEX IF EXISTS idx_payment_created_at;
            DROP INDEX IF EXISTS idx_payment_verification_queue;
            """
        ),
    ]
