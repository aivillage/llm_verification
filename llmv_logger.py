from flask import current_app
from logging import (
    CRITICAL,
    DEBUG,
    ERROR,
    Formatter,
    getLogger,
    INFO,
    StreamHandler,
    WARNING,
)
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys


def initialize_llmvctfd_loggers(module_name):
    """Create and initialize the loggers for the llmvctfd LLM Verification plugin.

    Arguments:
        module_name (str, required): Name of the LLMV module.

    Returns:
        logger: The logger for the llmvctfd LLM Verification plugin.
            This is here for posterity because `logging.get_logger(__name__)` is a cleaner way to
            get the logger.
    """
    # Use the module name as the logger name so this logger applies to all files in LLMV.
    log = getLogger(module_name)
    # Assume that CTFd's log folder already exists (defined in `CTFd/utils/initialization/__init__.py`) and store logfiles there.
    ctfd_logdir = current_app.config["LOG_FOLDER"]
    llmv_logfile = Path(ctfd_logdir, "llmv_verification.log")
    # Ensure that the log file exists.
    llmv_logfile.touch(exist_ok=True)
    llm_verification_log = RotatingFileHandler(
        llmv_logfile, maxBytes=10485760, backupCount=5
    )
    # Write all LLM Verification Plugin logs to the log file.
    log.addHandler(llm_verification_log)
    # Create a console logger for the LLM Verification Plugin.
    console_logger = StreamHandler(stream=sys.stdout)
    # todo: Make LLM Verification Plugin log severity level configurable via `config.json`.
    # Show console logs for all severity levels.
    console_logger.setLevel(DEBUG)
    # Add colorized formatter to console logger.
    console_logger.setFormatter(ColorizedFormatter())
    # Add the colorized console log handler to the LLM Verification Plugin's logger.
    log.addHandler(console_logger)
    # Don't pass log records to ancestor loggers.
    log.propagate = False
    log.info(f'Writing logs to CTFd\'s log directory "{llmv_logfile}"')
    log.info("Initialized LLMV logger")
    return log


## Set up console handler for log records.
class ColorizedFormatter(Formatter):
    """Colorized log record formatter that's keyed to the record's severity level."""

    def __init__(self):
        Formatter.__init__(self)
        # Define the output format for each log record.
        self.logline_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        # Set the color for each log record severity level type.
        self.severity_colors = {
            log_level: f"\033[1;{color_code}m{self.logline_format}\033[0m"
            for log_level, color_code in (
                (DEBUG, 90),  # Grey text.
                (INFO, 36),  # Cyan text.
                (WARNING, 33),  # Yellow text.
                (ERROR, 31),  # Red text.
                (CRITICAL, 41),
            )
        }  # White text with red background.

    def format(self, record) -> str:
        """Take a log record and return a colorized log entry.

        This overrides the `logging.Formatter.format` method and colorizes the log record.

        Arguments:
            record: The log record to format.
        """
        # Get the format for this log record based off of its severity level.
        log_format = self.severity_colors[record.levelno]
        # Set the formatter for this log record.
        record_formatter = Formatter(log_format)
        # Formate the log entry and return it.
        return record_formatter.format(record)
