"""Test for nornir plays in command_getter."""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

import yaml
from nautobot.core.testing import TransactionTestCase
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.models import Secret, SecretsGroup, SecretsGroupAssociation

from nautobot_device_onboarding.nornir_plays.command_getter import _get_commands_to_run, _parse_credentials
from nautobot_device_onboarding.nornir_plays.logger import NornirLogger
import logging
logger = logging.getLogger(__name__)
logger.level = logging.DEBUG

MOCK_DIR = os.path.join("nautobot_device_onboarding", "tests", "mock")


class TestGetCommandsToRunJunOS(unittest.TestCase):
    """Test the ability to get the proper commands to run."""

    def setUp(self):
        # stream_handler = logging.StreamHandler(sys.stdout)
        # logger.addHandler(stream_handler)
        self.logger = logging.getLogger(__name__)
        self.stream_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(self.stream_handler)
        self.logger.info("Setup %s\n", self._testMethodName)
        # logger.info("Testing get_commands_to_run for JunOS")

        with open(f"{MOCK_DIR}/command_mappers/mock_cisco_ios.yml", "r", encoding="utf-8") as mock_file_data:
            self.expected_data = yaml.safe_load(mock_file_data)

    def tearDown(self) -> None:
        self.logger.removeHandler(self.stream_handler)
        return super().tearDown()

    def test_deduplicate_command_list_sync_devices_junos(self):
        """Test dedup on sync_devices ssot job."""
        self.logger.info("Starting test  %s\n", self._testMethodName)
        get_commands_to_run = _get_commands_to_run(
            self.expected_data["sync_devices"],
            sync_vlans=False,
            sync_vrfs=False,
            sync_cables=False,
            sync_software_version=False,
        )
        expected_commands_to_run = [
            {"command": "show version", "jpath": "[*].hostname", "parser": "textfsm"},
            {
                "command": "show interfaces",
                "jpath": "[?ip_address=='{{ obj }}'].{name: interface, enabled: link_status}",
                "parser": "textfsm",
                "post_processor": "{{ (obj | selectattr('enabled', 'eq', 'up') | list | first ).name }}",
            },
        ]

        self.logger.info("Commands to run: %s expected: %s", len(get_commands_to_run), len(expected_commands_to_run))
        self.assertEqual(get_commands_to_run, expected_commands_to_run)

    def test_deduplicate_command_list_sync_data_no_vrfs_no_vlans_junos(self):
        """Test dedup on sync_network_data ssot job."""        
        get_commands_to_run = _get_commands_to_run(
            self.expected_data["sync_network_data"],
            sync_vlans=False,
            sync_vrfs=False,
            sync_cables=False,
            sync_software_version=False,
        )
        expected_commands_to_run = [
            {"command": "show version", "parser": "textfsm", "jpath": "[*].serial[]"},
            {
                "command": "show interfaces",
                "parser": "textfsm",
                "jpath": "[*].interface",
                "post_processor": "{% set result={} %}{% for interface in obj %}{{ result.update({interface: {}}) or '' }}{% endfor %}{{ result | tojson }}",
            },
            {
                "command": "show interfaces switchport",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key | abbreviated_interface_name }}'].{admin_mode: admin_mode, mode: mode, trunking_vlans: trunking_vlans}",
                "post_processor": "{{ obj | interface_mode_logic }}",
                "iterable_type": "str",
            },
            {
                "command": "show etherchannel summary",
                "parser": "textfsm",
                "jpath": "[?contains(@.member_interface, `{{ current_key | abbreviated_interface_name }}`)].bundle_name",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | canonical_interface_name }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "str",
            },
        ]
        self.assertEqual(get_commands_to_run, expected_commands_to_run)

    def test_deduplicate_command_list_sync_data_with_vrfs_no_vlans_junos(self):
        """Test dedup on sync_network_data ssot job."""
        get_commands_to_run = _get_commands_to_run(
            self.expected_data["sync_network_data"],
            sync_vlans=False,
            sync_vrfs=True,
            sync_cables=False,
            sync_software_version=False,
        )
        expected_commands_to_run = [
            {"command": "show version", "parser": "textfsm", "jpath": "[*].serial[]"},
            {
                "command": "show interfaces",
                "parser": "textfsm",
                "jpath": "[*].interface",
                "post_processor": "{% set result={} %}{% for interface in obj %}{{ result.update({interface: {}}) or '' }}{% endfor %}{{ result | tojson }}",
            },
            {
                "command": "show interfaces switchport",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key | abbreviated_interface_name }}'].{admin_mode: admin_mode, mode: mode, trunking_vlans: trunking_vlans}",
                "post_processor": "{{ obj | interface_mode_logic }}",
                "iterable_type": "str",
            },
            {
                "command": "show etherchannel summary",
                "parser": "textfsm",
                "jpath": "[?contains(@.member_interface, `{{ current_key | abbreviated_interface_name }}`)].bundle_name",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | canonical_interface_name }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "str",
            },
            {
                "command": "show ip interface",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key }}'].{name:vrf}",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | key_exist_or_default('name') | tojson }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "dict",
            },
        ]
        self.assertEqual(get_commands_to_run, expected_commands_to_run)

    def test_deduplicate_command_list_sync_data_no_vrfs_with_vlans_junos(self):
        """Test dedup on sync_network_data ssot job."""
        get_commands_to_run = _get_commands_to_run(
            self.expected_data["sync_network_data"],
            sync_vlans=True,
            sync_vrfs=False,
            sync_cables=False,
            sync_software_version=False,
        )
        expected_commands_to_run = [
            {"command": "show vlan", "parser": "textfsm", "jpath": "[*].{id: vlan_id, name: vlan_name}"},
            {"command": "show version", "parser": "textfsm", "jpath": "[*].serial[]"},
            {
                "command": "show interfaces",
                "parser": "textfsm",
                "jpath": "[*].interface",
                "post_processor": "{% set result={} %}{% for interface in obj %}{{ result.update({interface: {}}) or '' }}{% endfor %}{{ result | tojson }}",
            },
            {
                "command": "show interfaces switchport",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key | abbreviated_interface_name }}'].{admin_mode: admin_mode, mode: mode, trunking_vlans: trunking_vlans}",
                "post_processor": "{{ obj | interface_mode_logic }}",
                "iterable_type": "str",
            },
            {
                "command": "show etherchannel summary",
                "parser": "textfsm",
                "jpath": "[?contains(@.member_interface, `{{ current_key | abbreviated_interface_name }}`)].bundle_name",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | canonical_interface_name }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "str",
            },
        ]
        self.assertEqual(get_commands_to_run, expected_commands_to_run)

    def test_deduplicate_command_list_sync_data_with_vrfs_and_vlans_junos(self):
        """Test dedup on sync_network_data ssot job."""
        get_commands_to_run = _get_commands_to_run(
            self.expected_data["sync_network_data"],
            sync_vlans=True,
            sync_vrfs=True,
            sync_cables=False,
            sync_software_version=False,
        )
        expected_commands_to_run = [
            {"command": "show vlan", "parser": "textfsm", "jpath": "[*].{id: vlan_id, name: vlan_name}"},
            {"command": "show version", "parser": "textfsm", "jpath": "[*].serial[]"},
            {
                "command": "show interfaces",
                "parser": "textfsm",
                "jpath": "[*].interface",
                "post_processor": "{% set result={} %}{% for interface in obj %}{{ result.update({interface: {}}) or '' }}{% endfor %}{{ result | tojson }}",
            },
            {
                "command": "show interfaces switchport",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key | abbreviated_interface_name }}'].{admin_mode: admin_mode, mode: mode, trunking_vlans: trunking_vlans}",
                "post_processor": "{{ obj | interface_mode_logic }}",
                "iterable_type": "str",
            },
            {
                "command": "show etherchannel summary",
                "parser": "textfsm",
                "jpath": "[?contains(@.member_interface, `{{ current_key | abbreviated_interface_name }}`)].bundle_name",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | canonical_interface_name }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "str",
            },
            {
                "command": "show ip interface",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key }}'].{name:vrf}",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | key_exist_or_default('name') | tojson }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "dict",
            },
        ]
        self.assertEqual(get_commands_to_run, expected_commands_to_run)

    def test_deduplicate_command_list_sync_data_cables_junos(self):
        get_commands_to_run = _get_commands_to_run(
            self.expected_data["sync_network_data"],
            sync_vlans=False,
            sync_vrfs=False,
            sync_cables=True,
            sync_software_version=False,
        )
        expected_commands_to_run = [
            {"command": "show version", "parser": "textfsm", "jpath": "[*].serial[]"},
            {
                "command": "show interfaces",
                "parser": "textfsm",
                "jpath": "[*].interface",
                "post_processor": "{% set result={} %}{% for interface in obj %}{{ result.update({interface: {}}) or '' }}{% endfor %}{{ result | tojson }}",
            },
            {
                "command": "show interfaces switchport",
                "parser": "textfsm",
                "jpath": "[?interface=='{{ current_key | abbreviated_interface_name }}'].{admin_mode: admin_mode, mode: mode, trunking_vlans: trunking_vlans}",
                "post_processor": "{{ obj | interface_mode_logic }}",
                "iterable_type": "str",
            },
            {
                "command": "show etherchannel summary",
                "parser": "textfsm",
                "jpath": "[?contains(@.member_interface, `{{ current_key | abbreviated_interface_name }}`)].bundle_name",
                "post_processor": "{% if obj | length > 0 %}{{ obj[0] | canonical_interface_name }}{% else %}{{ obj }}{% endif %}",
                "iterable_type": "str",
            },
            {
                "command": "show cdp neighbors detail",
                "parser": "textfsm",
                "jpath": "[*].{local_interface:local_interface, remote_interface:neighbor_interface, remote_device:neighbor_name}",
            },
        ]
        self.assertEqual(get_commands_to_run, expected_commands_to_run)


@patch("nautobot_device_onboarding.nornir_plays.command_getter.NornirLogger", MagicMock())
class TestSSHCredParsingJunOS(TransactionTestCase):
    """Tests against the _parse_credentials helper function."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        username_secret, _ = Secret.objects.get_or_create(
            name="username", provider="environment-variable", parameters={"variable": "DEVICE_USER"}
        )
        password_secret, _ = Secret.objects.get_or_create(
            name="password", provider="environment-variable", parameters={"variable": "DEVICE_PASS"}
        )
        self.secrets_group, _ = SecretsGroup.objects.get_or_create(name="test secrets group")
        SecretsGroupAssociation.objects.get_or_create(
            secrets_group=self.secrets_group,
            secret=username_secret,
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
        )
        SecretsGroupAssociation.objects.get_or_create(
            secrets_group=self.secrets_group,
            secret=password_secret,
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
        )

    @patch.dict(os.environ, {"DEVICE_USER": "admin", "DEVICE_PASS": "worstP$$w0rd"})
    def test_parse_user_and_pass_junos(self):
        """Extract correct user and password from secretgroup env-vars"""
        assert _parse_credentials(credentials=self.secrets_group, logger=NornirLogger(job_result={}, log_level=1)) == (
            "admin",
            "worstP$$w0rd",
        )

    @patch.dict(os.environ, {"DEVICE_USER": "admin"})
    def test_parse_user_missing_pass_junos(self):
        """Extract just the username without bailing out if password is missing"""
        mock_job_result = MagicMock()
        assert _parse_credentials(
            credentials=self.secrets_group, logger=NornirLogger(job_result=mock_job_result, log_level=1)
        ) == ("admin", None)
        mock_job_result.log.assert_called_with("Missing credentials for ['password']", level_choice="debug")

    @patch(
        "nautobot_device_onboarding.nornir_plays.command_getter.settings",
        MagicMock(NAPALM_USERNAME="napalm_admin", NAPALM_PASSWORD="napalamP$$w0rd"),
    )
    def test_parse_napalm_creds_junos(self):
        """When no secrets group is provided, fallback to napalm creds"""
        assert _parse_credentials(credentials=None, logger=NornirLogger(job_result=None, log_level=1)) == (
            "napalm_admin",
            "napalamP$$w0rd",
        )
