"""Unit tests for subnet calculations, VLSM, and command-line validation."""

import unittest

from subnet import subnet_info
from utils import int_to_ip, ip_to_int, mask_from_prefix
from vlsm import prefix_for_hosts, vlsm_split


class UtilsTests(unittest.TestCase):
    def test_ip_conversion_round_trip(self) -> None:
        ip = "192.168.1.10"
        self.assertEqual(int_to_ip(ip_to_int(ip)), ip)

    def test_invalid_ip_and_integer_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ip_to_int("256.1.1.1")
        with self.assertRaises(ValueError):
            int_to_ip(-1)

    def test_prefix_boundaries(self) -> None:
        self.assertEqual(int_to_ip(mask_from_prefix(0)), "0.0.0.0")
        self.assertEqual(int_to_ip(mask_from_prefix(32)), "255.255.255.255")
        with self.assertRaises(ValueError):
            mask_from_prefix(33)


class SubnetTests(unittest.TestCase):
    def test_classic_subnet(self) -> None:
        result = subnet_info("192.168.1.10", 26)
        self.assertEqual(result["network"], "192.168.1.0")
        self.assertEqual(result["broadcast"], "192.168.1.63")
        self.assertEqual(result["first_host"], "192.168.1.1")
        self.assertEqual(result["last_host"], "192.168.1.62")
        self.assertEqual(result["host_count"], 62)
        self.assertEqual(result["total_addresses"], 64)

    def test_point_to_point_and_single_address_prefixes(self) -> None:
        point_to_point = subnet_info("10.0.0.1", 31)
        self.assertEqual(point_to_point["first_host"], "10.0.0.0")
        self.assertEqual(point_to_point["last_host"], "10.0.0.1")
        self.assertEqual(point_to_point["host_count"], 2)

        single = subnet_info("10.0.0.1", 32)
        self.assertEqual(single["network"], "10.0.0.1")
        self.assertEqual(single["first_host"], "10.0.0.1")
        self.assertEqual(single["last_host"], "10.0.0.1")
        self.assertEqual(single["host_count"], 1)

    def test_invalid_prefix_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            subnet_info("192.168.1.1", 33)


class VlsmTests(unittest.TestCase):
    def test_prefix_for_host_counts(self) -> None:
        self.assertEqual(prefix_for_hosts(100), 25)
        self.assertEqual(prefix_for_hosts(50), 26)
        self.assertEqual(prefix_for_hosts(2), 30)
        with self.assertRaises(ValueError):
            prefix_for_hosts(0)
        with self.assertRaises(ValueError):
            prefix_for_hosts(0xFFFFFFFF)

    def test_allocations_are_largest_first_and_aligned(self) -> None:
        allocations = vlsm_split(
            "192.168.1.0",
            24,
            [
                {"name": "LAN-A", "hosts": 100},
                {"name": "LAN-B", "hosts": 50},
                {"name": "LAN-C", "hosts": 25},
                {"name": "WAN-1", "hosts": 2},
                {"name": "WAN-2", "hosts": 2},
            ],
        )
        self.assertEqual(
            [allocation["cidr"] for allocation in allocations],
            [
                "192.168.1.0/25",
                "192.168.1.128/26",
                "192.168.1.192/27",
                "192.168.1.224/30",
                "192.168.1.228/30",
            ],
        )
        self.assertEqual(allocations[0]["usable"], 126)

    def test_unaligned_base_is_normalized_and_insufficient_space_fails(self) -> None:
        allocation = vlsm_split("192.168.1.99", 24, [{"name": "LAN", "hosts": 10}])
        self.assertEqual(allocation[0]["network"], "192.168.1.0")
        with self.assertRaisesRegex(ValueError, "not enough space"):
            vlsm_split(
                "192.168.1.0",
                24,
                [{"name": "LAN-A", "hosts": 200}, {"name": "LAN-B", "hosts": 100}],
            )

    def test_invalid_requirements_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            vlsm_split("192.168.1.0", 24, [{"name": "", "hosts": 10}])
        with self.assertRaises(ValueError):
            vlsm_split("192.168.1.0", 24, [{"name": "LAN", "hosts": True}])


if __name__ == "__main__":
    unittest.main()
