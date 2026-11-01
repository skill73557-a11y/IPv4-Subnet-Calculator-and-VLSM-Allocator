"""IPv4 address conversion and subnet-mask helpers."""

from ipaddress import IPv4Address


def ip_to_int(ip: str) -> int:
    """Convert a dotted-decimal IPv4 address to an unsigned 32-bit integer."""
    return int(IPv4Address(ip))


def int_to_ip(n: int) -> str:
    """Convert an unsigned 32-bit integer to dotted-decimal IPv4 notation."""
    if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 0xFFFFFFFF:
        raise ValueError("IPv4 integer must be between 0 and 4294967295")
    return str(IPv4Address(n))


def mask_from_prefix(prefix: int) -> int:
    """Return a subnet mask as an integer for a prefix from /0 through /32."""
    if not isinstance(prefix, int) or isinstance(prefix, bool) or not 0 <= prefix <= 32:
        raise ValueError("prefix must be an integer from 0 through 32")
    return (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
