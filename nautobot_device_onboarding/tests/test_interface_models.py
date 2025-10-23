from nautobot.apps.testing import TransactionTestCase, create_job_result_and_run_job,  TestCase
from nautobot.dcim.models import Device, Interface
from nautobot.extras.choices import JobResultStatusChoices

from netnam_cms_core.models import JuniperInterfaceUnit

from nautobot_device_onboarding.tests import utils
from nautobot_device_onboarding.tests.utils import setup_logging, cleanup_logging

class JuniperInterfaceUnitTestCase(TestCase):
    """Test cases for Juniper interface model handling."""

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        self.logger, self.etl_logger, self.unified_handler = setup_logging(__name__)
        self.logger.info("\nSetup %s\n", self._testMethodName)
    
    def tearDown(self) -> None:
        """Clean up unified logging setup."""
        cleanup_logging(self.logger, self.etl_logger, self.unified_handler)
        # return super().tearDown()

    def testLoadInterfaceUnits(self):
        """Test loading Juniper interface units from device."""
        devices = Device.objects.all()
        for device in devices:
            self.logger.info(f" Device: {device.name}")
            interfaces = Interface.objects.filter(device=device)
            for interface in interfaces:
                self.logger.info(" Interface: %s", interface.name)
                juniper_units = JuniperInterfaceUnit.objects.filter(interface=interface)
                for unit in juniper_units:
                    self.logger.info(
                        "Device: %s, Interface: %s",
                        device.name,
                        interface.name,                     
                    )
        