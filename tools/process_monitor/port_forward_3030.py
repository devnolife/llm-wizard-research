"""Forward port 3030 -> 8501 (web monitor) tanpa dependensi eksternal."""
import socket, threading

LISTEN, TARGET = ("0.0.0.0", 3030), ("127.0.0.1", 8501)

def pipe(src, dst):
    try:
        while (data := src.recv(65536)):
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try: s.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            s.close()

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(LISTEN); srv.listen(64)
print(f"forward {LISTEN} -> {TARGET}")
while True:
    cli, _ = srv.accept()
    try:
        up = socket.create_connection(TARGET, timeout=10)
    except OSError:
        cli.close(); continue
    threading.Thread(target=pipe, args=(cli, up), daemon=True).start()
    threading.Thread(target=pipe, args=(up, cli), daemon=True).start()
