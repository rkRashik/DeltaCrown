# apps/support/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import FAQ, Testimonial, ContactMessage


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question_preview', 'category', 'is_active', 'is_featured', 'order', 'updated_at']
    list_filter = ['category', 'is_active', 'is_featured', 'created_at']
    search_fields = ['question', 'answer']
    list_editable = ['order', 'is_active', 'is_featured']
    ordering = ['order', '-created_at']
    
    fieldsets = (
        ('Question Details', {
            'fields': ('category', 'question', 'answer')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'is_featured', 'order'),
            'description': 'Featured FAQs appear in footer/homepage. Order determines display sequence.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def question_preview(self, obj):
        return obj.question[:80] + ('...' if len(obj.question) > 80 else '')
    question_preview.short_description = 'Question'
    
    actions = ['make_featured', 'remove_featured', 'activate', 'deactivate']
    
    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f"{queryset.count()} FAQs marked as featured")
    make_featured.short_description = "Mark as featured (show in footer)"
    
    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, f"{queryset.count()} FAQs removed from featured")
    remove_featured.short_description = "Remove from featured"
    
    def activate(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} FAQs activated")
    activate.short_description = "Activate FAQs"
    
    def deactivate(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} FAQs deactivated")
    deactivate.short_description = "Deactivate FAQs"


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['name', 'team_name', 'rating_display', 'show_on_homepage', 'is_verified', 'order', 'created_at']
    list_filter = ['rating', 'show_on_homepage', 'is_verified', 'created_at']
    search_fields = ['name', 'team_name', 'testimonial_text']
    list_editable = ['order', 'show_on_homepage', 'is_verified']
    ordering = ['order', '-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'name', 'team_name', 'avatar_text')
        }),
        ('Testimonial Content', {
            'fields': ('rating', 'testimonial_text', 'prize_won', 'tournament_name')
        }),
        ('Display Settings', {
            'fields': ('show_on_homepage', 'is_verified', 'order'),
            'description': 'Only testimonials with "Show on homepage" will appear on the homepage.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'approved_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']
    
    def rating_display(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        color = '#facc15' if obj.rating >= 4 else '#f59e0b' if obj.rating >= 3 else '#ef4444'
        return format_html(
            '<span style="color: {}; font-size: 16px;">{}</span>',
            color,
            stars
        )
    rating_display.short_description = 'Rating'
    
    actions = ['feature_on_homepage', 'remove_from_homepage', 'verify_testimonial']
    
    def feature_on_homepage(self, request, queryset):
        queryset.update(show_on_homepage=True)
        self.message_user(request, f"{queryset.count()} testimonials added to homepage")
    feature_on_homepage.short_description = "Show on homepage"
    
    def remove_from_homepage(self, request, queryset):
        queryset.update(show_on_homepage=False)
        self.message_user(request, f"{queryset.count()} testimonials removed from homepage")
    remove_from_homepage.short_description = "Hide from homepage"
    
    def verify_testimonial(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f"{queryset.count()} testimonials verified")
    verify_testimonial.short_description = "Mark as verified"


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject_preview', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    list_editable = ['status', 'priority']
    readonly_fields = ['name', 'email', 'user', 'subject', 'message', 'created_at', 'ip_address', 'user_agent']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Sender Information', {
            'fields': ('name', 'email', 'user')
        }),
        ('Message Content', {
            'fields': ('subject', 'message')
        }),
        ('Status & Management', {
            'fields': ('status', 'priority', 'resolved_at', 'admin_notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def subject_preview(self, obj):
        return obj.subject[:50] + ('...' if len(obj.subject) > 50 else '')
    subject_preview.short_description = 'Subject'
    
    actions = ['mark_as_resolved', 'mark_as_in_progress', 'mark_as_urgent']
    
    def mark_as_resolved(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='RESOLVED', resolved_at=timezone.now())
        self.message_user(request, f"{queryset.count()} messages marked as resolved")
    mark_as_resolved.short_description = "Mark as resolved"
    
    def mark_as_in_progress(self, request, queryset):
        queryset.update(status='IN_PROGRESS')
        self.message_user(request, f"{queryset.count()} messages marked as in progress")
    mark_as_in_progress.short_description = "Mark as in progress"
    
    def mark_as_urgent(self, request, queryset):
        queryset.update(priority='URGENT')
        self.message_user(request, f"{queryset.count()} messages marked as urgent")
    mark_as_urgent.short_description = "Mark as urgent"
