"""Utilities for the LLM Verification plugin."""
from ast import List
from logging import getLogger
import random
from typing import Optional

# CTFd imports.
from CTFd.models import Fails, Solves, db
from CTFd.utils import get_config
from CTFd.utils.dates import isoformat
from CTFd.utils.modes import USERS_MODE, TEAMS_MODE
from CTFd.utils.user import get_current_user


# LLM Verification Plugin module imports.
from .llmv_models import LLMVGeneration, LlmModels


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


