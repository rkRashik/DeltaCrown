# Generated manually - add PaymentVerification model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0010_add_s3_migration_tracking'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentVerification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method', models.CharField(choices=[('bkash', 'bKash'), ('nagad', 'Nagad'), ('rocket', 'Rocket'), ('bank', 'Bank Transfer'), ('other', 'Other')], default='bkash', max_length=16)),
                ('payer_account_number', models.CharField(blank=True, help_text='Your bKash/Nagad/Rocket account number (payer)', max_length=32)),
                ('transaction_id', models.CharField(blank=True, help_text='Transaction ID from bKash/Nagad/Rocket', max_length=64)),
                ('reference_number', models.CharField(blank=True, help_text='Internal reference number for payment tracking', max_length=64, null=True)),
                ('amount_bdt', models.PositiveIntegerField(blank=True, null=True)),
                ('note', models.CharField(blank=True, max_length=255)),
                ('proof_image', models.ImageField(blank=True, null=True, upload_to='payments/proofs/')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('verified', 'Verified'), ('rejected', 'Rejected')], default='pending', max_length=16)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('reject_reason', models.TextField(blank=True)),
                ('last_action_reason', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('registration', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payment_verification', to='tournaments.registration')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Payment Verification',
                'verbose_name_plural': 'Payment Verifications',
                'db_table': 'tournaments_paymentverification',
            },
        ),
    ]
