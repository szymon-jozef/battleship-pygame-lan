from enum import StrEnum
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

"""

# TODO! Some kind of enum GameState is needed! It will need to be sent by the server


class PayloadTypes(StrEnum):
    """
    Enum representing types a payload can send

    Values:
        CONNECTION_STATUS
        ATTACK
        SHOT_RESULT
        READY
        START
        END
        GAME_OVER
    """

    CONNECTION_STATUS = "connection_status"
    ATTACK = "attack"
    SHOT_RESULT = "shot_result"
    READY = "ready"
    START = "start"
    END = "end"
    GAME_OVER = "game_over"


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
