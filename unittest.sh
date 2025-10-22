# invoke unittest -f -k -s -v
# invoke unittest -k -s -v
# invoke unittest --no-buffer -f -k -s -v -l nautobot_device_onboarding.tests.test_command_getter_junos
# invoke unittest --no-buffer -f -k -s -v -l nautobot_device_onboarding.tests.test_command_mapper_juniper_junos
# invoke unittest --no-buffer -f -k -s -v -l nautobot_device_onboarding.tests.test_command_getter_junos.TestJuniperJunosCommandGetterExtraction.test_extract_interface_description
# invoke unittest --no-buffer -f -k -s -v -l nautobot_device_onboarding.tests.test_command_getter_junos
# invoke unittest --no-buffer -f -k -s -v -l nautobot_device_onboarding.tests.test_command_getter_junos_interfaces
# invoke unittest --no-buffer -f -k -s -v -l nautobot_device_onboarding.tests.test_command_getter_junos_interfaces.TestJuniperJunosInterfaceExtractors
# poetry run invoke unittest --no-buffer -f -k -s -v -l nautobot_device_onboarding.tests.test_refactor_jobs.SSOTSyncDevicesTestCase
poetry run invoke unittest --no-buffer -f -s -v -l nautobot_device_onboarding.tests.test_refactor_jobs.SSOTSyncDevicesTestCase