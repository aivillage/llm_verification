"""Handle configuration for the LLM Verification Plugin."""
from json import loads as json_loads
from logging import getLogger
from pathlib import Path


log = getLogger(__name__)


def load_llmv_config(filename='llmv_config.json') -> dict:
    """Load configuration from LLMV's config file.

    Arguments:
        filename (str, optional): Name of the LLMV config file in `CTFd/plugins/llm_verification/`.
            Defaults to 'llmv_config.json'.

    Returns:
        dict: Configuration for the LLMV Plugin.
    """
    # Assume that this file (`__init__.py`) is in the `llm_verification` directory.
    module_dir = Path(__file__).parent
    # Assume that the LLM Verification ("LLMV") Plugin config file is in the same directory as this file.
    config_file = module_dir / filename
    try:
        # Load LLMV's settings from its configuration file.
        llmv_config = json_loads(config_file.read_text())
        log.info(f'LLM Verification Plugin config loaded from "{config_file}"')
    except FileNotFoundError as file_not_found_error:
        log.warning(f'LLM Verification Plugin config file not found at "{config_file}" '
                    f'Use the config file template at "{config_file.with_suffix(".template.json")}"')
        # Re-raise the missing config error so that the user knows that the config file is missing.
        raise file_not_found_error
    return llmv_config
