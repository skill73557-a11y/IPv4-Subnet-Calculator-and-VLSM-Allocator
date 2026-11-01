"""Local web interface for the IPv4 subnet calculator."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import IPv4Interface, IPv4Network, AddressValueError, NetmaskValueError
from pathlib import Path
from urllib.parse import urlsplit

from subnet import subnet_info
from vlsm import vlsm_split


WEB_DIR = Path(__file__).parent / "web"
MAX_REQUEST_BYTES = 16_384


class CalculatorHandler(BaseHTTPRequestHandler):
    """Serve the dashboard and expose the existing subnet calculation logic."""

    def do_GET(self) -> None:
        routes = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
        }
        route = routes.get(urlsplit(self.path).path)
        if route is None:
            self.send_error(404, "Not found")
            return

        filename, content_type = route
        content = (WEB_DIR / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path not in {"/api/subnet", "/api/vlsm"}:
            self._send_json({"error": "Not found"}, 404)
            return

        try:
            payload = self._read_json()
            if path == "/api/subnet":
                result = self._calculate_subnet(payload)
            else:
                result = self._calculate_vlsm(payload)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, 400)
            return

        self._send_json(result)

    def _read_json(self) -> dict[str, object]:
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            raise ValueError("request body is required")
        try:
            length = int(content_length)
        except ValueError as error:
            raise ValueError("invalid Content-Length header") from error
        if length < 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("request body is too large")

        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    @staticmethod
    def _calculate_subnet(payload: dict[str, object]) -> dict[str, str | int]:
        cidr = payload.get("cidr")
        if not isinstance(cidr, str):
            raise ValueError("enter an IPv4 address with a CIDR prefix")
        try:
            interface = IPv4Interface(cidr)
        except (AddressValueError, NetmaskValueError) as error:
            raise ValueError(f"invalid IPv4 CIDR: {cidr}") from error
        return subnet_info(str(interface.ip), interface.network.prefixlen)

    @staticmethod
    def _calculate_vlsm(payload: dict[str, object]) -> dict[str, object]:
        base_cidr = payload.get("base_cidr")
        requirements = payload.get("requirements")
        if not isinstance(base_cidr, str):
            raise ValueError("enter a base IPv4 network in CIDR notation")
        try:
            network = IPv4Network(base_cidr, strict=False)
        except (AddressValueError, NetmaskValueError) as error:
            raise ValueError(f"invalid IPv4 network CIDR: {base_cidr}") from error
        if not isinstance(requirements, list) or not requirements:
            raise ValueError("add at least one subnet requirement")
        if len(requirements) > 64:
            raise ValueError("a maximum of 64 subnet requirements is allowed")
        if any(not isinstance(requirement, dict) for requirement in requirements):
            raise ValueError("each subnet requirement must include a name and host count")

        allocations = vlsm_split(
            str(network.network_address),
            network.prefixlen,
            requirements,
        )
        return {
            "base_cidr": str(network),
            "total_addresses": network.num_addresses,
            "allocations": allocations,
        }

    def _send_json(self, result: object, status: int = 200) -> None:
        content = json.dumps(result).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[web] {self.address_string()} - {format % args}")


def main() -> None:
    host = "127.0.0.1"
    port = 8000
    server = ThreadingHTTPServer((host, port), CalculatorHandler)
    print(f"Subnet calculator is running at http://{host}:{port}")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping subnet calculator.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
