import logging


class Config:
    def __init__(self, release: bool = False):
        self.release = release
        self.prefix: str
        self.token: str
        self.base_dir: str = '/home/thijs/Lichess-discord-bot'
        self.top_gg_token = open('/etc/topggtoken.txt', 'r').read()
        self.logger = self._set_logger()

        self._set_config()

    def _set_config(self):
        if self.release:
            self.prefix = '-'
            self.token = open('/etc/lichessbottoken.txt', 'r').read()
        else:
            self.prefix = '$'
            self.token = open('/etc/lichessbottoken_dev.txt', 'r').read()

    def _set_logger(self) -> logging.getLoggerClass():
        logger = logging.getLogger("LichessBot")
        logger.setLevel(logging.INFO)
        if self.release:
            handler = logging.FileHandler(f"{self.base_dir}/LichessBot.log")
        else:
            handler = logging.FileHandler(f"{self.base_dir}/dev/LichessBotDev.log")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
