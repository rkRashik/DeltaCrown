"""
Template Rating and Review System Models

Allows tournament organizers to rate and review form templates they've used.
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class TemplateRating(models.Model):
    """
    Rating and review for a registration form template.
    
    Allows organizers to share their experience using templates, helping others
    choose appropriate templates for their tournaments.
    """
    
    template = models.ForeignKey(
        'tournaments.RegistrationFormTemplate',
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='template_ratings'
    )
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='template_ratings',
        help_text="Tournament where this template was used (optional)"
    )
    
    # Rating
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    
    # Review
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Short review title"
    )
    review = models.TextField(
        blank=True,
        help_text="Detailed review of the template"
    )
    
    # Aspects
    ease_of_use = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="How easy was it to use this template?"
    )
    participant_experience = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="How was the participant experience?"
    )
    data_quality = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Quality of data collected"
    )
    
    # Recommendations
    would_recommend = models.BooleanField(
        default=True,
        help_text="Would you recommend this template to others?"
    )
    
    # Engagement
    helpful_count = models.IntegerField(
        default=0,
        help_text="Number of users who found this review helpful"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Verification
    verified_usage = models.BooleanField(
        default=False,
        help_text="Verified that user actually used this template"
    )
    
    class Meta:
        db_table = 'tournaments_template_rating'
        ordering = ['-created_at']
        unique_together = [['template', 'user', 'tournament']]
        indexes = [
            models.Index(fields=['template', '-rating']),
            models.Index(fields=['template', '-helpful_count']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.template.name} ({self.rating}⭐)"
    
    def mark_helpful(self):
        """Increment helpful count"""
        self.helpful_count += 1
        self.save(update_fields=['helpful_count'])
    
    @property
    def average_aspect_rating(self):
        """Calculate average of all aspect ratings"""
        aspects = [
            self.ease_of_use,
            self.participant_experience,
            self.data_quality
        ]
        valid_aspects = [a for a in aspects if a is not None]
        if not valid_aspects:
            return None
        return sum(valid_aspects) / len(valid_aspects)


class RatingHelpful(models.Model):
    """
    Track which users found a rating helpful.
    
    Prevents duplicate "helpful" votes and allows users to track
    their feedback on reviews.
    """
    
    rating = models.ForeignKey(
        TemplateRating,
        on_delete=models.CASCADE,
        related_name='helpful_votes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='helpful_rating_votes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tournaments_rating_helpful'
        unique_together = [['rating', 'user']]
        indexes = [
            models.Index(fields=['rating', 'user']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} found rating #{self.rating.id} helpful"
