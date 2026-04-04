import logging
import socket
import threading

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

    def handle_client(self, conn: socket.socket, addr):
        logger.info(f"[NEW CONNECTION] {addr} connected")

        connected: bool = True
        while connected:
            msg_length = conn.recv(self.HEADER).decode(self.FORMAT)
            if msg_length:
                msg_length = int(msg_length)
                msg = conn.recv(msg_length).decode(self.FORMAT)

                if msg == self.DISCONNECT_MSG:
                    connected = False

                logger.info(f"[{addr}] {msg}")
        conn.close()

    def start(self):
        logger.info("[STARTING] Server is starting")
        logger.info(f"[LISTENING] Server is listening on {self.SERVER}")

        self.server.bind(self.ADDR)
        self.server.listen()
        while True:
            conn, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()
            logger.info(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
