"""Test for Juniper JunOS command mapper configuration."""

import os
import unittest
import yaml

from nautobot_device_onboarding.nornir_plays.command_getter import _get_commands_to_run

MOCK_DIR = os.path.join("nautobot_device_onboarding", "tests", "mock")


class TestJuniperJunosCommandMapper(unittest.TestCase):
    """Test the Juniper JunOS command mapper configuration."""

    def setUp(self):
        """Set up test case with Juniper JunOS command mapper data."""
        with open(f"{MOCK_DIR}/command_mappers/juniper_junos.yml", "r", encoding="utf-8") as mapper_file:
            self.command_mapper_data = yaml.safe_load(mapper_file)

    def test_sync_devices_command_deduplication(self):
        """Test command deduplication for sync_devices job type."""
        commands_to_run = _get_commands_to_run(
            self.command_mapper_data["sync_devices"],
            sync_vlans=False,
            sync_vrfs=False,
            sync_cables=False,
            sync_software_version=False,
        )
        
        expected_commands = [
            {
                "command": "show system information | display json",
                "parser": "none",
                "jpath": '"system-information"[]."host-name"[].data',
                "post_processor": "{{ obj | unique | first }}"
            },
            {
                "command": "show interfaces terse | display json",
                "parser": "none",
                "jpath": '"interface-information"[]."physical-interface"[]."logical-interface"[].{name: name[].data, ip: "address-family"[]."interface-address"[]."ifa-local"[].data}',
                "post_processor": "{% for entry in obj %}{% if entry['ip'] %}{% for ipaddr in entry['ip'] %}{% if original_host in ipaddr %}{{ entry['name'] | first }}{% endif %}{% endfor %}{% endif %}{% endfor %}"
            },
            {
                "command": "show configuration interfaces | display json",
                "parser": "none",
                "jpath": "configuration.interfaces.interface[].unit[?family.inet.address[?contains(name, `{{ obj }}`)]][].family.*.address[][].name",
                "post_processor": "{{ obj[0].split('/')[1] }}",
                "iterable_type": "int"
            }
        ]
        
        self.assertEqual(len(commands_to_run), 3)
        # Verify that show system information command is deduplicated (used for hostname, serial, device_type)
        system_info_commands = [cmd for cmd in commands_to_run if "show system information" in cmd["command"]]
        self.assertEqual(len(system_info_commands), 1)
        
        # Verify specific command structure
        for expected_cmd in expected_commands:
            self.assertIn(expected_cmd, commands_to_run)

    def test_sync_devices_command_deduplication_with_software_version(self):
        """Test command deduplication for sync_devices job type with software version."""
        commands_to_run = _get_commands_to_run(
            self.command_mapper_data["sync_devices"],
            sync_vlans=False,
            sync_vrfs=False,
            sync_cables=False,
            sync_software_version=True,
        )
        
        # Should still have only one "show system information" command even with software version enabled
        system_info_commands = [cmd for cmd in commands_to_run if "show system information" in cmd["command"]]
        self.assertEqual(len(system_info_commands), 1)

    def test_sync_network_data_no_options(self):
        """Test command generation for sync_network_data with no additional options."""
        commands_to_run = _get_commands_to_run(
            self.command_mapper_data["sync_network_data"],
            sync_vlans=False,
            sync_vrfs=False,
            sync_cables=False,
            sync_software_version=False,
        )
        
        # Should include system information, configuration interfaces, and interfaces commands
        command_names = [cmd["command"] for cmd in commands_to_run]
        
        self.assertIn("show system information | display json", command_names)
        self.assertIn("show configuration interfaces | display json", command_names)
        self.assertIn("show interfaces | display json", command_names)
        
        # Should NOT include VLAN, VRF, or cable commands
        self.assertNotIn("show vlans | display json", command_names)
        self.assertNotIn("show interfaces routing-instance all terse | display json", command_names)
        self.assertNotIn("show lldp neighbors | display json", command_names)

    def test_sync_network_data_with_vlans(self):
        """Test command generation for sync_network_data with VLAN sync enabled."""
        commands_to_run = _get_commands_to_run(
            self.command_mapper_data["sync_network_data"],
            sync_vlans=True,
            sync_vrfs=False,
            sync_cables=False,
            sync_software_version=False,
        )
        
        command_names = [cmd["command"] for cmd in commands_to_run]
        
        # Should include VLAN command
        self.assertIn("show vlans | display json", command_names)
        
        # Should NOT include VRF or cable commands
        self.assertNotIn("show interfaces routing-instance all terse | display json", command_names)
        self.assertNotIn("show lldp neighbors | display json", command_names)

    def test_sync_network_data_with_vrfs(self):
        """Test command generation for sync_network_data with VRF sync enabled."""
        commands_to_run = _get_commands_to_run(
            self.command_mapper_data["sync_network_data"],
            sync_vlans=False,
            sync_vrfs=True,
            sync_cables=False,
            sync_software_version=False,
        )
        
        command_names = [cmd["command"] for cmd in commands_to_run]
        
        # Should include VRF command
        self.assertIn("show interfaces routing-instance all terse | display json", command_names)
        
        # Should NOT include VLAN or cable commands
        self.assertNotIn("show vlans | display json", command_names)
        self.assertNotIn("show lldp neighbors | display json", command_names)

    def test_sync_network_data_with_cables(self):
        """Test command generation for sync_network_data with cable sync enabled."""
        commands_to_run = _get_commands_to_run(
            self.command_mapper_data["sync_network_data"],
            sync_vlans=False,
            sync_vrfs=False,
            sync_cables=True,
            sync_software_version=False,
        )
        
        command_names = [cmd["command"] for cmd in commands_to_run]
        
        # Should include cable discovery command
        self.assertIn("show lldp neighbors | display json", command_names)
        
        # Should NOT include VLAN or VRF commands
        self.assertNotIn("show vlans | display json", command_names)
        self.assertNotIn("show interfaces routing-instance all terse | display json", command_names)

    def test_sync_network_data_with_software_version(self):
        """Test command generation for sync_network_data with software version sync enabled."""
        commands_to_run = _get_commands_to_run(
            self.command_mapper_data["sync_network_data"],
            sync_vlans=False,
            sync_vrfs=False,
            sync_cables=False,
            sync_software_version=True,
        )
        
        # System information command should be present (for both serial and software version)
        system_info_commands = [cmd for cmd in commands_to_run if "show system information" in cmd["command"]]
        self.assertEqual(len(system_info_commands), 1)

    def test_sync_network_data_all_options_enabled(self):
        """Test command generation for sync_network_data with all options enabled."""
        commands_to_run = _get_commands_to_run(
            self.command_mapper_data["sync_network_data"],
            sync_vlans=True,
            sync_vrfs=True,
            sync_cables=True,
            sync_software_version=True,
        )
        
        command_names = [cmd["command"] for cmd in commands_to_run]
        
        # Should include all optional commands
        self.assertIn("show vlans | display json", command_names)
        self.assertIn("show interfaces routing-instance all terse | display json", command_names)
        self.assertIn("show lldp neighbors | display json", command_names)
        
        # System information should still be deduplicated
        system_info_commands = [cmd for cmd in commands_to_run if "show system information" in cmd["command"]]
        self.assertEqual(len(system_info_commands), 1)

    def test_command_mapper_structure_validation(self):
        """Test that the command mapper has the expected structure."""
        # Verify top-level sections exist
        self.assertIn("sync_devices", self.command_mapper_data)
        self.assertIn("sync_network_data", self.command_mapper_data)
        
        # Verify sync_devices required fields
        sync_devices = self.command_mapper_data["sync_devices"]
        required_device_fields = ["hostname", "serial", "device_type", "mgmt_interface", "mask_length"]
        for field in required_device_fields:
            self.assertIn(field, sync_devices)
            self.assertIn("commands", sync_devices[field])
            self.assertIsInstance(sync_devices[field]["commands"], list)
            self.assertGreater(len(sync_devices[field]["commands"]), 0)

    def test_interfaces_root_key_configuration(self):
        """Test that interfaces field is properly configured as root_key."""
        sync_network_data = self.command_mapper_data["sync_network_data"]
        
        # Verify interfaces is configured as root_key
        self.assertIn("interfaces", sync_network_data)
        self.assertTrue(sync_network_data["interfaces"].get("root_key", False))
        
        # Verify interface sub-fields exist
        interface_fields = [
            "interfaces__type",
            "interfaces__ip_addresses", 
            "interfaces__mtu",
            "interfaces__mac_address",
            "interfaces__description",
            "interfaces__link_status",
            "interfaces__802.1Q_mode",
            "interfaces__lag",
            "interfaces__vrf",
            "interfaces__tagged_vlans",
            "interfaces__untagged_vlan"
        ]
        
        for field in interface_fields:
            self.assertIn(field, sync_network_data)

    def test_parser_types_validation(self):
        """Test that command parser types are valid."""
        valid_parsers = ["none", "textfsm"]
        
        # Check sync_devices parsers
        for field_name, field_config in self.command_mapper_data["sync_devices"].items():
            for command in field_config["commands"]:
                self.assertIn(command["parser"], valid_parsers, 
                    f"Invalid parser '{command['parser']}' in sync_devices.{field_name}")
        
        # Check sync_network_data parsers
        for field_name, field_config in self.command_mapper_data["sync_network_data"].items():
            if "commands" in field_config:
                for command in field_config["commands"]:
                    self.assertIn(command["parser"], valid_parsers,
                        f"Invalid parser '{command['parser']}' in sync_network_data.{field_name}")

    def test_jpath_expressions_exist(self):
        """Test that all commands have jpath expressions defined."""
        # Check sync_devices
        for field_name, field_config in self.command_mapper_data["sync_devices"].items():
            for command in field_config["commands"]:
                self.assertIn("jpath", command, 
                    f"Missing jpath in sync_devices.{field_name}")
                self.assertIsInstance(command["jpath"], str)
                self.assertGreater(len(command["jpath"]), 0)
        
        # Check sync_network_data
        for field_name, field_config in self.command_mapper_data["sync_network_data"].items():
            if "commands" in field_config:
                for command in field_config["commands"]:
                    self.assertIn("jpath", command,
                        f"Missing jpath in sync_network_data.{field_name}")
                    self.assertIsInstance(command["jpath"], str)
                    self.assertGreater(len(command["jpath"]), 0)

    def test_post_processor_configuration(self):
        """Test that post processors are properly configured where needed."""
        # Fields that should have post processors
        fields_with_processors = [
            ("sync_devices", "hostname"),
            ("sync_devices", "serial"), 
            ("sync_devices", "device_type"),
            ("sync_devices", "mgmt_interface"),
            ("sync_devices", "mask_length"),
        ]
        
        for section, field in fields_with_processors:
            field_config = self.command_mapper_data[section][field]
            for command in field_config["commands"]:
                if "post_processor" in command:
                    self.assertIsInstance(command["post_processor"], str)
                    self.assertGreater(len(command["post_processor"]), 0)

    def test_iterable_type_configuration(self):
        """Test that iterable_type is properly configured where needed."""
        # Check that mask_length has iterable_type: int
        mask_length_config = self.command_mapper_data["sync_devices"]["mask_length"]
        self.assertEqual(mask_length_config["commands"][0].get("iterable_type"), "int")
        
        # Check network data fields with iterable types
        network_data = self.command_mapper_data["sync_network_data"]
        
        # Verify specific iterable types
        self.assertEqual(network_data["interfaces__type"]["commands"][0].get("iterable_type"), "str")
        self.assertEqual(network_data["interfaces__mtu"]["commands"][0].get("iterable_type"), "str")
        self.assertEqual(network_data["interfaces__description"]["commands"][0].get("iterable_type"), "str")
        self.assertEqual(network_data["interfaces__vrf"]["commands"][0].get("iterable_type"), "dict")
        self.assertEqual(network_data["cables"]["commands"][0].get("iterable_type"), "dict")