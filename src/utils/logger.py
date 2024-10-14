#!/usr/local/bin/python
"""
Author: Edmund Bennett
Copyright 2024
"""

from typing import Callable, Optional, Any
from types import FrameType
from logging import Logger, Formatter, StreamHandler, getLogger, INFO, setLoggerClass
from concurrent_log_handler import ConcurrentRotatingFileHandler
from tempfile import gettempdir
from re import search, match
from os.path import join, basename
from datetime import datetime
import time
import inspect


# Subclass the Logger class to add the custom method
class CustomLogger(Logger):
    def __init__(self, name: str, level: int = INFO) -> None:
        super().__init__(name, level)

    def function_call(self) -> None:
        """Creates a info log line for when a function is called.

        Example usage:
        >>> def some_function():
        >>>     log.function_call()
        >>>
        >>> some_function()
        >>>
        >>> 2016-05-28 00:00:00.000 INFO     [some_file.py:22] Calling some_function
        """
        currentframe: Optional[FrameType] = inspect.currentframe()
        if currentframe is not None and currentframe.f_back is not None:
            frame = inspect.currentframe().f_back
            func_name = frame.f_code.co_name
            file_path = frame.f_code.co_filename
            file_name = basename(file_path)
            line_number = frame.f_lineno

            # Create a temporary formatter with the correct file and line information
            temp_formatter = WhitespaceRemovingFormatter(
                f"%(asctime)s.%(msecs)03d %(levelname)s [{file_name}:{line_number}] %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )

            # Store the original formatters
            original_formatters = [
                (handler, handler.formatter) for handler in self.handlers
            ]

            # Set the temporary formatter
            for handler in self.handlers:
                handler.setFormatter(temp_formatter)

            # Log the function call
            self.info(f"Calling {func_name}")

            # Restore the original formatters
            for handler, formatter in original_formatters:
                handler.setFormatter(formatter)


def function_timer(log_result: bool = False) -> Callable:
    """Returns function run time and will print the function's
    returned value, if it is a dict. Otherwise the
    function's runtime will be printed

    Args:
        func (Callable): function, if func() -> dict, the
            dict will be printed

    Returns:
        Callable: wrapper function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            output = func(*args, **kwargs)
            finish_time = time.time()
            elapsed_time = finish_time - start_time
            msg = f"{func._name_} took {elapsed_time:.4f}s to run."

            try:
                if log_result:
                    # if not list or tuple try parse first element as dict
                    result = output
                    if isinstance(result, (list, tuple)) and result:
                        result = result[0]

                    log_results = [
                        f"{key} has a value of {value}" for key, value in result.items()
                    ]
                    log_results = "\n".join(log_results)
                    msg += f"where...\n{log_results}"

            except Exception as e:
                logger.warning(f"Error: {e}")
            finally:
                logger.info(msg)

            return output

        return wrapper

    return decorator


class WhitespaceRemovingFormatter(Formatter):
    """Clears whitespace from around log messages
    and truncates where appropriate.

    Args:
        Formatter (Formatter): An instance of a
        Python logging Formatter class

    Returns:
        Self: Instance of formatter (self)
    """

    MAX_LENGTH: int = 10000

    def format(self, record):
        record.msg = record.msg.strip()
        if len(record.msg) > WhitespaceRemovingFormatter.MAX_LENGTH:
            record.msg = f"{record.msg[: WhitespaceRemovingFormatter.MAX_LENGTH]}..."
        return super(__class__, self).format(record)


# Use this logger in place of the print statement.
# This inherits from Python's built-in logging module.
# Usage: log.info("Hello, World!")
# Information on the standard logging module available here:
# https://docs.python.org/3/library/logging.html

formatter = WhitespaceRemovingFormatter(
    "%(asctime)s.%(msecs)03d %(levelname)s [%(filename)s:%(lineno)d] %(message)s",
    "%Y-%m-%d %H:%M:%S",
)

file_handler = ConcurrentRotatingFileHandler(
    join(
        gettempdir(), "reporting.log"
    ),  # on a Windows device this normally points to C:\Users\Username\AppData\Local\Temp\
    maxBytes=10000000,
    backupCount=5,
)

file_handler.setFormatter(formatter)

console_handler = StreamHandler()
console_handler.setFormatter(formatter)

setLoggerClass(CustomLogger)
logger = getLogger(__name__)
logger.setLevel(INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


class LogScraper:
    """Class to extract content from existing log files.
    Also provides a helper method to delete logs. Works with tracebacks
    enabled via e.g.:
    log.info("Oh no, something bad happened!", exc_info=True)

    Usage:
        scraper = LogScraper(path_to_log)
        log_content = scraper.scrape_log()
    """

    TIMESTAMP_REGEX = (
        r"2[0-9]{3}-[0-1][0-9]-[0-3][0-9] [0-2][0-9]:[0-5][0-9]:[0-5][0-9].[0-9]{3}"
    )
    LOG_LEVEL_REGEX = r"[A-Z]{4,}"
    FILENAME_LINE_NUMBER_REGEX = r"\[([a-zA-Z0-9_.:]+)]"

    def _init_(
        self,
        log_file_path: str,  # C:\Users\EBennett\AppData\Local\Temp
    ) -> None:
        """Scrapes data from specified log file

        Args:
            log_file_path (str): Path to log file to be scraped
        """
        self.log_file_path = log_file_path

    def delete_log(self):
        """Deletes the log provided in the init method"""
        logger.info("Calling delete_log")
        try:
            del self.log_file_path
            logger.info("Log deleted.")
        except IOError as e:
            logger.error(f"Log not deleted. Error: {e}")

    def scrape_log(self) -> list[Optional[dict[str, Any]]]:
        """Scrapes the log provided in the init method.

        Returns:
            list[Optional[dict[str, Any]]]: A list of log entries.
            Tracebacks are appended to the most recent log entry.
        """
        logger.info("Calling scrape_log")
        log_lines = None
        with open(self.log_file_path, "r") as log_file:
            log_lines = log_file.readlines()

        if log_lines is not None:
            logger.info("Log read successful. Scraping log.")

            parsed_log_entries: list[Optional[dict[str, Any]]] = []
            for (
                log_content
            ) in (
                log_lines
            ):  # for each log line, regex matches are removed until all that remains is the content
                log_date: Optional[datetime] = None
                timestamp_search_result = search(self.TIMESTAMP_REGEX, log_content)
                if timestamp_search_result is not None:
                    log_date = datetime.fromisoformat(timestamp_search_result.group())
                    log_content = log_content.replace(
                        timestamp_search_result.group(), ""
                    ).strip()

                if (
                    log_date is None
                ):  # this approach will fail if the log does not start with an ISO datetime, or if the traceback DOES start with one
                    logger.info(
                        "Log line does not start with timestamp. Assuming traceback found and appending to last record."
                    )
                    parsed_log_entries[-1]["traceback"].append(log_content)  # type: ignore [index]
                    continue

                log_level: Optional[str] = None
                log_level_search_result = search(self.LOG_LEVEL_REGEX, log_content)
                if log_level_search_result is not None:
                    log_level = log_level_search_result.group()
                    log_content = log_content.replace(
                        log_level_search_result.group(), ""
                    ).strip()

                log_filename: Optional[str] = None
                log_line_number: Optional[str] = None
                filename_line_number_search_result = match(
                    self.FILENAME_LINE_NUMBER_REGEX, log_content
                )
                if filename_line_number_search_result is not None:
                    (
                        log_filename,
                        log_line_number,
                    ) = filename_line_number_search_result.groups()[0].split(":")
                    log_content = log_content.replace(
                        filename_line_number_search_result.group(), ""
                    ).strip()

                parsed_log_entries.append(
                    {
                        "log_date": log_date,
                        "log_level": log_level,
                        "log_filename": log_filename,
                        "log_line_number": (
                            int(log_line_number) if log_line_number else 0
                        ),
                        "content": log_content,
                        "traceback": [],
                    }
                )

            return parsed_log_entries
