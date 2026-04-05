import json
import logging
import socket
import threading

from .network_core import NetworkCore
from .payloads import PayloadTypes, build_start_payload

logger = logging.getLogger(__name__)


class NetworkServer(NetworkCore):
    def __init__(
        self, server_ip: str = socket.gethostbyname(socket.gethostname())
    ) -> None:
        super().__init__(ip_address=server_ip)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients: list[socket.socket] = []
        self.ready_players: set[str] = set()

    def handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        logger.info(f"[NEW CONNECTION] {addr} connected")
        self.clients.append(conn)

        connected: bool = True
        while connected:
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
                            player_name = payload_data.get("player_name")
                            logger.info(
                                f"[Server] Player {player_name} wanted to disconnect"
                            )
                            if player_name in self.ready_players:
                                self.ready_players.remove(player_name)
                            connected = False
                            break
                        case (
                            PayloadTypes.READY.value
                        ):  # TODO! test this behaviour in tests
                            player_name = payload_data.get("player_name")
                            self.ready_players.add(player_name)

                            logger.info(
                                f"[Server] Player {player_name} is ready! "
                                f"({len(self.ready_players)}/2)"
                            )

                            if len(self.ready_players) == 2:
                                self.start_game()
                        case _:
                            pass
                except json.JSONDecodeError:
                    logger.error(f"[Server] Weird json from: {addr}")
        if conn in self.clients:
            self.clients.remove(conn)

        conn.close()

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
        for client in self.clients:
            if client != sender_conn:
                try:
                    self.send_to_socket(client, msg)
                except Exception as e:
                    logger.error(f"Error while broadcasting to: {client}\n\nError: {e}")

    def start_game(self) -> None:
        logger.info("[SERVER] The game is starting!")
        payload = build_start_payload()
        self.broadcast(payload)
