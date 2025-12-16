# apps/support/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class FAQ(models.Model):
    """Frequently Asked Questions - Admin manageable"""
    
    CATEGORY_CHOICES = [
        ('GENERAL', 'General'),
        ('TOURNAMENTS', 'Tournaments'),
        ('PAYMENTS', 'Payments'),
        ('TECHNICAL', 'Technical Support'),
        ('TEAMS', 'Teams & Players'),
        ('RULES', 'Rules & Fair Play'),
    ]
    
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='GENERAL',
        help_text="Question category"
    )
    question = models.CharField(
        max_length=500,
        help_text="The question text"
    )
    answer = models.TextField(
        help_text="The answer (HTML allowed)"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Show on FAQ page"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Show on homepage/footer"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
    
    def __str__(self):
        return f"[{self.category}] {self.question[:50]}"


class Testimonial(models.Model):
    """User reviews and testimonials - Admin manageable"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='testimonials',
        null=True,
        blank=True,
        help_text="User who submitted (optional)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (overrides user name if set)"
    )
    team_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Team affiliation (e.g., 'Dhaka Dragons')"
    )
    avatar_text = models.CharField(
        max_length=2,
        blank=True,
        help_text="1-2 letters for avatar (e.g., 'RA')"
    )
    rating = models.IntegerField(
        default=5,
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
        help_text="Star rating (1-5)"
    )
    testimonial_text = models.TextField(
        help_text="The testimonial content"
    )
    prize_won = models.CharField(
        max_length=100,
        blank=True,
        help_text="Prize amount if applicable (e.g., '৳50,000')"
    )
    tournament_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Tournament won (optional)"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Verified winner/user"
    )
    show_on_homepage = models.BooleanField(
        default=False,
        help_text="Display on homepage"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "Testimonial"
        verbose_name_plural = "Testimonials"
    
    def __str__(self):
        return f"{self.name} - {self.rating}★ - {'Homepage' if self.show_on_homepage else 'Hidden'}"


class ContactMessage(models.Model):
    """Contact form submissions"""
    
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    # Sender Information
    name = models.CharField(max_length=120, help_text="Sender's name")
    email = models.EmailField(help_text="Sender's email address")
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_messages',
        help_text="Associated user if logged in"
    )
    
    # Message Content
    subject = models.CharField(max_length=200, help_text="Message subject")
    message = models.TextField(help_text="Message content")
    
    # Status & Priority
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='NEW',
        help_text="Current status"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='MEDIUM',
        help_text="Priority level"
    )
    
    # Metadata
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Sender's IP address"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Browser user agent"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the issue was resolved"
    )
    
    # Admin Notes
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal notes (not visible to user)"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.subject} [{self.status}]"
    
    @property
    def is_resolved(self):
        return self.status in ['RESOLVED', 'CLOSED']
