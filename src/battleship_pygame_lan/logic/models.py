from uuid import uuid4

from .enums import FieldState, ShipType


class Ship:
    """
    Represents a single ship on the board.
    Every ship has unique ID, type and current health.
    """

    def __init__(self, ship_type: ShipType) -> None:
        self.id = str(uuid4())
        self.ship_type: ShipType = ship_type
        self.health = self.ship_type.value

    def hit(self) -> None:
        """
        Decrease the ship's health by 1.
        """
        self.health -= 1

    @property
    def is_sunk(self) -> bool:
        """
        Checks if the ship is still alive (if we can even call it that lol).

        Returns:
            bool: True if health if 0 or less, False if it's alive!
        """
        return self.health <= 0


class _Field:
    """
    Class Field represents one specific game field on the board.
    Holds its current state and a reference to a Ship (if it's there)
    """

    def __init__(self) -> None:
        self.state: FieldState = FieldState.Empty
        self.ship: Ship | None = None
