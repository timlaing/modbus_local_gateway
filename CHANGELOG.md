# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

Releases up to `v2.0.0` follow SemVer. From `2025.3.1` on, versions are
CalVer (`YYYY.M.PATCH`) because Home Assistant expects date-based versions for
custom integrations. Pre-releases are not listed here.

## [Unreleased]

### Added

- **Read-modify-write for bit fields**: a register that packs several independent controls could be read with `bits` / `shift_bits` but never written, because Modbus has no bit write for holding registers. Writing such a field now reads the register, replaces only that field and writes it back, inside the same client lock `update_device()` takes, so no poll or other write on that gateway can land in between. No new YAML syntax — `bits` / `shift_bits` already describe the geometry the merge needs. A value that does not fit its mask raises rather than truncating, a failed read aborts the write instead of merging onto a guess, and the field is read in one transaction so a field split across two reads cannot tear. `signed` and `sum_scale` are rejected on writable bit fields because the merge cannot express their arithmetic; coils still reject `bits` entirely. Documented in the README.
- **`unavailable_values` on an entity**: devices publish a sentinel when a sensor is absent or a function is inactive — commonly `0xFFFF`, `0xFF` or `0` — and the integration published it as a real reading. A device config can now declare `unavailable_values`, and the entity goes unavailable while one of them is reported, which keeps the sentinel out of long-term statistics entirely instead of only off a dashboard. Used by the Midea heat-pump config for the curve-setpoint registers that read 255 with the climate curve off.
- **`no_flag_value` on an entity**: a register used as a bit-flag field — typically an error code — had no state of its own for "nothing is flagged", so the sensor reported the raw register value and the fault it had shown before could not be distinguished from a clear reading. A device config can now declare `no_flag_value`, and that value is reported whenever none of the entity's `flags` bits is set, e.g. `no_flag_value: "No error"`. Without the key the raw number is still reported, so existing configs are unaffected. A value a sensor cannot hold (a float, bool, list or mapping) is rejected at load with a warning. Documented in the README.

### Fixed

- **Writes to devices that only implement preset multiple registers**: a single holding register write always went out as _Preset Single Register_ (FC `0x06`), and some devices only implement _Preset Multiple Registers_ (FC `0x10`). Those devices either answer FC `0x06` with an exception or stay silent, so the write was lost and the entity reported a failure — the reported case is an inverter whose `select` on register 301 failed with "No response received after 5 retries" until it was written by hand with FC `0x10`. A refused single-register write is now retried once with FC `0x10`, mirroring the fallback multi-register writes already take in the other direction, and the retry goes straight to `write_registers` so the function that just failed is not attempted a second time. A write that gets no answer at all is _not_ simply repeated: writing a register can run a command, and a lost response does not mean the device left it alone, so the register is read back first. A read-back that already holds the requested value is treated as done and prevents the retry — it proves the state, not that the write ran. A read-back that still holds the old value leaves it ambiguous: for a device that has never answered FC `0x06` the function is not implemented and the FC `0x10` retry is safe, while a device that does answer `0x06` may have run a command and lost only the response, so its write is reported as failed and not repeated — the shipped Pichler config documents that register 33 (`Reset` / `Snooze`) clears itself again, which would otherwise run the command twice. When the read-back cannot be answered either, the write is reported as failed and nothing is repeated. The log names the failed attempt, its reason and pymodbus' own diagnostics.

- **A `map:` miss no longer freezes an entity**: `_convert_to_enum` returned `None` for an unmapped value and the platforms skip the update on `None`, so the entity silently kept its previous state — no error, no `unknown`, just a stale reading that looks current. The raw number is returned instead, so the state is either a label or a bare number and the reading is never older than the last poll. The miss is logged at debug.
- **Failed register writes are reported to Home Assistant**: the write helpers were annotated `-> None` and never returned the PDU they received, so the `if pdu and pdu.isError()` check in `write_data()` was dead code — a Modbus exception response to a write was reported back as a successful write. The PDU is now returned and `write_data()` raises `ModbusException`, which the coordinator entity wraps into `UpdateFailed`. Behaviour change: writes that previously failed silently now raise.
- **Number writes are read back**: `async_set_native_value` called the client directly, bypassing `ModbusCoordinatorEntity.write_data()` and the re-read that switch, select and text all perform, so the matching sensor stayed stale for a full `scan_interval` after every number write.
- **An empty poll list no longer fails the refresh**: `async_update` polls only entities without a `scan_interval`, so a device config that sets one on every entity left that list empty and raised `UpdateFailed` on every refresh — marking all of the integration's entities unavailable, including the ones their own timers were polling fine. An empty poll list now returns the data the per-entity timers already stored.
- **The client is closed when the last config entry using it unloads**: `async_unload_entry()` unloaded the platforms and dropped the coordinator but never closed the client or evicted it from the cache, so the TCP connection outlived the config entry with pymodbus' retry machinery still running on it. The client is cached per host/port/framer and shared by every entry pointing at the same gateway, so it is closed once no remaining coordinator references it, and `ModbusProtocol.close()` sets `is_closing` so no reconnect task is spawned.

### Changed

- **Standard names for the connection type**: the two options in the config flow were labelled by how the device is reached — "Via Gateway Device" and "Direct Connection" — which does not say what is on the wire, and neither is the name the protocol carries in a manual or a datasheet. They are now "Modbus TCP" and "Modbus RTU over TCP", matching `FramerType.SOCKET` and `FramerType.RTU`, which is what the selection actually changes. The stored value, and therefore existing config entries, are untouched.

- **Python 3.14 only**: packaging metadata and CI no longer advertise 3.13, and the dev Home Assistant pin follows.
- **Repo tooling and docs**: `prek` hook set (ruff, isort, cspell, yamllint, prettier, mypy, pylint, coverage) plus a dependency sync script, contributor and security docs, a repo-specific PR template, the code-review skill and updated CI workflows. SonarQube scans moved to `workflow_run` with a validated coverage report, keeping the token out of fork-derived code.
- **mypy and pylint run on every commit** instead of on a manual stage; the findings across the integration, tests and test server are fixed (pylint 10.00/10, mypy clean across all 21 source files). The config flow schemas are cast so they type-check against both voluptuous and the `probatio` annotation Home Assistant 2026.10 uses.

### Device configurations

- **Midea-built air-to-water heat pumps** (Kaisai KHA/KMK/KHC controller): 97 entities covering temperatures, refrigerant circuit, electrical values, status and load bitfields, fault history, energy counters and the commissioning parameters. Compatibility follows the wired controller rather than the badge on the outdoor unit; register 131 reports the controller version as a diagnostic. Setpoint ranges are the protocol's, with each unit's own limits exposed as sensors so they can be narrowed. Optional hardware is disabled by default because an unfitted sensor reports a fixed sentinel.
- **Midea heat-pump config**: the curve-setpoint sentinels are declared with `unavailable_values`; the nine remaining register 129 load-output bits are surfaced; and the fault codes in registers 124-127 are now decoded, which is safe because an unmapped `map:` value falls back to the raw number rather than freezing the sensor on the previous fault.
- **Eastron SDM630 demand registers**: `Total System Power demand` and `Total System VA demand` were declared `state_class: total_increasing` with `never_resets: true`, but a demand is a measurement. While the meter exports to the grid both are negative, `total_increasing` cannot hold a negative state — the recorder rejected it and the integration's `never_resets` guard logged "Ignoring device value" and kept the previous import reading, so the sensor froze on the last positive value. Both are now `measurement`, matching the `Total System Power` / `Total System VA` registers they sit beside, and the inert `never_resets` is gone. A test walks the shipped configs so no power device class can be declared as a total again.
- **Schneider Altivar ATV 312**, **Salda RIS 700 PE**, **LAE AC1-27 controller** and **Fröling BWP300PV** configurations.

### Dependencies

- pymodbus `>=3.11.1` → `>=3.13.1`, Home Assistant `>=2026.6.3`, setuptools `>=82.0.1,<84.1`, yarl `>=1.24.2`, pycryptodome `>=3.23.0`, tox `4.64.4`, ruff `0.15.20`, prek `>=0.4.5`, isort `>=8.0.1`, pytest-asyncio `>=1.4.0`, pytest-cov `>=7.14.3`, pytest-homeassistant-custom-component, coverage `>=7.14.3` and pylint `>=4.0.6`; the dev `requirements_dev.txt` dependency conflicts are fixed and dependabot is set to `increase-if-necessary`.

### CI & tooling

- GitHub Actions bumps: `checkout` 4 → 7, `github-script` 7 → 9, `setup-node` 4 → 7, `setup-python` 5 → 7, `upload-artifact` 6 → 7, `download-artifact` 7 → 8, `codeql-action` 4.32.3 → 4.38.0, `release-drafter` 6 → 7.6.0, `j178/prek-action` 1.1.1 → 2, `SonarSource/sonarqube-scan-action` 7 → 8, and the devcontainer Node feature 1.7.1 → 2.0.0.

## [v2026.02.0] - 2026-02-21

- Prefix entity IDs with gateway host (no separators) and migrate exist… ([#133](https://github.com/timlaing/modbus_local_gateway/pull/133))
- Drop manufacturer prefix from entity names ([#134](https://github.com/timlaing/modbus_local_gateway/pull/134))
- Add Pichler LG350/LG450 ventilation device configuration ([#139](https://github.com/timlaing/modbus_local_gateway/pull/139))
- feature: Add slider/step support for number entities ([#138](https://github.com/timlaing/modbus_local_gateway/pull/138))
- Update setuptools requirement from <80.10,>=77.0 to >=77.0,<82.1 ([#146](https://github.com/timlaing/modbus_local_gateway/pull/146))
- Bump tox from 4.32.0 to 4.44.0 ([#152](https://github.com/timlaing/modbus_local_gateway/pull/152))
- Potential fix for code scanning alert no. 21: Workflow does not contain permissions ([#129](https://github.com/timlaing/modbus_local_gateway/pull/129))
- Potential fix for code scanning alert no. 10: Workflow does not contain permissions ([#131](https://github.com/timlaing/modbus_local_gateway/pull/131))
- Potential fix for code scanning alert no. 24: Workflow does not contain permissions ([#130](https://github.com/timlaing/modbus_local_gateway/pull/130))
- Potential fix for code scanning alert no. 20: Workflow does not contain permissions ([#128](https://github.com/timlaing/modbus_local_gateway/pull/128))
- Bump actions/cache from 4 to 5 ([#123](https://github.com/timlaing/modbus_local_gateway/pull/123))
- Bump peter-evans/create-pull-request from 7 to 8 ([#122](https://github.com/timlaing/modbus_local_gateway/pull/122))
- Bump actions/upload-artifact from 5 to 6 ([#124](https://github.com/timlaing/modbus_local_gateway/pull/124))
- Bump actions/download-artifact from 6 to 7 ([#125](https://github.com/timlaing/modbus_local_gateway/pull/125))
- Update Python version to 3.14 and adjust dependencies ([#127](https://github.com/timlaing/modbus_local_gateway/pull/127))
- Bump homeassistant from 2025.11.3 to 2025.12.2 ([#121](https://github.com/timlaing/modbus_local_gateway/pull/121))

## [v2025.12.0] - 2025-12-02

- Bump actions/download-artifact from 5 to 6 ([#99](https://github.com/timlaing/modbus_local_gateway/pull/99))
- Bump actions/upload-artifact from 4 to 5 ([#98](https://github.com/timlaing/modbus_local_gateway/pull/98))
- Bump homeassistant from 2025.10.3 to 2025.11.1 ([#102](https://github.com/timlaing/modbus_local_gateway/pull/102))
- Refactor GitHub workflows for Home Assistant testing ([#103](https://github.com/timlaing/modbus_local_gateway/pull/103))
- Update home-assistant-dev.yml ([#104](https://github.com/timlaing/modbus_local_gateway/pull/104))
- Bump peter-evans/repository-dispatch from 3 to 4 ([#107](https://github.com/timlaing/modbus_local_gateway/pull/107))
- Bump actions/checkout from 4 to 5 ([#106](https://github.com/timlaing/modbus_local_gateway/pull/106))
- Bump actions/github-script from 7 to 8 ([#105](https://github.com/timlaing/modbus_local_gateway/pull/105))
- Bump actions/checkout from 5 to 6 ([#110](https://github.com/timlaing/modbus_local_gateway/pull/110))
- Add support for Husdata H60 and Waveshare RTU Relay (D) devices ([#116](https://github.com/timlaing/modbus_local_gateway/pull/116))
- Bump homeassistant from 2025.11.1 to 2025.11.3 ([#111](https://github.com/timlaing/modbus_local_gateway/pull/111))
- Add connection type configuration to resolve #113 & #115. Fixed Prefi… ([#117](https://github.com/timlaing/modbus_local_gateway/pull/117))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v2025.10.0...v2025.12.0

## [v2025.10.0] - 2025-10-18

- Bump homeassistant from 2025.5.3 to 2025.10.3 ([#94](https://github.com/timlaing/modbus_local_gateway/pull/94))
- Add config_entry parameter to ModbusCoordinator ([#95](https://github.com/timlaing/modbus_local_gateway/pull/95))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v2025.9.0...v2025.10.0

## [v2025.9.0] - 2025-09-05

- Add configuration for ME31-AXAX404 device with read/write boolean and… ([#83](https://github.com/timlaing/modbus_local_gateway/pull/83))
- Bump actions/checkout from 4 to 5 ([#85](https://github.com/timlaing/modbus_local_gateway/pull/85))
- Bump actions/download-artifact from 4 to 5 ([#84](https://github.com/timlaing/modbus_local_gateway/pull/84))
- update to support latest ha version ([#88](https://github.com/timlaing/modbus_local_gateway/pull/88))
- Bump actions/setup-python from 5 to 6 ([#87](https://github.com/timlaing/modbus_local_gateway/pull/87))

### New Contributors

- @dependabot[bot] made their first contribution ([#85](https://github.com/timlaing/modbus_local_gateway/pull/85))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v2025.6.3...v2025.9.0

## [v2025.6.3] - 2025-06-15

- Fix: unit of measurement issue ([#80](https://github.com/timlaing/modbus_local_gateway/pull/80))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v2025.6.2...v2025.6.3

## [v2025.6.2] - 2025-06-14

- Add scan_interval option and improve Modbus entity logic ([#69](https://github.com/timlaing/modbus_local_gateway/pull/69))
- Enhance Modbus integration with config file handling and improved device loading ([#72](https://github.com/timlaing/modbus_local_gateway/pull/72))
- Rename 'native_unit_of_measurement' to 'unit_of_measurement' for consistency ([#74](https://github.com/timlaing/modbus_local_gateway/pull/74))
- Add asyncio support to tests and handle InvalidStateError in data_received method ([#75](https://github.com/timlaing/modbus_local_gateway/pull/75))
- Fix typo in MyTransactionManager docstring and add async_unload_entry test for Modbus integration ([#76](https://github.com/timlaing/modbus_local_gateway/pull/76))

### Resolves issues

- Writing swapped 32 bit registers sets their value 0 after edit iso the value in the UI #68
- Scan interval at register level iso device level #63
- Custom Devices Deleted after update #57

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v2025.6.1...v2025.6.2

## [v2025.6.1] - 2025-06-09

- Update README.md ([#65](https://github.com/timlaing/modbus_local_gateway/pull/65))
- Refactor conversion logic and enhance precision handling in ModbusSensorEntity ([#67](https://github.com/timlaing/modbus_local_gateway/pull/67))

### Resolves Issues

- [Sensor Values suddenly wrong.](https://github.com/timlaing/modbus_local_gateway/issues/66) #66
- [sum_scale: [1, 65536] with Little-endian results are wrong](https://github.com/timlaing/modbus_local_gateway/issues/62) #66 bug

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v2025.6.0...v2025.6.1

## [v2025.6.0] - 2025-06-07

- Refactor Modbus integration for improved precision handling and data updates ([#59](https://github.com/timlaing/modbus_local_gateway/pull/59))
- Add configuration for Waveshare Modbus POE ETH Relay 30CH ([#60](https://github.com/timlaing/modbus_local_gateway/pull/60))
- Update development environment and issue templates ([#61](https://github.com/timlaing/modbus_local_gateway/pull/61))
- Refactor Modbus integration and enhance documentation ([#64](https://github.com/timlaing/modbus_local_gateway/pull/64))

### Resolved issues

- sum_scale: [1, 65536] with Little-endian results are wrong #62
- Feature to Invert State of Binary Sensors #56
- Eastron SDM630 v2 with Waveshare rs485 #38
- Waveshare controller #58

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v2025.5.2...v2025.6.0

## [v2025.5.2] - 2025-05-26

- Improve support for binary sensors and switches ([#54](https://github.com/timlaing/modbus_local_gateway/pull/54))
- Enhance Modbus configurations and debugging capabilities ([#55](https://github.com/timlaing/modbus_local_gateway/pull/55))

Addresses issues:

- #52
- #38

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v2025.5.1...v2025.5.2

## [v2025.5.1] - 2025-05-18

- Allow value to reset if max change defined ([#53](https://github.com/timlaing/modbus_local_gateway/pull/53))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v2025.5.0...v2025.5.1

## [v2025.5.0] - 2025-05-05

- Added multiplier support for floating point registers ([#46](https://github.com/timlaing/modbus_local_gateway/pull/46))
- Update SDM630.yaml ([#45](https://github.com/timlaing/modbus_local_gateway/pull/45))
- Create FUNDING.yml ([#47](https://github.com/timlaing/modbus_local_gateway/pull/47))
- Prevent duplicate data ([#48](https://github.com/timlaing/modbus_local_gateway/pull/48))
- Minor typing improvements and type hint enhancements ([#49](https://github.com/timlaing/modbus_local_gateway/pull/49))
- Update sonar.yml ([#50](https://github.com/timlaing/modbus_local_gateway/pull/50))
- Feature/max change ([#51](https://github.com/timlaing/modbus_local_gateway/pull/51))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v2025.3.1...v2025.5.0

## [v2025.3.1] - 2025-03-26

### Bugfixes

Resolve issue #38 where sensors become unavailable

- Allow update of total increasing values. Value may be smaller dur to … ([#39](https://github.com/timlaing/modbus_local_gateway/pull/39))
- Allow old and new device identifiers and link to mac address if possible ([#41](https://github.com/timlaing/modbus_local_gateway/pull/41))
- Supress logging errors caused due to multiple connections to the same… ([#40](https://github.com/timlaing/modbus_local_gateway/pull/40))
- Ha updates ([#42](https://github.com/timlaing/modbus_local_gateway/pull/42))
- Update sensor.py ([#43](https://github.com/timlaing/modbus_local_gateway/pull/43))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v2.0.0...v2025.3.1

## [v2.0.0] - 2025-03-07

- A few new features ([#33](https://github.com/timlaing/modbus_local_gateway/pull/33))
- Fixed sonarqube warnings ([#35](https://github.com/timlaing/modbus_local_gateway/pull/35))
- Create single device per endpoint ([#37](https://github.com/timlaing/modbus_local_gateway/pull/37))

### New Contributions

Many thanks to @dmatscheko for their contribution.

### Notes

- Improved device naming may cause legacy devices to become orphaned. Entities will not be affected.

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.7.0...v2.0.0

## [v1.7.0] - 2025-02-06

- Uplift for pymodbus 3.8.3 ([#31](https://github.com/timlaing/modbus_local_gateway/pull/31))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.6.1...v1.7.0

## [v1.6.1] - 2025-01-15

Minor bugfixes for HA 2025.01 and PyModbus 3.7.4

- Fix for read registers response. Update to devices to fix HA error ([#30](https://github.com/timlaing/modbus_local_gateway/pull/30))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.6.0...v1.6.1

## [v1.6.0] - 2025-01-05

- Support HA 2025.01 #27, #28 ([#29](https://github.com/timlaing/modbus_local_gateway/pull/29))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.5.0...v1.6.0

## [v1.5.0] - 2024-10-06

- Added pre-commit and fixes for HA 2024.10 ([#26](https://github.com/timlaing/modbus_local_gateway/pull/26))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.4.2...v1.5.0

## [v1.4.2] - 2024-08-09

- Backward compatibility with modbus component ([#24](https://github.com/timlaing/modbus_local_gateway/pull/24))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.4.1...v1.4.2

## [v1.4.1] - 2024-08-08

Hotfix for v1.4.0

- update of manifest to bump pymodbus dependancy to version 3.7
- fixed precision handling

- Hotfix v1.4.0 ([#23](https://github.com/timlaing/modbus_local_gateway/pull/23))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.4.0...v1.4.1

## [v1.4.0] - 2024-08-07

- New Devices & Bump to latest versions ([#22](https://github.com/timlaing/modbus_local_gateway/pull/22))

Addresses:

- #13 Added SDM630
- #21 Added MOD-6000TL-X
- #12 & #19 Fixed device connection issue
- #15 Fixed values for 7M.38

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.3.0...v1.4.0

## [v1.3.0] - 2024-03-22

- Add support for writable values ([#18](https://github.com/timlaing/modbus_local_gateway/pull/18))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.2.2...v1.3.0

## [v1.2.2] - 2024-03-21

- Remove deprecation warning ([#16](https://github.com/timlaing/modbus_local_gateway/pull/16))
- Upgrade to python 3.12 and fixed version of pymodbus ([#17](https://github.com/timlaing/modbus_local_gateway/pull/17))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.2.1...v1.2.2

## [v1.2.1] - 2023-10-29

- Added state classes ([#11](https://github.com/timlaing/modbus_local_gateway/pull/11))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.2.0...v1.2.1

## [v1.2.0] - 2023-10-29

- Bugfixes ([#10](https://github.com/timlaing/modbus_local_gateway/pull/10))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.1.2...v1.2.0

## [v1.1.2] - 2023-10-28

- Added support for bit fields and masks ([#5](https://github.com/timlaing/modbus_local_gateway/pull/5))
- Fixed startup issues ([#9](https://github.com/timlaing/modbus_local_gateway/pull/9))

### New Contributors

- @timlaing made their first contribution ([#5](https://github.com/timlaing/modbus_local_gateway/pull/5))

**Full Changelog**: https://github.com/timlaing/modbus_local_gateway/compare/v1.1.0...v1.1.2

## [v1.1.0] - 2023-08-18

With thanks to @wasn-eu added prefix support.

## [v1.0.0] - 2023-08-14

First public release
