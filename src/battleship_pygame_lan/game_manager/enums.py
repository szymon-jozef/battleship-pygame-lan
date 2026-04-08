from enum import Enum, auto


class GuiEvent(Enum):
    """
    Enum representing type of action gui should take.
    For example: make some kind of sound, show some text etc.
    """

    ShotMade = auto()
    ShotHit = auto()
    ShotMissed = auto()
    ShotMarked = auto()
