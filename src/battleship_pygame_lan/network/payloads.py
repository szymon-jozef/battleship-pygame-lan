from json import dumps

from battleship_pygame_lan.logic import ShotResult

from .models import GameState, PayloadTypes

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


def build_attack_payload(row: int, column: int, sender: str, receiver: str) -> str:
    """
    Payload player sends to the oponent, saying which place he wants to attack
    """
    return dumps(
        {
            "type": PayloadTypes.ATTACK,
            "row": row,
            "column": column,
            "sender": sender,
            "receiver": receiver,
        }
    )


def build_shot_result_payload(
    row: int, column: int, result: ShotResult, sender: str, receiver: str
) -> str:
    """
    Payload player sends to the oponent, saying if the oponent hit any ship
    """
    return dumps(
        {
            "type": PayloadTypes.SHOT_RESULT,
            "row": row,
            "column": column,
            "result": result.name,
            "sender": sender,
            "receiver": receiver,
        }
    )


def build_ready_payload(player_name: str, status: bool = True) -> str:
    """
    Payload player sends to the server, saying if he is ready to start the game
    """
    return dumps(
        {"type": PayloadTypes.READY, "player_name": player_name, "status": status}
    )


def build_start_game_payload(start: bool = True) -> str:
    """
    Payload server sends to the players, saying it's time to start the game
    """
    return dumps({"type": PayloadTypes.GAME_START, "start": start})


def build_end_game_payload(over: bool = True) -> str:
    """
    Payload server sends to the player, saying the game was has ended
    """
    return dumps({"type": PayloadTypes.GAME_END, "over": over})


def build_lost_payload(player_name: str) -> str:
    """
    Payload player sends to the server, saying he lost all ships
    """
    return dumps({"type": PayloadTypes.LOST, "player_name": player_name})


def build_game_state_payload(current_game_state: GameState) -> str:
    """
    Payload the server sends to the players, saying what game state are we in
    """
    return dumps({"type": PayloadTypes.GAME_STATE, "state": current_game_state.name})
