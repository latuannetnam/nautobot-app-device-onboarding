# Tasks: Juniper Onboarding Enhancement

**Input**: Design documents from `/specs/002-juniper-onboarding-enhancement/`
**Prerequisites**: spec.md (required for user stories)

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Analyze the existing onboarding mechanism to understand how to extend it for Juniper devices.

- [ ] T001 [US1] Analyze the `SSOTSyncDevices` and `SSOTSyncNetworkData` jobs in `nautobot_device_onboarding/jobs.py` to understand the high-level orchestration of the onboarding process.
- [ ] T002 [US1] Analyze the `StandaloneOnboarding` class in `nautobot_device_onboarding/onboarding/onboarding.py` to understand how devices are created in Nautobot.
- [ ] T003 [US1] Analyze the `NetdevKeeper` class in `nautobot_device_onboarding/netdev_keeper.py` to understand how device information is collected.
- [ ] T004 [US1] Analyze the `nornir_plays` directory to understand how `nornir` and `netmiko` are used to execute commands on devices and process the output.

## Phase 2: User Story 1 - Onboard a Juniper Device (Priority: P1) 🎯 MVP

**Goal**: Create a dedicated onboarding extension for Juniper devices that can be used to onboard a Juniper device into Nautobot.

### Implementation for User Story 1

- [ ] T005 [US1] Create a new file `nautobot_device_onboarding/onboarding_extensions/juniper.py` that will contain the onboarding extension for Juniper devices.
- [ ] T006 [US1] In the new file, create a new class `JuniperOnboardingDriverExtensions` that inherits from the `OnboardingDriverExtensions` class.
- [ ] T007 [US1] In the new class, implement the `onboarding_class` property to return a custom `JuniperStandaloneOnboarding` class.
- [ ] T008 [US1] In the new file, create a new class `JuniperStandaloneOnboarding` that inherits from the `StandaloneOnboarding` class.
- [ ] T009 [US1] In the `JuniperStandaloneOnboarding` class, implement the `run` method to handle any Juniper-specific logic for creating a device in Nautobot.

## Phase 3: User Story 2 - Sync Juniper Device Configuration (Priority: P2)

**Goal**: Extend the Juniper onboarding extension to support the syncing of configuration data from a Juniper device to Nautobot.

### Implementation for User Story 2

- [ ] T010 [US2] In the `JuniperOnboardingDriverExtensions` class, implement the `ext_result` property to return a dictionary of Juniper-specific configuration data.
- [ ] T011 [US2] In the `JuniperStandaloneOnboarding` class, update the `run` method to use the new Django models in `nautobot_device_onboarding/models` to store the Juniper-specific configuration data.

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T012 [P] Update the `onboarding_extensions_map` in the `settings.py` file to include the new Juniper onboarding extension.
- [ ] T013 [P] Create a new command mapper file for Juniper devices in the `nautobot_device_onboarding/parsers` directory.
- [ ] T014 [P] Add new unit tests for the Juniper onboarding extension in the `nautobot_device_onboarding/tests` directory.
- [ ] T015 [P] Update the documentation to include information about the new Juniper onboarding extension.