"""Anti-SSRF guard for URLs the server is asked to download on a user's behalf.

``/api/papers/fetch-pdf`` and ``/download-and-analyze`` accept arbitrary
``pdf_url`` values (and URLs resolved from Unpaywall). Without a check the
backend could be pointed at ``http://127.0.0.1:8001/...`` or a LAN host.

Scope: literal IPs and every address a hostname resolves to must be globally
routable. DNS rebinding between this check and the actual request (TOCTOU) is
out of scope for a single-user localhost deployment.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})


class UnsafeURLError(ValueError):
    """The URL points at a scheme or network location the server must not fetch."""


def resolve_host(hostname: str) -> list[str]:
    """Return every IP address ``hostname`` resolves to (module-level so tests can stub it)."""
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"host tidak bisa diresolusi: {hostname}") from exc
    return sorted({info[4][0] for info in infos})


def _is_public(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    # is_global already excludes private, loopback, link-local, reserved and unspecified
    return address.is_global and not address.is_multicast


def assert_public_http_url(url: str) -> str:
    """Return ``url`` unchanged if it is http(s) to a public host; raise ``UnsafeURLError`` otherwise."""
    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURLError(f"skema URL tidak diizinkan: {parts.scheme or '(kosong)'}")
    if parts.username is not None or parts.password is not None:
        raise UnsafeURLError("URL dengan kredensial tidak diizinkan")

    host = parts.hostname
    if not host:
        raise UnsafeURLError("URL tanpa host")
    if host == "localhost" or host.endswith(".localhost"):
        raise UnsafeURLError("URL menunjuk ke localhost")

    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        addresses = [ipaddress.ip_address(addr) for addr in resolve_host(host)]
    if not addresses:
        raise UnsafeURLError(f"host tidak punya alamat IP: {host}")

    for address in addresses:
        if not _is_public(address):
            raise UnsafeURLError(f"URL menunjuk ke alamat internal ({address})")
    return url
