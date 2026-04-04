import logging

from .boards import Board, Radar
from .enums import FieldState, ShipType, ShotResult

logger = logging.getLogger(__name__)


class Player:
    """
    Player class is the main entry point into the games logic.
    It provides methods to interact with the whole game.

    Attributes:
        name (str): Name of the player
        board (Board):  Players own board
        radar (Radar): Players enemy board
        available_ships (dict[ShipType, int]): Inventory of ships remaining to be placed
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.reset()

    def reset(self) -> None:
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
                f"Player {self.name} tried placing ship of type {ship_type.name}, but "
                "he doesn't have any left"
            )
            raise ValueError("Player doesn't have enough ships of chosen type")
        self.board.place_ship(ship_type, row, column, horizontal)
        self.available_ships[ship_type] -= 1
        return True

    def mark_shot(self, row: int, column: int, shot_result: ShotResult) -> None:
        """
        Mark your shot on the radar

        Important:
            This method only marks the field on the radar with shot_result value.
            It doesn't validate anything.
            Chosen row and column should be validated for repeated shots, before
            shooting calling it this method
        """
        logger.info(
            f"Player {self.name} marked ({row}, {column}) as {shot_result} on his radar"
        )
        self.radar.mark_shot_result(row, column, shot_result)

    def receive_shot(self, row: int, column: int) -> ShotResult:
        logger.info(f"Player {self.name} received a shot at ({row}, {column})")
        return self.board.shoot(row, column)

    @property
    def is_every_ship_placed(self) -> bool:
        """Returns: True if player doesn't have any more ships left in his bay"""
        return (
            sum(self.available_ships.values()) <= 0
        )  # if there is more than 0 ships it will return false

    @property
    def is_dead(self) -> bool:
        """Returns: True if player doesn't have any ships left on the battlefield"""
        return self.board.is_game_over

    def get_own_board_state(self, row: int, column: int) -> FieldState:
        return self.board.get_field_state(row, column)

    def get_radar_state(self, row: int, column: int) -> FieldState:
        return self.radar.get_field_state(row, column)
