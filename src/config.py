class Config:
    def __init__(self, release: bool = False):
        self.release = release
        self.prefix: str = ""
        self.token: str = ""
        self.base_dir: str = ""
        self._set_config()

    def _set_config(self):
        if self.release:
            self.prefix = '-'
            self.token = open('/etc/lichessbottoken.txt', 'r').read()
            self.base_dir = '/home/thijs/Lichess-discord-bot'
        else:
            self.prefix = '$'
            self.token = open('/etc/lichessbottoken_dev.txt', 'r').read()
            self.base_dir = '/home/thijs/Lichess-discord-bot-dev'
