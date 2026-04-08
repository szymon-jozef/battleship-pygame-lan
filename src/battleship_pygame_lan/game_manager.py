import socket

from battleship_pygame_lan.logic import Player
from battleship_pygame_lan.network import NetworkClient


class GameManager:
    """
    Manager class to handle Player on the logic layer and network client
    on the network layer.
    """

    def __init__(
        self,
        player_name: str,
        server_ip: str = socket.gethostbyname(socket.gethostname()),
    ) -> None:
        self.player: Player = Player(player_name)
        self.network_client: NetworkClient = NetworkClient(player_name, server_ip)
        self.network_client.connect()

    def shot(self, row: int, column: int) -> None:
        self.network_client.send_attack_info(row, column)
        self.network_client.message_queue.get()
