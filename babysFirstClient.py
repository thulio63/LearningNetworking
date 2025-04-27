import socket

HOST = "127.0.0.1"
#doesn't validate data, first step
PORT = int(input("choose what port to attempt to access:\t"))

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(b"Hello, world!")
    data = s.recv(1024)

print(f"Received {data!r}")