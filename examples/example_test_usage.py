"""Example test file showing how to use the logging utilities from utils.py

This demonstrates how other test files can import and use the unified logging
functions that were extracted to nautobot_device_onboarding.tests.utils.
"""

import unittest
from nautobot_device_onboarding.tests.utils import setup_command_getter_logging, cleanup_command_getter_logging


class ExampleTestUsingUtilsLogging(unittest.TestCase):
    """Example test class showing direct usage of utils logging functions."""
    
    def setUp(self):
        """Set up logging using imported utility functions."""
        self.logger, self.etl_logger, self.handler = setup_command_getter_logging(__name__)
        self.logger.info("Example test setup completed")
    
    def tearDown(self):
        """Clean up logging using imported utility functions.""" 
        cleanup_command_getter_logging(self.logger, self.etl_logger, self.handler)
        
    def test_example_with_logging(self):
        """Example test method that uses unified logging."""
        self.logger.info("Running example test")
        self.etl_logger.debug("This would be logged by ETL processes")
        
        # Your test logic here
        self.assertTrue(True)
        
        self.logger.info("Example test completed successfully")


# Alternative approach using the BaseCommandGetterTest class
from nautobot_device_onboarding.tests.test_command_getter_junos import BaseCommandGetterTest


class ExampleTestUsingBaseClass(BaseCommandGetterTest):
    """Example test class using inheritance from BaseCommandGetterTest."""
    
    def setUp(self):
        """Set up logging using base class method."""
        self.logger, self.etl_logger, self.handler = self.setup_unified_logging()
        self.logger.info("Example base class test setup completed")
        
    def tearDown(self):
        """Clean up logging using base class method."""
        self.cleanup_unified_logging(self.logger, self.etl_logger, self.handler)
        
    def test_example_with_base_class_logging(self):
        """Example test method using base class logging setup."""
        self.logger.info("Running example test with base class")
        self.etl_logger.debug("ETL debug message from base class approach")
        
        # Your test logic here
        self.assertTrue(True)
        
        self.logger.info("Base class example test completed successfully")


if __name__ == "__main__":
    unittest.main()