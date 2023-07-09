"""Utilities for the LLM Verification plugin."""
from logging import getLogger

# CTFd imports.
from CTFd.models import Fails, Solves
from CTFd.utils import get_config
from CTFd.utils.dates import isoformat
from CTFd.utils.modes import USERS_MODE, TEAMS_MODE
from CTFd.utils.user import get_current_user

# LLM Verification Plugin module imports.
from .grt_models import Awarded, GRTSolves, GRTSubmission, Pending


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


def retrieve_submissions(submission_type, challenge_id) -> list[dict[str, str]]:
    """Query the database for a user's answer submissions to a challenge.

    When a user submits an answer for a challenge, it's added to the 
    `GRTSubmissions` table. When an administrator marks a "pending" challenge as
    `Correct` (`submission_type` `"solve"`), `Award` (`submission_type`
    `"award"`), or `Fail` (`submission_type` `"fail"`), the `GRTSubmissions`
    table entry is deleted and a new  entry is made in the
    `GRTSolves` table.

    With this in mind, when we retrieve an answer submissions's prompt and
    generated text, we need to query different tables for the same information.
    If the answer submission is "pending," we need to query the `GRTSubmissions`
    table. If the answer submission is "solved," "awarded," or "failed," then we
    need to query the `GRTSolves` table.

    Arguments:
        submission_type(CTFd model, required): Type of answer submission.
            Choose from `Pending`, `Solves`, `Awarded`, or `Fails`.
        challenge_id(int, required): ID of the challenge that answers were submitted for.

    Returns:
        answer_submissions(list[dict[str, str]]): A list of answer submissions for the given submission type.
    """
    # Create answer-submission-type-specific query filters for the current user/team.
    mode_uid, current_uid = get_filter_by_mode(ctfd_model=submission_type)
    # Query the database for the user's answer submissions for this challenge.
    answer_submissions = submission_type.query.filter(mode_uid == current_uid,
                                                 submission_type.challenge_id == challenge_id).all()
    log.debug(f'User "{get_current_user().name}" '
              f'has {len(answer_submissions)} "{submission_type}" '
              f'answer submissions for challenge "{challenge_id}"')
    # Make a place to put answer submissions of the given submission type for this challenge.
    answer_submissions = []
    # For each answer submission that was submitted for this submission type (`e.g.` `Pending`, `Solves`, `Awarded`, or `Fails`)...`):
    for answer_submission in answer_submissions:
        # If the submission type is "pending"...
        if issubclass(submission_type, Pending):
            # ... retrieve the answer submissions's corresponding GRTSubmission entry.
            answer_query = GRTSubmission.query.filter_by(submission_id=answer_submission.id).first()
        # Otherwise, if the submission type is "awarded," "fails," or "solves"...
        elif issubclass(submission_type, (Awarded, Fails, Solves)):
            # ... retrieve the answer submissions's corresponding GRTSolves entry.
            answer_query = GRTSolves.query.filter_by(challenge_id=challenge_id).first()
        else:
            raise TypeError(f'Submission type: "{submission_type}" '
                            f'is not an instance of "{Pending}," "{Solves}," "{Awarded}," or "{Fails}"')
        if answer_query == None:
            log.warn(f'Found no GRTSubmission/GRTSolves entry for answer submission "{answer_submission.id}" '
                     f'on challenge "{challenge_id}" '
                     f'for user "{get_current_user().name}"')
        # Extract the answer submission's prompt and the text that it generated.
        answer_submissions.append({'prompt': answer_query.prompt,
                                   'date': isoformat(answer_submission.date),
                                   'generated_text': answer_query.text})
    log.debug(f'Extracted "{submission_type}" submissions: {answer_submissions}')
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
