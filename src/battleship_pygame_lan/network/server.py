import json
import logging
import socket
import threading
from contextlib import suppress

from battleship_pygame_lan.logic import ShotResult

from .models import GameState, NetworkPlayer, PayloadTypes
from .network_core import NetworkCore
from .payloads import (
    build_end_game_payload,
    build_game_state_payload,
    build_players_payload,
    build_turn_payload,
)

logger = logging.getLogger(__name__)


class NetworkServer(NetworkCore):
    def __init__(self, server_ip: str = "0.0.0.0") -> None:
        super().__init__(ip_address=server_ip)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.MAX_PLAYERS: int = 2
        self.players_lock = threading.Lock()
        self.players: list[NetworkPlayer] = []
        self.current_game_state: GameState | None = None
        self.current_turn: NetworkPlayer | None = None
        self.is_running: bool = False

    def start(self) -> None:
        """
        Public method to start the server in blocking way, so preferably must be run in
        separate thread.
        """
        logger.info("[STARTING] Server is starting")
        logger.info(f"[LISTENING] Server is listening on {self.HOST}")
        self.server.bind(self.ADDR)
        self.server.listen()
        self.is_running = True
        self.current_game_state = GameState.LOBBY

        while self.is_running:
            with suppress(OSError):
                conn, addr = self.server.accept()
                player = NetworkPlayer(conn=conn, addr=addr)
                with self.players_lock:
                    self.players.append(player)

                thread = threading.Thread(
                    target=self._handle_client, args=(player,), daemon=True
                )
                thread.start()

    def stop(self) -> None:
        self.is_running = False
        with self.players_lock:
            for player in self.players:
                player.conn.close()
        self.server.close()

    def _handle_client(self, player: NetworkPlayer) -> None:
        logger.info(f"[NEW CONNECTION] {player.addr} connected")
        logger.info(f"[ACTIVE CONNECTIONS] {threading.active_count() - 2}")

        connected: bool = True
        while connected and self.is_running:
            try:
                # 1. Read header
                header_msg = player.conn.recv(self.HEADER).decode(self.FORMAT)
                if not header_msg:
                    break

                msg_length = int(header_msg.strip())

                # 2. Read actual payload
                msg = player.conn.recv(msg_length).decode(self.FORMAT)
                payload_data: dict = json.loads(msg)
                payload_type = payload_data.get("type")

                print(f"[{player.addr}] {msg}")

                match payload_type:
                    case PayloadTypes.CONNECTION_STATUS.value:
                        player.player_name = payload_data.get("player_name")
                        self._broadcast_players()
                        self._change_game_state(self.current_game_state)
                    case PayloadTypes.READY.value:
                        player.ready_status = payload_data.get("status")
                        logger.info(
                            f"[Server] Player {player.player_name} has placed all his ships! "
                            f"({sum(1 for p in self.players if p.ready_status)}/{self.MAX_PLAYERS}) "
                            f"out of {len(self.players)} placed"
                        )
                        if (
                            sum(1 for p in self.players if p.ready_status)
                            == self.MAX_PLAYERS
                        ):
                            self._start_war()
                        else:
                            logger.info(
                                f"[Server] Waiting for the rest of the players ({sum(1 for p in self.players if p.ready_status)}/{self.MAX_PLAYERS})"
                            )
                    case PayloadTypes.ATTACK.value:
                        self._handle_attack(payload_data, msg)
                    case PayloadTypes.SHOT_RESULT.value:
                        self._handle_shot_result(payload_data, msg)
                    case PayloadTypes.LOST.value:
                        self._end_game(player.player_name)

            except (ConnectionResetError, ValueError, OSError):
                break

        with self.players_lock:
            if player in self.players:
                self.players.remove(player)
        player.conn.close()
        logger.info(f"[DISCONNECT] {player.addr} disconnected")
        self._broadcast_players()

    def _handle_attack(self, payload_data: dict, msg: str) -> None:
        receiver_name = payload_data.get("receiver")
        with self.players_lock:
            receiver = next(
                (p for p in self.players if p.player_name == receiver_name), None
            )
        if receiver:
            logger.info(
                f"[Server] {payload_data.get('sender')} attacked {receiver_name}!"
            )
            self.send_to_socket(receiver.conn, msg)

    def _handle_shot_result(self, payload_data: dict, msg: str) -> None:
        attacker = payload_data.get("attacker")
        result_raw = payload_data.get("result")

        if not result_raw or not attacker:
            logger.error(
                f"[Server] Brak kluczowych danych strzału. Napastnik: {attacker}, Wynik: {result_raw}"
            )
            return

        try:
            shot_result = ShotResult[result_raw]
        except KeyError:
            return

        # 1. NAJPIERW ROZSYŁAMY WYNIK STRZAŁU (Gracze nanoszą zmiany na ekrany)
        self._broadcast(msg)

        # 2. DOPIERO POTEM OBSŁUGUJEMY ZMIANĘ TURY
        if self.current_turn and self.current_turn.player_name == attacker:
            if shot_result == ShotResult.Miss:
                logger.info(f"[Server] Gracz {attacker} SPUDŁOWAŁ. Zmiana tury...")
                self._switch_turn()
            else:
                logger.info(f"[Server] Gracz {attacker} TRAFIŁ. Zachowuje turę.")
                payload = build_turn_payload(attacker)
                self._broadcast(payload)

    def _switch_turn(self) -> None:
        with self.players_lock:
            if not self.players:
                return
            if self.current_turn is None:
                self.current_turn = self.players[0]
            else:
                current_index = self.players.index(self.current_turn)
                next_index = (current_index + 1) % len(self.players)
                self.current_turn = self.players[next_index]

        logger.info(
            f"[SERVER] War started. First turn strictly assigned to Host: {self.current_turn.player_name}"
        )
        payload = build_turn_payload(self.current_turn.player_name)
        self._broadcast(payload)

    def _broadcast(self, msg: str) -> None:
        with self.players_lock:
            for player in self.players:
                self.send_to_socket(player.conn, msg)

    def _end_game(self, loser: str) -> None:
        logger.info("[Server] The game has finished!")
        payload = build_end_game_payload(loser)
        self._broadcast(payload)
        self.current_game_state = GameState.FINISH
        self._change_game_state(self.current_game_state)

    def _start_war(self) -> None:
        with self.players_lock:
            ready_players: int = sum(
                1 for player in self.players if player.ready_status
            )

        if ready_players != self.MAX_PLAYERS:
            raise RuntimeError(
                "Critical: tried to start a war when not every side is ready!"
            )

        self._switch_turn()
        self.current_game_state = GameState.WAR
        self._change_game_state(self.current_game_state)

    def _change_game_state(self, game_state: GameState) -> None:
        logger.info(f"[Server] We're changing the game state to {game_state.value}")
        payload = build_game_state_payload(game_state)
        self._broadcast(payload)

    def _broadcast_players(self) -> None:
        with self.players_lock:
            payload = build_players_payload(
                [p.player_name for p in self.players if p.player_name]
            )
        self._broadcast(payload)
