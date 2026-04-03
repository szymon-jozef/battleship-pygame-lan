import logging
import uuid
from enum import Enum

logger = logging.getLogger(__name__)


class ShipType(Enum):
    FourMaster = 4
    ThreeMaster = 3
    TwoMaster = 2
    OneMaster = 1


class Ship:
    def __init__(self, ship_type: ShipType) -> None:
        self.id = str(uuid.uuid4())
        self.ship_type: ShipType = ship_type
        self.health = self.ship_type.value

    def hit(self) -> None:
        self.health -= 1

    def is_sunk(self) -> bool:
        return self.health <= 0


class FieldState(Enum):
    # numbers can be later changed to colors
    Empty = 1
    Taken = 2
    Missed = 3
    Hit = 4


class Field:
    """
    Class Field represents one specific game field.
    """

    def __init__(self) -> None:
        self.state: FieldState = FieldState.Empty
        self.ship: Ship | None = None


class Board:
    """
    Board class. It handles most of the game logic.
    """

    def __init__(self, x=10, y=10) -> None:
        self.x = x
        self.y = y
        self.board: list[list[Field]] = [
            [Field() for _ in range(self.x)] for _ in range(self.y)
        ]

    def place_ship(
        self, ship_type: ShipType, start_x: int, start_y: int, horizontal: bool
    ):
        """
        Place a ship at specified place.
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
                if self.board[i][j].state != FieldState.Empty:
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

            self.board[current_x][current_y].state = FieldState.Taken
            self.board[current_x][current_y].ship = new_ship

        logger.info(
            f"Ship {ship_type.name} was succesfully placed at ({start_x}, {start_y})"
        )

    def shot(self, x: int, y: int) -> bool:
        """
        Take a shoot at specific field. Return True if something was hit and False if it
        was a miss.
        """
        if x >= self.x or x < 0 or y >= self.y or y < 0:
            logger.info(
                f"Player tried shooting at ({x}, {y}), but it was out of bounds"
            )
            raise ValueError("X or Y is out of bounds!")

        pos = self.board[x][y]

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
