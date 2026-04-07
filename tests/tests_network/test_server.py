import json
import socket
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from battleship_pygame_lan.logic import ShotResult
from battleship_pygame_lan.network import (
    GameState,
    NetworkClient,
    NetworkPlayer,
    NetworkServer,
    build_attack_payload,
    build_end_game_payload,
    build_shot_result_payload,
    build_start_game_payload,
)


@pytest.fixture
def mock_socket() -> Generator:
    with patch("socket.socket") as mock_mock:
        mock_sock = mock_mock.return_value
        mock_sock.recv.return_value = b""
        yield mock_mock.return_value


@pytest.fixture
def client(mock_socket: socket.socket) -> NetworkClient:
    return NetworkClient("morbius")


@pytest.fixture
def mock_server(mock_socket: MagicMock) -> NetworkServer:
    return NetworkServer(server_ip="127.0.0.2")


def test_server_initialization(mock_server: NetworkServer) -> None:
    assert mock_server.MAX_PLAYERS == 2
    assert len(mock_server.players) == 0


def test_server_start_game(mock_server: NetworkServer) -> None:
    mock_conn = MagicMock()
    mock_player = NetworkPlayer(mock_conn, addr=("127.0.0.2", 5001))

    mock_conn2 = MagicMock()
    mock_player2 = NetworkPlayer(mock_conn2, addr=("127.0.0.2", 5001))
    mock_player.ready_status = True
    mock_player2.ready_status = True
    mock_server.players = [mock_player, mock_player2]

    mock_server._start_game()

    expected_paload: bytes = build_start_game_payload().encode("utf-8")
    mock_conn.sendall.assert_any_call(expected_paload)


def test_server_end_game(mock_server: NetworkServer) -> None:
    name: str = "morbius"
    mock_conn = MagicMock()
    mock_player = NetworkPlayer(mock_conn, addr=("127.0.0.2", 5001), player_name=name)
    mock_server.players = [mock_player]

    mock_server._end_game(name)

    expected_paload: bytes = build_end_game_payload(name).encode("utf-8")
    mock_conn.sendall.assert_any_call(expected_paload)


def test_server_attack_route(mock_server: NetworkServer) -> None:
    mock_conn_morbius = MagicMock()
    player_morbius = NetworkPlayer(mock_conn_morbius, addr=("127.0.0.1", 5001))
    player_morbius.player_name = "morbius"

    mock_conn_spider = MagicMock()
    player_spider = NetworkPlayer(mock_conn_spider, addr=("127.0.0.2", 5002))
    player_spider.player_name = "spider-mid"

    mock_server.players = [player_morbius, player_spider]
    mock_server.current_turn = player_morbius

    msg: str = build_attack_payload(
        row=2, column=2, sender="morbius", receiver="spider-mid"
    )
    payload_data: dict = json.loads(msg)

    mock_server._handle_attack(payload_data, msg)

    expected_bytes = msg.encode("utf-8")

    mock_conn_spider.sendall.assert_any_call(expected_bytes)


def test_server_shot_result_route(mock_server: NetworkServer) -> None:
    mock_conn_morbius = MagicMock()
    player_morbius = NetworkPlayer(mock_conn_morbius, addr=("127.0.0.1", 5001))
    player_morbius.player_name = "morbius"

    mock_conn_spider = MagicMock()
    player_spider = NetworkPlayer(mock_conn_spider, addr=("127.0.0.2", 5002))
    player_spider.player_name = "spider-mid"

    mock_server.players = [player_morbius, player_spider]
    mock_server.current_turn = player_spider
    mock_server.current_game_state = GameState.WAR

    msg: str = build_shot_result_payload(
        row=2, column=2, result=ShotResult.Hit, sender="morbius", receiver="spider-mid"
    )
    payload_data: dict = json.loads(msg)

    mock_server._handle_shot_result(payload_data, msg)

    expected_bytes = msg.encode("utf-8")

    mock_conn_spider.sendall.assert_any_call(expected_bytes)

    assert mock_server.current_turn is player_morbius


def test_shot_result_no_war(mock_server: NetworkServer) -> None:
    mock_conn_morbius = MagicMock()
    player_morbius = NetworkPlayer(mock_conn_morbius, addr=("127.0.0.1", 5001))
    player_morbius.player_name = "morbius"

    mock_conn_spider = MagicMock()
    player_spider = NetworkPlayer(mock_conn_spider, addr=("127.0.0.2", 5002))
    player_spider.player_name = "spider-mid"

    mock_server.players = [player_morbius, player_spider]
    mock_server.current_turn = player_spider
    mock_server.current_game_state = GameState.LOBBY

    msg: str = build_shot_result_payload(
        row=2, column=2, result=ShotResult.Hit, sender="morbius", receiver="spider-mid"
    )
    payload_data: dict = json.loads(msg)

    mock_server._handle_shot_result(payload_data, msg)
    mock_conn_morbius.sendall.assert_not_called()
    mock_conn_spider.sendall.assert_not_called()
    assert mock_server.current_turn is player_spider


def test_server_reject_conn_full(mock_server: NetworkServer) -> None:
    mock_server.players = [
        NetworkPlayer(conn=MagicMock(), addr=("127.0.0.2", 5001)),
        NetworkPlayer(conn=MagicMock(), addr=("127.0.0.2", 5002)),
    ]

    new_conn = MagicMock()
    new_addr = ("127.0.0.1", 5003)

    mock_server._handle_client(new_conn, new_addr)

    new_conn.close.assert_called_once()
    assert len(mock_server.players) == 2


@patch.object(NetworkServer, "send_to_socket")
def test_server_broadcast(
    mock_send_to_socket: MagicMock, mock_server: NetworkServer
) -> None:
    p1 = NetworkPlayer(conn=MagicMock(), addr=("127.0.0.2", 5001))
    p2 = NetworkPlayer(conn=MagicMock(), addr=("127.0.0.2", 5002))
    p3 = NetworkPlayer(conn=MagicMock(), addr=("127.0.0.2", 5003))
    mock_server.players.extend([p1, p2, p3])

    test_msg = '{"type": "start"}'

    mock_server._broadcast(test_msg, sender_conn=p1.conn)
    assert mock_send_to_socket.call_count == 2
    mock_send_to_socket.assert_any_call(p2.conn, test_msg)
    mock_send_to_socket.assert_any_call(p3.conn, test_msg)


def test_server_player_cleanup(mock_server: NetworkServer) -> None:
    p1 = NetworkPlayer(conn=MagicMock(), addr=("127.0.0.2", 5001))
    mock_server.players.append(p1)
    mock_server._handle_player_cleanup(p1)
    assert len(mock_server.players) == 0
    p1.conn.close.assert_called_once()


@patch.object(NetworkServer, "send_to_socket")
def test_server_routing(
    mock_send_to_socket: MagicMock, mock_server: NetworkServer
) -> None:
    p1_name = "morbius"
    p2_name = "spider-mid"
    p1 = NetworkPlayer(conn=MagicMock(), addr=("127.0.0.2", 5001), player_name=p1_name)
    p2 = NetworkPlayer(conn=MagicMock(), addr=("127.0.0.2", 5002), player_name=p2_name)
    mock_server.players.extend([p1, p2])
    test_msg = "test-msg"
    mock_server._route(test_msg, p2_name)

    mock_send_to_socket.assert_called_once_with(p2.conn, test_msg)


@patch.object(NetworkServer, "send_to_socket")
def test_server_routing_player_not_found(
    mock_send_to_socket: MagicMock, mock_server: NetworkServer
) -> None:
    p1_name = "morbius"
    p1 = NetworkPlayer(conn=MagicMock(), addr=("127.0.0.2", 5001), player_name=p1_name)
    mock_server.players.append(p1)

    mock_server._route("test-msg", "doctor-weird")

    mock_send_to_socket.assert_not_called()
