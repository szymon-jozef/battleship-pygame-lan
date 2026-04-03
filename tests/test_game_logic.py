import pytest

from src.battleship_pygame_lan.game_logic import Board, FieldState, Ship, ShipType


def test_ship_initialization():
    ship = Ship(ShipType.ThreeMaster)
    assert ship.health == 3
    assert not ship.is_sunk()


def test_ship_hit_sink():
    ship = Ship(ShipType.OneMaster)
    ship.hit()

    assert ship.health == 0
    assert ship.is_sunk() is True


def test_board_initialization():
    board = Board(10, 10)

    with pytest.raises(ValueError, match="out of bounds"):
        board.shoot(10, 10)

    with pytest.raises(ValueError, match="out of bounds"):
        board.shoot(-1, 5)


def test_shoot_miss():
    board = Board()
    result = board.shoot(0, 0)

    assert result is False
    assert board.board[0][0].state == FieldState.Missed


def test_shoot_taken():
    board = Board()
    board.shoot(0, 0)

    with pytest.raises(ValueError, match="This place was already shoot!"):
        board.shoot(0, 0)


def test_game():
    board = Board()
    ship = Ship(ShipType.TwoMaster)

    # later it should be done in one Board method
    board.board[1][1].state = FieldState.Taken
    board.board[1][1].ship = ship

    board.board[1][2].state = FieldState.Taken
    board.board[1][2].ship = ship

    result_1 = board.shoot(1, 1)
    assert result_1 is True
    assert board.board[1][1].state == FieldState.Hit
    assert ship.health == 1
    assert not ship.is_sunk()

    result_2 = board.shoot(1, 2)
    assert result_2 is True
    assert board.board[1][2].state == FieldState.Hit
    assert ship.health == 0
    assert ship.is_sunk() is True
