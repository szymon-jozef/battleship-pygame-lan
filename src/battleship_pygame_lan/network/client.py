import socket


class NetworkClient:
    def __init__(self) -> None:
        self.SERVER = socket.gethostbyname(socket.gethostname())
        self.HEADER = 64
        self.PORT = 6969
        self.FORMAT = "utf-8"
        self.DISCONNECT_MSG = "!DISCONNET"
        self.ADDR = (self.SERVER, self.PORT)

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(self.ADDR)

    def send(self, msg: str) -> None:
        message = msg.encode(self.FORMAT)
        msg_length = len(message)
        send_length = str(msg_length).encode(self.FORMAT)
        send_length += b" " * (self.HEADER - len(send_length))
        self.client.send(send_length)
        self.client.send(message)


if __name__ == "__main__":
    client = NetworkClient()
    client.send("Hello world!")
