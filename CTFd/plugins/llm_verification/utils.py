"""Utilities for the LLM Verification plugin."""
from logging import getLogger

# CTFd imports.
from CTFd.utils import get_config
from CTFd.utils.dates import isoformat
from CTFd.utils.modes import USERS_MODE, TEAMS_MODE
from CTFd.utils.user import get_current_user

# LLM Verification Plugin module imports.
from .grt_models import GRTSolves, GRTSubmission


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
    # For each answer submission that was submitted for this submission type (`e.g.` `Pending`, `Solves`, `Awarded`, or `Fails`)...`):
    for answer_submission in query_results:
        # ... retrieve the answer submissions's corresponding GRTSubmission entry.
        answer_query = GRTSubmission.query.filter_by(submission_id=answer_submission.id).first()
        if answer_query == None:
            log.warn(f'Found no GRTSubmission entry for answer submission "{answer_submission.id}" '
                     f'on challenge "{challenge_id}" '
                     f'for user "{get_current_user().name}," '
                     f'so defaulting to "None" for the "prompt" and "generated_text" fields.')
        # Extract the answer submission's prompt and the text that it generated.
        answer_submissions.append({'prompt': answer_query.prompt if answer_query else 'None',
                                   'date': isoformat(answer_submission.date),
                                   'generated_text': answer_query.text if answer_query else 'None'})
    log.debug(f'Extracted "{submission_type}" '
              f'submissions: {answer_submissions}')
    return answer_submissions


def create_grt_solve_entry(solve_status, ctfd_submission, grt_submission):
    """Create a database entry for a challenge solve.
    
    Arguments:
        solve_status(bool, required): Whether the challenge was solved.
        ctfd_submission(CTFd model, required): CTFd database entry for the challenge submission.
        grt_submission(GRTSubmission, required): GRT database entry for the challenge submission.

    Returns:
        solve_entry(GRTSolves): Database entry for the challenge solve.
    """
    solve_entry= GRTSolves(success=solve_status,
                           challenge_id=ctfd_submission.challenge_id,
                           text=grt_submission.text,
                           prompt=grt_submission.prompt,
                           date=ctfd_submission.date,
                           user_id=ctfd_submission.user_id,
                           team_id=ctfd_submission.team_id)
    log.debug(f'Created GRTSolves entry: {solve_entry}')
    return solve_entry
