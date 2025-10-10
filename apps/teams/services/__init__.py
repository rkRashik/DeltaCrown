# apps/teams/services/__init__.py
"""
Team Services Package

Provides business logic services for team-related operations.
"""

from .ranking_service import ranking_service, TeamRankingService
from .analytics_calculator import AnalyticsCalculator, AnalyticsAggregator
from .csv_export import CSVExportService
from .chat_service import ChatService, MentionParser, AttachmentValidator
from .discussion_service import DiscussionService, NotificationService

# Lazy import for MarkdownProcessor to avoid circular import issues
def get_markdown_processor():
    """Lazy import of MarkdownProcessor"""
    from .markdown_processor import MarkdownProcessor
    return MarkdownProcessor

from .sponsorship import (
    SponsorshipService,
    SponsorInquiryService,
    MerchandiseService,
    PromotionService,
    RevenueReportingService,
)

__all__ = [
    'ranking_service', 
    'TeamRankingService',
    'AnalyticsCalculator',
    'AnalyticsAggregator',
    'CSVExportService',
    'ChatService',
    'MentionParser',
    'AttachmentValidator',
    'DiscussionService',
    'NotificationService',
    'MarkdownProcessor',
    'SponsorshipService',
    'SponsorInquiryService',
    'MerchandiseService',
    'PromotionService',
    'RevenueReportingService',
]