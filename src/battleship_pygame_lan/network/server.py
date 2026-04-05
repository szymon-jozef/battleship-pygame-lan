import json
import logging
import socket
import threading
from dataclasses import dataclass

from .network_core import NetworkCore
from .payloads import PayloadTypes, build_start_payload

logger = logging.getLogger(__name__)


@dataclass
class Player:
    conn: socket.socket
    addr: tuple[str, int]
    player_name: str | None = None
    ready_status: bool = False


class NetworkServer(NetworkCore):
    def __init__(
        self, server_ip: str = socket.gethostbyname(socket.gethostname())
    ) -> None:
        super().__init__(ip_address=server_ip)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.players: list[Player] = []

    def handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        logger.info(f"[NEW CONNECTION] {addr} connected")
        current_player = Player(conn=conn, addr=addr)
        self.players.append(current_player)

        connected: bool = True
        while connected:
            try:
                msg_length_str: str = conn.recv(self.HEADER).decode(self.FORMAT).strip()
                if msg_length_str:
                    msg_length: int = int(msg_length_str)
                    msg: str = conn.recv(msg_length).decode(self.FORMAT)

                    logger.info(f"[{addr}] {msg}")

                    try:
                        payload_data = json.loads(msg)
                        payload_type = payload_data.get("type")

                        # TODO! handle other payload types
                        match payload_type:
                            case PayloadTypes.CONNECTION_STATUS.value:
                                if not bool(payload_data.get("status")):
                                    logger.info(
                                        f"[Server] Player {current_player.player_name} "
                                        "wanted to disconnect"
                                    )
                                    if current_player in self.players:
                                        self.players.remove(current_player)
                                    connected = False
                                    break
                            case (
                                PayloadTypes.READY.value
                            ):  # TODO! test this behaviour in tests
                                current_player.player_name = payload_data.get(
                                    "player_name"
                                )
                                current_player.ready_status = True

                                ready_count = sum(
                                    1 for c in self.players if c.ready_status
                                )

                                logger.info(
                                    f"[Server] Player {current_player.player_name} is "
                                    f"ready! ({ready_count}/2)"
                                )

                                if len(self.players) == 2:
                                    self.start_game()
                            case _:
                                pass
                    except json.JSONDecodeError:
                        logger.error(f"[Server] Weird json from: {addr}")
            except OSError:
                logger.error(f"[Server] Critical error from: {addr}")
                break
        if current_player in self.players:
            self.players.remove(current_player)

        conn.close()
        logger.info(f"[Server] {addr} disconnected.")

    def start(self) -> None:
        logger.info("[STARTING] Server is starting")
        logger.info(f"[LISTENING] Server is listening on {self.HOST}")

        self.server.bind(self.ADDR)
        self.server.listen()
        while True:
            conn, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()
            logger.info(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

    def broadcast(self, msg: str, sender_conn: socket.socket | None = None) -> None:
        """
        Send message to every connected client
        """
        for player in self.players:
            if player.conn != sender_conn:
                try:
                    self.send_to_socket(player.conn, msg)
                except Exception as e:
                    logger.error(
                        f"Error while broadcasting to: {player.conn}\n\nError: {e}"
                    )

    def start_game(self) -> None:
        logger.info("[SERVER] The game is starting!")
        payload = build_start_payload()
        self.broadcast(payload)
