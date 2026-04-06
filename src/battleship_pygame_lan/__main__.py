import logging

from battleship_pygame_lan.logic import Player, ShipType
from battleship_pygame_lan.network import NetworkServer


def main() -> None:
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename="battleships.log", level=logging.INFO)
    logger.info("Started")

    # dirty code showcase

    # network
    server = NetworkServer()
    server.start()

    # create player
    player1 = Player("Morbius")
    player1.place_ship(ShipType.ThreeMaster, 1, 1)
    player1.place_ship(ShipType.FourMaster, 5, 5, False)

    # do stuff with his board
    print(f"{player1.name} board:")
    print(player1.board)
    print(f"{player1.name} radar:")
    print(player1.radar)
    print(f"{player1.name} gets shot, but it was a miss!")
    player1.receive_shot(2, 2)
    print(player1.board)
    print(f"{player1.name} gets shot!")
    player1.receive_shot(1, 1)
    print(player1.board)
    print(f"{player1.name} gets sink!")
    player1.receive_shot(1, 2)
    player1.receive_shot(1, 3)
    print(player1.board)

    logger.info("Finished")


if __name__ == "__main__":
    main()
