"""
Sponsorship Services
Business logic for sponsor management, inquiries, and monetization
"""
from django.db.models import Q, Sum, Avg, Count
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta

from apps.teams.models.sponsorship import (
    TeamSponsor,
    SponsorInquiry,
    TeamMerchItem,
    TeamPromotion,
)


class SponsorshipService:
    """Service for managing team sponsorships"""
    
    @staticmethod
    def get_active_sponsors(team, tier=None):
        """
        Get active sponsors for a team, optionally filtered by tier
        """
        sponsors = TeamSponsor.objects.filter(
            team=team,
            status='active',
            is_active=True
        )
        
        if tier:
            sponsors = sponsors.filter(sponsor_tier=tier)
        
        return sponsors.order_by('display_order', '-sponsor_tier')
    
    @staticmethod
    def create_sponsor(team, sponsor_data, approved_by=None):
        """
        Create a new sponsor for a team
        """
        sponsor = TeamSponsor.objects.create(
            team=team,
            **sponsor_data
        )
        
        if approved_by and sponsor_data.get('status') == 'active':
            sponsor.approve(approved_by)
        
        return sponsor
    
    @staticmethod
    def approve_sponsor(sponsor, user):
        """
        Approve a pending sponsor
        """
        if sponsor.status != 'pending':
            raise ValueError(f"Cannot approve sponsor with status: {sponsor.status}")
        
        sponsor.approve(user)
        
        # Send notification to team (Task 9 integration)
        from apps.notifications.services import NotificationService
        try:
            NotificationService.notify_sponsor_approved(sponsor)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send sponsor approval notification: {e}")
        
        return sponsor
    
    @staticmethod
    def expire_sponsors():
        """
        Mark expired sponsors as expired (to be run daily via cron)
        """
        today = timezone.now().date()
        expired = TeamSponsor.objects.filter(
            status='active',
            end_date__lt=today
        )
        
        count = expired.update(status='expired', is_active=False)
        return count
    
    @staticmethod
    def get_sponsor_analytics(team):
        """
        Get analytics for all team sponsors
        """
        sponsors = team.sponsors.all()
        
        return {
            'total_sponsors': sponsors.count(),
            'active_sponsors': sponsors.filter(status='active', is_active=True).count(),
            'pending_sponsors': sponsors.filter(status='pending').count(),
            'expired_sponsors': sponsors.filter(status='expired').count(),
            'total_clicks': sponsors.aggregate(total=Sum('click_count'))['total'] or 0,
            'total_impressions': sponsors.aggregate(total=Sum('impression_count'))['total'] or 0,
            'total_deal_value': sponsors.filter(
                status='active'
            ).aggregate(total=Sum('deal_value'))['total'] or 0,
            'sponsors_by_tier': {
                tier[0]: sponsors.filter(sponsor_tier=tier[0], is_active=True).count()
                for tier in TeamSponsor.TIER_CHOICES
            }
        }
    
    @staticmethod
    def get_top_sponsors(team, limit=5):
        """
        Get top performing sponsors by clicks
        """
        return team.sponsors.filter(
            status='active',
            is_active=True
        ).order_by('-click_count')[:limit]


class SponsorInquiryService:
    """Service for managing sponsor inquiries"""
    
    @staticmethod
    def create_inquiry(team, inquiry_data, request=None):
        """
        Create a new sponsor inquiry
        """
        # Add IP and user agent if request provided
        if request:
            inquiry_data['ip_address'] = SponsorInquiryService._get_client_ip(request)
            inquiry_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        inquiry = SponsorInquiry.objects.create(
            team=team,
            **inquiry_data
        )
        
        # Send notification email to team admins
        SponsorInquiryService._notify_team_admins(inquiry)
        
        return inquiry
    
    @staticmethod
    def check_rate_limit(ip_address, limit=3):
        """
        Check if IP has exceeded inquiry rate limit (default: 3 per day)
        """
        today_start = timezone.now().replace(hour=0, minute=0, second=0)
        count = SponsorInquiry.objects.filter(
            ip_address=ip_address,
            created_at__gte=today_start
        ).count()
        
        return count < limit
    
    @staticmethod
    def convert_inquiry_to_sponsor(inquiry, sponsor_data, approved_by):
        """
        Convert an inquiry to an actual sponsor
        """
        # Create sponsor from inquiry
        sponsor = TeamSponsor.objects.create(
            team=inquiry.team,
            sponsor_name=sponsor_data.get('sponsor_name', inquiry.company_name),
            contact_name=inquiry.contact_name,
            contact_email=inquiry.contact_email,
            contact_phone=inquiry.contact_phone,
            sponsor_link=inquiry.website or '',
            sponsor_tier=inquiry.interested_tier or 'bronze',
            **{k: v for k, v in sponsor_data.items() if k not in ['sponsor_name']}
        )
        
        # Link inquiry to sponsor
        inquiry.convert_to_sponsor(sponsor)
        
        # Approve sponsor
        sponsor.approve(approved_by)
        
        # Send confirmation email to sponsor
        SponsorInquiryService._send_approval_email(inquiry, sponsor)
        
        return sponsor
    
    @staticmethod
    def get_pending_inquiries(team):
        """
        Get pending inquiries for a team
        """
        return team.sponsor_inquiries.filter(
            status='pending'
        ).order_by('-created_at')
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def _notify_team_admins(inquiry):
        """Send notification email to team admins (Task 9 integration)"""
        from apps.notifications.services import notify
        
        # Get team captain and admin users
        recipients = []
        if inquiry.team.captain and inquiry.team.captain.user:
            recipients.append(inquiry.team.captain.user)
        
        # Send notification if we have recipients
        if recipients:
            try:
                notify(
                    recipients=recipients,
                    ntype='sponsor_inquiry',
                    title=f"New Sponsor Inquiry for {inquiry.team.name}",
                    body=f"{inquiry.company_name} has submitted a sponsorship inquiry. Company: {inquiry.company_name}, Contact: {inquiry.contact_name}",
                    url=f"/teams/{inquiry.team.slug}/sponsors/",
                    email_subject=f"New Sponsor Inquiry - {inquiry.company_name}",
                    email_template='notifications/sponsor_inquiry',
                    email_ctx={'inquiry': inquiry}
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to notify team admins of sponsor inquiry: {e}")

    
    @staticmethod
    def _send_approval_email(inquiry, sponsor):
        """Send approval confirmation to sponsor (Task 9 integration)"""
        from django.core.mail import send_mail
        from django.conf import settings
        from django.template.loader import render_to_string
        
        try:
            # Send email to sponsor contact
            subject = f"Sponsorship Approved - {inquiry.team.name}"
            context = {
                'inquiry': inquiry,
                'sponsor': sponsor,
                'team': inquiry.team,
            }
            
            # Render email templates
            html_message = render_to_string('emails/sponsor_approved.html', context)
            text_message = render_to_string('emails/sponsor_approved.txt', context)
            
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[inquiry.contact_email],
                html_message=html_message,
                fail_silently=True
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to send approval email to sponsor: {e}")


class MerchandiseService:
    """Service for managing team merchandise"""
    
    @staticmethod
    def get_active_merchandise(team, category=None, featured_only=False):
        """
        Get active merchandise for a team
        """
        merch = team.merchandise.filter(is_active=True)
        
        if category:
            merch = merch.filter(category=category)
        
        if featured_only:
            merch = merch.filter(is_featured=True)
        
        return merch.order_by('-is_featured', 'display_order', '-created_at')
    
    @staticmethod
    def create_merch_item(team, item_data):
        """
        Create a new merchandise item
        """
        return TeamMerchItem.objects.create(
            team=team,
            **item_data
        )
    
    @staticmethod
    def update_stock(item, quantity):
        """
        Update merchandise stock after purchase
        """
        if item.unlimited_stock:
            return item
        
        item.stock = max(0, quantity)
        item.is_in_stock = item.stock > 0
        item.save(update_fields=['stock', 'is_in_stock'])
        
        return item
    
    @staticmethod
    def get_merch_analytics(team):
        """
        Get analytics for team merchandise
        """
        merch = team.merchandise.all()
        
        return {
            'total_items': merch.count(),
            'active_items': merch.filter(is_active=True).count(),
            'featured_items': merch.filter(is_featured=True).count(),
            'out_of_stock': merch.filter(is_in_stock=False, unlimited_stock=False).count(),
            'total_views': merch.aggregate(total=Sum('view_count'))['total'] or 0,
            'total_clicks': merch.aggregate(total=Sum('click_count'))['total'] or 0,
            'items_by_category': {
                cat[0]: merch.filter(category=cat[0], is_active=True).count()
                for cat in TeamMerchItem.CATEGORY_CHOICES
            }
        }
    
    @staticmethod
    def get_top_merchandise(team, limit=5):
        """
        Get top selling merchandise by clicks
        """
        return team.merchandise.filter(
            is_active=True
        ).order_by('-click_count')[:limit]
    
    @staticmethod
    def mark_low_stock_items(team, threshold=10):
        """
        Get items with low stock
        """
        return team.merchandise.filter(
            is_active=True,
            unlimited_stock=False,
            stock__lte=threshold,
            stock__gt=0
        ).order_by('stock')


class PromotionService:
    """Service for managing team promotions"""
    
    @staticmethod
    def get_active_promotions(promotion_type=None):
        """
        Get active promotions, optionally filtered by type
        """
        promotions = TeamPromotion.objects.filter(
            status='active',
            is_active=True
        )
        
        if promotion_type:
            promotions = promotions.filter(promotion_type=promotion_type)
        
        return promotions.order_by('-start_at')
    
    @staticmethod
    def create_promotion(team, promotion_data, approved_by=None):
        """
        Create a new promotion
        """
        promotion = TeamPromotion.objects.create(
            team=team,
            **promotion_data
        )
        
        if approved_by and promotion_data.get('status') in ['paid', 'active']:
            promotion.approve(approved_by)
        
        return promotion
    
    @staticmethod
    def approve_promotion(promotion, user):
        """
        Approve a pending promotion
        """
        if promotion.status != 'pending':
            raise ValueError(f"Cannot approve promotion with status: {promotion.status}")
        
        promotion.approve(user)
        
        # Send notification (Task 9 integration)
        from apps.notifications.services import NotificationService
        try:
            # Notification is sent via signal when promotion becomes 'active'
            # Signal handler in apps/teams/signals.py handles this
            pass  # No manual notification needed - handled by signal
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in promotion approval notification: {e}")
        
        return promotion
    
    @staticmethod
    def expire_promotions():
        """
        Mark expired promotions as completed (to be run hourly via cron)
        """
        now = timezone.now()
        expired = TeamPromotion.objects.filter(
            status='active',
            end_at__lt=now
        )
        
        count = expired.update(status='completed', is_active=False)
        return count
    
    @staticmethod
    def activate_scheduled_promotions():
        """
        Activate promotions that are scheduled to start (to be run hourly via cron)
        """
        now = timezone.now()
        to_activate = TeamPromotion.objects.filter(
            status='paid',
            start_at__lte=now,
            end_at__gt=now
        )
        
        count = 0
        for promotion in to_activate:
            promotion.is_active = True
            promotion.status = 'active'
            promotion.save()
            count += 1
        
        return count
    
    @staticmethod
    def get_promotion_analytics(team):
        """
        Get analytics for team promotions
        """
        promotions = team.promotions.all()
        
        return {
            'total_promotions': promotions.count(),
            'active_promotions': promotions.filter(status='active', is_active=True).count(),
            'pending_promotions': promotions.filter(status='pending').count(),
            'completed_promotions': promotions.filter(status='completed').count(),
            'total_spent': promotions.filter(
                status__in=['paid', 'active', 'completed']
            ).aggregate(total=Sum('paid_amount'))['total'] or 0,
            'total_impressions': promotions.aggregate(total=Sum('impression_count'))['total'] or 0,
            'total_clicks': promotions.aggregate(total=Sum('click_count'))['total'] or 0,
            'total_conversions': promotions.aggregate(total=Sum('conversion_count'))['total'] or 0,
            'average_ctr': promotions.filter(
                impression_count__gt=0
            ).annotate(
                ctr=(Sum('click_count') * 100.0 / Sum('impression_count'))
            ).aggregate(avg=Avg('ctr'))['avg'] or 0,
        }
    
    @staticmethod
    def get_featured_teams(promotion_type='featured_homepage', limit=6):
        """
        Get featured teams for homepage or hub
        """
        promotions = PromotionService.get_active_promotions(promotion_type)[:limit]
        return [p.team for p in promotions]


class RevenueReportingService:
    """Service for revenue reporting and analytics"""
    
    @staticmethod
    def get_team_revenue_summary(team):
        """
        Get comprehensive revenue summary for a team
        """
        sponsors = team.sponsors.filter(status='active')
        promotions = team.promotions.filter(status__in=['paid', 'active', 'completed'])
        
        return {
            'sponsor_revenue': sponsors.aggregate(
                total=Sum('deal_value')
            )['total'] or 0,
            'promotion_spending': promotions.aggregate(
                total=Sum('paid_amount')
            )['total'] or 0,
            'active_sponsors': sponsors.count(),
            'total_promotions': promotions.count(),
            'sponsor_breakdown': [
                {
                    'name': s.sponsor_name,
                    'tier': s.get_sponsor_tier_display(),
                    'value': s.deal_value,
                    'start_date': s.start_date,
                    'end_date': s.end_date,
                }
                for s in sponsors
            ],
            'promotion_breakdown': [
                {
                    'type': p.get_promotion_type_display(),
                    'amount': p.paid_amount,
                    'impressions': p.impression_count,
                    'clicks': p.click_count,
                    'ctr': p.get_ctr(),
                }
                for p in promotions
            ]
        }
    
    @staticmethod
    def export_sponsor_report(team):
        """
        Export sponsor report data (for CSV generation)
        """
        sponsors = team.sponsors.all()
        
        return [
            {
                'Sponsor Name': s.sponsor_name,
                'Tier': s.get_sponsor_tier_display(),
                'Status': s.get_status_display(),
                'Start Date': s.start_date,
                'End Date': s.end_date,
                'Deal Value': s.deal_value or 0,
                'Currency': s.currency,
                'Impressions': s.impression_count,
                'Clicks': s.click_count,
                'CTR': f"{(s.click_count / s.impression_count * 100) if s.impression_count > 0 else 0:.2f}%",
                'Days Remaining': s.days_remaining(),
            }
            for s in sponsors
        ]
    
    @staticmethod
    def export_merch_report(team):
        """
        Export merchandise report data (for CSV generation)
        """
        merchandise = team.merchandise.all()
        
        return [
            {
                'Title': m.title,
                'SKU': m.sku,
                'Category': m.get_category_display(),
                'Price': m.price,
                'Sale Price': m.sale_price or '',
                'Currency': m.currency,
                'Stock': 'Unlimited' if m.unlimited_stock else m.stock,
                'In Stock': 'Yes' if m.is_in_stock else 'No',
                'Featured': 'Yes' if m.is_featured else 'No',
                'Views': m.view_count,
                'Clicks': m.click_count,
                'CTR': f"{(m.click_count / m.view_count * 100) if m.view_count > 0 else 0:.2f}%",
            }
            for m in merchandise
        ]
    
    @staticmethod
    def export_promotion_report(team):
        """
        Export promotion report data (for CSV generation)
        """
        promotions = team.promotions.all()
        
        return [
            {
                'Type': p.get_promotion_type_display(),
                'Title': p.title,
                'Status': p.get_status_display(),
                'Start Date': p.start_at,
                'End Date': p.end_at,
                'Amount': p.paid_amount,
                'Currency': p.currency,
                'Impressions': p.impression_count,
                'Clicks': p.click_count,
                'Conversions': p.conversion_count,
                'CTR': f"{p.get_ctr():.2f}%",
                'Conversion Rate': f"{p.get_conversion_rate():.2f}%",
            }
            for p in promotions
        ]
