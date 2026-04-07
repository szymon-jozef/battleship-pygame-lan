import socket
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from battleship_pygame_lan.network import (
    NetworkClient,
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
