from logging import getLogger, Formatter, StreamHandler
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from os import getenv, path, makedirs

# Standard logging class for all microservices

class BotLog:
    def __init__(self, logger_name: str) -> None:
        self.log_level = getenv("LOG_LEVEL", "INFO")
        self.logger = getLogger(logger_name)
        self.log_file_name = f"logs/api_{self.log_level}_{datetime.now().strftime('%b').lower()}.log"
        self.logger.setLevel(self.log_level)
        # Create the log file if it doesn't exist
        self.made_log_file = False

        # create handler for logger to write to file
        if not path.exists(self.log_file_name):
            self.made_log_file = True
            makedirs(path.dirname(self.log_file_name), exist_ok=True)
            open(self.log_file_name, 'a').close()

        # create handler for logger to write to file
        handler = TimedRotatingFileHandler(self.log_file_name, when='midnight', interval=1, backupCount=120)
        handler.setLevel(self.log_level)
        formatter = Formatter('[%(asctime)s][%(levelname)s][%(name)s]: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # create handler for logger to print to console
        console_handler = StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        self.logger.info(f"Logger {logger_name} initialized with log level {self.log_level}")
        if self.made_log_file:
            self.logger.warning(f"Log file {self.log_file_name} created")
        else:
            self.logger.debug(f"Log file {self.log_file_name} already exists")

    def debug(self, message: str) -> None:
        self.logger.debug(message)

    def info(self, message: str) -> None:
        self.logger.info(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def error(self, message: str) -> None:
        self.logger.error(message)

    def critical(self, message: str) -> None:
        self.logger.critical(message)
