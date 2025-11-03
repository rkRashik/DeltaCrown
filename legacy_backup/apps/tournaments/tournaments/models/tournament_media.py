"""
TournamentMedia Model
Handles all media-related fields for tournaments including banners, thumbnails,
rules PDFs, and promotional images.

Part of Phase 1 - Core Tournament Models
"""

from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from typing import Optional
import os


class TournamentMedia(models.Model):
    """
    Media and visual assets for tournaments.
    
    This model handles all media-related fields that were previously part of
    the Tournament model. It provides centralized management of tournament
    visual assets.
    
    Fields:
    - banner: Main tournament banner image
    - thumbnail: Thumbnail for cards/listings
    - rules_pdf: Tournament rules document
    - promotional_image_1-3: Additional promotional images
    - social_media_image: Optimized for social sharing
    - created_at: Timestamp of creation
    - updated_at: Timestamp of last update
    """
    
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='media',
        help_text="Associated tournament"
    )
    
    # Main visual assets
    banner = models.ImageField(
        upload_to='tournaments/banners/',
        blank=True,
        null=True,
        help_text="Main tournament banner (recommended: 1920x1080px)"
    )
    
    thumbnail = models.ImageField(
        upload_to='tournaments/thumbnails/',
        blank=True,
        null=True,
        help_text="Thumbnail for cards and listings (recommended: 400x300px)"
    )
    
    # Rules and documentation
    rules_pdf = models.FileField(
        upload_to='tournaments/rules/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Tournament rules PDF document"
    )
    
    # Promotional images
    promotional_image_1 = models.ImageField(
        upload_to='tournaments/promotional/',
        blank=True,
        null=True,
        help_text="First promotional image"
    )
    
    promotional_image_2 = models.ImageField(
        upload_to='tournaments/promotional/',
        blank=True,
        null=True,
        help_text="Second promotional image"
    )
    
    promotional_image_3 = models.ImageField(
        upload_to='tournaments/promotional/',
        blank=True,
        null=True,
        help_text="Third promotional image"
    )
    
    # Social media
    social_media_image = models.ImageField(
        upload_to='tournaments/social/',
        blank=True,
        null=True,
        help_text="Optimized for social media sharing (recommended: 1200x630px)"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this media record was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this media record was last updated"
    )
    
    class Meta:
        db_table = 'tournament_media'
        verbose_name = 'Tournament Media'
        verbose_name_plural = 'Tournament Media'
        ordering = ['-updated_at']
    
    def __str__(self) -> str:
        return f"Media for {self.tournament.name}"
    
    def clean(self) -> None:
        """
        Validate media fields.
        - Check file sizes
        - Validate image dimensions (if needed)
        - Ensure at least one media asset exists
        """
        super().clean()
        
        # Check banner size (max 5MB)
        if self.banner and hasattr(self.banner, 'size'):
            if self.banner.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError({
                    'banner': 'Banner image must be less than 5MB'
                })
        
        # Check thumbnail size (max 2MB)
        if self.thumbnail and hasattr(self.thumbnail, 'size'):
            if self.thumbnail.size > 2 * 1024 * 1024:  # 2MB
                raise ValidationError({
                    'thumbnail': 'Thumbnail image must be less than 2MB'
                })
        
        # Check rules PDF size (max 10MB)
        if self.rules_pdf and hasattr(self.rules_pdf, 'size'):
            if self.rules_pdf.size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError({
                    'rules_pdf': 'Rules PDF must be less than 10MB'
                })
        
        # Check promotional images (max 3MB each)
        for i, field in enumerate([self.promotional_image_1, self.promotional_image_2, self.promotional_image_3], 1):
            if field and hasattr(field, 'size'):
                if field.size > 3 * 1024 * 1024:  # 3MB
                    raise ValidationError({
                        f'promotional_image_{i}': f'Promotional image {i} must be less than 3MB'
                    })
        
        # Check social media image (max 3MB)
        if self.social_media_image and hasattr(self.social_media_image, 'size'):
            if self.social_media_image.size > 3 * 1024 * 1024:  # 3MB
                raise ValidationError({
                    'social_media_image': 'Social media image must be less than 3MB'
                })
    
    # Property methods for easy access
    @property
    def has_banner(self) -> bool:
        """Check if tournament has a banner"""
        return bool(self.banner)
    
    @property
    def has_thumbnail(self) -> bool:
        """Check if tournament has a thumbnail"""
        return bool(self.thumbnail)
    
    @property
    def has_rules_pdf(self) -> bool:
        """Check if tournament has rules PDF"""
        return bool(self.rules_pdf)
    
    @property
    def has_social_image(self) -> bool:
        """Check if tournament has social media image"""
        return bool(self.social_media_image)
    
    @property
    def promotional_images_count(self) -> int:
        """Count of promotional images"""
        count = 0
        if self.promotional_image_1:
            count += 1
        if self.promotional_image_2:
            count += 1
        if self.promotional_image_3:
            count += 1
        return count
    
    @property
    def has_promotional_images(self) -> bool:
        """Check if tournament has any promotional images"""
        return self.promotional_images_count > 0
    
    @property
    def has_complete_media(self) -> bool:
        """Check if tournament has all recommended media"""
        return all([
            self.has_banner,
            self.has_thumbnail,
            self.has_social_image
        ])
    
    @property
    def media_count(self) -> int:
        """Count total number of media items"""
        count = 0
        if self.banner:
            count += 1
        if self.thumbnail:
            count += 1
        if self.rules_pdf:
            count += 1
        if self.social_media_image:
            count += 1
        count += self.promotional_images_count
        return count
    
    @property
    def banner_url(self) -> Optional[str]:
        """Get banner URL or None"""
        return self.banner.url if self.banner else None
    
    @property
    def banner_url_or_default(self) -> str:
        """Get banner URL or return default placeholder"""
        if self.banner:
            return self.banner.url
        # Return default placeholder image
        return '/static/images/tournament-banner-default.jpg'
    
    @property
    def thumbnail_url(self) -> Optional[str]:
        """Get thumbnail URL or None"""
        return self.thumbnail.url if self.thumbnail else None
    
    @property
    def thumbnail_url_or_default(self) -> str:
        """Get thumbnail URL or return default placeholder"""
        if self.thumbnail:
            return self.thumbnail.url
        # Return default placeholder for cards
        return '/static/images/tournament-card-default.jpg'
    
    @property
    def rules_pdf_url(self) -> Optional[str]:
        """Get rules PDF URL or None"""
        return self.rules_pdf.url if self.rules_pdf else None
    
    @property
    def social_media_url(self) -> Optional[str]:
        """Get social media image URL or None"""
        return self.social_media_image.url if self.social_media_image else None
    
    @property
    def banner_filename(self) -> Optional[str]:
        """Get banner filename"""
        return os.path.basename(self.banner.name) if self.banner else None
    
    @property
    def rules_filename(self) -> Optional[str]:
        """Get rules PDF filename"""
        return os.path.basename(self.rules_pdf.name) if self.rules_pdf else None
    
    def get_promotional_images(self) -> list:
        """Get list of all promotional images"""
        images = []
        if self.promotional_image_1:
            images.append(self.promotional_image_1)
        if self.promotional_image_2:
            images.append(self.promotional_image_2)
        if self.promotional_image_3:
            images.append(self.promotional_image_3)
        return images
    
    def get_promotional_image_urls(self) -> list:
        """Get list of all promotional image URLs"""
        return [img.url for img in self.get_promotional_images()]
    
    def get_all_images(self) -> dict:
        """Get all images in a structured format"""
        return {
            'banner': self.banner_url,
            'thumbnail': self.thumbnail_url,
            'social_media': self.social_media_url,
            'promotional': self.get_promotional_image_urls()
        }
    
    def delete(self, *args, **kwargs) -> tuple:
        """
        Delete media files from storage when record is deleted
        """
        # Delete all image files
        if self.banner:
            self.banner.delete(save=False)
        if self.thumbnail:
            self.thumbnail.delete(save=False)
        if self.rules_pdf:
            self.rules_pdf.delete(save=False)
        if self.promotional_image_1:
            self.promotional_image_1.delete(save=False)
        if self.promotional_image_2:
            self.promotional_image_2.delete(save=False)
        if self.promotional_image_3:
            self.promotional_image_3.delete(save=False)
        if self.social_media_image:
            self.social_media_image.delete(save=False)
        
        return super().delete(*args, **kwargs)
