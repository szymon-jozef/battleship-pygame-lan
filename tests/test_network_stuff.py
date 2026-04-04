import json

from battleship_pygame_lan.logic import ShotResult
from battleship_pygame_lan.network import payloads


def test_building_payloads_attack() -> None:
    attack_json_str = payloads.build_attack_payload(1, 1)
    attack_dict = json.loads(attack_json_str)
    expected_attack = {"type": "attack", "row": 1, "column": 1}
    assert attack_dict == expected_attack


def test_building_payloads_shot_result() -> None:
    shot_json_str = payloads.build_shot_result_payload(1, 1, ShotResult.Hit)
    shot_dict = json.loads(shot_json_str)
    expected_shot = {
        "type": "shot_result",
        "row": 1,
        "column": 1,
        "result": ShotResult.Hit.name,
    }
    assert shot_dict == expected_shot


def test_building_payloads_ready() -> None:
    ready_json_str = payloads.build_ready_payload("Morbius")
    ready_dict = json.loads(ready_json_str)
    expected_ready = {
        "type": "ready",
        "player_name": "Morbius",
        "status": True,
    }
    assert ready_dict == expected_ready


def test_building_payloads_start() -> None:
    start_json_str = payloads.build_start_payload()
    start_dict = json.loads(start_json_str)
    expected_start = {
        "type": "start",
        "start": True,
    }
    assert start_dict == expected_start


def test_building_payloads_end() -> None:
    end_json_str = payloads.build_end_payload()
    end_dict = json.loads(end_json_str)
    expected_end = {
        "type": "end",
        "end": True,
    }
    assert end_dict == expected_end


def test_building_payloads_game_over() -> None:
    game_over_json_str = payloads.build_game_over_payload()
    game_over_dict = json.loads(game_over_json_str)
    expected_game_over = {
        "type": "game_over",
        "over": True,
    }
    assert game_over_dict == expected_game_over
