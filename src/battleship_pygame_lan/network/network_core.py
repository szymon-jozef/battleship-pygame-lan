import socket
from logging import getLogger

logger = getLogger(__name__)


class NetworkCore:
    def __init__(self, ip_address: str, port: int = 6769) -> None:
        self.HEADER = 64
        self.FORMAT = "utf-8"
        self.PORT = port
        self.HOST = ip_address
        self.ADDR = (self.HOST, self.PORT)

    def send_to_socket(self, target_socket: socket.socket, msg: str) -> None:
        """Universal send to socket"""
        try:
            message: bytes = msg.encode(self.FORMAT)
            msg_len: int = len(message)
            encoded_message: bytes = str(msg_len).encode(self.FORMAT)
            padded_header: bytes = encoded_message + b" " * (
                self.HEADER - len(encoded_message)
            )

            target_socket.sendall(padded_header)
            target_socket.sendall(message)
        except OSError as e:
            logger.error(f"[Network] Error while sending data: {e}")
