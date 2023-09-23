# Standard library imports.
from logging import getLogger

# CTFd imports.
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.migrations import upgrade as ctfd_migrations

# LLM Verification Plugin module imports.
from .llmv_logger import initialize_llmvctfd_loggers
from .llmv_models import LlmSubmissionChallenge, fill_models_table
from .llmv_routes import add_routes

log = initialize_llmvctfd_loggers(__name__)

def load(app):
    """Load plugin config from TOML file and register plugin assets."""
    print('Loading LLM Verification Plugin')
    # Get the logger for the LLM Verification plugin.
    # Perform database migrations (if necessary).
    ctfd_migrations()
    log.debug('Performed CTFd database migrations')
    # Add new challenge type: `llm_verification`.
    CHALLENGE_CLASSES['llm_verification'] = LlmSubmissionChallenge
    log.debug(f'Added new challenge type: {LlmSubmissionChallenge}')
    # Register LLMV web assets with CTFd.
    register_plugin_assets_directory(app, base_path='/plugins/llm_verification/assets/')
    log.debug('Registered LLMV plugin assets directory with CTFd')
    llmv_verifications = add_routes()
    fill_models_table()
    # Register LLMV blueprints with CTFd.
    app.register_blueprint(llmv_verifications)
    log.debug('Registered LLMV blueprints with CTFd')
    log.info('Loaded LLM Verification Plugin')
