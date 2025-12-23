"""
Public ID Generator Service

Generates unique, human-readable, branded public user IDs in DC-YY-NNNNNN format.
Year-based sequential allocation with atomic counter management.

See: Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_02_PUBLIC_USER_ID_STRATEGY.md

Note: PublicIDCounter model is defined here (not in models/) to keep it with the service.
"""
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
import logging
import re

logger = logging.getLogger(__name__)


class PublicIDCounter(models.Model):
    """
    Year-based counter for public ID generation.
    One row per year, atomic counter allocation with F() expressions.
    """
    year = models.IntegerField(unique=True, help_text="Year (YY format, e.g., 25 for 2025)")
    counter = models.IntegerField(default=0, help_text="Sequential counter for this year")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile_publicidcounter'
        verbose_name = 'Public ID Counter'
        verbose_name_plural = 'Public ID Counters'
        indexes = [
            models.Index(fields=['year'], name='idx_publicid_year'),
        ]
    
    def __str__(self):
        return f"PublicIDCounter(year={self.year}, counter={self.counter})"


class PublicIDGenerator:
    """
    Service for generating unique public user IDs.
    
    Format: DC-YY-NNNNNN
    - DC: DeltaCrown brand prefix
    - YY: Year (2025 → 25)
    - NNNNNN: Sequential counter (000001, 000002, ...)
    
    Example: DC-25-000042
    
    Thread-safe with select_for_update() locking.
    Supports year rollover (new counter for new year).
    Handles collisions with retry logic.
    """
    
    PUBLIC_ID_REGEX = re.compile(r'^DC-\d{2}-\d{6}$')
    MAX_RETRIES = 3
    MAX_COUNTER_VALUE = 999999  # 6 digits
    
    @classmethod
    def generate_public_id(cls) -> str:
        """
        Generate next sequential public ID for current year.
        
        Returns:
            str: Public ID in format DC-YY-NNNNNN
        
        Raises:
            ValidationError: If counter overflow (> 999999)
            RuntimeError: If allocation fails after retries
        
        Example:
            >>> public_id = PublicIDGenerator.generate_public_id()
            >>> print(public_id)
            'DC-25-000042'
        """
        current_year = timezone.now().year % 100  # 2025 → 25
        
        for attempt in range(cls.MAX_RETRIES):
            try:
                with transaction.atomic():
                    # Get or create counter for current year
                    counter_obj, created = PublicIDCounter.objects.select_for_update().get_or_create(
                        year=current_year,
                        defaults={'counter': 0}
                    )
                    
                    # Check for overflow
                    if counter_obj.counter >= cls.MAX_COUNTER_VALUE:
                        raise ValidationError(
                            f"Public ID counter overflow for year {current_year}. "
                            f"Maximum {cls.MAX_COUNTER_VALUE} users per year reached. "
                            "Manual intervention required."
                        )
                    
                    # Atomic increment
                    counter_obj.counter = models.F('counter') + 1
                    counter_obj.save(update_fields=['counter'])
                    
                    # Refresh to get actual value
                    counter_obj.refresh_from_db()
                    counter_value = counter_obj.counter
                    
                    # Format public ID
                    public_id = f"DC-{current_year:02d}-{counter_value:06d}"
                    
                    # Validate format
                    if not cls.validate_format(public_id):
                        raise ValidationError(f"Generated invalid public_id format: {public_id}")
                    
                    logger.info(
                        f"Generated public_id={public_id} "
                        f"(year={current_year}, counter={counter_value}, attempt={attempt + 1})"
                    )
                    
                    return public_id
            
            except Exception as e:
                if attempt < cls.MAX_RETRIES - 1:
                    logger.warning(
                        f"Public ID generation failed (attempt {attempt + 1}/{cls.MAX_RETRIES}): {e}, "
                        "retrying..."
                    )
                    continue
                else:
                    logger.error(
                        f"Public ID generation failed after {cls.MAX_RETRIES} attempts: {e}",
                        exc_info=True
                    )
                    raise RuntimeError(
                        f"Failed to generate public_id after {cls.MAX_RETRIES} attempts. "
                        f"Last error: {e}"
                    )
        
        # Should never reach here
        raise RuntimeError("Unexpected: generate_public_id exhausted retries")
    
    @classmethod
    def validate_format(cls, public_id: str) -> bool:
        """
        Validate public_id format.
        
        Args:
            public_id: Public ID string to validate
        
        Returns:
            bool: True if valid format, False otherwise
        
        Example:
            >>> PublicIDGenerator.validate_format('DC-25-000042')
            True
            >>> PublicIDGenerator.validate_format('DC-25-42')
            False
        """
        if not public_id:
            return False
        return cls.PUBLIC_ID_REGEX.match(public_id) is not None
    
    @classmethod
    def get_year_from_public_id(cls, public_id: str) -> int:
        """
        Extract year from public_id.
        
        Args:
            public_id: Public ID in format DC-YY-NNNNNN
        
        Returns:
            int: Year (YY format)
        
        Raises:
            ValueError: If invalid format
        
        Example:
            >>> PublicIDGenerator.get_year_from_public_id('DC-25-000042')
            25
        """
        if not cls.validate_format(public_id):
            raise ValueError(f"Invalid public_id format: {public_id}")
        
        parts = public_id.split('-')
        return int(parts[1])
    
    @classmethod
    def get_counter_from_public_id(cls, public_id: str) -> int:
        """
        Extract counter from public_id.
        
        Args:
            public_id: Public ID in format DC-YY-NNNNNN
        
        Returns:
            int: Counter value
        
        Raises:
            ValueError: If invalid format
        
        Example:
            >>> PublicIDGenerator.get_counter_from_public_id('DC-25-000042')
            42
        """
        if not cls.validate_format(public_id):
            raise ValueError(f"Invalid public_id format: {public_id}")
        
        parts = public_id.split('-')
        return int(parts[2])
