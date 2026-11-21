#!/usr/bin/env python3
"""Socket proxy between a GTK app and gtk4-broadwayd that keeps the daemon alive.

GTK's Broadway renderer sends "reuse node <id>" for a render node it already
sent in the last frame. When the same render node object is in the tree twice
(GTK 4.22 and later share the node of a symbolic icon between all widgets
that show it), it sends the same id twice, and gtk4-broadwayd aborts with

    broadway-output.c: append_node_ops: assertion failed: (!reused_node->consumed)

This proxy forwards everything unchanged, except that in each frame the
second and later "reuse" of an id is replaced by a copy of that node with new
ids. A copy may show a texture the app has released meanwhile (textures drawn
for one frame), so a release is held back while a node that can still be
copied uses the texture. Details: docs/screenshot-testing.md.

Usage: broadway_dedup.py LISTEN_SOCKET BROADWAYD_SOCKET
"""
import array
import os
import signal
import socket
import struct
import sys
import threading

# gdk/broadway/broadway-protocol.h (GTK 4.14 to 4.24)
REQUEST_DESTROY_SURFACE = 4
REQUEST_RELEASE_TEXTURE = 14
REQUEST_SET_NODES = 15
HEADER = struct.Struct("=III")  # size, serial, type

TEXTURE, CONTAINER, COLOR, BORDER, OUTSET_SHADOW, INSET_SHADOW = range(6)
ROUNDED_CLIP, LINEAR_GRADIENT, SHADOW, OPACITY, CLIP, TRANSFORM = range(6, 12)
DEBUG, REUSE = 12, 13

# Ids of copies: the renderer restarts its own ids below this value.
FIRST_COPY_ID = 0x80000000
MAX_FDS = 32


def _layout(kind, words, pos):
    """(data words, children) of the node of type `kind` whose data starts
    at words[pos]; as decode_nodes() in gdk/broadway/broadway-server.c."""
    if kind == CONTAINER:
        return 1, words[pos]
    if kind == TRANSFORM:
        matrix = words[pos]
        if matrix not in (0, 1):
            raise ValueError(f"unknown transform type {matrix}")
        return 1 + (16 if matrix else 2), 1
    if kind == LINEAR_GRADIENT:
        return 9 + 2 * words[pos + 8], 0
    if kind == SHADOW:
        return 1 + 4 * words[pos], 1
    if kind == DEBUG:
        return 1 + (words[pos] + 3) // 4, 1
    fixed = {TEXTURE: (5, 0), COLOR: (5, 0), BORDER: (20, 0),
             OUTSET_SHADOW: (17, 0), INSET_SHADOW: (17, 0),
             ROUNDED_CLIP: (12, 1), OPACITY: (1, 1), CLIP: (4, 1)}
    if kind not in fixed:
        raise ValueError(f"unknown node type {kind}")
    return fixed[kind]


class Surface:
    """The nodes one surface's renderer may reuse in its next frame."""

    def __init__(self):
        self.nodes = {}  # id -> (type, data words, child ids)
        self.textures = set()  # texture ids the nodes use
        self.next_copy = FIRST_COPY_ID
        self.copies = 0

    def rewrite(self, words):
        """One frame (the data of a SET_NODES request) with every id reused
        at most once. Returns the input list itself when nothing changed."""
        out, seen, defined = [], set(), {}
        pos, changed = self._read(words, 0, out, seen, defined)
        if pos != len(words):
            raise ValueError("trailing data after the root node")
        # The renderer reuses only what was in this frame.
        for node in seen:
            if node in self.nodes:
                defined.setdefault(node, self.nodes[node])
        self.nodes = defined
        self.textures = {data[4] for kind, data, _children in defined.values()
                         if kind == TEXTURE}
        return out if changed else words

    def _read(self, words, pos, out, seen, defined):
        """Copies the node at words[pos] to `out`. Returns the position
        after it and whether anything was replaced."""
        kind, node = words[pos], words[pos + 1]
        pos += 2
        if kind == REUSE:
            if node in seen and node in self.nodes:
                self._copy(node, out)
                return pos, True
            self._mark(node, seen)
            out += (kind, node)
            return pos, False
        size, n_children = _layout(kind, words, pos)
        data = tuple(words[pos:pos + size])
        if len(data) != size:
            raise ValueError("truncated node")
        pos += size
        out += (kind, node)
        out += data
        children, changed = [], False
        for _ in range(n_children):
            children.append(words[pos + 1])
            pos, replaced = self._read(words, pos, out, seen, defined)
            changed = changed or replaced
        defined[node] = (kind, data, tuple(children))
        return pos, changed

    def _mark(self, node, seen):
        """The daemon takes a reused node with everything below it, so
        none of those may be reused again in this frame."""
        todo = [node]
        while todo:
            node = todo.pop()
            if node not in seen:
                seen.add(node)
                todo.extend(self.nodes.get(node, (0, (), ()))[2])

    def _copy(self, node, out):
        kind, data, children = self.nodes[node]
        out += (kind, self.next_copy)
        out += data
        self.next_copy += 1
        self.copies += 1
        for child in children:
            if child in self.nodes:
                self._copy(child, out)
            else:  # not ours to expand; the daemon knows it
                out += (REUSE, child)


class Requests:
    """Splits the app's byte stream into requests and rewrites SET_NODES."""

    def __init__(self):
        self.buffer = bytearray()
        self.surfaces = {}
        self.held = set()  # textures whose release waits
        self.broken = False

    def feed(self, chunk):
        """Bytes to send to the daemon for the received `chunk`."""
        if self.broken:
            return bytes(chunk)
        self.buffer += chunk
        out = bytearray()
        while len(self.buffer) >= HEADER.size:
            size, _serial, kind = HEADER.unpack_from(self.buffer)
            if size < HEADER.size:
                return self._give_up(out, "request smaller than its header")
            if len(self.buffer) < size:
                break
            request = bytes(self.buffer[:size])
            del self.buffer[:size]
            try:
                out += self._request(kind, request)
            except (ValueError, IndexError, struct.error) as error:
                out += request
                return self._give_up(out, str(error))
        return bytes(out)

    def _request(self, kind, request):
        if kind == REQUEST_SET_NODES:
            return self._set_nodes(request) + self._release(request)
        if kind == REQUEST_DESTROY_SURFACE:
            self.surfaces.pop(struct.unpack_from("=I", request, HEADER.size)[0], None)
            return request + self._release(request)
        if kind == REQUEST_RELEASE_TEXTURE:
            texture = struct.unpack_from("=I", request, HEADER.size)[0]
            if texture in self._textures():
                self.held.add(texture)
                return b""
        return request

    def _textures(self):
        return set().union(*(surface.textures for surface in self.surfaces.values()))

    def _release(self, request):
        """RELEASE_TEXTURE requests for the held textures no node uses any
        more, with the serial of the request they follow."""
        free = self.held - self._textures()
        self.held -= free
        serial = HEADER.unpack_from(request)[1]
        return b"".join(HEADER.pack(HEADER.size + 4, serial, REQUEST_RELEASE_TEXTURE)
                        + struct.pack("=I", texture) for texture in sorted(free))

    def _set_nodes(self, request):
        n_words = (len(request) - HEADER.size) // 4
        fields = struct.unpack_from(f"={n_words}I", request, HEADER.size)
        surface = self.surfaces.setdefault(fields[0], Surface())
        words = list(fields[1:])
        new = surface.rewrite(words)
        if new is words:
            return request
        _size, serial, kind = HEADER.unpack_from(request)
        body = struct.pack(f"={len(new) + 1}I", fields[0], *new)
        return HEADER.pack(HEADER.size + len(body), serial, kind) + body

    def _give_up(self, out, reason):
        """Unknown protocol: forward unchanged from here on. Held textures
        stay with the daemon until the app disconnects."""
        print(f"broadway_dedup: {reason}; forwarding unchanged", file=sys.stderr, flush=True)
        self.broken = True
        out += self.buffer
        self.buffer.clear()
        return bytes(out)

    def copies(self):
        return sum(surface.copies for surface in self.surfaces.values())


def _app_to_daemon(app, daemon, requests):
    """Texture uploads pass their memory as file descriptors; they go on
    with the next bytes, which hold the request they belong to."""
    fds = []
    space = socket.CMSG_LEN(MAX_FDS * array.array("i").itemsize)
    try:
        while True:
            chunk, ancillary, _flags, _address = app.recvmsg(65536, space)
            for level, kind, data in ancillary:
                if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                    received = array.array("i")
                    received.frombytes(data[:len(data) - len(data) % received.itemsize])
                    fds += received
            if not chunk:
                break
            out = requests.feed(chunk)
            if not out:
                continue
            if fds:
                rights = (socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))
                sent = daemon.sendmsg([out], [rights])
                for fd in fds:
                    os.close(fd)
                fds = []
                out = out[sent:]
            daemon.sendall(out)
    except OSError:
        pass
    finally:
        for fd in fds:
            os.close(fd)
        _close(app, daemon)


def _daemon_to_app(daemon, app):
    try:
        while chunk := daemon.recv(65536):
            app.sendall(chunk)
    except OSError:
        pass
    finally:
        _close(app, daemon)


def _close(*sockets):
    for sock in sockets:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


def serve(listen_path, daemon_path):
    clients = []

    def report(*_signal):
        copies = sum(requests.copies() for requests in clients)
        print(f"broadway_dedup: {len(clients)} connections, replaced {copies} repeated node reuses",
              file=sys.stderr, flush=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, report)
    if os.path.exists(listen_path):
        os.unlink(listen_path)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(listen_path)
    server.listen()
    while True:
        app, _address = server.accept()
        daemon = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            daemon.connect(daemon_path)
        except OSError as error:
            print(f"broadway_dedup: {daemon_path}: {error}", file=sys.stderr, flush=True)
            app.close()
            continue
        clients.append(Requests())
        threading.Thread(target=_app_to_daemon, args=(app, daemon, clients[-1]), daemon=True).start()
        threading.Thread(target=_daemon_to_app, args=(daemon, app), daemon=True).start()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__.strip().splitlines()[-1])
    serve(sys.argv[1], sys.argv[2])
