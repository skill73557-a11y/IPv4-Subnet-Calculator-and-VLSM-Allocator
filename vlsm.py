"""Variable Length Subnet Mask (VLSM) allocation."""

from collections.abc import Mapping, Sequence

from utils import int_to_ip, ip_to_int, mask_from_prefix


def prefix_for_hosts(hosts: int) -> int:
    """Return the smallest conventional IPv4 prefix with room for ``hosts`` usable hosts."""
    if not isinstance(hosts, int) or isinstance(hosts, bool) or hosts <= 0:
        raise ValueError("host requirement must be a positive integer")

    host_bits = max(2, (hosts + 1).bit_length())
    if host_bits > 32:
        raise ValueError("host requirement is too large for IPv4")
    return 32 - host_bits


def vlsm_split(
    base_network: str,
    base_prefix: int,
    requirements: Sequence[Mapping[str, str | int]],
) -> list[dict[str, str | int]]:
    """Allocate subnet blocks largest-first within an IPv4 network.

    Each requirement must contain a non-empty ``name`` and a positive integer
    ``hosts`` count. Allocations use conventional network/broadcast reservations,
    so a two-host requirement is allocated a /30 rather than a /31.
    """
    base_mask = mask_from_prefix(base_prefix)
    base_int = ip_to_int(base_network) & base_mask
    end = base_int + (1 << (32 - base_prefix))

    normalized: list[tuple[str, int, int]] = []
    for requirement in requirements:
        name = requirement.get("name")
        hosts = requirement.get("hosts")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("each requirement must have a non-empty name")
        if not isinstance(hosts, int) or isinstance(hosts, bool) or hosts <= 0:
            raise ValueError(f"host requirement for {name!r} must be a positive integer")
        normalized.append((name.strip(), hosts, prefix_for_hosts(hosts)))

    normalized.sort(key=lambda item: item[1], reverse=True)

    cursor = base_int
    allocations: list[dict[str, str | int]] = []
    for name, hosts, prefix in normalized:
        size = 1 << (32 - prefix)
        aligned_cursor = (cursor + size - 1) & ~(size - 1)

        if aligned_cursor + size > end:
            raise ValueError(f"not enough space for {name} ({hosts} hosts)")

        network = aligned_cursor
        broadcast = network + size - 1
        allocations.append(
            {
                "name": name,
                "need": hosts,
                "cidr": f"{int_to_ip(network)}/{prefix}",
                "network": int_to_ip(network),
                "broadcast": int_to_ip(broadcast),
                "first": int_to_ip(network + 1),
                "last": int_to_ip(broadcast - 1),
                "usable": size - 2,
            }
        )
        cursor = broadcast + 1

    return allocations
