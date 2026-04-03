import logging

from .enums import FieldState, ShipType, ShotResult
from .models import Ship, _Field

logger = logging.getLogger(__name__)


class BaseGrid:
    """
    Base class representing a 2D grid of fields.
    Handles basic grid generation, dimensions, and string representation.
    """

    def __init__(self, row=10, column=10) -> None:
        self.row = row
        self.column = column
        self._grid: list[list[_Field]] = [
            [_Field() for _ in range(self.column)] for _ in range(self.row)
        ]

    def __str__(self) -> str:
        header = "   " + " ".join(str(i) for i in range(self.column))
        rows = [header]

        mapping = {
            FieldState.Empty: "_",
            FieldState.Taken: "s",
            FieldState.Missed: "o",
            FieldState.Hit: "x",
        }

        for i in range(self.row):
            row_chars = [mapping[self._grid[i][j].state] for j in range(self.column)]
            rows.append(f"{i:2} {' '.join(row_chars)}")

        return "\n".join(rows)

    def get_field_state(self, row: int, column: int) -> FieldState:
        """Returns the state of the specified field."""
        return self._grid[row][column].state


class Board(BaseGrid):
    """
    Board class manages the game grid, ship placement and shooting mechanics.
    Acts as the main logical API for the player's own board.
    """

    def __init__(self, row=10, column=10) -> None:
        super().__init__(row, column)
        self._ships: list[Ship] = []

    def get_field_ship(self, row: int, column: int) -> Ship | None:
        return self._grid[row][column].ship

    def place_ship(
        self,
        ship_type: ShipType,
        start_row: int,
        start_column: int,
        horizontal: bool = True,
    ) -> bool:
        """
        Attempts to place a ship on the board following classic Battleship rules.
        Ensures the ship doesn't go out of bounds and doesn't touch other ships.
        Placed ship is heading right way, if horizontal.
        If horizontal is False, then it'll be heading up.

        Args:
            ship_type (ShipType): The type and size of the ship to place.
            start_row (int): The row of the ship's starting point.
            start_column (int): The column of the ship's starting point.
            horizontal (bool, optional): True for horizontal placement,
            False for vertical
        Raises:
            ValueError: If the ship is placed out of the board's boundaries.
            ValueError: If the ship touches or overlaps another already placed ship.

        Returns:
            bool: True if the ship was successfully placed.
        """

        length: int = ship_type.value
        end_row = start_row if horizontal else start_row - length + 1
        end_column = start_column + length - 1 if horizontal else start_column

        if (
            end_row >= self.row
            or end_row < 0
            or end_column >= self.column
            or start_row < 0
            or start_column < 0
        ):
            logger.info(
                f"Player tried putting his ship of length {length} at: "
                f"[start: ({start_row}, {start_column}), end: "
                f"({end_row}, {end_column})]"
            )
            raise ValueError("Row or column is out of bounds!")

        min_row = max(min(start_row, end_row) - 1, 0)
        max_row = min(self.row - 1, max(start_row, end_row) + 1)
        min_column = max(start_column - 1, 0)
        max_column = min(self.column - 1, end_column + 1)

        for i in range(min_row, max_row + 1):
            for j in range(min_column, max_column + 1):
                if self._grid[i][j].state != FieldState.Empty:
                    logger.info(
                        f"Player tried putting his ship at "
                        f"({start_row}, {start_column}), "
                        f"{'horizontally' if horizontal else 'vertically'}, "
                        f"but he cannot do that, because field ({i}, {j}) is already "
                        "taken"
                    )
                    raise ValueError("Field nearby is taken")

        new_ship = Ship(ship_type)

        for i in range(length):
            current_row = start_row if horizontal else start_row - i
            current_column = start_column + i if horizontal else start_column

            self._grid[current_row][current_column].state = FieldState.Taken
            self._grid[current_row][current_column].ship = new_ship

        self._ships.append(new_ship)
        logger.info(
            f"Ship {ship_type.name} was succesfully placed at "
            f"({start_row}, {start_column})"
        )
        return True

    def shoot(self, row: int, column: int) -> ShotResult:
        if row >= self.row or row < 0 or column >= self.column or column < 0:
            logger.info(
                f"Player tried shooting at ({row}, {column}), but it was out of bounds"
            )
            raise ValueError("Row or column is out of bounds!")

        pos = self._grid[row][column]

        if pos.state in [FieldState.Hit, FieldState.Missed]:
            logger.info("Field already shot, no action taken")
            return ShotResult.AlreadyShot

        if pos.state == FieldState.Taken:
            logger.info(f"Ship at position ({row}, {column}) was hit!")
            pos.state = FieldState.Hit

            if pos.ship:
                pos.ship.hit()
                if pos.ship.is_sunk():
                    logger.info(f"Ship {pos.ship.ship_type.name} was sunk!")
                    return ShotResult.Sunk
            return ShotResult.Hit

        logger.info(f"Player tried shooting at ({row}, {column}), but missed!")
        pos.state = FieldState.Missed
        return ShotResult.Miss

    def is_game_over(self) -> bool:
        if not self._ships:
            return False
        return all(ship.is_sunk() for ship in self._ships)


class Radar(BaseGrid):
    """
    Radar class represents the player's view of the opponent's board.
    It tracks where the player has shot and the outcome (Hit/Miss).
    """

    def __init__(self, row=10, column=10) -> None:
        super().__init__(row, column)

    def mark_shot_result(self, row: int, column: int, state: ShotResult) -> None:
        """
        Updates the radar with the result of a shot made by the player.
        """
        if row >= self.row or row < 0 or column >= self.column or column < 0:
            raise ValueError("Row or column is out of bounds!")

        if state == ShotResult.AlreadyShot:
            raise ValueError("This position is already marked shot")

        translation = {
            ShotResult.Miss: FieldState.Missed,
            ShotResult.Hit: FieldState.Hit,
            ShotResult.Sunk: FieldState.Hit,
        }

        self._grid[row][column].state = translation[state]
