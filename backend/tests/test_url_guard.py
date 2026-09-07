"""Unit tests for the anti-SSRF URL guard (no network: DNS is stubbed)."""

import pytest

from app.utils import url_guard
from app.utils.url_guard import UnsafeURLError, assert_public_http_url


@pytest.fixture
def dns(monkeypatch):
    """Stub DNS with a hostname -> [ip, ...] table; unknown hosts fail to resolve."""
    table: dict[str, list[str]] = {}

    def fake_resolve(hostname):
        if hostname not in table:
            raise UnsafeURLError(f"host tidak bisa diresolusi: {hostname}")
        return table[hostname]

    monkeypatch.setattr(url_guard, "resolve_host", fake_resolve)
    return table


def test_public_hostname_passes_and_returns_url(dns):
    dns["arxiv.org"] = ["151.101.1.1", "2a04:4e42::1"]
    url = "https://arxiv.org/pdf/1234.5678.pdf"
    assert assert_public_http_url(url) == url


def test_public_literal_ip_passes_without_dns(dns):
    # nothing in the table: a literal IP must never hit DNS
    assert assert_public_http_url("http://8.8.8.8/paper.pdf")


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8001/health",
    "http://localhost/x.pdf",
    "http://api.localhost/x.pdf",
    "http://10.0.0.5/x.pdf",
    "http://172.16.3.4/x.pdf",
    "http://192.168.1.1/x.pdf",
    "http://169.254.169.254/latest/meta-data",
    "http://0.0.0.0/x.pdf",
    "http://[::1]/x.pdf",
    "http://[fe80::1]/x.pdf",
    "http://[fd00::1]/x.pdf",
    "http://[::ffff:127.0.0.1]/x.pdf",
    "http://224.0.0.1/x.pdf",
])
def test_internal_addresses_are_rejected(dns, url):
    with pytest.raises(UnsafeURLError):
        assert_public_http_url(url)


@pytest.mark.parametrize("url", [
    "ftp://arxiv.org/x.pdf",
    "file:///etc/passwd",
    "gopher://arxiv.org/",
    "arxiv.org/x.pdf",
    "https:///x.pdf",
    "https://user:pass@arxiv.org/x.pdf",
])
def test_bad_schemes_hosts_and_credentials_are_rejected(dns, url):
    dns["arxiv.org"] = ["151.101.1.1"]
    with pytest.raises(UnsafeURLError):
        assert_public_http_url(url)


def test_hostname_resolving_to_private_ip_is_rejected(dns):
    dns["evil.example"] = ["127.0.0.1"]
    with pytest.raises(UnsafeURLError, match="alamat internal"):
        assert_public_http_url("https://evil.example/x.pdf")


def test_hostname_with_mixed_public_and_private_ips_is_rejected(dns):
    dns["mixed.example"] = ["151.101.1.1", "10.0.0.9"]
    with pytest.raises(UnsafeURLError):
        assert_public_http_url("https://mixed.example/x.pdf")


def test_hostname_resolving_to_ipv4_mapped_loopback_is_rejected(dns):
    dns["mapped.example"] = ["::ffff:127.0.0.1"]
    with pytest.raises(UnsafeURLError):
        assert_public_http_url("https://mapped.example/x.pdf")


def test_unresolvable_hostname_is_rejected(dns):
    with pytest.raises(UnsafeURLError, match="tidak bisa diresolusi"):
        assert_public_http_url("https://nonexistent.invalid/x.pdf")
