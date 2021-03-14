import logging


class Config:
    def __init__(self, release: bool = False):
        self.release = release
        self.default_prefix: str
        self.universal_prefix: str = "%lb"
        self.token: str
        self.base_dir: str = '/home/thijs/Lichess-discord-bot'
        self.top_gg_token = open('/etc/topggtoken.txt', 'r').read()
        self.logger = self._set_logger()

        if self.release:
            self.default_prefix = '-'
            self.token = open('/etc/lichessbottoken.txt', 'r').read()
        else:  # Development mode
            self.default_prefix = '$'
            self.token = open('/etc/lichessbottoken_dev.txt', 'r').read()

    def _set_logger(self) -> logging.getLoggerClass():
        logger = logging.getLogger("LichessBot")
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s", "%Y-%m-%d %H:%M")
        if self.release:
            handler = logging.FileHandler(f"{self.base_dir}/LichessBot.log")
        else:
            handler = logging.FileHandler(f"{self.base_dir}/dev/LichessBotDev.log")
            console = logging.StreamHandler()  # Also print development log to console
            console.setLevel(logging.DEBUG)
            console.setFormatter(formatter)
            logger.addHandler(console)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
