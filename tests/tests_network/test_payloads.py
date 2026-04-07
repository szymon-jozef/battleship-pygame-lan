import json

from battleship_pygame_lan.logic import ShotResult
from battleship_pygame_lan.network import (
    GameState,
    ReadyType,
    payloads,
)


# payloads
def test_building_payloads_attack() -> None:
    sender: str = "morbius"
    receiver: str = "spider-mid"
    attack_json_str = payloads.build_attack_payload(1, 1, sender, receiver)
    attack_dict = json.loads(attack_json_str)
    expected_attack = {
        "type": "attack",
        "row": 1,
        "column": 1,
        "sender": sender,
        "receiver": receiver,
    }
    assert attack_dict == expected_attack


def test_building_payloads_shot_result() -> None:
    sender: str = "morbius"
    receiver: str = "spider-mid"
    shot_json_str = payloads.build_shot_result_payload(
        1, 1, ShotResult.Hit, sender, receiver
    )
    shot_dict = json.loads(shot_json_str)
    expected_shot = {
        "type": "shot_result",
        "row": 1,
        "column": 1,
        "result": ShotResult.Hit.name,
        "sender": sender,
        "receiver": receiver,
    }
    assert shot_dict == expected_shot


def test_building_payloads_ready() -> None:
    ready_type: ReadyType = ReadyType.LOBBY
    ready_json_str = payloads.build_ready_payload("Morbius", ready_type)
    ready_dict = json.loads(ready_json_str)
    expected_ready = {
        "type": "ready",
        "player_name": "Morbius",
        "ready_type": "lobby_ready",
        "status": True,
    }
    assert ready_dict == expected_ready


def test_building_payloads_ready_ship_placed() -> None:
    ready_type: ReadyType = ReadyType.SHIP_PLACED
    ready_json_str = payloads.build_ready_payload("Spider-mid", ready_type)
    ready_dict = json.loads(ready_json_str)
    expected_ready = {
        "type": "ready",
        "player_name": "Spider-mid",
        "ready_type": "ship_placed",
        "status": True,
    }
    assert ready_dict == expected_ready


def test_building_payloads_game_start() -> None:
    start_json_str = payloads.build_start_game_payload()
    start_dict = json.loads(start_json_str)
    expected_start = {
        "type": "game_start",
        "start": True,
    }
    assert start_dict == expected_start


def test_building_payloads_game_end() -> None:
    name: str = "morbius"
    game_end_json_str = payloads.build_end_game_payload(name)
    game_end_dict = json.loads(game_end_json_str)
    expected_game_end = {"type": "game_end", "over": True, "loser": name}
    assert game_end_dict == expected_game_end


def test_building_payloads_lost() -> None:
    gamer: str = "spider-mid"
    end_json_str = payloads.build_lost_payload(gamer)
    end_dict = json.loads(end_json_str)
    expected_end = {
        "type": "lost",
        "player_name": gamer,
    }
    assert end_dict == expected_end


def test_building_payloads_game_state() -> None:
    state: GameState = GameState.LOBBY
    game_state_payload: str = payloads.build_game_state_payload(state)
    game_state_dict = json.loads(game_state_payload)
    expected_game_state = {"type": "game_state", "state": state.name}
    assert game_state_dict == expected_game_state
