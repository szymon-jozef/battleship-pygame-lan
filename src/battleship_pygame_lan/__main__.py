import logging

from battleship_pygame_lan.logic import Board, ShipType


def main() -> None:
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename="battleships.log", level=logging.INFO)
    logger.info("Started")

    # dirty code test
    board = Board()
    board.place_ship(ShipType.OneMaster, 1, 1)
    print(str(board))
    board.shoot(1, 1)
    print(str(board))
    print(f"Is game over? {board.is_game_over()}")

    logger.info("Finished")


if __name__ == "__main__":
    main()
