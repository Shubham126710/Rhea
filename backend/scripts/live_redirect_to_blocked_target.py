"""
Closes the one live-test gap the sandbox environment couldn't host:
a REAL, reachable hop-1 server (on a real, non-blocked address) that
issues a 302 to a blocked internal target, exercised with real
sockets end-to-end (no httpx.MockTransport, no getaddrinfo mocking).

Why this couldn't run in the original sandbox: that container's only
connectable interface address was 192.0.2.2 (TEST-NET-1), itself in a
blocked range, so no "safe" hop-1 server could be hosted there.

Run this on any machine/VM with a real public-range outbound IP
(a laptop, a cloud instance, etc.) from the backend/ directory:

    PYTHONPATH=. python3 scripts/live_redirect_to_blocked_target.py

Expects the shared_preprocessing package to be importable (i.e. run
from within the backend/ project root with its venv active).
"""
import http.server
import socket
import threading

from app.shared_preprocessing.exceptions import SSRFBlocked
from app.shared_preprocessing.url_fetch import fetch_and_extract


def _own_outbound_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def main() -> None:
    own_ip = _own_outbound_ip()
    print(f"This machine's outbound address: {own_ip}")
    print("(If this is itself a private/reserved range, this environment")
    print(" can't close the gap either -- you need a real public IP.)")

    class RedirectHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", "http://10.0.0.5/internal-secret")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer((own_ip, 0), RedirectHandler)
    port = server.server_port
    threading.Thread(target=server.serve_forever, daemon=True).start()

    url = f"http://{own_ip}:{port}/start"
    print(f"Requesting {url} (a real, live, reachable hop-1 server)")
    print("that issues a real 302 redirect to http://10.0.0.5/ (blocked)")

    try:
        fetch_and_extract(url)
        print("FAIL: fetch succeeded -- the redirect to a blocked target was NOT stopped")
    except SSRFBlocked as exc:
        print(f"PASS: hop 2 blocked live -- {exc}")
    except Exception as exc:
        print(f"UNEXPECTED exception type: {type(exc).__name__}: {exc}")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
