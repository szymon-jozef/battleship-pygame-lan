import socket
from logging import getLogger
from queue import Empty, Queue

from battleship_pygame_lan.logic import (
    AlreadyShotError,
    FieldState,
    OutOfBoundsError,
    Player,
    ShipType,
    ShotResult,
)
from battleship_pygame_lan.network import GameState, NetworkClient, PayloadTypes

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
        self.network_client.connect()

    @property
    def get_game_state(self) -> GameState | None:
        return self.network_client.current_game_state

    def place_ship(
        self, ship_type: ShipType, row: int, column: int, horizontal: bool = True
    ) -> bool:
        """
        Attempts to place a ship on the player's board.
        First checks if the player has the requested ship type in their inventory.
        If available, delegates the placement to the Board class.

        Args:
            ship_type (ShipType): The type and size of the ship to place.
            row (int): The row of the ship's starting point.
            column (int): The column of the ship's starting point.
            horizontal (bool, optional): True for horizontal placement.
            False for vertical (heading up).

        Raises:
            ValueError: If the player doesn't have enough ships of chosen type.
            ValueError: If the ship is placed out of the board's boundaries (from Board)
            ValueError: If the ship touches or overlaps another placed ship (from Board)
            RuntimeError: If called when it's not GameState.SHIP_PLACEMENT

        Returns:
            bool: True if the ship was successfully placed and removed from inventory.
        """
        if self.network_client.current_game_state == GameState.SHIP_PLACEMENT:
            return self.player.place_ship(ship_type, row, column, horizontal=True)
        else:
            raise RuntimeError("Tried to place a ship, when it's not the time for this")

    def shoot(self, row: int, column: int) -> None:
        self.network_client.send_attack_info(row, column)

    def handle_response(self) -> None:
        while not self.network_client.message_queue.empty():
            try:
                message = self.network_client.message_queue.get_nowait()
            except Empty:
                logger.info(
                    "[GameClient] Tried getting message from the queue, but it was "
                    "empty"
                )
                break

            message_type: PayloadTypes = PayloadTypes(message.get("type"))

            match message_type:
                case PayloadTypes.ATTACK.value:
                    self._handle_shot(message)
                case PayloadTypes.SHOT_RESULT.value:
                    self._handle_shot_result(message)
                case _:  # we pass for now
                    pass

    def _handle_shot(self, message: dict) -> None:
        row_content = message.get("row")
        column_content = message.get("column")
        if row_content is not None and column_content is not None:
            row: int = int(row_content)
            column: int = int(column_content)
        else:
            logger.error("[GameClient] row or column is empty in handle_shot()")
            # if message is weird then we just ignore it
            return

        field_state: FieldState = self.player.get_own_board_state(row, column)
        try:
            self.player.board.shoot(row, column)
        except OutOfBoundsError:
            logger.info("[GameClient] Enemy tried to shot out of bounds!")
            self.network_client.send_shot_result(
                row, column, ShotResult.AlreadyShot
            )  # we don't have specific value for that
            # TODO we probably should do something about that
            return
        except AlreadyShotError:
            logger.info(
                "[Gameclient] Enemy tried to shot at place that was already shot!"
            )
            self.network_client.send_shot_result(row, column, ShotResult.AlreadyShot)
            return

        if field_state == FieldState.Taken:
            self.network_client.send_shot_result(row, column, ShotResult.Hit)
        else:
            self.network_client.send_shot_result(row, column, ShotResult.Miss)

    def _handle_shot_result(self, message: dict) -> None:
        row_content = message.get("row")
        column_content = message.get("column")
        if row_content is not None and column_content is not None:
            row: int = int(row_content)
            column: int = int(column_content)
        else:
            logger.error("[GameClient] row or column is empty in handle_shot()")
            # if message is weird then we just ignore it
            return

        try:
            shot_result: ShotResult = ShotResult[str(message.get("result"))]
        except KeyError:
            logger.info("[GameClient] weird key in shot_result in handle_shot_result()")
            return
        try:
            self.player.mark_shot(row, column, shot_result)
        except OutOfBoundsError:
            logger.info("[GameClient] Enemy reported the shot was out of bounds!")
            return
        except AlreadyShotError:
            logger.info(
                "[GameClient] Enemy reported that the player already "
                f"made shot at {row, column}"
            )
            return

        match shot_result:
            case ShotResult.Hit:
                self.gui_events_queue.put(GuiEvent.ShotHit)
            case ShotResult.Miss:
                self.gui_events_queue.put(GuiEvent.ShotMissed)
            case _:
                pass
