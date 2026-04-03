import logging

from .boards import Board, Radar
from .enums import ShipType, ShotResult

logger = logging.getLogger(__name__)


class Player:
    def __init__(self, name: str) -> None:
        self.name = name
        self.board: Board = Board()
        self.radar: Radar = Radar()
        self.available_ships: dict[ShipType, int] = {
            ShipType.FourMaster: 1,
            ShipType.ThreeMaster: 2,
            ShipType.TwoMaster: 3,
            ShipType.OneMaster: 4,
        }

    def reset(self) -> None:
        # probably could be done more efficiently in the future
        self.board: Board = Board()
        self.radar: Radar = Radar()
        self.available_ships: dict[ShipType, int] = {
            ShipType.FourMaster: 1,
            ShipType.ThreeMaster: 2,
            ShipType.TwoMaster: 3,
            ShipType.OneMaster: 4,
        }

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

        Returns:
            bool: True if the ship was successfully placed and removed from inventory.
        """

        if self.available_ships[ship_type] <= 0:
            logger.info(
                f"Player tried placing ship of type {ship_type.name}, but he doesn't "
                "have any left"
            )
            raise ValueError("Player doesn't have enough ships of chosen type")
        self.board.place_ship(ship_type, row, column, horizontal)
        self.available_ships[ship_type] -= 1
        return True

    def take_shot(self, row: int, column: int, shot_result: ShotResult) -> None:
        """Mark your shot on the radar"""
        self.radar.mark_shot_result(row, column, shot_result)

    def receive_shot(self, row: int, column: int) -> ShotResult:
        return self.board.shoot(row, column)

    def is_every_ship_placed(self) -> bool:
        """Returns: True if player doesn't have any more ships left in his bay"""
        return (
            sum(self.available_ships.values()) <= 0
        )  # if there is more than 0 ships it will return false

    def is_dead(self) -> bool:
        """Returns: True if player doesn't has any ships left on the battlefield"""
        return self.board.is_game_over()
