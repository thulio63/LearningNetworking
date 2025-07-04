import selectors
import socket
import sys
import traceback

import babysFirstLibServer

sel = selectors.DefaultSelector()


def accept_wrapper(sock):
    conn, addr = sock.accept() # ready to read
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    message = babysFirstLibServer.Message(sel, conn, addr)
    sel.register(conn, selectors.EVENT_READ, data=message)
    
if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <host> <port>")
    sys.exit(1)
    

host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# avoiding err48: address already in use
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((host, port))
lsock.listen()
print(f"Listening to port {port} on {host}")
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                message = key.data
                try:
                    message.process_events(mask)
                except Exception:
                    print(
                        f"Main: Error: Exception for {message.addr}:\n"
                        f"{traceback.format_exc()}"
                    )
                    message.close()
except KeyboardInterrupt:
    print("\nCaught keyboard interrupt, exiting")
finally:
    sel.close()