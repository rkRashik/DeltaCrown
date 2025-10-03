"""
Tournament Archive Helper Functions

Comprehensive helpers for tournament archiving, cloning, and restoration.

Categories:
1. Archive Status Checks (8 functions)
2. Archive Operations (7 functions)
3. Clone Operations (8 functions)
4. Restore Operations (5 functions)
5. Metadata Access (6 functions)
6. Query Optimization (5 functions)
7. Historical Data (4 functions)

Total: 43 helper functions
"""

from django.db.models import QuerySet, Prefetch, Q, Max
from django.utils import timezone
from typing import Optional, Dict, Any, List
from apps.tournaments.models import Tournament, TournamentArchive


# ==================== Category 1: Archive Status Checks (8 functions) ====================

def is_archived(tournament: Tournament) -> bool:
    """
    Check if tournament is archived.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        True if archived, False otherwise
    """
    if not hasattr(tournament, 'archive'):
        return False
    return tournament.archive.is_archived


def is_active(tournament: Tournament) -> bool:
    """
    Check if tournament is active (not archived).
    
    Args:
        tournament: Tournament to check
        
    Returns:
        True if active, False otherwise
    """
    if not hasattr(tournament, 'archive'):
        return True  # No archive record = active
    return tournament.archive.is_active


def is_clone(tournament: Tournament) -> bool:
    """
    Check if tournament is a clone.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        True if clone, False otherwise
    """
    if not hasattr(tournament, 'archive'):
        return False
    return tournament.archive.is_clone


def is_original(tournament: Tournament) -> bool:
    """
    Check if tournament is original (not a clone).
    
    Args:
        tournament: Tournament to check
        
    Returns:
        True if original, False otherwise
    """
    if not hasattr(tournament, 'archive'):
        return True  # No archive record = original
    return tournament.archive.is_original


def can_restore(tournament: Tournament) -> bool:
    """
    Check if tournament can be restored from archive.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        True if can restore, False otherwise
    """
    if not hasattr(tournament, 'archive'):
        return False
    return tournament.archive.is_archived and tournament.archive.can_restore


def has_clones(tournament: Tournament) -> bool:
    """
    Check if tournament has been cloned.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        True if has clones, False otherwise
    """
    if not hasattr(tournament, 'archive'):
        return tournament.clones.exists()
    return tournament.archive.has_clones


def has_been_restored(tournament: Tournament) -> bool:
    """
    Check if tournament has been restored from archive.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        True if restored, False otherwise
    """
    if not hasattr(tournament, 'archive'):
        return False
    return tournament.archive.has_been_restored


def get_archive_status(tournament: Tournament) -> str:
    """
    Get archive status of tournament.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Archive status: 'ACTIVE', 'ARCHIVED', or 'CLONED'
    """
    if not hasattr(tournament, 'archive'):
        return 'ACTIVE'
    return tournament.archive.archive_type


# ==================== Category 2: Archive Operations (7 functions) ====================

def archive_tournament(
    tournament: Tournament,
    user=None,
    reason: str = '',
    preserve_all: bool = True
) -> TournamentArchive:
    """
    Archive a tournament.
    
    Args:
        tournament: Tournament to archive
        user: User performing the archive
        reason: Reason for archiving
        preserve_all: Whether to preserve all data types
        
    Returns:
        TournamentArchive instance
    """
    # Create archive record if doesn't exist
    archive, created = TournamentArchive.objects.get_or_create(
        tournament=tournament,
        defaults={
            'preserve_participants': preserve_all,
            'preserve_matches': preserve_all,
            'preserve_media': preserve_all,
        }
    )
    
    # Archive the tournament
    archive.archive(user=user, reason=reason)
    
    return archive


def unarchive_tournament(tournament: Tournament, user=None) -> TournamentArchive:
    """
    Restore (unarchive) a tournament.
    
    Args:
        tournament: Tournament to restore
        user: User performing the restore
        
    Returns:
        TournamentArchive instance
    """
    if not hasattr(tournament, 'archive'):
        raise ValueError("Tournament has no archive record")
    
    archive = tournament.archive
    archive.restore(user=user)
    
    return archive


def get_archive_reason(tournament: Tournament) -> str:
    """
    Get reason for tournament archival.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Archive reason or empty string
    """
    if not hasattr(tournament, 'archive'):
        return ''
    return tournament.archive.archive_reason


def get_archived_at(tournament: Tournament) -> Optional[timezone.datetime]:
    """
    Get when tournament was archived.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Archive timestamp or None
    """
    if not hasattr(tournament, 'archive'):
        return None
    return tournament.archive.archived_at


def get_archived_by(tournament: Tournament) -> Optional[str]:
    """
    Get who archived the tournament.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Username of archiver or None
    """
    if not hasattr(tournament, 'archive'):
        return None
    if not tournament.archive.archived_by:
        return None
    return tournament.archive.archived_by.username


def get_archive_age_days(tournament: Tournament) -> Optional[int]:
    """
    Get number of days since archival.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Days since archival or None
    """
    if not hasattr(tournament, 'archive'):
        return None
    return tournament.archive.archive_age_days


def set_archive_preservation(
    tournament: Tournament,
    preserve_participants: bool = True,
    preserve_matches: bool = True,
    preserve_media: bool = True
) -> TournamentArchive:
    """
    Set data preservation settings for archive.
    
    Args:
        tournament: Tournament to configure
        preserve_participants: Whether to preserve participant data
        preserve_matches: Whether to preserve match data
        preserve_media: Whether to preserve media files
        
    Returns:
        TournamentArchive instance
    """
    archive, created = TournamentArchive.objects.get_or_create(
        tournament=tournament
    )
    
    archive.preserve_participants = preserve_participants
    archive.preserve_matches = preserve_matches
    archive.preserve_media = preserve_media
    archive.save()
    
    return archive


# ==================== Category 3: Clone Operations (8 functions) ====================

def get_source_tournament(tournament: Tournament) -> Optional[Tournament]:
    """
    Get source tournament if this is a clone.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Source tournament or None
    """
    if not hasattr(tournament, 'archive'):
        return None
    return tournament.archive.source_tournament


def get_clone_number(tournament: Tournament) -> int:
    """
    Get clone generation number.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Clone number (0 = original, 1+ = clone)
    """
    if not hasattr(tournament, 'archive'):
        return 0
    return tournament.archive.clone_number


def get_cloned_at(tournament: Tournament) -> Optional[timezone.datetime]:
    """
    Get when tournament was cloned.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Clone timestamp or None
    """
    if not hasattr(tournament, 'archive'):
        return None
    return tournament.archive.cloned_at


def get_cloned_by(tournament: Tournament) -> Optional[str]:
    """
    Get who cloned the tournament.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Username of cloner or None
    """
    if not hasattr(tournament, 'archive'):
        return None
    if not tournament.archive.cloned_by:
        return None
    return tournament.archive.cloned_by.username


def get_clone_count(tournament: Tournament) -> int:
    """
    Get number of times tournament has been cloned.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Number of clones
    """
    if not hasattr(tournament, 'archive'):
        return tournament.clones.count()
    return tournament.archive.clone_count


def get_clone_age_days(tournament: Tournament) -> Optional[int]:
    """
    Get number of days since cloning.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Days since cloning or None
    """
    if not hasattr(tournament, 'archive'):
        return None
    return tournament.archive.clone_age_days


def get_all_clones(tournament: Tournament) -> QuerySet:
    """
    Get all clones of a tournament.
    
    Args:
        tournament: Source tournament
        
    Returns:
        QuerySet of Tournament objects that are clones of this tournament
    """
    # source_tournament FK is in TournamentArchive with related_name='clones'
    # So tournament.clones returns TournamentArchive objects
    # We need to get the tournaments from those archives
    from apps.tournaments.models import TournamentArchive
    clone_archives = TournamentArchive.objects.filter(source_tournament=tournament)
    return Tournament.objects.filter(archive__in=clone_archives)


def mark_tournament_as_clone(
    tournament: Tournament,
    source: Tournament,
    user=None,
    clone_num: Optional[int] = None
) -> TournamentArchive:
    """
    Mark a tournament as a clone.
    
    Args:
        tournament: Tournament to mark as clone
        source: Source tournament
        user: User performing the clone
        clone_num: Clone generation number (auto-calculated if None)
        
    Returns:
        TournamentArchive instance
    """
    # Calculate clone number if not provided
    if clone_num is None:
        # Get highest clone number from source's clones
        # Note: source.clones gets Tournament objects, we need to get their archive.clone_number
        from apps.tournaments.models import TournamentArchive
        max_clone = TournamentArchive.objects.filter(
            source_tournament=source
        ).aggregate(Max('clone_number'))['clone_number__max']
        clone_num = (max_clone or 0) + 1
    
    # Create or get archive record
    archive, created = TournamentArchive.objects.get_or_create(
        tournament=tournament
    )
    
    # Mark as clone
    archive.mark_as_clone(source=source, user=user, clone_num=clone_num)
    
    return archive


# ==================== Category 4: Restore Operations (5 functions) ====================

def can_be_restored(tournament: Tournament) -> bool:
    """
    Check if tournament can be restored (with reason).
    
    Args:
        tournament: Tournament to check
        
    Returns:
        True if can restore, False otherwise
    """
    return can_restore(tournament)


def get_restored_at(tournament: Tournament) -> Optional[timezone.datetime]:
    """
    Get when tournament was restored.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Restore timestamp or None
    """
    if not hasattr(tournament, 'archive'):
        return None
    return tournament.archive.restored_at


def get_restored_by(tournament: Tournament) -> Optional[str]:
    """
    Get who restored the tournament.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Username of restorer or None
    """
    if not hasattr(tournament, 'archive'):
        return None
    if not tournament.archive.restored_by:
        return None
    return tournament.archive.restored_by.username


def disable_restore(tournament: Tournament) -> TournamentArchive:
    """
    Disable restoration for a tournament.
    
    Args:
        tournament: Tournament to configure
        
    Returns:
        TournamentArchive instance
    """
    archive, created = TournamentArchive.objects.get_or_create(
        tournament=tournament
    )
    
    archive.can_restore = False
    archive.save()
    
    return archive


def enable_restore(tournament: Tournament) -> TournamentArchive:
    """
    Enable restoration for a tournament.
    
    Args:
        tournament: Tournament to configure
        
    Returns:
        TournamentArchive instance
    """
    archive, created = TournamentArchive.objects.get_or_create(
        tournament=tournament
    )
    
    archive.can_restore = True
    archive.save()
    
    return archive


# ==================== Category 5: Metadata Access (6 functions) ====================

def get_archive_metadata(tournament: Tournament) -> Dict[str, Any]:
    """
    Get complete archive metadata.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Dictionary of archive metadata
    """
    if not hasattr(tournament, 'archive'):
        return {
            'archive_type': 'ACTIVE',
            'is_archived': False,
            'archived_at': None,
            'archived_by': None,
            'archive_reason': '',
            'can_restore': False,
            'restored_at': None,
            'restored_by': None,
            'archive_age_days': None,
        }
    return tournament.archive.archive_metadata


def get_clone_metadata(tournament: Tournament) -> Dict[str, Any]:
    """
    Get complete clone metadata.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Dictionary of clone metadata
    """
    if not hasattr(tournament, 'archive'):
        return {
            'is_clone': False,
            'source_tournament': None,
            'clone_number': 0,
            'cloned_at': None,
            'cloned_by': None,
            'clone_age_days': None,
            'has_clones': tournament.clones.exists(),
            'clone_count': tournament.clones.count(),
        }
    return tournament.archive.clone_metadata


def get_preservation_settings(tournament: Tournament) -> Dict[str, bool]:
    """
    Get data preservation settings.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Dictionary of preservation settings
    """
    if not hasattr(tournament, 'archive'):
        return {
            'participants': True,
            'matches': True,
            'media': True,
        }
    return tournament.archive.preservation_settings


def is_fully_preserved(tournament: Tournament) -> bool:
    """
    Check if all data types are preserved.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        True if fully preserved, False otherwise
    """
    if not hasattr(tournament, 'archive'):
        return True  # Default to preserved
    return tournament.archive.is_fully_preserved


def has_original_data(tournament: Tournament) -> bool:
    """
    Check if tournament has original data snapshot.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        True if has snapshot, False otherwise
    """
    if not hasattr(tournament, 'archive'):
        return False
    return tournament.archive.has_original_data


def get_archive_notes(tournament: Tournament) -> str:
    """
    Get archive notes.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Archive notes or empty string
    """
    if not hasattr(tournament, 'archive'):
        return ''
    return tournament.archive.notes


# ==================== Category 6: Query Optimization (5 functions) ====================

def optimize_queryset_for_archive(queryset: QuerySet) -> QuerySet:
    """
    Optimize queryset for archive access.
    
    Args:
        queryset: Tournament queryset
        
    Returns:
        Optimized queryset with archive data
    """
    return queryset.select_related(
        'archive',
        'archive__archived_by',
        'archive__cloned_by',
        'archive__restored_by',
        'archive__source_tournament'
    )


def get_archived_tournaments() -> QuerySet:
    """
    Get all archived tournaments.
    
    Returns:
        QuerySet of archived tournaments
    """
    return Tournament.objects.filter(
        archive__is_archived=True
    ).select_related('archive')


def get_active_tournaments() -> QuerySet:
    """
    Get all active (non-archived) tournaments.
    
    Returns:
        QuerySet of active tournaments
    """
    return Tournament.objects.filter(
        Q(archive__is_archived=False) | Q(archive__isnull=True)
    ).select_related('archive')


def get_cloned_tournaments() -> QuerySet:
    """
    Get all cloned tournaments.
    
    Returns:
        QuerySet of cloned tournaments
    """
    return Tournament.objects.filter(
        archive__archive_type='CLONED'
    ).select_related('archive', 'archive__source_tournament')


def get_original_tournaments() -> QuerySet:
    """
    Get all original (non-cloned) tournaments.
    
    Returns:
        QuerySet of original tournaments
    """
    return Tournament.objects.filter(
        Q(archive__source_tournament__isnull=True) | Q(archive__isnull=True)
    ).select_related('archive')


# ==================== Category 7: Historical Data (4 functions) ====================

def save_tournament_snapshot(tournament: Tournament, data: Dict[str, Any]) -> TournamentArchive:
    """
    Save a snapshot of tournament data.
    
    Args:
        tournament: Tournament to snapshot
        data: Data to preserve
        
    Returns:
        TournamentArchive instance
    """
    archive, created = TournamentArchive.objects.get_or_create(
        tournament=tournament
    )
    
    archive.save_snapshot(data)
    
    return archive


def get_tournament_snapshot(tournament: Tournament) -> Dict[str, Any]:
    """
    Get saved tournament data snapshot.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Snapshot data or empty dict
    """
    if not hasattr(tournament, 'archive'):
        return {}
    return tournament.archive.original_data


def get_archive_context(tournament: Tournament) -> Dict[str, Any]:
    """
    Get complete archive context for templates.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Complete context dictionary with 50+ keys
    """
    context = {
        'tournament': tournament,
        'has_archive': hasattr(tournament, 'archive'),
    }
    
    # Archive status
    context['is_archived'] = is_archived(tournament)
    context['is_active'] = is_active(tournament)
    context['is_clone'] = is_clone(tournament)
    context['is_original'] = is_original(tournament)
    context['archive_status'] = get_archive_status(tournament)
    
    # Archive metadata
    context['archive_reason'] = get_archive_reason(tournament)
    context['archived_at'] = get_archived_at(tournament)
    context['archived_by'] = get_archived_by(tournament)
    context['archive_age_days'] = get_archive_age_days(tournament)
    
    # Restore info
    context['can_restore'] = can_restore(tournament)
    context['has_been_restored'] = has_been_restored(tournament)
    context['restored_at'] = get_restored_at(tournament)
    context['restored_by'] = get_restored_by(tournament)
    
    # Clone info
    context['source_tournament'] = get_source_tournament(tournament)
    context['clone_number'] = get_clone_number(tournament)
    context['cloned_at'] = get_cloned_at(tournament)
    context['cloned_by'] = get_cloned_by(tournament)
    context['clone_age_days'] = get_clone_age_days(tournament)
    context['has_clones'] = has_clones(tournament)
    context['clone_count'] = get_clone_count(tournament)
    
    # Preservation settings
    context['preservation_settings'] = get_preservation_settings(tournament)
    context['is_fully_preserved'] = is_fully_preserved(tournament)
    context['has_original_data'] = has_original_data(tournament)
    
    # Complete metadata dicts
    context['archive_metadata'] = get_archive_metadata(tournament)
    context['clone_metadata'] = get_clone_metadata(tournament)
    
    # Notes
    context['archive_notes'] = get_archive_notes(tournament)
    
    return context


def get_archive_summary(tournament: Tournament) -> Dict[str, Any]:
    """
    Get brief archive summary.
    
    Args:
        tournament: Tournament to check
        
    Returns:
        Summary dictionary
    """
    return {
        'is_archived': is_archived(tournament),
        'is_clone': is_clone(tournament),
        'has_clones': has_clones(tournament),
        'can_restore': can_restore(tournament),
        'archive_age_days': get_archive_age_days(tournament),
    }
