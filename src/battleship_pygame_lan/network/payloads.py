from enum import Enum, StrEnum, auto
from json import dumps

from battleship_pygame_lan.logic import ShotResult

"""
What communication do we want?

# Player - Player
- I attacked you
- You attacked me and you missed/hit

I thinks that's all for that.

This is represented by PayloadTypes.ATTACK and PayloadTypes.SHOT_RESULT

# Player - server
- I placed all my ships, please note that I'm ready
- Okay!

I forgot about some of the most important stuff!

- Hey, I'm a player that wants to do ship stuff, my name is morbius
- Okay I have you on my list

and

- Hey, me morbius is tired of morbing for now, please disconnect
- Bye!!!

Represented by PayloadTypes.READY

- I lost all my ships, please end the game!
- Okey dokey

Represented by PayloadTypes.END

# Server - player
- Player {player} has lost! Please stop playing
- Ok

Represented by PayloadTypes.GAME_OVER

- Now we are doing this: <for example: placing ships>
- Oki ^^

"""


# TODO this does not belong in here
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
    START = "start"
    END = "end"
    GAME_OVER = "game_over"
    GAME_STATE = "game_state"


def build_connection_status_payload(player_name: str, connect: bool) -> str:
    """
    Payload player sends to the server, when he wants to change connection status
    """
    return dumps(
        {
            "type": PayloadTypes.CONNECTION_STATUS,
            "player_name": player_name,
            "status": connect,
        }
    )


def build_attack_payload(row: int, column: int) -> str:
    """
    Payload player sends to the oponent, saying which place he wants to attack
    """
    return dumps({"type": PayloadTypes.ATTACK, "row": row, "column": column})


def build_shot_result_payload(row: int, column: int, result: ShotResult) -> str:
    """
    Payload player sends to the oponent, saying if the oponent hit any ship
    """
    return dumps(
        {
            "type": PayloadTypes.SHOT_RESULT,
            "row": row,
            "column": column,
            "result": result.name,
        }
    )


def build_ready_payload(player_name: str, status: bool = True) -> str:
    """
    Payload player sends to the server, saying if he is ready to start the game
    """
    return dumps(
        {"type": PayloadTypes.READY, "player_name": player_name, "status": status}
    )


def build_start_payload(start: bool = True) -> str:
    """
    Payload server sends to the players, saying it's time to start the game
    """
    return dumps({"type": PayloadTypes.START, "start": start})


def build_end_payload(end: bool = True) -> str:
    """
    Payload player sends to the server, saying he lost all ships
    """
    return dumps({"type": PayloadTypes.END, "end": end})


def build_game_over_payload(over: bool = True) -> str:
    """
    Payload server sends to the player, saying the game was has ended
    """
    return dumps({"type": PayloadTypes.GAME_OVER, "over": over})


def build_game_state_payload(current_game_state: GameState) -> str:
    """
    Payload the server sends to the players, saying what game state are we in
    """
    return dumps({"type": PayloadTypes.GAME_STATE, "state": current_game_state.name})
