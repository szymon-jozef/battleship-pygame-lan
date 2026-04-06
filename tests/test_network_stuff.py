import json
import socket
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from battleship_pygame_lan.logic import ShotResult
from battleship_pygame_lan.network import (
    GameState,
    NetworkClient,
    NetworkServer,
    Player,
    payloads,
)


# payloads
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


def test_building_payloads_game_state() -> None:
    state: GameState = GameState.LOBBY
    game_state_payload: str = payloads.build_game_state_payload(state)
    game_state_dict = json.loads(game_state_payload)
    expected_game_state = {"type": "game_state", "state": state.name}
    assert game_state_dict == expected_game_state


# client
@pytest.fixture
def mock_socket() -> Generator:
    with patch("socket.socket") as mock_mock:
        mock_sock = mock_mock.return_value
        mock_sock.recv.return_value = b""
        yield mock_mock.return_value


@pytest.fixture
def client(mock_socket: socket.socket) -> NetworkClient:
    return NetworkClient("morbius")


def test_client_send_success(client: NetworkClient, mock_socket: MagicMock) -> None:
    test_msg = "test_msg"
    client.connect()
    client.send(test_msg)

    encoded_msg: bytes = test_msg.encode(client.FORMAT)
    expected_header_len: bytes = str(len(encoded_msg)).encode("utf-8")
    expected_header: bytes = expected_header_len + b" " * (
        client.HEADER - len(expected_header_len)
    )

    assert mock_socket.sendall.call_count == 2

    mock_socket.sendall.assert_any_call(expected_header)
    mock_socket.sendall.assert_any_call(encoded_msg)


# server
@pytest.fixture
def mock_server(mock_socket: MagicMock) -> NetworkServer:
    return NetworkServer(server_ip="127.0.0.2")


def test_server_initialization(mock_server: NetworkServer) -> None:
    assert mock_server.MAX_PLAYERS == 2
    assert len(mock_server.players) == 0


def test_server_reject_conn_full(mock_server: NetworkServer) -> None:
    mock_server.players = [
        Player(conn=MagicMock(), addr=("127.0.0.2", 5001)),
        Player(conn=MagicMock(), addr=("127.0.0.2", 5002)),
    ]

    new_conn = MagicMock()
    new_addr = ("127.0.0.1", 5003)

    mock_server.handle_client(new_conn, new_addr)

    new_conn.close.assert_called_once()
    assert len(mock_server.players) == 2


@patch.object(NetworkServer, "send_to_socket")
def test_server_broadcast(
    mock_send_to_socket: MagicMock, mock_server: NetworkServer
) -> None:
    p1 = Player(conn=MagicMock(), addr=("127.0.0.2", 5001))
    p2 = Player(conn=MagicMock(), addr=("127.0.0.2", 5002))
    p3 = Player(conn=MagicMock(), addr=("127.0.0.2", 5003))
    mock_server.players.extend([p1, p2, p3])

    test_msg = '{"type": "start"}'

    mock_server.broadcast(test_msg, sender_conn=p1.conn)
    assert mock_send_to_socket.call_count == 2
    mock_send_to_socket.assert_any_call(p2.conn, test_msg)
    mock_send_to_socket.assert_any_call(p3.conn, test_msg)


def test_server_player_cleanup(mock_server: NetworkServer) -> None:
    p1 = Player(conn=MagicMock(), addr=("127.0.0.2", 5001))
    mock_server.players.append(p1)
    mock_server._handle_player_cleanup(p1)
    assert len(mock_server.players) == 0
    p1.conn.close.assert_called_once()
