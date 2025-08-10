import socket

class NetworkHandler:
    def __init__(self, port=50999):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', self.port))
        self.sock.settimeout(1.0)

    def broadcast(self, message):
        self.sock.sendto(message.encode('utf-8'), ('<broadcast>', self.port))

    def unicast(self, message, ip_address):
        self.sock.sendto(message.encode('utf-8'), (ip_address, self.port))

    def receive(self):
        try:
            data, addr = self.sock.recvfrom(32768) # Buffer size 32KB
            return data.decode('utf-8'), addr
        except socket.timeout:
            return None, None

    def close(self):
        self.sock.close()
