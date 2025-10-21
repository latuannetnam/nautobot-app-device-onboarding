# Tasks: Juniper Onboarding Enhancement

**Input**: Design documents from `/specs/002-juniper-onboarding-enhancement/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

## Phase 1: Foundational (Blocking Prerequisites)

- [x] T001 [US1] Analyze the `SSOTSyncDevices` and `SSOTSyncNetworkData` jobs in `nautobot_device_onboarding/jobs.py`.
- [x] T002 [US1] Analyze the `StandaloneOnboarding` class in `nautobot_device_onboarding/onboarding/onboarding.py`.
- [x] T003 [US1] Analyze the `NetdevKeeper` class in `nautobot_device_onboarding/netdev_keeper.py`.
- [x] T004 [US1] Analyze the `nornir_plays` directory.
- [x] T005 [US1] Ensure `napalm` is properly configured to connect to Juniper devices.

## Phase 2: User Story 1 - Onboard a Juniper Device (Priority: P1) 🎯 MVP

- [x] T006 [US1] Create a new file `nautobot_device_onboarding/onboarding_extensions/juniper.py`.
- [x] T007 [US1] In `juniper.py`, create a new class `JuniperOnboardingDriverExtensions` that inherits from `OnboardingDriverExtensions`.
- [x] T008 [US1] In `JuniperOnboardingDriverExtensions`, implement the `onboarding_class` property to return a custom `JuniperStandaloneOnboarding` class.
- [x] T009 [US1] In `juniper.py`, create a new class `JuniperStandaloneOnboarding` that inherits from `StandaloneOnboarding`.
- [x] T010 [US1] In `JuniperStandaloneOnboarding`, implement the `run` method to handle Juniper-specific device creation logic.

## Phase 3: User Story 2 - Sync Juniper Device Configuration (Priority: P2)

- [x] T011 [US2] In `JuniperOnboardingDriverExtensions`, implement the `ext_result` property to return Juniper-specific configuration data.
- [x] T012 [US2] In `JuniperStandaloneOnboarding`, update the `run` method to use the new Django models in `nautobot_device_onboarding/models` to store the Juniper-specific configuration data.

## Phase N: Polish & Cross-Cutting Concerns

- [x] T013 [P] Update the `onboarding_extensions_map` in the `settings.py` file to include the new Juniper onboarding extension.
- [x] T014 [P] Create a new command mapper file for Juniper devices in `nautobot_device_onboarding/parsers`.
- [x] T015 [P] Add new unit tests for the Juniper onboarding extension in the `nautobot_device_onboarding/tests` directory.
- [x] T016 [P] Update the documentation to include information about the new Juniper onboarding extension.