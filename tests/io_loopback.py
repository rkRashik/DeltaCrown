"""Finite loopback fault fixture; no services/credentials outside QA."""
import select
import socket
import threading


class Loopback:
    def __init__(self, handler):
        self.handler = handler
        self.stop = threading.Event()
        self.peers, self.workers, self.errors = [], [], []
        self.count = 0

    def __enter__(self):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.port = self.listener.getsockname()[1]
        self.listener.listen()
        self.listener.settimeout(.1)
        self.thread = threading.Thread(target=self.accept, daemon=True)
        self.thread.start()
        return self

    def accept(self):
        while not self.stop.is_set():
            try:
                peer, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self.count += 1
            self.peers.append(peer)
            worker = threading.Thread(target=self.serve, args=(peer, self.count), daemon=True)
            self.workers.append(worker)
            worker.start()

    def serve(self, peer, number):
        try:
            with peer:
                peer.settimeout(.5)
                self.handler(peer, number, self)
        except OSError:
            pass  # Expected peer disconnects/timeouts during injected faults.
        except Exception as error:
            self.errors.append(type(error).__name__)  # Never raw protocol/header data.

    def __exit__(self, *args):
        self.stop.set()
        self.listener.close()
        self.thread.join(2)
        for peer in self.peers:
            try:
                peer.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            peer.close()
        for worker in self.workers:
            worker.join(2)
        assert not self.thread.is_alive() and not any(w.is_alive() for w in self.workers)
        assert not self.errors, self.errors


def blackhole(peer, number, server):
    server.stop.wait(4)  # Finite even if the client under test never disconnects.


def redis_replies(peer, number, server, *, stall_ping=False):
    """Minimal RESP for cache/PING tests only; Channels uses real disposable Redis."""
    source = peer.makefile("rb")
    while not server.stop.is_set():
        line = source.readline()
        if not line:
            return
        if not line.startswith(b"*"):
            raise ValueError("QA RESP array required")
        parts = []
        for _ in range(int(line[1:])):
            size = int(source.readline()[1:])
            parts.append(source.read(size))
            source.read(2)
        command = parts[0].upper()
        if command == b"PING" and stall_ping:
            blackhole(peer,number,server)
            return
        peer.sendall(b"+PONG\r\n" if command == b"PING" else b"$-1\r\n" if command == b"GET" else b"+OK\r\n")


def relay(peer, number, server, port):
    """Only a guarded disposable Redis port, never a provider URL."""
    with socket.create_connection(("127.0.0.1", port), timeout=.5) as upstream:
        while not server.stop.is_set():
            readable, _, _ = select.select([peer, upstream], [], [], .05)
            for source in readable:
                chunk = source.recv(65536)
                if not chunk:
                    return
                (upstream if source is peer else peer).sendall(chunk)
