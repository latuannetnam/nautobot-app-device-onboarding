# Feature Specification: Juniper Onboarding Enhancement

**Feature Branch**: `002-juniper-onboarding-enhancement`  
**Created**: 2025-10-20T12:34:06.779Z
**Status**: Draft  
**Input**: User description: "Create architecture document to refactor project. Goals:
- Onboard Juniper device configuration to Nautobot with new  model at folder 'nautobot_device_onboarding/models' (see below for file content) 
-  Utilize the same onboard mechanism (Analyze project to discover the logic)
- Extend existing mechanism, tech stack to onboard more device configuration information

Note: Do not implement code, only generate architecture documentation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Onboard a Juniper Device (Priority: P1)

As a network administrator, I want to onboard a Juniper device into Nautobot using the existing onboarding mechanism, so that I can manage its configuration data in a centralized location.

**Why this priority**: This is the core functionality of the feature and provides immediate value by extending the onboarding capabilities to a new vendor.

**Independent Test**: This can be tested by running the `SSOTSyncDevices` job with the IP address of a Juniper device and verifying that a new device is created in Nautobot with the correct basic information (hostname, vendor, model, serial number).

**Acceptance Scenarios**:

1. **Given** a reachable Juniper device with valid credentials, **When** the `SSOTSyncDevices` job is run with the device's IP address, **Then** a new device is created in Nautobot with the correct hostname, vendor, model, and serial number.
2. **Given** an existing Juniper device in Nautobot, **When** the `SSOTSyncDevices` job is run with the device's IP address, **Then** the existing device's information is updated with the latest data from the device.

---

### User Story 2 - Sync Juniper Device Configuration (Priority: P2)

As a network administrator, I want to sync the configuration of a Juniper device into Nautobot, including interfaces, VLANs, VRFs, and routing information, so that I can have a complete and accurate representation of the device's state in Nautobot.

**Why this priority**: This user story builds on the first by adding the ability to sync detailed configuration data, which is essential for network automation and management.

**Independent Test**: This can be tested by running the `SSOTSyncNetworkData` job for a Juniper device and verifying that the corresponding Nautobot objects (interfaces, VLANs, VRFs, etc.) are created or updated correctly.

**Acceptance Scenarios**:

1. **Given** an onboarded Juniper device, **When** the `SSOTSyncNetworkData` job is run, **Then** the device's interfaces, VLANs, VRFs, and routing information are synced to Nautobot.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST be able to onboard a Juniper device using the existing `SSOTSyncDevices` job.
- **FR-002**: The system MUST be able to sync the configuration of a Juniper device using the existing `SSOTSyncNetworkData` job.
- **FR-003**: The system MUST use the `napalm` library to connect to Juniper devices and fetch configuration data.
- **FR-004**: The system MUST use the new Django models in `nautobot_device_onboarding/models` to store Juniper-specific configuration data.
- **FR-005**: The system MUST have a dedicated onboarding extension for Juniper devices to handle any vendor-specific logic.

### Key Entities *(include if feature involves data)*

- **JuniperFirewallFilter**: Represents a Juniper firewall filter configuration.
- **JuniperFirewallTerm**: Represents a term within a Juniper firewall filter.
- **JuniperInterfaceUnit**: Represents a Juniper interface unit with VLAN configuration.
- **JuniperPolicyStatement**: Represents a Juniper network policy statement.
- **JuniperStaticRoute**: Represents a Juniper static route configuration.

### Proposed Onboarding Mechanism

The proposed mechanism for onboarding Juniper devices will leverage the existing infrastructure provided by the `nautobot-app-device-onboarding-latest` app. The core components of this mechanism are:

- **Nornir**: An automation framework that will be used to orchestrate the onboarding process. Nornir will be responsible for managing the inventory of devices to be onboarded, executing tasks on those devices, and collecting the results.
- **Netmiko**: A Python library that will be used to connect to the Juniper devices and execute commands. Netmiko provides a simple and consistent API for interacting with a wide variety of network devices, including those from Juniper.
- **NAPALM**: A Python library that provides a unified API for interacting with different network devices. NAPALM will be used to fetch basic information from the Juniper devices, such as the device's hostname, vendor, model, and serial number.
- **Onboarding Extensions**: A set of custom Python classes that will be used to extend the functionality of the onboarding process. These classes will be responsible for parsing the output of the commands executed on the Juniper devices and creating the corresponding Nautobot objects.

The onboarding process will be initiated by a user through the Nautobot UI. The user will provide the IP address of the Juniper device to be onboarded, as well as the necessary credentials. The `SSOTSyncDevices` job will then be executed, which will trigger the Nornir automation framework. Nornir will then connect to the Juniper device, execute a series of commands to collect the necessary information, and then create the corresponding Nautobot objects.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Juniper device can be successfully onboarded into Nautobot using the `SSOTSyncDevices` job in under 2 minutes.
- **SC-002**: The configuration of a Juniper device can be successfully synced to Nautobot using the `SSOTSyncNetworkData` job in under 5 minutes.
- **SC-003**: The system can onboard and sync at least 10 Juniper devices concurrently without any performance degradation.

## Constitution Alignment

*   **Extensibility and Modularity**: This feature extends the existing onboarding mechanism by adding support for a new vendor (Juniper) in a modular way. This is achieved by creating a dedicated onboarding extension for Juniper devices, which encapsulates all vendor-specific logic. This approach makes it easy to add support for other vendors in the future without modifying the core onboarding logic.
*   **Vendor-Agnosticism**: This feature promotes vendor-agnosticism by using the `napalm` library, which provides a unified API for interacting with different network devices. This allows the core onboarding logic to remain vendor-agnostic, while the vendor-specific details are handled by the onboarding extensions.
*   **Idempotency**: The onboarding and sync processes are idempotent, meaning that they can be run multiple times without changing the result beyond the initial application. This is achieved by using the `diffsync` library, which compares the state of the device with the state of Nautobot and only applies the necessary changes.
*   **Comprehensive Data Collection**: This feature contributes to comprehensive data collection by syncing a wide range of configuration data from Juniper devices, including interfaces, VLANs, VRFs, and routing information. This data can be used for various network automation and management tasks.
*   **Clear and Actionable Logging**: The onboarding and sync processes provide clear and actionable logging, which helps to troubleshoot any issues that may arise. The logs include detailed information about the steps that are being performed, as well as any errors that occur.
