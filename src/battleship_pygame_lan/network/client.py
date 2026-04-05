import json
import socket
from logging import getLogger
from queue import Queue
from threading import Thread

from battleship_pygame_lan.logic import ShotResult

from .network_core import NetworkCore
from .payloads import (
    PayloadTypes,
    build_attack_payload,
    build_connection_status_payload,
    build_end_payload,
    build_ready_payload,
    build_shot_result_payload,
)

logger = getLogger(__name__)


class NetworkClient(NetworkCore):
    def __init__(
        self,
        player_name: str,
        server_ip: str = socket.gethostbyname(socket.gethostname()),
    ) -> None:
        super().__init__(ip_address=server_ip)

        self.player_name: str = player_name
        self.message_queue: Queue = Queue()
        self.connected: bool = False

    def connect(self) -> None:
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(self.ADDR)
        self.connected = True

        receive_thread: Thread = Thread(target=self.receive, daemon=True)
        receive_thread.start()

    def disconnect(self) -> None:
        self.send(build_connection_status_payload(self.player_name, False))
        self.connected = False
        self.client.close()

    def send(self, msg: str) -> None:
        self.send_to_socket(self.client, msg)

    def receive(self) -> None:
        while self.connected:
            try:
                header: bytes = self.client.recv(self.HEADER)

                if not header:
                    logger.info("[Client] Connection closed by the server.")
                    self.connected = False
                    break

                msg_length_str: str = header.decode(self.FORMAT).strip()
                if msg_length_str:
                    msg_len: int = int(msg_length_str)
                    msg: str = self.client.recv(msg_len).decode(self.FORMAT)

                    logger.info("[Client] Got new message!")
                    logger.debug(f"[Client] Message: {msg}")

                    try:
                        payload_data: dict = json.loads(msg)
                        payload_type = payload_data.get("type")

                        match payload_type:
                            case PayloadTypes.CONNECTION_STATUS.value:
                                if not bool(payload_data.get("status")):
                                    logger.info(
                                        "[Client] Server wanted to disconnect, so "
                                        "disconnecting... :("
                                    )
                                    self.connected = False
                                    break
                            case PayloadTypes.ATTACK.value:
                                self.message_queue.put(payload_data)
                            case _:
                                pass
                    except json.JSONDecodeError:
                        logger.error("[Client] got weird json")
            except OSError as e:
                logger.error(f"[Client] Connection error in receive: {e}")
                self.connected = False
                break

    def ready(self, name: str) -> None:
        self.send(build_ready_payload(name))

    def send_attack_info(self, row: int, column: int) -> None:
        self.send(build_attack_payload(row, column))

    def send_shot_result(self, row: int, column: int, shot_result: ShotResult) -> None:
        self.send(build_shot_result_payload(row, column, shot_result))

    def end(self) -> None:
        self.send(build_end_payload())
