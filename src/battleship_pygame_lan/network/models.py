import socket
from dataclasses import dataclass
from enum import Enum, StrEnum, auto


@dataclass
class NetworkPlayer:
    conn: socket.socket
    addr: tuple[str, int]
    player_name: str | None = None
    ready_status: bool = False


class GameState(Enum):
    LOBBY = auto()
    SHIP_PLACEMENT = auto()
    WAR = auto()
    FINISH = auto()


class PayloadTypes(StrEnum):
    """
    Enum representing types a payload can send

    Values:
        CONNECTION_STATUS -  current connection status (bool, True when connected)
        ATTACK - used when you want to attack someone
        SHOT_RESULT - used when you were attacked
        READY - used to signal that you're ready to play
        START - used by the server to say that the game is about to start
        END - used when you lost all ships
        GAME_OVER - used by the server to say someone has lost
        GAME_STATE - used by the server to indicate current game state
    """

    CONNECTION_STATUS = "connection_status"
    ATTACK = "attack"
    SHOT_RESULT = "shot_result"
    READY = "ready"
    GAME_START = "game_start"
    LOST = "lost"
    GAME_END = "game_end"
    GAME_STATE = "game_state"
