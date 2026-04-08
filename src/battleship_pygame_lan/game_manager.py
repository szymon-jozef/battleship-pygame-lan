import socket
from enum import Enum, auto
from logging import getLogger
from queue import Empty, Queue

from battleship_pygame_lan.logic import (
    AlreadyShotError,
    OutOfBoundsError,
    Player,
    ShotResult,
)
from battleship_pygame_lan.network import NetworkClient, PayloadTypes

logger = getLogger(__name__)


class GuiEvent(Enum):
    """
    Enum representing type of action gui should take.
    For example: make some kind of sound, show some text etc.
    """

    ShotMade = auto()
    ShotHit = auto()
    ShotMissed = auto()
    ShotMarked = auto()


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
        self.network_client.connect()
        self.gui_events_queue: Queue[GuiEvent] = Queue()

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
                case PayloadTypes.SHOT_RESULT:
                    row: int = int(message.get("row"))
                    column: int = int(message.get("column"))
                    shot_result: ShotResult = ShotResult(message.get("result"))
                    self._handle_shot_result(shot_result)
                    try:
                        self.player.mark_shot(row, column, shot_result)
                    except OutOfBoundsError:
                        logger.info(
                            "[GameClient] Enemy reported the shot was out of bounds!"
                        )
                    except AlreadyShotError:
                        logger.info(
                            "[GameClient] Enemy reported that the player already "
                            f"made shot at {row, column}"
                        )
                case _:  # we pass for now
                    pass

    def _handle_shot_result(self, shot_result: ShotResult) -> None:
        match shot_result:
            case ShotResult.Hit:
                self.gui_events_queue.put(GuiEvent.ShotHit)
            case ShotResult.Miss:
                self.gui_events_queue.put(GuiEvent.ShotMissed)
            case _:
                pass
