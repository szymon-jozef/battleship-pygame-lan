import json
import logging
import socket
import threading
from dataclasses import dataclass

from .network_core import NetworkCore
from .payloads import (
    GameState,
    PayloadTypes,
    build_game_state_payload,
    build_start_payload,
)

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
        self.MAX_PLAYERS: int = 2
        self.players_lock = threading.Lock()
        self.players: list[Player] = []
        self.current_game_state: GameState | None = None

    def handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        with self.players_lock:
            if len(self.players) >= self.MAX_PLAYERS:
                logger.info(
                    f"[Server] client at {addr} tried to connect, but server is full"
                )
                conn.close()
                return

        logger.info(f"[NEW CONNECTION] {addr} connected")
        current_player = Player(conn=conn, addr=addr)
        self.players.append(current_player)

        connected: bool = True
        while connected:
            try:
                msg_length_str: str = conn.recv(self.HEADER).decode(self.FORMAT).strip()
                if not msg_length_str:
                    logger.error(
                        f"[Server] client {addr} sent empty bytes. Disconnecting..."
                    )
                    connected = False
                    break

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
                                break
                        case PayloadTypes.READY.value:
                            self._handle_player_ready(current_player)
                        case PayloadTypes.ATTACK.value:
                            # TODO some kind of routing
                            pass
                        case PayloadTypes.SHOT_RESULT.value:
                            # same as above
                            pass
                        case _:
                            pass

                except json.JSONDecodeError:
                    logger.error(f"[Server] Weird json from: {addr}")
            except OSError:
                logger.error(f"[Server] Critical error from: {addr}")
                break
        self._handle_player_cleanup(current_player)

    def _handle_player_cleanup(self, player: Player) -> None:
        with self.players_lock:
            if player in self.players:
                self.players.remove(player)
        player.conn.close()
        logger.info(f"[Server] {player.addr} disconnected and cleaned up")

    def _handle_player_ready(self, current_player: Player) -> None:
        current_player.ready_status = True

        with self.players_lock:
            ready_count = sum(1 for c in self.players if c.ready_status)
            players_len = len(self.players)

        logger.info(
            f"[Server] Player {current_player.player_name} is ready! "
            f"({ready_count}/{self.MAX_PLAYERS}) out of {players_len} "
            "connected"
        )

        if ready_count == self.MAX_PLAYERS:
            self.start_game()

    def start(self) -> None:
        logger.info("[STARTING] Server is starting")
        logger.info(f"[LISTENING] Server is listening on {self.HOST}")

        self.server.bind(self.ADDR)
        self.server.listen()
        while True:
            conn, addr = self.server.accept()
            thread = threading.Thread(
                target=self.handle_client, args=(conn, addr), daemon=True
            )
            thread.start()
            logger.info(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

    def broadcast(self, msg: str, sender_conn: socket.socket | None = None) -> None:
        """
        Send message to every connected client
        """
        players_copy: list[Player] = []
        with self.players_lock:
            players_copy = [
                player for player in self.players if player.conn != sender_conn
            ]

        for player in players_copy:
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

    def change_game_state(self, game_state: GameState) -> None:
        logger.info(f"[Server] We're changing the game state to {game_state.value}")
        payload = build_game_state_payload(game_state)
        self.broadcast(payload)
