import rules
from django.db.models import Q

from pretalx.person.permissions import can_change_submissions, is_reviewer
from pretalx.submission.models import SubmissionStates


@rules.predicate
def has_submissions(user, obj):
    event = obj.event
    return event.submissions.filter(speakers__in=[user]).exists()


@rules.predicate
def is_speaker(user, obj):
    obj = getattr(obj, "submission", obj)
    return obj and user in obj.speakers.all()


@rules.predicate
def can_be_withdrawn(user, obj):
    return obj and SubmissionStates.WITHDRAWN in SubmissionStates.valid_next_states.get(
        obj.state, []
    )


@rules.predicate
def can_be_rejected(user, obj):
    return obj and SubmissionStates.REJECTED in SubmissionStates.valid_next_states.get(
        obj.state, []
    )


@rules.predicate
def can_be_accepted(user, obj):
    return obj and SubmissionStates.ACCEPTED in SubmissionStates.valid_next_states.get(
        obj.state, []
    )


@rules.predicate
def can_be_confirmed(user, obj):
    return obj and SubmissionStates.CONFIRMED in SubmissionStates.valid_next_states.get(
        obj.state, []
    )


@rules.predicate
def can_be_canceled(user, obj):
    return obj and SubmissionStates.CANCELED in SubmissionStates.valid_next_states.get(
        obj.state, []
    )


@rules.predicate
def can_be_removed(user, obj):
    return obj and SubmissionStates.DELETED in SubmissionStates.valid_next_states.get(
        obj.state, []
    )


@rules.predicate
def can_be_edited(user, obj):
    return obj and obj.editable


@rules.predicate
def is_review_author(user, obj):
    return obj and obj.user == user


@rules.predicate
def can_be_reviewed(user, obj):
    if not obj:
        return False
    obj = getattr(obj, "submission", obj)
    phase = obj.event.active_review_phase and obj.event.active_review_phase.can_review
    state = obj.state == SubmissionStates.SUBMITTED
    return bool(state and phase)


@rules.predicate
def can_view_reviews(user, obj):
    phase = obj.event.active_review_phase
    if not phase:
        return False
    if phase.can_see_other_reviews == "always":
        return True
    if phase.can_see_other_reviews == "after_review":
        return obj.reviews.filter(user=user).exists()
    return False


@rules.predicate
def can_view_all_reviews(user, obj):
    phase = obj.event.active_review_phase
    if not phase:
        return False
    return phase.can_see_other_reviews == "always"


@rules.predicate
def is_comment_author(user, obj):
    return obj and obj.user == user


@rules.predicate
def submission_comments_active(user, obj):
    return obj.event.get_feature_flag("use_submission_comments")


@rules.predicate
def has_reviewer_access(user, obj):
    from pretalx.submission.models import Submission

    obj = getattr(obj, "submission", obj)
    if not isinstance(obj, Submission):
        raise Exception("Incorrect use of reviewer permissions")
    if user in obj.assigned_reviewers.all():
        return True
    phase = obj.event.active_review_phase
    if not phase:
        return False
    if phase.proposal_visibility == "all":
        return user.teams.filter(
            Q(Q(all_events=True) | Q(limit_events__in=[obj.event]))
            & Q(Q(limit_tracks__isnull=True) | Q(limit_tracks__in=[obj.track])),
            is_reviewer=True,
        ).exists()
    return False


@rules.predicate
def reviewer_can_change_submissions(user, obj):
    return bool(
        obj.event.active_review_phase
        and obj.event.active_review_phase.can_change_submission_state
    )


rules.add_perm(
    "submission.accept_or_reject_submissions",
    can_change_submissions | (is_reviewer & reviewer_can_change_submissions),
)
rules.add_perm("submission.perform_actions", is_speaker)
rules.add_perm("submission.withdraw_submission", can_be_withdrawn & is_speaker)
rules.add_perm(
    "submission.reject_submission",
    can_be_rejected
    & (can_change_submissions | (is_reviewer & reviewer_can_change_submissions)),
)
rules.add_perm(
    "submission.accept_submission",
    can_be_accepted
    & (can_change_submissions | (is_reviewer & reviewer_can_change_submissions)),
)
rules.add_perm(
    "submission.confirm_submission",
    can_be_confirmed & (is_speaker | can_change_submissions),
)
rules.add_perm(
    "submission.cancel_submission",
    can_be_canceled & (is_speaker | can_change_submissions),
)
rules.add_perm("submission.remove_submission", can_be_removed & can_change_submissions)
rules.add_perm(
    "submission.edit_submission", (can_be_edited & is_speaker) | can_change_submissions
)
rules.add_perm(
    "submission.view_submission",
    is_speaker | can_change_submissions | has_reviewer_access,
)
rules.add_perm("submission.review_submission", has_reviewer_access & can_be_reviewed)
rules.add_perm(
    "submission.edit_review", has_reviewer_access & can_be_reviewed & is_review_author
)
rules.add_perm("submission.view_reviews", has_reviewer_access | can_change_submissions)
rules.add_perm("submission.edit_speaker_list", is_speaker | can_change_submissions)
rules.add_perm(
    "submission.view_feedback",
    is_speaker | can_change_submissions | has_reviewer_access,
)
rules.add_perm(
    "submission.view_submission_comments",
    submission_comments_active & (has_reviewer_access | can_change_submissions),
)
rules.add_perm(
    "submission.add_submission_comments",
    submission_comments_active & (has_reviewer_access | can_change_submissions),
)
rules.add_perm(
    "submission.delete_submission_comment",
    submission_comments_active
    & (has_reviewer_access | can_change_submissions)
    & is_comment_author,
)
