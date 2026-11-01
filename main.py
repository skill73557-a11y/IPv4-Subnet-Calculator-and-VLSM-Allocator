"""Command-line interface for the IPv4 subnet calculator and VLSM allocator."""

import argparse
from ipaddress import IPv4Interface, IPv4Network, AddressValueError, NetmaskValueError

from subnet import subnet_info
from vlsm import vlsm_split


def _ipv4_interface(value: str) -> IPv4Interface:
    try:
        return IPv4Interface(value)
    except (AddressValueError, NetmaskValueError, ValueError) as error:
        raise argparse.ArgumentTypeError(f"invalid IPv4 CIDR: {value}") from error


def _ipv4_network(value: str) -> IPv4Network:
    try:
        return IPv4Network(value, strict=False)
    except (AddressValueError, NetmaskValueError, ValueError) as error:
        raise argparse.ArgumentTypeError(f"invalid IPv4 network CIDR: {value}") from error


def _requirement(value: str) -> dict[str, str | int]:
    name, separator, host_text = value.partition(":")
    if not separator or not name.strip() or not host_text:
        raise argparse.ArgumentTypeError("requirements must use NAME:HOSTS format")
    try:
        hosts = int(host_text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"invalid host count in {value!r}") from error
    if hosts <= 0:
        raise argparse.ArgumentTypeError("host counts must be positive")
    return {"name": name.strip(), "hosts": hosts}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IPv4 subnet calculator and VLSM allocator")
    commands = parser.add_subparsers(dest="command", required=True)

    subnet_parser = commands.add_parser("subnet", help="calculate details for an IPv4 CIDR")
    subnet_parser.add_argument("cidr", type=_ipv4_interface, help="for example, 192.168.1.10/26")

    vlsm_parser = commands.add_parser("vlsm", help="allocate subnets using VLSM")
    vlsm_parser.add_argument("base_cidr", type=_ipv4_network, help="for example, 192.168.1.0/24")
    vlsm_parser.add_argument(
        "requirements",
        nargs="*",
        type=_requirement,
        metavar="NAME:HOSTS",
        help="host requirement, for example, LAN-A:50",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "subnet":
        interface = args.cidr
        try:
            info = subnet_info(str(interface.ip), interface.network.prefixlen)
        except ValueError as error:
            parser.error(str(error))
        for key, value in info.items():
            print(f"{key:>16}: {value}")
        return

    network = args.base_cidr
    try:
        allocations = vlsm_split(
            str(network.network_address),
            network.prefixlen,
            args.requirements,
        )
    except ValueError as error:
        parser.error(str(error))

    if not allocations:
        parser.error("provide at least one NAME:HOSTS requirement")

    for allocation in allocations:
        print(
            f"{allocation['name']:10} {allocation['cidr']:18} "
            f"{allocation['first']:15} - {allocation['last']:15} "
            f"usable={allocation['usable']}"
        )


if __name__ == "__main__":
    main()
