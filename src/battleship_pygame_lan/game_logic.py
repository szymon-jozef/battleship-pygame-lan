import logging
import uuid
from enum import Enum

logger = logging.getLogger(__name__)


class ShipType(Enum):
    """
    Defines the available ship types and their length. Ship length is also it's health
    """

    FourMaster = 4
    ThreeMaster = 3
    TwoMaster = 2
    OneMaster = 1


class Ship:
    """
    Represents a single ship on the board.
    Every ship has unique ID, type and current health.
    """

    def __init__(self, ship_type: ShipType) -> None:
        self.id = str(uuid.uuid4())
        self.ship_type: ShipType = ship_type
        self.health = self.ship_type.value

    def hit(self) -> None:
        """
        Decrease the ship's health by 1.
        """
        self.health -= 1

    def is_sunk(self) -> bool:
        """
        Checks if the ship is still alive (if we can even call it that lol).

        Returns:
            bool: True if health if 0 or less, False if it's alive!
        """
        return self.health <= 0


class FieldState(Enum):
    """
    Represents the current state of a single field on the board.
    """

    # numbers can be later changed to colors
    Empty = 1
    Taken = 2
    Missed = 3
    Hit = 4


class _Field:
    """
    Class Field represents one specific game field on the board.
    Holds its current state and a reference to a Ship (if it's there)
    """

    def __init__(self) -> None:
        self.state: FieldState = FieldState.Empty
        self.ship: Ship | None = None


class Board:
    """
    Board class manages the game grid, ship placement and shooting mechanics.
    Acts as the main logical API for the game.
    """

    def __init__(self, x=10, y=10) -> None:
        self.x = x
        self.y = y
        self._board: list[list[_Field]] = [
            [_Field() for _ in range(self.x)] for _ in range(self.y)
        ]

    def get_field_state(self, x: int, y: int) -> FieldState:
        """
        Returns:
            FieldState: State of the specified field
        """
        return self._board[x][y].state

    def get_field_ship(self, x: int, y: int) -> Ship:
        """
        Returns:
            Ship: Reference to the ship at specified field
        """
        return self._board[x][y].ship

    def place_ship(
        self, ship_type: ShipType, start_x: int, start_y: int, horizontal: bool = True
    ) -> bool:
        """
        Attempts to place a ship on the board following classic Battleship rules.
        Ensures the ship doesn't go out of bounds and doesn't touch other ships.

        Args:
            ship_type (ShipType): The type and size of the ship to place.
            start_x (int): The X coordinate of the ship's starting point.
            start_y (int): The Y coordinate of the ship's starting point.
            horizontal (bool, optional): True for horizontal placement,
            False for vertical
        Raises:
            ValueError: If the ship is placed out of the board's boundaries.
            ValueError: If the ship touches or overlaps another already placed ship.

        Returns:
            bool: True if the ship was successfully placed.
        """
        length: int = ship_type.value
        end_x = start_x + length - 1 if horizontal else start_x
        end_y = start_y + length - 1 if not horizontal else start_y

        if end_x >= self.x or end_y >= self.y or start_x < 0 or start_y < 0:
            logger.info(
                f"Player tried putting his ship of length {length} at: "
                f"[start: ({start_x}, {start_y}), end: ({end_x}, {end_y})]"
            )
            raise ValueError("X or Y is out of bounds!")

        min_x = max(start_x - 1, 0)
        max_x = min(self.x - 1, end_x + 1)
        min_y = max(start_y - 1, 0)
        max_y = min(self.y - 1, end_y + 1)

        for i in range(min_x, max_x + 1):
            for j in range(min_y, max_y + 1):
                if self._board[i][j].state != FieldState.Empty:
                    logger.info(
                        f"Player tried putting his ship at ({start_x}, {start_y}), "
                        f"{'horizontally' if horizontal else 'vertically'}, "
                        f"but he cannot do that, because field ({i}, {j}) is already "
                        "taken"
                    )
                    raise ValueError("Field nearby is taken")

        new_ship = Ship(ship_type)

        for i in range(length):
            current_x = start_x + i if horizontal else start_x
            current_y = start_y + i if not horizontal else start_y

            self._board[current_x][current_y].state = FieldState.Taken
            self._board[current_x][current_y].ship = new_ship

        logger.info(
            f"Ship {ship_type.name} was succesfully placed at ({start_x}, {start_y})"
        )

    def shot(self, x: int, y: int) -> bool:
        """
        Take a shoot at specific field.

        Raises:
            ValueError: If the coordinates are out of bounds
            ValueError: If the field was already shot

        Returns:
            bool: True if something was hit and False if it was a miss.
        """
        if x >= self.x or x < 0 or y >= self.y or y < 0:
            logger.info(
                f"Player tried shooting at ({x}, {y}), but it was out of bounds"
            )
            raise ValueError("X or Y is out of bounds!")

        pos = self._board[x][y]

        if pos.state in [FieldState.Hit, FieldState.Missed]:
            logger.info(
                f"Player tried shooting at ({x}, {y}), but it was already shot, so no "
                "action was taken"
            )
            raise ValueError("This place was already shot!")

        if pos.state == FieldState.Taken:
            logger.info(f"Ship at position ({x}, {y}) was hit!")
            pos.state = FieldState.Hit

            if pos.ship:
                pos.ship.hit()
                if pos.ship.is_sunk():
                    logger.info(
                        f"Ship {pos.ship.ship_type.name} at ({x}, {y}) was sunk! "
                    )

            return True

        logger.info(f"Player tried shooting at ({x}, {y}), but missed!")
        pos.state = FieldState.Missed
        return False
