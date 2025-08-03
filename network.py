import socket

class NetworkHandler:
    def __init__(self, port=50999):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', self.port))

    def broadcast(self, message):
        self.sock.sendto(message.encode('utf-8'), ('<broadcast>', self.port))

    def unicast(self, message, ip_address):
        self.sock.sendto(message.encode('utf-8'), (ip_address, self.port))

    def receive(self):
        data, addr = self.sock.recvfrom(1024) # Buffer size 1024 bytes
        return data.decode('utf-8'), addr

    def close(self):
        self.sock.close()
