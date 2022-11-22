import logging


class CustomFormatter(logging.Formatter):
    grey = '\x1b[38;20m'
    green = '\x1b[32;20m'
    yellow = '\x1b[33;20m'
    red = '\x1b[31;20m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'
    format = '[{levelname}] {name}: {message}'
    dt_fmt = '%Y-%m-%d %H:%M:%S'

    FORMATS: dict[int, str] = {
        logging.DEBUG: '[{asctime}] ' + grey + format + reset,
        logging.INFO: '[{asctime}] ' + green + format + reset,
        logging.WARNING: '[{asctime}] ' + yellow + format + reset,
        logging.ERROR: '[{asctime}] ' + red + format + reset,
        logging.CRITICAL: '[{asctime}] ' + bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, self.dt_fmt, style='{')
        return formatter.format(record)
