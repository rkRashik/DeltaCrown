"""Deliberate field categories; unknown fields never become public by inference."""
from django.apps import apps
from django.conf import settings

PUBLIC_MODELS = {
    'games.game', 'games.gamemappool', 'organizations.organization',
    'organizations.team', 'tournaments.registrationformtemplate',
    'tournaments.tournamentsponsor', 'user_profile.gameprofile',
    'ecommerce.category', 'ecommerce.brand', 'ecommerce.product',
    'ecommerce.productimage', 'economy.inventoryitem',
    'siteui.arenahighlight', 'siteui.arenastream',
}

# Exact reviewed fields. New fields fail closed until deliberately classified.
KNOWN_FIELDS = frozenset([('contracts.contractproofsubmission', 'proof_file'), ('ecommerce.brand', 'logo'), ('ecommerce.category', 'image'), ('ecommerce.product', 'featured_image'), ('ecommerce.product', 'hover_image'), ('ecommerce.productimage', 'image'), ('economy.inventoryitem', 'icon'), ('games.game', 'banner'), ('games.game', 'card_image'), ('games.game', 'icon'), ('games.game', 'logo'), ('games.gamemappool', 'image'), ('organizations.organization', 'badge'), ('organizations.organization', 'banner'), ('organizations.organization', 'logo'), ('organizations.team', 'banner'), ('organizations.team', 'logo'), ('organizations.teammedia', 'file'), ('organizations.teammembership', 'roster_image'), ('siteui.arenahighlight', 'custom_thumbnail'), ('siteui.arenastream', 'custom_thumbnail'), ('siteui.communitypostmedia', 'file'), ('siteui.communitypostmedia', 'thumbnail'), ('tournaments.certificate', 'file_image'), ('tournaments.certificate', 'file_pdf'), ('tournaments.certificaterecord', 'generated_pdf'), ('tournaments.disputeevidence', 'evidence_file'), ('tournaments.formresponse', 'payment_proof'), ('tournaments.kycsubmission', 'document_back'), ('tournaments.kycsubmission', 'document_front'), ('tournaments.kycsubmission', 'selfie_image'), ('tournaments.matchmedia', 'file'), ('tournaments.matchresultsubmission', 'proof_screenshot'), ('tournaments.payment', 'payment_proof'), ('tournaments.payment', 'proof_image'), ('tournaments.paymentverification', 'proof_image'), ('tournaments.registrationformtemplate', 'thumbnail'), ('tournaments.tournament', 'banner_image'), ('tournaments.tournament', 'rules_pdf'), ('tournaments.tournament', 'terms_pdf'), ('tournaments.tournament', 'thumbnail_image'), ('tournaments.tournamentsponsor', 'banner_image'), ('tournaments.tournamentsponsor', 'logo'), ('user_profile.certificate', 'image'), ('user_profile.gameprofile', 'rank_image'), ('user_profile.kycsubmission', 'document_back'), ('user_profile.kycsubmission', 'document_front'), ('user_profile.kycsubmission', 'selfie_with_document'), ('user_profile.userprofile', 'avatar'), ('user_profile.userprofile', 'banner'), ('user_profile.verificationrecord', 'id_document_back'), ('user_profile.verificationrecord', 'id_document_front'), ('user_profile.verificationrecord', 'selfie_with_id')])
PUBLIC_FIELDS = frozenset([('ecommerce.brand', 'logo'), ('ecommerce.category', 'image'), ('ecommerce.product', 'featured_image'), ('ecommerce.product', 'hover_image'), ('ecommerce.productimage', 'image'), ('economy.inventoryitem', 'icon'), ('games.game', 'banner'), ('games.game', 'card_image'), ('games.game', 'icon'), ('games.game', 'logo'), ('games.gamemappool', 'image'), ('organizations.organization', 'badge'), ('organizations.organization', 'banner'), ('organizations.organization', 'logo'), ('organizations.team', 'banner'), ('organizations.team', 'logo'), ('siteui.arenahighlight', 'custom_thumbnail'), ('siteui.arenastream', 'custom_thumbnail'), ('tournaments.registrationformtemplate', 'thumbnail'), ('tournaments.tournament', 'banner_image'), ('tournaments.tournament', 'thumbnail_image'), ('tournaments.tournamentsponsor', 'banner_image'), ('tournaments.tournamentsponsor', 'logo'), ('user_profile.gameprofile', 'rank_image'), ('user_profile.userprofile', 'avatar'), ('user_profile.userprofile', 'banner')])


# Only organization brand artwork has no draft, member-only or profile-privacy
# policy. Visibility-controlled artwork stays private, even while published.
# CDN publication is not revocable by changing a Django visibility flag.
CLOUDINARY_PUBLIC_FIELDS = frozenset({
    ('organizations.organization', 'logo'),
    ('organizations.organization', 'banner'),
    ('organizations.organization', 'badge'),
})


def storage_alias(field):
    label = field.model._meta.concrete_model._meta.label_lower
    public_fields = (CLOUDINARY_PUBLIC_FIELDS
                     if getattr(settings, 'OWNLOBBY_MEDIA_MODE', 'legacy') == 'hybrid'
                     else PUBLIC_FIELDS)
    return 'public_media' if (label, field.name) in public_fields else 'private_media'



def team_member(user, team):
    if not user.is_authenticated:
        return False
    return team.created_by_id == user.pk or apps.get_model('organizations.TeamMembership').objects.filter(
        team_id=team.pk, user_id=user.pk, status='ACTIVE'
    ).exists()


def team_visible(user, team):
    return team.status == 'ACTIVE' and (team.visibility in {'PUBLIC', 'UNLISTED'} or team_member(user, team))


def tournament_visible(user, tournament):
    return not tournament.is_deleted and (
        tournament.status not in {'draft', 'pending_approval'}
        or (user.is_authenticated and tournament.organizer_id == user.pk)
    )


def match_participant(user, match):
    """Participant integers are team OR user IDs, never both namespaces."""
    if not user.is_authenticated:
        return False
    ids = {match.participant1_id, match.participant2_id} - {None}
    kind = match.tournament.participation_type
    if kind == 'solo':
        return user.pk in ids
    if kind == 'team':
        return apps.get_model('organizations.TeamMembership').objects.filter(
            user_id=user.pk, status='ACTIVE', team_id__in=ids
        ).exists()
    return False


def can_download(user, obj, field_name):
    label = obj._meta.concrete_model._meta.label_lower
    if (label, field_name) not in KNOWN_FIELDS:
        return False
    if getattr(obj, 'is_deleted', False):
        return False
    authenticated = bool(user and user.is_authenticated and user.is_active)
    if authenticated and (user.is_superuser or (user.is_staff and user.has_perm(
        f'{obj._meta.app_label}.view_{obj._meta.model_name}'
    ))):
        return True
    uid = user.pk if authenticated else None
    if label == 'user_profile.userprofile':
        if uid == obj.user_id:
            return True
        privacy = getattr(obj, 'privacy_settings', None)
        return bool(privacy and (
            (not privacy.is_private_account and privacy.visibility_preset != 'private')
            or (authenticated and apps.get_model('user_profile.Follow').objects.filter(
                follower_id=uid, following_id=obj.user_id
            ).exists())
        ))
    if label == 'user_profile.gameprofile':
        return uid == obj.user_id or (obj.visibility == 'public' and can_download(user, obj.user.profile, 'avatar'))
    if label in {'user_profile.verificationrecord', 'user_profile.kycsubmission'}:
        return authenticated and obj.user_profile.user_id == uid
    if label in {'user_profile.certificate', 'tournaments.certificaterecord', 'tournaments.kycsubmission'}:
        # KYC is owner or explicit model-permission reviewer, never all organizers.
        return authenticated and obj.user_id == uid
    if label == 'organizations.team':
        return team_visible(user, obj)
    if label == 'organizations.organization':
        return True  # Organization brand mark is public; not staff/roster documents.
    if label == 'organizations.teammembership':
        return authenticated and (obj.user_id == uid or team_member(user, obj.team))
    if label == 'organizations.teammedia':
        return authenticated and team_member(user, obj.team)
    if label == 'tournaments.tournament':
        return tournament_visible(user, obj)
    if label == 'tournaments.tournamentsponsor':
        return obj.is_active and tournament_visible(user, obj.tournament)
    if label in {'tournaments.payment', 'tournaments.paymentverification'}:
        reg = obj.registration
        return authenticated and not reg.is_deleted and (
            reg.user_id == uid or reg.tournament.organizer_id == uid
        )
    if label == 'tournaments.formresponse':
        return authenticated and (obj.user_id == uid or obj.tournament.organizer_id == uid)
    if label == 'tournaments.certificate':
        return authenticated and not obj.revoked_at and (
            obj.participant.user_id == uid or obj.tournament.organizer_id == uid
        )
    if label == 'contracts.contractproofsubmission':
        return authenticated and obj.enrollment.user_id == uid
    if label in {'tournaments.matchresultsubmission', 'tournaments.matchmedia', 'tournaments.disputeevidence'}:
        if not authenticated:
            return False
        if label == 'tournaments.disputeevidence':
            match = obj.dispute.submission.match
            owner = obj.uploaded_by_id == uid or obj.dispute.opened_by_user_id == uid
        else:
            match = obj.match
            owner = (getattr(obj, 'submitted_by_user_id', None) == uid or
                     getattr(obj, 'uploaded_by_id', None) == uid)
        return owner or match.tournament.organizer_id == uid or match_participant(user, match)
    if label == 'siteui.communitypostmedia':
        post = obj.post
        if authenticated and post.author.user_id == uid:
            return True
        if not can_download(user, post.author, 'avatar'):
            return False
        if not post.is_approved:
            return False
        if post.team_id and not team_visible(user, post.team):
            return False
        return post.visibility == 'public' or (
            post.visibility == 'friends' and authenticated and apps.get_model('user_profile.Follow').objects.filter(follower_id=uid, following_id=post.author.user_id).exists()
        )
    if label == 'ecommerce.productimage':
        return obj.product.is_active and not obj.product.is_deleted
    if label in PUBLIC_MODELS:
        return bool(getattr(obj, 'is_active', True))
    return False
