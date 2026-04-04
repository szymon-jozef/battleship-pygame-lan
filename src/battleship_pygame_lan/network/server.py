import json
import logging
import socket
import threading

from .payloads import PayloadTypes, build_start_payload

logger = logging.getLogger(__name__)


class NetworkServer:
    def __init__(self) -> None:
        self.SERVER = socket.gethostbyname(socket.gethostname())
        self.HEADER = 64
        self.PORT = 6969
        self.FORMAT = "utf-8"
        self.DISCONNECT_MSG = "!DISCONNET"
        self.ADDR = (self.SERVER, self.PORT)

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients: list[socket.socket] = []
        self.ready_players: set[str] = set()

    def handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        logger.info(f"[NEW CONNECTION] {addr} connected")
        self.clients.append(conn)

        connected: bool = True
        while connected:
            msg_length_str: str = conn.recv(self.HEADER).decode(self.FORMAT).strip()
            if msg_length_str:
                msg_length: int = int(msg_length_str)
                msg: str = conn.recv(msg_length).decode(self.FORMAT)

                if msg == self.DISCONNECT_MSG:
                    connected = False
                    continue

                logger.info(f"[{addr}] {msg}")

                try:
                    payload_data = json.loads(msg)
                    payload_type = payload_data.get("type")

                    # TODO! handle other payload types
                    match payload_type:
                        case (
                            PayloadTypes.READY.value
                        ):  # TODO! test this behaviour in tests
                            player_name = payload_data.get("player_name")
                            self.ready_players.add(player_name)

                            logger.info(
                                f"[Server] Player {player_name} is ready! "
                                f"({len(self.ready_players)}/2)"
                            )

                            if len(self.ready_players) == 2:
                                self.start_game()
                        case _:
                            pass
                except json.JSONDecodeError:
                    logger.error(f"[Server] Weird json from: {addr}")
        if conn in self.clients:
            self.clients.remove(conn)

        conn.close()

    def start(self) -> None:
        logger.info("[STARTING] Server is starting")
        logger.info(f"[LISTENING] Server is listening on {self.SERVER}")

        self.server.bind(self.ADDR)
        self.server.listen()
        while True:
            conn, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()
            logger.info(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

    def broadcast(self, msg: str, sender_conn: socket.socket | None = None) -> None:
        """
        Send message to every connected client
        """
        message = msg.encode(self.FORMAT)
        msg_length = len(message)
        send_length = str(msg_length).encode(self.FORMAT)
        send_length += b" " * (self.HEADER - len(send_length))

        for client in self.clients:
            if client != sender_conn:
                try:
                    client.send(send_length)
                    client.send(message)
                except Exception as e:
                    logger.error(f"Error while broadcasting to: {client}\n\nError: {e}")

    def start_game(self) -> None:
        logger.info("[SERVER] The game is starting!")
        payload = build_start_payload()
        self.broadcast(payload)
