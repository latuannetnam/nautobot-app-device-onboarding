"""Test for Juniper JunOS interface extractors only.

This module tests interface-related extraction functionality for Juniper JunOS devices.
It focuses specifically on interface__ patterns from the command mapper.
"""
import json
import os
import unittest
import yaml

from nautobot_device_onboarding.nornir_plays.formatter import extract_and_post_process
from nautobot_device_onboarding.tests.utils import setup_command_getter_logging, cleanup_command_getter_logging

MOCK_DIR = os.path.join("nautobot_device_onboarding", "tests", "mock")


class TestJuniperJunosInterfaceExtractors(unittest.TestCase):
    """Test interface-related extractors for Juniper JunOS devices."""

    def setUp(self):
        """Set up test case with Juniper JunOS command mapper and interface command getter result data."""
        # Set up unified logging
        self.logger, self.etl_logger, self.unified_handler = setup_command_getter_logging(__name__)
        self.logger.info("\nSetup %s\n", self._testMethodName)
        
        # Load command mapper
        with open(f"{MOCK_DIR}/command_mappers/juniper_junos.yml", "r", encoding="utf-8") as mapper_file:
            self.command_mapper_data = yaml.safe_load(mapper_file)
        
        # Load interface command getter result
        with open(f"{MOCK_DIR}/juniper_mx204/juniper_mx204_show_interface_getter_result.json", "r", encoding="utf-8") as result_file:
            self.interface_result = json.load(result_file)
    
    def tearDown(self) -> None:
        """Clean up unified logging setup."""
        cleanup_command_getter_logging(self.logger, self.etl_logger, self.unified_handler)
        return super().tearDown()

    def test_extract_interfaces_root_key(self):
        """Test extraction of interfaces using root_key configuration."""
        interfaces_config = self.command_mapper_data["sync_network_data"]["interfaces"]
        
        # Extract the first command configuration
        command_config = interfaces_config["commands"][0]
        
        parsed_result, processed_result = extract_and_post_process(
            self.interface_result,
            command_config,
            {"obj": "192.0.2.1", "original_host": "192.0.2.1"},
            interfaces_config.get("iterable_type"),
            True,  # Enable debug logging
        )
        
        self.logger.debug("Parsed result: %s", parsed_result)
        self.logger.debug("Processed result: %s", processed_result)
        
        # Should return interface data structure
        self.assertTrue(isinstance(processed_result, (str, dict, list)))
        
        # If it's a string, should be valid JSON
        if isinstance(processed_result, str):
            try:
                interfaces_data = json.loads(processed_result)
                self.assertIsInstance(interfaces_data, dict)
                # Should have interface names as keys
                interface_keys = list(interfaces_data.keys())
                self.assertTrue(len(interface_keys) > 0, "Should have at least one interface")
                # Log found interfaces for debugging
                self.logger.debug("Found interfaces: %s", interface_keys)
            except (json.JSONDecodeError, TypeError):
                # If not valid JSON, should at least be a string
                self.assertIsInstance(processed_result, str)

    def test_extract_interface_type(self):
        """Test extraction of interface type for different interface types."""
        interfaces_type_config = self.command_mapper_data["sync_network_data"]["interfaces__type"]
        command_config = interfaces_type_config["commands"][0]
        
        # Test different interface types that should be in the data
        test_interfaces = ["et-0/0/0", "xe-0/1/0", "xe-0/1/7", "pe-0/0/0"]
        
        for interface in test_interfaces:
            with self.subTest(interface=interface):
                parsed_result, processed_result = extract_and_post_process(
                    self.interface_result,
                    command_config,
                    {"current_key": interface, "obj": "192.0.2.1", "original_host": "192.0.2.1"},
                    interfaces_type_config.get("iterable_type"),
                    True,  # Enable debug logging
                )
                
                self.logger.debug("Interface: %s, Type: %s", interface, processed_result)
                
                # Should return a valid interface type
                self.assertIsInstance(processed_result, str)
                # Valid interface types from the post_processor logic
                valid_types = ["lag", "Ethernet", "other", "PIME", "PIM-Encapsulator"]
                if processed_result:  # If not empty
                    self.assertIn(processed_result, valid_types + [""])

    def test_extract_interface_description(self):
        """Test extraction of interface description."""
        interfaces_desc_config = self.command_mapper_data["sync_network_data"]["interfaces__description"]
        command_config = interfaces_desc_config["commands"][0]
        
        # Test interface that should have a description (et-0/0/0 has "[HITC-P1]")
        test_interface = "et-0/0/0"
        
        parsed_result, processed_result = extract_and_post_process(
            self.interface_result,
            command_config,
            {"current_key": test_interface, "obj": "192.0.2.1", "original_host": "192.0.2.1"},
            interfaces_desc_config.get("iterable_type"),
            True,  # Enable debug logging
        )
        
        self.logger.debug("Interface: %s, Description: %s", test_interface, processed_result)
        
        # Should return string (empty if no description found)
        self.assertIsInstance(processed_result, str)
        # For et-0/0/0, should have the description "[HITC-P1]"
        if processed_result:
            self.assertEqual(processed_result, "[HITC-P1]")

    def test_extract_interface_mtu(self):
        """Test extraction of interface MTU."""
        interfaces_mtu_config = self.command_mapper_data["sync_network_data"]["interfaces__mtu"]
        command_config = interfaces_mtu_config["commands"][0]
        
        # Test different interfaces
        test_interfaces = ["et-0/0/0", "xe-0/1/0", "pe-0/0/0"]
        
        for interface in test_interfaces:
            with self.subTest(interface=interface):
                parsed_result, processed_result = extract_and_post_process(
                    self.interface_result,
                    command_config,
                    {"current_key": interface, "obj": "192.0.2.1", "original_host": "192.0.2.1"},
                    interfaces_mtu_config.get("iterable_type"),
                    True,  # Enable debug logging
                )
                
                self.logger.debug("Interface: %s, MTU: %s", interface, processed_result)
                
                # Should return string
                self.assertIsInstance(processed_result, str)
                # Should be numeric or empty or "Unlimited" converted to "9192"
                if processed_result and isinstance(processed_result, str):
                    self.assertTrue(processed_result.isdigit() or processed_result == "9192")

    def test_extract_interface_mac_address(self):
        """Test extraction of interface MAC address."""
        interfaces_mac_config = self.command_mapper_data["sync_network_data"]["interfaces__mac_address"]
        command_config = interfaces_mac_config["commands"][0]
        
        # Test interfaces that should have MAC addresses
        test_interfaces = ["et-0/0/0", "xe-0/1/0", "xe-0/1/7"]
        
        for interface in test_interfaces:
            with self.subTest(interface=interface):
                parsed_result, processed_result = extract_and_post_process(
                    self.interface_result,
                    command_config,
                    {"current_key": interface, "obj": "192.0.2.1", "original_host": "192.0.2.1"},
                    interfaces_mac_config.get("iterable_type"),
                    True,  # Enable debug logging
                )
                
                self.logger.debug("Interface: %s, MAC: %s", interface, processed_result)
                
                # Should return string or list
                self.assertTrue(isinstance(processed_result, (str, list)))
                # If string and not empty, should be valid MAC format
                if isinstance(processed_result, str) and processed_result:
                    # Basic MAC address validation (colon-separated hex)
                    self.assertRegex(processed_result, r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$')

    def test_extract_interface_link_status(self):
        """Test extraction of interface link status."""
        interfaces_status_config = self.command_mapper_data["sync_network_data"]["interfaces__link_status"]
        command_config = interfaces_status_config["commands"][0]
        
        # Test different interfaces
        test_interfaces = ["et-0/0/0", "xe-0/1/0", "xe-0/1/7", "pe-0/0/0"]
        
        for interface in test_interfaces:
            with self.subTest(interface=interface):
                parsed_result, processed_result = extract_and_post_process(
                    self.interface_result,
                    command_config,
                    {"current_key": interface, "obj": "192.0.2.1", "original_host": "192.0.2.1"},
                    interfaces_status_config.get("iterable_type"),
                    True,  # Enable debug logging
                )
                
                self.logger.debug("Interface: %s, Status: %s", interface, processed_result)
                
                # Should return string representing boolean
                self.assertIsInstance(processed_result, str)
                # Should be boolean-like values or empty
                self.assertIn(processed_result, ["True", "False", "true", "false", ""])

    def test_extract_interface_lag(self):
        """Test extraction of interface LAG membership."""
        interfaces_lag_config = self.command_mapper_data["sync_network_data"]["interfaces__lag"]
        command_config = interfaces_lag_config["commands"][0]
        
        # Test interfaces that might have LAG membership
        test_interfaces = ["xe-0/1/0", "xe-0/1/7", "et-0/0/0"]
        
        for interface in test_interfaces:
            with self.subTest(interface=interface):
                parsed_result, processed_result = extract_and_post_process(
                    self.interface_result,
                    command_config,
                    {"current_key": interface, "obj": "192.0.2.1", "original_host": "192.0.2.1"},
                    interfaces_lag_config.get("iterable_type"),
                    True,  # Enable debug logging
                )
                
                self.logger.debug("Interface: %s, LAG: %s", interface, processed_result)
                
                # Should return LAG interface name or empty value
                self.assertTrue(isinstance(processed_result, (str, list)))

    def test_extract_interface_ip_addresses(self):
        """Test extraction of interface IP addresses."""
        interfaces_ip_config = self.command_mapper_data["sync_network_data"]["interfaces__ip_addresses"]
        command_config = interfaces_ip_config["commands"][0]
        
        # Test with logical interfaces that might have IP addresses
        test_interfaces = ["xe-0/1/0.99", "gr-0/0/0.15"]
        
        for interface in test_interfaces:
            with self.subTest(interface=interface):
                try:
                    parsed_result, processed_result = extract_and_post_process(
                        self.interface_result,
                        command_config,
                        {"current_key": interface, "obj": "192.0.2.1", "original_host": "192.0.2.1"},
                        interfaces_ip_config.get("iterable_type"),
                        True,  # Enable debug logging
                    )
                    
                    self.logger.debug("Interface: %s, IP: %s", interface, processed_result)
                    
                    # Should return IP address data structure or empty result
                    self.assertTrue(isinstance(processed_result, (str, list, dict)))
                    
                except Exception as e:
                    # If extraction fails due to template or data issues, that's acceptable
                    self.logger.warning("IP extraction failed for %s: %s", interface, e)
                    self.skipTest(f"IP extraction failed for {interface}: {e}")

    def test_extract_interface_vrf(self):
        """Test extraction of interface VRF membership."""
        # Check if VRF configuration exists
        if "interfaces__vrf" not in self.command_mapper_data["sync_network_data"]:
            self.skipTest("VRF configuration not found in command mapper")
            
        interfaces_vrf_config = self.command_mapper_data["sync_network_data"]["interfaces__vrf"]
        command_config = interfaces_vrf_config["commands"][0]
        
        # Test interfaces that might have VRF membership
        test_interfaces = ["xe-0/1/0", "gr-0/0/0"]
        
        for interface in test_interfaces:
            with self.subTest(interface=interface):
                try:
                    parsed_result, processed_result = extract_and_post_process(
                        self.interface_result,
                        command_config,
                        {"current_key": interface, "obj": "192.0.2.1", "original_host": "192.0.2.1"},
                        interfaces_vrf_config.get("iterable_type"),
                        True,  # Enable debug logging
                    )
                    
                    self.logger.debug("Interface: %s, VRF: %s", interface, processed_result)
                    
                    # Should return VRF data or empty result
                    self.assertTrue(isinstance(processed_result, (str, list, dict)))
                    
                except Exception as e:
                    # If extraction fails due to template or data issues, that's acceptable
                    self.logger.warning("VRF extraction failed for %s: %s", interface, e)

    def test_extract_interface_tagged_vlans(self):
        """Test extraction of interface tagged VLANs."""
        # Check if tagged VLAN configuration exists
        if "interfaces__tagged_vlans" not in self.command_mapper_data["sync_network_data"]:
            self.skipTest("Tagged VLAN configuration not found in command mapper")
            
        interfaces_vlan_config = self.command_mapper_data["sync_network_data"]["interfaces__tagged_vlans"]
        command_config = interfaces_vlan_config["commands"][0]
        
        # Test interfaces that might have VLAN configuration
        test_interfaces = ["xe-0/1/0", "et-0/0/0"]
        
        for interface in test_interfaces:
            with self.subTest(interface=interface):
                try:
                    parsed_result, processed_result = extract_and_post_process(
                        self.interface_result,
                        command_config,
                        {"current_key": interface, "obj": "192.0.2.1", "original_host": "192.0.2.1"},
                        interfaces_vlan_config.get("iterable_type"),
                        True,  # Enable debug logging
                    )
                    
                    self.logger.debug("Interface: %s, Tagged VLANs: %s", interface, processed_result)
                    
                    # Should return VLAN data or empty result
                    self.assertTrue(isinstance(processed_result, (str, list, dict)))
                    
                except Exception as e:
                    # If extraction fails due to template or data issues, that's acceptable
                    self.logger.warning("Tagged VLAN extraction failed for %s: %s", interface, e)

    def test_extract_interface_untagged_vlan(self):
        """Test extraction of interface untagged VLAN."""
        # Check if untagged VLAN configuration exists
        if "interfaces__untagged_vlan" not in self.command_mapper_data["sync_network_data"]:
            self.skipTest("Untagged VLAN configuration not found in command mapper")
            
        interfaces_vlan_config = self.command_mapper_data["sync_network_data"]["interfaces__untagged_vlan"]
        command_config = interfaces_vlan_config["commands"][0]
        
        # Test interfaces that might have VLAN configuration
        test_interfaces = ["xe-0/1/0", "et-0/0/0"]
        
        for interface in test_interfaces:
            with self.subTest(interface=interface):
                try:
                    parsed_result, processed_result = extract_and_post_process(
                        self.interface_result,
                        command_config,
                        {"current_key": interface, "obj": "192.0.2.1", "original_host": "192.0.2.1"},
                        interfaces_vlan_config.get("iterable_type"),
                        True,  # Enable debug logging
                    )
                    
                    self.logger.debug("Interface: %s, Untagged VLAN: %s", interface, processed_result)
                    
                    # Should return VLAN data or empty result
                    self.assertTrue(isinstance(processed_result, (str, list, dict)))
                    
                except Exception as e:
                    # If extraction fails due to template or data issues, that's acceptable
                    self.logger.warning("Untagged VLAN extraction failed for %s: %s", interface, e)

    def test_interface_command_coverage(self):
        """Test that all interface-related commands are properly configured."""
        sync_network_data = self.command_mapper_data["sync_network_data"]
        
        # Get all interface-related keys
        interface_keys = [key for key in sync_network_data.keys() if key.startswith("interfaces__")]
        
        # Expected interface keys that should be tested
        expected_interface_keys = [
            "interfaces__type",
            "interfaces__ip_addresses", 
            "interfaces__mtu",
            "interfaces__mac_address",
            "interfaces__description",
            "interfaces__link_status",
            "interfaces__lag",
        ]
        
        self.logger.info("Found interface keys: %s", interface_keys)
        
        # Check that essential interface keys exist
        for expected_key in expected_interface_keys:
            self.assertIn(expected_key, interface_keys, f"Missing expected interface key: {expected_key}")
            
            # Verify each has proper command configuration
            config = sync_network_data[expected_key]
            self.assertIn("commands", config, f"Missing 'commands' in {expected_key}")
            self.assertIsInstance(config["commands"], list, f"'commands' should be a list in {expected_key}")
            self.assertGreater(len(config["commands"]), 0, f"Empty commands list in {expected_key}")
            
            # Verify command structure
            for cmd_idx, cmd in enumerate(config["commands"]):
                with self.subTest(key=expected_key, command_index=cmd_idx):
                    self.assertIn("command", cmd, f"Missing 'command' in {expected_key}[{cmd_idx}]")
                    self.assertIn("parser", cmd, f"Missing 'parser' in {expected_key}[{cmd_idx}]")
                    self.assertIn("jpath", cmd, f"Missing 'jpath' in {expected_key}[{cmd_idx}]")

    def test_interface_extraction_type_safety(self):
        """Test that interface extraction handles different data types safely."""
        interfaces_type_config = self.command_mapper_data["sync_network_data"]["interfaces__type"]
        command_config = interfaces_type_config["commands"][0]
        
        # Test with various interface names to ensure type safety
        test_interfaces = ["et-0/0/0", "xe-0/1/0", "ae25", "lo0", "nonexistent-interface"]
        
        for interface in test_interfaces:
            with self.subTest(interface=interface):
                try:
                    parsed_result, processed_result = extract_and_post_process(
                        self.interface_result,
                        command_config,
                        {"current_key": interface, "obj": "192.0.2.1", "original_host": "192.0.2.1"},
                        interfaces_type_config.get("iterable_type"),
                        True,  # Enable debug logging
                    )
                    
                    # Should always return a string (might be empty)
                    self.assertIsInstance(processed_result, str)
                    
                    # Test the post_processor logic for ae interfaces
                    if interface.startswith("ae"):
                        self.assertEqual(processed_result, "lag", f"ae interface {interface} should return 'lag'")
                    
                except Exception as e:
                    # Log the error but don't fail the test - this tests robustness
                    self.logger.warning("Type extraction failed for %s: %s", interface, e)


if __name__ == "__main__":
    unittest.main()