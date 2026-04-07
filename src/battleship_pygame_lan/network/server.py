import json
import logging
import socket
import threading

from battleship_pygame_lan.logic import ShotResult

from .models import GameState, NetworkPlayer, PayloadTypes
from .network_core import NetworkCore
from .payloads import (
    build_end_game_payload,
    build_game_state_payload,
    build_start_game_payload,
)

logger = logging.getLogger(__name__)


class NetworkServer(NetworkCore):
    def __init__(
        self, server_ip: str = socket.gethostbyname(socket.gethostname())
    ) -> None:
        super().__init__(ip_address=server_ip)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.MAX_PLAYERS: int = 2
        self.players_lock = threading.Lock()
        self.players: list[NetworkPlayer] = []
        self.current_game_state: GameState | None = None
        self.current_turn: NetworkPlayer | None = None

    def start(self) -> None:
        """
        Method for starting the server. Needs to be run if you want to use the server!!!
        """
        logger.info("[STARTING] Server is starting")
        logger.info(f"[LISTENING] Server is listening on {self.HOST}")

        self.server.bind(self.ADDR)
        self.server.listen()
        while True:
            conn, addr = self.server.accept()
            thread = threading.Thread(
                target=self._handle_client, args=(conn, addr), daemon=True
            )
            thread.start()
            logger.info(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

    def start_game(
        self,
    ) -> None:
        """
        Method for handling the game start.
        It broadcasts the game was started
        """
        logger.info("[SERVER] The game is starting!")
        payload = build_start_game_payload()
        self._broadcast(payload)

    def end_game(self) -> None:
        """
        Method for broadcasting the game has finished.
        """
        logger.info("[Server] The game has finished!")
        payload = build_end_game_payload()
        self._broadcast(payload)

    def change_game_state(self, game_state: GameState) -> None:
        """
        Broadcast game state to every player
        """
        logger.info(f"[Server] We're changing the game state to {game_state.value}")
        payload = build_game_state_payload(game_state)
        self._broadcast(payload)

    def _broadcast(self, msg: str, sender_conn: socket.socket | None = None) -> None:
        """
        Send message to every connected client
        """
        players_copy: list[NetworkPlayer] = []
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

    def _route(self, msg: str, receiver: str) -> None:
        """
        Route the message to receiver
        """
        player_receiver: NetworkPlayer | None = None
        with self.players_lock:
            for player in self.players:
                if player.player_name == receiver:
                    player_receiver = player
                    break
        if player_receiver:
            try:
                self.send_to_socket(player_receiver.conn, msg)
            except Exception as e:
                logger.error(f"[Server] Error while routing to {receiver}: {e}")
        else:
            logger.warning(
                f"[Server] Could not route the message. Receiver {receiver} not found"
            )

    def _handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        """
        Private method for handling the client.
        Remember! This method is meant to run in it's own thread
        """
        with self.players_lock:
            if len(self.players) >= self.MAX_PLAYERS:
                logger.info(
                    f"[Server] client at {addr} tried to connect, but server is full"
                )
                conn.close()
                return

        logger.info(f"[NEW CONNECTION] {addr} connected")
        current_player = NetworkPlayer(conn=conn, addr=addr)
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
                            player_name = payload_data.get("player_name")
                            if player_name:
                                current_player.player_name = str(player_name)
                            self._handle_player_ready(current_player)
                        case PayloadTypes.ATTACK.value:  # TODO! test this
                            self._handle_attack(payload_data, msg)
                        case PayloadTypes.SHOT_RESULT.value:  # TODO! and test this
                            self._handle_shot_result(payload_data, msg)
                        case _:
                            pass

                except json.JSONDecodeError:
                    logger.error(f"[Server] Weird json from: {addr}")
            except OSError:
                logger.error(f"[Server] Critical error from: {addr}")
                break
        self._handle_player_cleanup(current_player)

    def _handle_attack(self, payload_data: dict, msg: str) -> None:
        receiver: str | None = payload_data.get("receiver")
        sender: str | None = payload_data.get("sender")
        if receiver:
            self._route(msg, receiver)
        logger.info(f"[Server] {sender} attacked {receiver}!")

    def _handle_shot_result(self, payload_data: dict, msg: str) -> None:
        attacker: str | None = payload_data.get("receiver")
        result_raw: str | None = payload_data.get("result")
        if not isinstance(result_raw, str):
            logger.error(f"[Server] Invliad or missing shot result: {result_raw}")

        if result_raw:
            shot_result: ShotResult = ShotResult[result_raw]

        if (
            self.current_turn is not None
            and self.current_turn.player_name == attacker
            and attacker
            and self.current_game_state == GameState.WAR
            and shot_result != ShotResult.AlreadyShot
        ):
            self._route(msg, attacker)
            self._switch_turn()
            logger.info(
                f"[Server] {attacker} attack info was sent back to "
                "him. Changing turn..."
            )

    def _handle_player_cleanup(self, player: NetworkPlayer) -> None:
        with self.players_lock:
            if player in self.players:
                self.players.remove(player)
        player.conn.close()
        logger.info(f"[Server] {player.addr} disconnected and cleaned up")

    def _handle_player_ready(self, current_player: NetworkPlayer) -> None:
        """
        Private method used when every player is ready for the game
        """
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
            self._switch_turn()

    def _switch_turn(self) -> None:
        """
        Private method for switching turn.
        Pretty self-explanatory, if I do say so myself
        """
        with self.players_lock:
            for player in self.players:
                if player != self.current_turn:
                    self.current_turn = player
                    break
