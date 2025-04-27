import sys
import socket
import selectors
import types


# establishes listener
sel = selectors.DefaultSelector()

# accepts connection
def accept_wrapper(sock):
    conn, addr = sock.accept() # ready to read
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)

# reads and writes data
def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024) # ready to read
        if recv_data:
            data.outb += recv_data
        else:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print(f"Echoing {data.outb!r} to {data.addr}")
            sent = sock.send(data.outb) # ready to write
            data.outb = data.outb[sent:]

if len(sys.argv) != 3:
    print(f"Expected format: {sys.argv[0]} <host> <port>\nExiting command now")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((host, port))
lsock.listen()
print(f"Listening at {(host, port)}") #is this bad?
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

# event loop
try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                service_connection(key,mask)
except KeyboardInterrupt:
    print("\nCaught keyboard interrupt, exiting")
finally:
    sel.close()