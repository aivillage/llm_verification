# Standard library imports.
from logging import getLogger

# CTFd imports.
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.migrations import upgrade as ctfd_migrations

# LLM Verification Plugin module imports.
from .llmv_logger import initialize_grtctfd_loggers
from .grt_models import LlmSubmissionChallenge
from .grt_routes import add_routes


log = getLogger(__name__)

def load(app):
    """Load plugin config from TOML file and register plugin assets."""
    print('Loading LLM Verification Plugin')
    # Get the logger for the LLM Verification plugin.
    log = initialize_grtctfd_loggers(module_name=__name__)
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
    # Register LLMV blueprints with CTFd.
    app.register_blueprint(llmv_verifications)
    log.debug('Registered LLMV blueprints with CTFd')
    log.info('Loaded LLM Verification Plugin "LLMV"')
