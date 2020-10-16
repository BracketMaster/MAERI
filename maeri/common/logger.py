import logging
class LogIndent():
    indent = "\t"

    def __enter__(self):
        LogIndent.indent += "\t"

    def __exit__(self ,type, value, traceback):
        LogIndent.indent = LogIndent.indent[:-1]

class AppFilter(logging.Filter):
    def filter(self, record):
        record.indent = LogIndent.indent
        return True

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    magenta = "\u001b[35m"
    blue = "\u001b[34m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(levelname)s: %(indent)s%(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: magenta + format + reset,
        logging.INFO: blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

logger = logging.getLogger()
logger.addFilter(AppFilter())
    
# create console handler with a higher log level
ch = logging.StreamHandler()

# was debug set on terminal?
import os
if os.getenv('DEBUG'):
    logger.setLevel(logging.DEBUG)
    ch.setLevel(logging.DEBUG)

ch.setFormatter(CustomFormatter())
logger.addHandler(ch)