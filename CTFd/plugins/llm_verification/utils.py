"""Utilities for the LLM Verification plugin."""
from logging import getLogger

# CTFd imports.
from CTFd.utils import get_config
from CTFd.utils.dates import isoformat
from CTFd.utils.modes import USERS_MODE, TEAMS_MODE
from CTFd.utils.user import get_current_user

# LLM Verification Plugin module imports.
from .grt_models import GRTSubmission


log = getLogger(__name__)

def get_filter_by_mode(ctfd_model):
    """Get a query filter for the current user/team.

    Arguments:
        ctfd_model: The CTFd model to use for the query filter.

    Returns:
        tuple (mode_uid, current_uid): A query filter for the current user/team and the current 
            user/team's ID.
    """
    # If CTFd's configured for "users..."
    if get_config('user_mode') == USERS_MODE:
        # ... then define a query filter for the "user" `USER_MODE`.
        mode_uid = ctfd_model.user_id
        current_uid = get_current_user().id
    # Otherwise, if CTFd's configured for "teams..."
    elif get_config('user_mode') == TEAMS_MODE:
        # ... then define a query filter for the "team" `USER_MODE`.
        mode_uid = ctfd_model.team_id
        current_uid = get_current_user().team_id
    # Otherwise, if CTFd's configured for neither "users" nor "teams"...
    else:
        # ... then raise an error.
        raise ValueError(f'Invalid user mode: "{get_config("user_mode")}" '
                         f'is not "{USERS_MODE}" '
                         f'or "{TEAMS_MODE}"')
    return mode_uid, current_uid


def retrieve_submissions(submission_type, challenge_id, user_id) -> list[dict[str, str]]:
    """Query the database for a user's answer submissions to a challenge.

    Arguments:
        submission_type(CTFd model, required): Type of answer submission.
            Choose from `Pending`, `Solves`, `Awarded`, or `Fails`.
        challenge_id(int, required): ID of the challenge that answers were submitted for.
        user_id(int, required): ID of the user who submitted answers to the challenge.
    """
    # Create answer-submission-type-specific query filters for the current user/team.
    mode_uid, current_uid = get_filter_by_mode(ctfd_model=submission_type)
    # Query the database for the user's answer submissions for this challenge.
    query_results = submission_type.query.filter(mode_uid == current_uid,
                                                 submission_type.challenge_id == challenge_id).all()
    log.debug(f'User "{get_current_user().name}" '
              f'has {len(query_results)} "{submission_type}" '
              f'answer submissions for challenge "{challenge_id}"')
    answer_submissions = []
    for answer_submission in query_results:
        answer_query = GRTSubmission.query.filter_by(submission_id=answer_submission.id).first()
        # Extract the values of the `provided` and `date` columns from each answer submission.
        answer_submissions.append({'provided': answer_submission.provided,
                                   'date': isoformat(answer_submission.date),
                                   'generated_text': answer_query.text})
    log.debug(f'Extracted "{submission_type}" '
              f'submissions: {answer_submissions}')
    return answer_submissions
