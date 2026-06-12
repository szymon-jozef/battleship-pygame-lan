import json
import socket
from logging import getLogger
from queue import Empty, Queue

from battleship_pygame_lan.logic import (
    AlreadyShotError,
    OutOfBoundsError,
    Player,
    ShipType,
    ShotResult,
)
from battleship_pygame_lan.network import GameState, NetworkClient

from .enums import GuiEvent

logger = getLogger(__name__)


class GameManager:
    """
    Manager class to handle Player on the logic layer and network client
    on the network layer.
    """

    def __init__(
        self,
        player_name: str,
        server_ip: str = socket.gethostbyname(socket.gethostname()),
    ) -> None:
        self.player: Player = Player(player_name)
        self.network_client: NetworkClient = NetworkClient(player_name, server_ip)
        self.gui_events_queue: Queue[GuiEvent] = Queue()

    def connect(self) -> None:
        """
        Connect to the server. Must be run before game
        """
        self.network_client.connect()

    @property
    def game_state(self) -> GameState | None:
        return self.network_client.current_game_state

    def place_ship(
        self, ship_type: ShipType, row: int, column: int, horizontal: bool = True
    ) -> bool:
        if self.network_client.current_game_state == GameState.SHIP_PLACEMENT:
            return self.player.place_ship(ship_type, row, column, horizontal)
        else:
            raise RuntimeError("Tried to place a ship, when it's not the time for this")

    def shoot(self, row: int, column: int) -> None:
        self.network_client.send_attack_info(row, column)

    def handle_response(self) -> None:
        """
        Handles responses from the game sever. Should be run in some kind of loop.
        For example: pygame game loop
        """
        while not self.network_client.message_queue.empty():
            try:
                message = self.network_client.message_queue.get_nowait()
            except Empty:
                break

            message_type_str = message.get("type")
            if not message_type_str:
                self.network_client.message_queue.task_done()
                continue

            # Obsługa zmiany tury nadchodzącej z serwera
            if message_type_str == "change_turn":
                turn_user = message.get("turn")
                self.network_client.is_my_turn = turn_user == self.player.name
                logger.info(
                    f"[GameManager] Zmiana tury! Strzela: {turn_user} (Moja tura: {self.network_client.is_my_turn})"
                )
                self.network_client.message_queue.task_done()
                continue

            elif message_type_str == "game_state":
                state_val = message.get("state")
                if state_val:
                    try:
                        self.network_client.current_game_state = GameState[state_val]
                    except KeyError:
                        pass
                self.network_client.message_queue.task_done()
                continue

            # Obsługa akcji bojowych
            if message_type_str == "attack":
                self._handle_shot(message)
            elif message_type_str == "shot_result":
                self._handle_shot_result(message)
            elif message_type_str in ("game_end", "end_game"):
                self._handle_game_end(message)

            self.network_client.message_queue.task_done()

    def _get_cords(self, message: dict) -> tuple[int, int] | None:
        row_content = message.get("row")
        column_content = (
            message.get("column")
            if message.get("column") is not None
            else message.get("col")
        )

        if row_content is not None and column_content is not None:
            return int(row_content), int(column_content)
        return None

    def _handle_shot(self, message: dict) -> None:
        """Wywoływane, gdy to wróg strzela we MNIE (lewa plansza floty)."""
        coords = self._get_cords(message)
        if coords is None:
            return
        row, column = coords

        attacker = message.get("sender") or message.get("attacker")

        try:
            # receive_shot automatycznie aktualizuje naszą lewą planszę (board)
            shot_result: ShotResult = self.player.receive_shot(row, column)
        except (OutOfBoundsError, AlreadyShotError):
            return

        # Budujemy jawny pakiet odpowiedzi dla serwera, zachowując strukturę kluczy
        result_payload = {
            "type": "shot_result",
            "attacker": attacker,
            "receiver": self.player.name,
            "row": row,
            "column": column,
            "result": shot_result.name,
        }
        self.network_client.send_to_socket(
            self.network_client.client, json.dumps(result_payload)
        )

        if self.player.is_dead:
            logger.info("[GameManager] Player is dead :(")
            self.network_client.end()
            self.gui_events_queue.put(GuiEvent.GameLost)

    def _handle_shot_result(self, message: dict) -> None:
        """Wywoływane po rozgłoszeniu wyniku strzału przez serwer."""
        attacker = message.get("attacker")

        # ODKRYWANIE RADARU: Tylko jeśli to MY oddaliśmy ten strzał!
        if attacker != self.player.name:
            return

        coords = self._get_cords(message)
        if coords is None:
            return
        row, column = coords

        try:
            shot_result: ShotResult = ShotResult[str(message.get("result"))]
        except KeyError:
            return

        try:
            # Zapisujemy trafienie/pudło wyłącznie na prawym ekranie (radar) strzelającego
            self.player.mark_shot(row, column, shot_result)
            logger.info(
                f"[GameManager] Zaktualizowano radar na pozycji {row, column} jako {shot_result.name}"
            )
        except (OutOfBoundsError, AlreadyShotError):
            return

        if shot_result == ShotResult.Hit:
            self.gui_events_queue.put(GuiEvent.ShotHit)
        elif shot_result == ShotResult.Miss:
            self.gui_events_queue.put(GuiEvent.ShotMissed)

    def _handle_game_end(self, message: dict) -> None:
        loser: str = str(message.get("loser"))
        if loser != self.player.name:
            self.gui_events_queue.put(GuiEvent.GameWon)
        self.network_client.disconnect()
