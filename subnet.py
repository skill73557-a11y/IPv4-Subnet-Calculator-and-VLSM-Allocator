"""IPv4 subnet calculations."""

from utils import int_to_ip, ip_to_int, mask_from_prefix


def subnet_info(ip: str, prefix: int) -> dict[str, str | int]:
    """Calculate network, broadcast, host range, and address counts for an IPv4 subnet."""
    ip_int = ip_to_int(ip)
    mask = mask_from_prefix(prefix)
    network = ip_int & mask
    broadcast = network | (~mask & 0xFFFFFFFF)
    host_bits = 32 - prefix

    if prefix == 31:
        first, last, hosts = network, broadcast, 2
    elif prefix == 32:
        first = last = network
        hosts = 1
    else:
        first = network + 1
        last = broadcast - 1
        hosts = (1 << host_bits) - 2

    return {
        "input_ip": ip,
        "prefix": prefix,
        "subnet_mask": int_to_ip(mask),
        "network": int_to_ip(network),
        "broadcast": int_to_ip(broadcast),
        "first_host": int_to_ip(first),
        "last_host": int_to_ip(last),
        "host_count": hosts,
        "total_addresses": 1 << host_bits,
        "wildcard": int_to_ip(~mask & 0xFFFFFFFF),
    }
