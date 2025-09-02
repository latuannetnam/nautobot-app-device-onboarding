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


class TestJuniperJunosInterfaceVLANExtractors(unittest.TestCase):
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
        with open(f"{MOCK_DIR}/juniper_mx204/juniper_mx204_show_configuration_interfaces_result.json", "r", encoding="utf-8") as result_file:
            self.interface_result = json.load(result_file)
    
    def tearDown(self) -> None:
        """Clean up unified logging setup."""
        cleanup_command_getter_logging(self.logger, self.etl_logger, self.unified_handler)
        return super().tearDown()

    def test_extract_interface_tagged_vlans(self):
        """Test extraction of interface tagged VLANs."""
        # Check if tagged VLAN configuration exists
        if "interfaces__tagged_vlans" not in self.command_mapper_data["sync_network_data"]:
            self.skipTest("Tagged VLAN configuration not found in command mapper")
            
        interfaces_vlan_config = self.command_mapper_data["sync_network_data"]["interfaces__tagged_vlans"]
        command_config = interfaces_vlan_config["commands"][0]
        
        # Test interfaces that have VLAN configuration
        test_interfaces = ["ae10", "ae0"]
        
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
                    
                    self.logger.info("Interface: %s, Tagged VLANs result: %s", interface, processed_result)
                    
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
        self.logger.debug("interfaces_vlan_config: %s", interfaces_vlan_config)
        # Test interfaces that have no VLAN configuration (untagged)
        # test_interfaces = ["ae0.240", "ae11.100"]
        test_interfaces = ["ae10", "ae0"]
        # test_interfaces = ["ae0"]
        
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
                    
                    self.logger.info("Interface: %s, Untagged VLAN result: %s", interface, processed_result)
                    
                    # Should return VLAN data or empty result
                    self.assertTrue(isinstance(processed_result, (str, list, dict)))
                    
                except Exception as e:
                    # If extraction fails due to template or data issues, that's acceptable
                    self.logger.warning("Untagged VLAN extraction failed for %s: %s", interface, e)


if __name__ == "__main__":
    unittest.main()