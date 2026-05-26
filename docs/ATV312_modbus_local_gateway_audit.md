# ATV312 Modbus Local Gateway Audit

## Scope

This audit covers:

- the exact YAML schema used by `custom_components/modbus_local_gateway/device_configs/`
- the repo tests that validate device configs
- the supported fields confirmed in the loader/parser
- the standard safe profile for `Schneider_ATV312.yaml`
- the optional expert profile for `Schneider_ATV312_expert.yaml`

Primary device source used:

- `ATV312_communication_variables_EN_BBV51701_01.pdf`

Repo sources audited:

- `README.md`
- `custom_components/modbus_local_gateway/entity_management/base.py`
- `custom_components/modbus_local_gateway/entity_management/modbus_device_info.py`
- `custom_components/modbus_local_gateway/entity_management/device_loader.py`
- `tests/test_device_loader.py`
- `tests/test_modbus_device_info.py`

## 1. Exact YAML Schema Supported by the Repo

The README and parser agree on this structure:

```yaml
device:
  manufacturer: "Vendor"
  model: "Model"
  max_register_read: 8

read_write_word: {}
read_only_word: {}
read_write_boolean: {}
read_only_boolean: {}
```

Important parser constraints:

- do not add unsupported keys
- do not use custom metadata fields like `notes:` or `comment:`
- use YAML comments only for safety notes and operating guidance

## 2. Supported Fields Confirmed in the Loader

Confirmed as supported:

- `address`
- `name`
- `size`
- `scan_interval`
- `multiplier`
- `offset`
- `signed`
- `float`
- `string`
- `swap`
- `sum_scale`
- `shift_bits`
- `bits`
- `precision`
- `map`
- `flags`
- `unit_of_measurement`
- `device_class`
- `state_class`
- `entity_category`
- `entity_registry_enabled_default`
- `never_resets`
- `max_change`
- `control: number`
- `control: select`
- `control: switch`
- `control: text`
- `control: binary_sensor`
- `number.min`
- `number.max`
- `number.step`
- `number.mode`
- `options`
- `switch.on`
- `switch.off`

## 3. Existing Validation in the Repo

The main config validation already present is:

- `tests/test_modbus_device_info.py::test_devices_yaml`

What it checks:

- YAML files load through the real device loader
- entity descriptions are created without parser warnings
- `manufacturer` and `model` resolve correctly

Related tests also cover:

- `tests/test_device_loader.py`
- `tests/test_modbus_device_info.py`
- `tests/test_number.py`
- `tests/test_select.py`
- `tests/test_switch.py`

## 4. Motor + UV Lamp Use Case ( example )

Real operating context:

- ATV312 drives a 3-phase motor from a single-phase supply
- minimum usable speed: `18 Hz`
- normal filtration: `30-40 Hz`
- temporary boost only: `60 Hz`
- UV lamp is switched by a relay output only when the motor has reached cruise speed

Design goals for the standard profile:

- safe Home Assistant speed control through `LFr`
- strong monitoring of actual frequency, current, thermal load and faults
- safe configuration exposure with dangerous or topology-changing items hidden by default
- no factory reset, no auto-tuning, no advanced stop-mode controls in the standard file

## 5. Standard Profile: `Schneider_ATV312.yaml`

### Standard read/write entities

Exposed for normal use:

- `LFr` as the main Home Assistant speed setpoint
  - `18.0` to `60.0 Hz`
  - `0.1 Hz` step
  - comments document `30-40 Hz` normal filtration and `60 Hz` temporary boost

Exposed but hidden by default:

- raw `CMD` register, without a Home Assistant run/stop switch
- optional `PISP`
- `ACC`, `dEC`, `LSP`, `HSP`, `tFr`
- `ItH`, `CLI`
- `Ftd`, `R1`, `R2`
- `JPF`, `JF2`, `tLS`, `rPt`, `Inr`, `AC2`, `dE2`, `Frt`, `brA`, `SFr`, `nrd`, `SrF`
- `Fr1`, `Fr2`, `Cd1`, `Cd2`

Why `CMD` is not exposed as a standard Home Assistant switch:

- the control word is a full bitfield
- some important bits are active-low
- sending the wrong composite value is easy
- a raw hidden register is safer than a misleading on/off abstraction

### Standard read-only monitoring and diagnostics

Core motor monitoring:

- `ETA`
- `rFr`
- `FrH`
- `LFR1`
- `LCr`
- `Otr`
- `OPr`
- `ULn`
- `tHr`
- `tHd`
- `TDM`
- `rtH`
- `INV`
- `ERRD`

State and fault entities:

- `Drive Fault Active`
- `Drive Alarm Present`
- `Reference Reached`
- `Motor Running`
- `Relay R1 Output Active`
- `Relay R2 Output Active`
- `Drive Accelerating`
- `Drive Decelerating`
- `Current Limit Alarm`
- `Frequency Threshold Reached`
- `High Speed Reached`
- `Speed Reference Reached Status`
- `IOLR`
- `ETI`
- `LRS1`
- `LRS3`
- `LFt`
- `DP1` to `DP4`
- `EP1` to `EP4`

Static diagnostics kept available but hidden:

- `NCV`
- `VCAL`
- `TSP`
- `O1Ct`
- `UdP`

## 6. UV Lamp Strategy

Recommended safe relay strategy:

- set the UV relay assignment (`R1` or `R2`) to `FtA`
- set `Ftd` to the cruise speed threshold, typically between `30` and `40 Hz`
- do not use `FLA` for UV in this installation, because `FLA` follows `HSP` and `HSP` can be `60 Hz` for temporary boost

Direct relay-state monitoring:

- available in the standard profile through `Relay R1 Output Active` and `Relay R2 Output Active`
- `IOLR` is also exposed read-only for logic-input and relay-state diagnostics
- `AO1R` remains outside the standard profile and stays in the expert profile only

## 7. Recommended Home Assistant Entities

Recommended to surface in dashboards or automations:

- `number.lfr_frequency_reference_via_bus`
- `sensor.rfr_output_frequency`
- `sensor.lcr_motor_current`
- `sensor.opr_motor_power`
- `sensor.thr_motor_thermal_state`
- `sensor.thd_drive_thermal_state`
- `sensor.errd_active_fault_code`
- `sensor.lft_last_detected_fault`
- `binary_sensor.drive_fault_active`
- `binary_sensor.motor_running`
- `binary_sensor.frequency_threshold_reached`
- `binary_sensor.relay_r1_output_active`
- `binary_sensor.relay_r2_output_active`
- `number.ftd_motor_frequency_threshold`

Recommended but usually left hidden unless tuning is needed:

- `number.acc_acceleration_ramp_time`
- `number.dec_deceleration_ramp_time`
- `number.lsp_low_speed`
- `number.hsp_high_speed`
- `select.relay_r1_assignment`
- `select.relay_r2_assignment`
- `select.fr1_reference_channel_1`
- `select.cd1_control_channel_1`

## 8. Recommended Automations

- UV `ON` only when the motor is running and actual frequency is stable at or above cruise speed
- UV `OFF` if the motor stops, a drive fault appears, actual frequency drops below the cruise threshold, or Modbus communication is lost
- `60 Hz` boost should always be wrapped in a timer or script that returns to the normal filtration band
- generate alerts on overload, overheat, undervoltage, overcurrent or persistent current-limit alarms

Practical signals for those automations:

- `rFr` for actual frequency
- `Motor Running`
- `Drive Fault Active`
- `Drive Alarm Present`
- `Frequency Threshold Reached`
- `Relay R1 Output Active` or `Relay R2 Output Active` if the UV lamp is wired on that relay
- `LFt`
- `ERRD`
- `tHr`
- `tHd`
- `LCr`

## 9. Expert Profile: `Schneider_ATV312_expert.yaml`

Purpose:

- keep the standard profile clean and safe
- expose low-level diagnostics and communication settings in a separate opt-in profile

Expert file includes:

- Modbus communication parameters: `Add`, `tbr`, `tFO`, `ttO`
- low-level bus images: `CMI1`, `CMI2`
- full low-level I/O and relay state: `IOLR`, `Relay R1 Output Active`, `Relay R2 Output Active`, `Logic Output Active`, `Keypad Present`
- analog diagnostics: `AI1C`, `AI2C`, `AI3C`, `AO1R`

Expert profile safety posture:

- all expert entities are disabled by default
- communication settings are marked as configuration
- YAML comments warn that changing them can break Modbus communication immediately

## 10. Registers Excluded from the Standard Profile

Excluded with reason:

- `CMI`, `CMI1`, `CMI2` in standard
  - low-level control-word internals, not needed for normal motor operation
- `SCS`, `FCS`
  - save/restore/factory settings
- `rP`, `rSF`
  - fault-reset actions should not be automated from the standard profile
- `LAC`, `CHCF`, `CCS`, `rFC`
  - control/reference routing changes with non-obvious consequences
- `tCC`, `tCt`, `rrS`
  - control wiring and logic behavior
- `AO1R` in standard
  - kept in the expert profile only; it is not needed for normal motor control
- write access to `IOLR`
  - standard profile exposes `IOLR` read-only only, with no write path
- `9601` to `9609`
  - motor nameplate and auto-tuning parameters
- `11201` to `11230`
  - stop modes and DC injection behavior
- undocumented or reserved addresses
  - never written

## 11. Validation Commands

Required YAML validation:

```bash
python3 - <<'PY'
import yaml
from pathlib import Path
for p in Path("custom_components/modbus_local_gateway/device_configs").glob("Schneider_ATV312*.yaml"):
    print("checking", p)
    yaml.safe_load(p.read_text())
print("YAML OK")
PY
```

Repo test commands:

```bash
pytest tests/test_modbus_device_info.py -k test_devices_yaml
pytest
```

Validation status in this workspace:

Validation commands could not be executed because `pytest` is not installed in the current environment (`pytest: command not found`).
