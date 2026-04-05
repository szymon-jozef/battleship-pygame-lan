import socket
from logging import getLogger

from battleship_pygame_lan.logic import ShotResult

from .payloads import (
    build_attack_payload,
    build_end_payload,
    build_ready_payload,
    build_shot_result_payload,
)

logger = getLogger(__name__)


class NetworkClient:
    def __init__(self) -> None:
        self.SERVER = socket.gethostbyname(socket.gethostname())
        self.HEADER = 64
        self.PORT = 6969
        self.FORMAT = "utf-8"
        self.DISCONNECT_MSG = "!DISCONNET"
        self.ADDR = (self.SERVER, self.PORT)

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(self.ADDR)

    def send(self, msg: str) -> None:
        try:
            message = msg.encode(self.FORMAT)
            msg_length = len(message)
            send_length = str(msg_length).encode(self.FORMAT)
            send_length += b" " * (self.HEADER - len(send_length))
            self.client.sendall(send_length)
            self.client.sendall(message)
        except OSError as e:
            logger.error(f"[Client] Error while sending the message: {e}")

    def disconnect(self) -> None:
        self.send(self.DISCONNECT_MSG)

    def ready(self, name: str) -> None:
        self.send(build_ready_payload(name))

    def send_attack_info(self, row: int, column: int) -> None:
        self.send(build_attack_payload(row, column))

    def send_shot_result(self, row: int, column: int, shot_result: ShotResult) -> None:
        self.send(build_shot_result_payload(row, column, shot_result))

    def end(self) -> None:
        self.send(build_end_payload())


if __name__ == "__main__":
    client = NetworkClient()
    client.send("Hello world!")
