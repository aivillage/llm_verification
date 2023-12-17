import os
import logging
from pathlib import Path
import sys

from flask import current_app


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
    log = logging.getLogger(module_name)

    # Assume that CTFd's log folder already exists (defined in `CTFd/utils/initialization/__init__.py`) and store logfiles there.
    ctfd_logdir = current_app.config["LOG_FOLDER"]
    llmv_logfile = Path(ctfd_logdir, "llmv_verification.log")

    # Ensure that the log file exists.
    llmv_logfile.touch(exist_ok=True)
    llm_verification_log = logging.handlers.RotatingFileHandler(
        llmv_logfile, maxBytes=10485760, backupCount=5
    )

    # Write all LLM Verification Plugin logs to the log file.
    log.addHandler(llm_verification_log)

    # Create a console logger for the LLM Verification Plugin.
    console_logger = logging.StreamHandler(stream=sys.stdout)

    # Show console logs for all severity levels.
    log_level = os.getenv("LLM_VERIFICATION_LOGGING_LEVEL", "INFO")
    console_logger.setLevel(log_level)

    # Add colorized formatter to console logger.
    console_logger.setFormatter(ColorizedFormatter())

    # Add the colorized console log handler to the LLM Verification Plugin's logger.
    log.addHandler(console_logger)

    # Don't pass log records to ancestor loggers.
    log.propagate = False
    log.info("Initialized LLMV logger")
    log.info(f'Writing logs to CTFd\'s log directory "{llmv_logfile}" at {log_level} log level')
    return log


## Set up console handler for log records.
class ColorizedFormatter(logging.Formatter):
    """Colorized log record formatter that's keyed to the record's severity level."""

    def __init__(self):
        logging.Formatter.__init__(self)

        # Define the output format for each log record.
        self.logline_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Set the color for each log record severity level type.
        self.severity_colors = {
            log_level: f"\033[1;{color_code}m{self.logline_format}\033[0m"
            for log_level, color_code in (
                (logging.DEBUG, 90),  # Grey text.
                (logging.INFO, 36),  # Cyan text.
                (logging.WARNING, 33),  # Yellow text.
                (logging.ERROR, 31),  # Red text.
                (logging.CRITICAL, 41),
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
        record_formatter = logging.Formatter(log_format)
        # Formate the log entry and return it.
        return record_formatter.format(record)
