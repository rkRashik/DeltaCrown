"""
TOC API — Serializers.

Sprint 1: Overview, Lifecycle Transition, Alert serializers.
Sprint 2: Participant list, detail, bulk action serializers.
Sprint 3: Emergency Sub, Free Agent, Waitlist, Guest/Fee Waiver serializers.
Sprint 4: Payment, Revenue, Bounty, KYC serializers.
Sprint 5: Bracket, Group, Schedule, Pipeline serializers.
"""

from rest_framework import serializers


class LifecycleStageSerializer(serializers.Serializer):
    """Single stage in the lifecycle pipeline."""
    name = serializers.CharField()
    icon = serializers.CharField()
    status = serializers.ChoiceField(choices=['done', 'active', 'pending', 'cancelled'])


class LifecycleProgressSerializer(serializers.Serializer):
    """Full lifecycle progress from CommandCenterService."""
    stage = serializers.CharField()
    progress_pct = serializers.IntegerField()
    stages = LifecycleStageSerializer(many=True)


class AlertSerializer(serializers.Serializer):
    """Single alert from CommandCenterService."""
    id = serializers.IntegerField(help_text='Synthetic ID for dismiss tracking')
    severity = serializers.ChoiceField(choices=['critical', 'warning', 'info'])
    icon = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    count = serializers.IntegerField(allow_null=True)
    link_tab = serializers.CharField(allow_null=True)
    link_label = serializers.CharField(allow_null=True)


class UpcomingEventSerializer(serializers.Serializer):
    """Upcoming event entry (registration close, check-in, start, end)."""
    label = serializers.CharField()
    datetime = serializers.DateTimeField()
    icon = serializers.CharField()


class StatCardSerializer(serializers.Serializer):
    """Single stat card for the overview grid."""
    key = serializers.CharField()
    label = serializers.CharField()
    value = serializers.IntegerField()
    detail = serializers.CharField(allow_blank=True)
    color = serializers.CharField(help_text='Tailwind color hint: theme/success/warning/danger')


class TransitionOptionSerializer(serializers.Serializer):
    """A valid transition target from the current state."""
    to_status = serializers.CharField()
    label = serializers.CharField()
    can_transition = serializers.BooleanField()
    reason = serializers.CharField(allow_null=True, allow_blank=True)


class OverviewSerializer(serializers.Serializer):
    """Full overview payload for the Command Center tab."""
    status = serializers.CharField()
    status_display = serializers.CharField()
    is_frozen = serializers.BooleanField()
    freeze_reason = serializers.CharField(allow_blank=True)
    lifecycle = LifecycleProgressSerializer()
    stats = StatCardSerializer(many=True)
    alerts = AlertSerializer(many=True)
    events = UpcomingEventSerializer(many=True)
    transitions = TransitionOptionSerializer(many=True)


class LifecycleTransitionInputSerializer(serializers.Serializer):
    """Input for POST /lifecycle/transition/."""
    to_status = serializers.CharField()
    reason = serializers.CharField(required=False, default='', allow_blank=True)
    force = serializers.BooleanField(required=False, default=False)


class FreezeInputSerializer(serializers.Serializer):
    """Input for POST /lifecycle/freeze/."""
    reason = serializers.CharField(min_length=3)


class UnfreezeInputSerializer(serializers.Serializer):
    """Input for POST /lifecycle/unfreeze/."""
    reason = serializers.CharField(required=False, default='', allow_blank=True)


# ── Sprint 2: Participant Serializers ─────────────────────────────────


class ParticipantRowSerializer(serializers.Serializer):
    """Single row in the participants grid."""
    id = serializers.IntegerField()
    registration_number = serializers.CharField()
    participant_name = serializers.CharField()
    username = serializers.CharField(allow_null=True)
    team_id = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()
    status_display = serializers.CharField()
    payment_status = serializers.CharField()
    checked_in = serializers.BooleanField()
    seed = serializers.IntegerField(allow_null=True)
    slot_number = serializers.IntegerField(allow_null=True)
    waitlist_position = serializers.IntegerField(allow_null=True)
    is_guest_team = serializers.BooleanField()
    game_id = serializers.CharField(allow_blank=True)
    registered_at = serializers.CharField(allow_null=True)


class ParticipantListSerializer(serializers.Serializer):
    """Paginated participant list response."""
    results = ParticipantRowSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    pages = serializers.IntegerField()
    page_size = serializers.IntegerField()


class ParticipantPaymentSerializer(serializers.Serializer):
    """Payment detail nested in participant detail."""
    status = serializers.CharField()
    status_display = serializers.CharField()
    method = serializers.CharField(allow_blank=True)
    amount_bdt = serializers.CharField(allow_null=True)
    transaction_id = serializers.CharField(allow_blank=True)
    payer_account_number = serializers.CharField(allow_blank=True)
    reference_number = serializers.CharField(allow_blank=True)
    proof_image = serializers.CharField(allow_null=True)
    verified_by = serializers.CharField(allow_null=True)
    verified_at = serializers.CharField(allow_null=True)
    reject_reason = serializers.CharField(allow_blank=True)
    created_at = serializers.CharField(allow_null=True)


class ParticipantDetailSerializer(serializers.Serializer):
    """Full participant detail for the drawer."""
    id = serializers.IntegerField()
    registration_number = serializers.CharField()
    participant_name = serializers.CharField()
    user_id = serializers.IntegerField(allow_null=True)
    username = serializers.CharField(allow_null=True)
    team_id = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()
    status_display = serializers.CharField()
    registered_at = serializers.CharField(allow_null=True)
    checked_in = serializers.BooleanField()
    checked_in_at = serializers.CharField(allow_null=True)
    seed = serializers.IntegerField(allow_null=True)
    slot_number = serializers.IntegerField(allow_null=True)
    waitlist_position = serializers.IntegerField(allow_null=True)
    is_guest_team = serializers.BooleanField()
    completion_percentage = serializers.FloatField()
    registration_data = serializers.DictField()
    lineup_snapshot = serializers.ListField()
    payment = ParticipantPaymentSerializer(allow_null=True)
    created_at = serializers.CharField(allow_null=True)
    updated_at = serializers.CharField(allow_null=True)


class BulkActionInputSerializer(serializers.Serializer):
    """Input for POST /participants/bulk-action/."""
    action = serializers.ChoiceField(choices=['approve', 'reject', 'disqualify', 'checkin'])
    ids = serializers.ListField(child=serializers.IntegerField(), min_length=1, max_length=200)
    reason = serializers.CharField(required=False, default='', allow_blank=True)


class BulkActionResultSerializer(serializers.Serializer):
    """Result of a bulk action."""
    action = serializers.CharField()
    processed = serializers.IntegerField()
    total_requested = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.DictField())


class RejectInputSerializer(serializers.Serializer):
    """Input for reject/DQ actions."""
    reason = serializers.CharField(required=False, default='', allow_blank=True)
    evidence = serializers.CharField(required=False, default='', allow_blank=True)


# ── Sprint 3: Participants Advanced Serializers ──────────────────────


class EmergencySubRequestSerializer(serializers.Serializer):
    """Single emergency substitution request."""
    id = serializers.CharField()
    tournament_id = serializers.IntegerField()
    registration_id = serializers.IntegerField()
    requested_by = serializers.CharField(allow_null=True)
    requested_by_id = serializers.IntegerField()
    dropping_player = serializers.CharField(allow_null=True)
    dropping_player_id = serializers.IntegerField()
    substitute_player = serializers.CharField(allow_null=True)
    substitute_player_id = serializers.IntegerField()
    reason = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    reviewed_by = serializers.CharField(allow_null=True)
    reviewed_at = serializers.CharField(allow_null=True)
    review_notes = serializers.CharField(allow_blank=True)
    created_at = serializers.CharField(allow_null=True)


class EmergencySubInputSerializer(serializers.Serializer):
    """Input for POST emergency-sub."""
    dropping_player_id = serializers.IntegerField()
    substitute_player_id = serializers.IntegerField()
    reason = serializers.CharField(min_length=3)


class EmergencySubReviewSerializer(serializers.Serializer):
    """Input for approve / deny emergency sub."""
    notes = serializers.CharField(required=False, default='', allow_blank=True)


class FreeAgentSerializer(serializers.Serializer):
    """Single free agent entry."""
    id = serializers.CharField()
    tournament_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    username = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    status_display = serializers.CharField()
    preferred_role = serializers.CharField(allow_blank=True)
    rank_info = serializers.CharField(allow_blank=True)
    bio = serializers.CharField(allow_blank=True)
    availability_notes = serializers.CharField(allow_blank=True)
    game_id = serializers.CharField(allow_blank=True)
    assigned_to_team = serializers.CharField(allow_null=True)
    assigned_to_team_id = serializers.IntegerField(allow_null=True)
    assigned_at = serializers.CharField(allow_null=True)
    created_at = serializers.CharField(allow_null=True)


class FreeAgentAssignSerializer(serializers.Serializer):
    """Input for assigning a free agent to a team."""
    team_id = serializers.IntegerField()


class WaitlistEntrySerializer(serializers.Serializer):
    """Single waitlist entry."""
    id = serializers.IntegerField()
    position = serializers.IntegerField(allow_null=True)
    participant_name = serializers.CharField()
    username = serializers.CharField(allow_null=True)
    registration_number = serializers.CharField(allow_blank=True)
    registered_at = serializers.CharField(allow_null=True)


class FeeWaiverInputSerializer(serializers.Serializer):
    """Input for fee waiver action."""
    reason = serializers.CharField(min_length=3)


# ── Sprint 4: Financial Operations Serializers ───────────────────


class PaymentRowSerializer(serializers.Serializer):
    """Single row in the payments grid."""
    id = serializers.IntegerField()
    registration_id = serializers.IntegerField()
    registration_number = serializers.CharField(allow_blank=True)
    participant_name = serializers.CharField()
    username = serializers.CharField(allow_null=True)
    amount = serializers.CharField()
    method = serializers.CharField(allow_blank=True)
    method_display = serializers.CharField(allow_blank=True)
    transaction_id = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    status_display = serializers.CharField()
    proof_url = serializers.CharField(allow_null=True)
    verified_by = serializers.CharField(allow_null=True)
    verified_at = serializers.CharField(allow_null=True)
    reject_reason = serializers.CharField(allow_blank=True)
    waived = serializers.BooleanField()
    waive_reason = serializers.CharField(allow_blank=True)
    created_at = serializers.CharField(allow_null=True)


class PaymentListSerializer(serializers.Serializer):
    """Paginated payment list response."""
    results = PaymentRowSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    pages = serializers.IntegerField()
    page_size = serializers.IntegerField()


class PaymentRejectInputSerializer(serializers.Serializer):
    """Input for rejecting a payment."""
    reason = serializers.CharField(required=False, default='', allow_blank=True)


class PaymentRefundInputSerializer(serializers.Serializer):
    """Input for refunding a payment."""
    reason = serializers.CharField(required=False, default='', allow_blank=True)


class BulkPaymentVerifyInputSerializer(serializers.Serializer):
    """Input for bulk payment verification."""
    ids = serializers.ListField(child=serializers.IntegerField(), min_length=1, max_length=200)


class RevenueSummarySerializer(serializers.Serializer):
    """Revenue summary response."""
    total_payments = serializers.IntegerField()
    total_amount = serializers.CharField()
    verified_count = serializers.IntegerField()
    verified_amount = serializers.CharField()
    pending_count = serializers.IntegerField()
    pending_amount = serializers.CharField()
    rejected_count = serializers.IntegerField()
    refunded_count = serializers.IntegerField()
    refunded_amount = serializers.CharField()
    waived_count = serializers.IntegerField()
    expected_revenue = serializers.CharField()
    collection_rate = serializers.FloatField()
    method_breakdown = serializers.ListField(child=serializers.DictField())


class BountySerializer(serializers.Serializer):
    """Single bounty entry."""
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    bounty_type = serializers.CharField()
    bounty_type_display = serializers.CharField()
    prize_amount = serializers.CharField()
    prize_currency = serializers.CharField()
    source = serializers.CharField()
    source_display = serializers.CharField()
    sponsor_name = serializers.CharField(allow_blank=True)
    is_assigned = serializers.BooleanField()
    assigned_to = serializers.CharField(allow_null=True)
    assigned_to_id = serializers.IntegerField(allow_null=True)
    assigned_by = serializers.CharField(allow_null=True)
    assigned_at = serializers.CharField(allow_null=True)
    assignment_reason = serializers.CharField(allow_blank=True)
    claim_status = serializers.CharField()
    created_at = serializers.CharField(allow_null=True)


class BountyCreateInputSerializer(serializers.Serializer):
    """Input for creating a bounty."""
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, default='', allow_blank=True)
    bounty_type = serializers.ChoiceField(
        choices=['mvp', 'stat_leader', 'community_vote', 'special_achievement', 'custom'],
        default='custom',
    )
    prize_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    prize_currency = serializers.CharField(default='BDT', max_length=20)
    source = serializers.ChoiceField(
        choices=['prize_pool', 'sponsor', 'platform'],
        default='prize_pool',
    )
    sponsor_name = serializers.CharField(required=False, default='', allow_blank=True, max_length=200)


class BountyAssignInputSerializer(serializers.Serializer):
    """Input for assigning a bounty."""
    user_id = serializers.IntegerField()
    registration_id = serializers.IntegerField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, default='', allow_blank=True)


class KYCSerializer(serializers.Serializer):
    """Single KYC submission."""
    id = serializers.CharField()
    user_id = serializers.IntegerField()
    username = serializers.CharField(allow_null=True)
    tournament_id = serializers.IntegerField()
    document_type = serializers.CharField()
    document_type_display = serializers.CharField()
    document_front_url = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    status_display = serializers.CharField()
    reviewer = serializers.CharField(allow_null=True)
    reviewed_at = serializers.CharField(allow_null=True)
    rejection_reason = serializers.CharField(allow_blank=True)
    expires_at = serializers.CharField(allow_null=True)
    created_at = serializers.CharField(allow_null=True)


class KYCReviewInputSerializer(serializers.Serializer):
    """Input for reviewing a KYC submission."""
    action = serializers.ChoiceField(choices=['approve', 'reject', 'flag'])
    reason = serializers.CharField(required=False, default='', allow_blank=True)


# ═══════════════════════════════════════════════════════════════
# Sprint 5 — Brackets, Groups, Schedule, Pipelines
# ═══════════════════════════════════════════════════════════════

class BracketSerializer(serializers.Serializer):
    """Read serializer for bracket data."""
    id = serializers.CharField()
    format = serializers.CharField()
    total_rounds = serializers.IntegerField()
    total_matches = serializers.IntegerField()
    seeding_method = serializers.CharField()
    is_finalized = serializers.BooleanField()
    generated_at = serializers.CharField(allow_null=True)


class BracketNodeSerializer(serializers.Serializer):
    """Read serializer for bracket node data."""
    id = serializers.IntegerField()
    position = serializers.IntegerField()
    round_number = serializers.IntegerField()
    match_number = serializers.IntegerField()
    bracket_type = serializers.CharField()
    participant1_id = serializers.IntegerField(allow_null=True)
    participant1_name = serializers.CharField(allow_null=True)
    participant2_id = serializers.IntegerField(allow_null=True)
    participant2_name = serializers.CharField(allow_null=True)
    winner_id = serializers.IntegerField(allow_null=True)
    is_bye = serializers.BooleanField()
    match = serializers.DictField(allow_null=True)


class SeedReorderInputSerializer(serializers.Serializer):
    """Input: list of seed assignments."""
    seeds = serializers.ListField(
        child=serializers.DictField(),
        help_text="[{registration_id, seed}, ...]",
    )


class GroupStageSerializer(serializers.Serializer):
    """Read serializer for group stage overview."""
    exists = serializers.BooleanField()
    stage = serializers.DictField(allow_null=True)
    groups = serializers.ListField(child=serializers.DictField())


class GroupConfigInputSerializer(serializers.Serializer):
    """Input for configuring groups."""
    num_groups = serializers.IntegerField(min_value=2, max_value=32, default=4)
    group_size = serializers.IntegerField(min_value=2, max_value=16, default=4)
    format = serializers.ChoiceField(
        choices=['round_robin', 'double_round_robin'],
        default='round_robin',
    )
    advancement_count = serializers.IntegerField(min_value=1, default=2)


class GroupDrawInputSerializer(serializers.Serializer):
    """Input for executing group draw."""
    method = serializers.ChoiceField(
        choices=['random', 'seeded', 'manual'],
        default='random',
    )


class ScheduleMatchSerializer(serializers.Serializer):
    """Read serializer for a scheduled match."""
    id = serializers.IntegerField()
    round_number = serializers.IntegerField()
    match_number = serializers.IntegerField()
    participant1_name = serializers.CharField(allow_null=True)
    participant2_name = serializers.CharField(allow_null=True)
    participant1_score = serializers.IntegerField(allow_null=True)
    participant2_score = serializers.IntegerField(allow_null=True)
    state = serializers.CharField()
    winner_id = serializers.IntegerField(allow_null=True)
    scheduled_time = serializers.CharField(allow_null=True)
    started_at = serializers.CharField(allow_null=True)
    completed_at = serializers.CharField(allow_null=True)
    stream_url = serializers.CharField(allow_blank=True)


class AutoScheduleInputSerializer(serializers.Serializer):
    """Input for auto-scheduling matches."""
    start_time = serializers.CharField(required=False, allow_blank=True)
    match_duration_minutes = serializers.IntegerField(default=30, min_value=5)
    break_minutes = serializers.IntegerField(default=10, min_value=0)
    max_concurrent = serializers.IntegerField(default=1, min_value=1)
    round_number = serializers.IntegerField(required=False, allow_null=True)


class BulkShiftInputSerializer(serializers.Serializer):
    """Input for bulk-shifting match times."""
    shift_minutes = serializers.IntegerField()
    round_number = serializers.IntegerField(required=False, allow_null=True)


class BreakInsertInputSerializer(serializers.Serializer):
    """Input for inserting a schedule break."""
    after_round = serializers.IntegerField(min_value=1)
    break_minutes = serializers.IntegerField(min_value=5, default=15)
    label = serializers.CharField(default='Break', max_length=100)


class PipelineSerializer(serializers.Serializer):
    """Read serializer for qualifier pipeline."""
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    stages = serializers.ListField(child=serializers.DictField())
    created_at = serializers.CharField()


class PipelineCreateInputSerializer(serializers.Serializer):
    """Input for creating a qualifier pipeline."""
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, default='', allow_blank=True)
