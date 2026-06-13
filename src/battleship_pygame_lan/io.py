import configparser
from pathlib import Path

from appdirs import user_config_dir  # type: ignore


class Config:
    def __init__(self, config_dir: Path | None = None) -> None:
        if config_dir is None:
            config_dir = Path(user_config_dir("battleship-pygame-lan"))

        self.config_dir: Path = config_dir
        self.file_name: str = "config.ini"

        self.full_path: Path = self.config_dir / self.file_name
        self.config_parser: configparser.ConfigParser = configparser.ConfigParser()
        self.section = "Settings"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def read_config(self) -> None:
        self.config_parser.read(self.full_path, encoding="utf-8")

        if not self.config_parser.has_section(self.section):
            self.config_parser.add_section(self.section)

    def _save_config(self) -> None:
        with open(self.full_path, "w", encoding="utf-8") as f:
            self.config_parser.write(f)

    @property
    def get_player_name(self) -> str:
        self.read_config()
        return self.config_parser.get(self.section, "player_name", fallback="Player")

    @property
    def get_volume(self) -> float:
        self.read_config()
        return self.config_parser.getfloat(self.section, "volume", fallback=0.5)

    def save_player_name(self, player_name: str) -> None:
        self.read_config()
        self.config_parser.set(self.section, "player_name", player_name)
        self._save_config()

    def save_volume(self, volume: float) -> None:
        self.read_config()
        self.config_parser.set(self.section, "volume", str(volume))
        self._save_config()
