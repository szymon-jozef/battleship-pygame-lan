import pytest

from battleship_pygame_lan.logic import Board, FieldState, Ship, ShipType, ShotResult


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


def test_board_str_rows():
    board = Board(3, 3)
    board.place_ship(ShipType.TwoMaster, 0, 0, horizontal=True)  # (0,0) and (1,0)

    lines = str(board).strip().split("\n")

    #  "   0 1 2"
    #  " 0 s _ _"
    #  " 1 s _ _"

    assert "s" in lines[1]
    assert "s" in lines[2]
    assert "s" not in lines[3]


def test_shot_miss():
    board = Board()
    result = board.shoot(0, 0)

    assert result == ShotResult.Miss
    assert board.get_field_state(0, 0) == FieldState.Missed


def test_shot_taken():
    board = Board()
    board.shoot(0, 0)

    assert board.shoot(0, 0) == ShotResult.AlreadyShot


def test_placing_ship_success():
    board = Board()
    board.place_ship(ShipType.OneMaster, 0, 0)
    assert board.get_field_state(0, 0) == FieldState.Taken
    assert board.get_field_ship(0, 0).health == 1

    board.place_ship(ShipType.TwoMaster, 3, 3)
    assert board.get_field_state(3, 3) == FieldState.Taken
    assert board.get_field_state(4, 3) == FieldState.Taken
    assert board.get_field_ship(3, 3).health == 2
    ship_1 = board.get_field_ship(3, 3)
    ship_2 = board.get_field_ship(4, 3)
    assert ship_1 is ship_2  # check if this is the same ship
    assert ship_1.id == ship_2.id  # check if id matches


@pytest.mark.parametrize(
    "x, y",
    [
        (123, 0),
        (-123, 0),
        (0, 123),
        (0, -123),
        (123, -123),
    ],
)
def test_placing_ship_out_of_bounds(x, y):
    board = Board()
    with pytest.raises(ValueError, match="X or Y is out of bounds!"):
        board.place_ship(ShipType.OneMaster, x, y)


def test_placing_ship_collision():
    board = Board()
    board.place_ship(ShipType.OneMaster, 1, 1)

    with pytest.raises(ValueError, match="Field nearby is taken"):
        board.place_ship(ShipType.OneMaster, 1, 1)

    with pytest.raises(ValueError, match="Field nearby is taken"):
        board.place_ship(ShipType.OneMaster, 2, 1)

    with pytest.raises(ValueError, match="Field nearby is taken"):
        board.place_ship(ShipType.OneMaster, 1, 2)


def test_game_over():
    board = Board()
    board.place_ship(ShipType.OneMaster, 1, 1)
    assert not board.is_game_over()
    board.shoot(1, 1)
    assert board.is_game_over()


def test_game():
    board = Board()

    board.place_ship(ShipType.TwoMaster, 1, 1, True)
    placed_ship = board.get_field_ship(1, 1)

    result_1 = board.shoot(1, 1)
    assert result_1 == ShotResult.Hit
    assert board.get_field_state(1, 1) == FieldState.Hit
    assert placed_ship.health == 1
    assert not placed_ship.is_sunk()

    assert not board.is_game_over()

    result_2 = board.shoot(2, 1)
    assert result_2 == ShotResult.Sunk
    assert board.get_field_state(2, 1) == FieldState.Hit
    assert placed_ship.health == 0
    assert placed_ship.is_sunk() is True

    assert board.is_game_over()
