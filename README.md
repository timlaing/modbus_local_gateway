# Modbus Local Gateway Integration for Home Assistant

[![Build Status](https://github.com/timlaing/modbus_local_gateway/actions/workflows/tests.yml/badge.svg)](https://github.com/timlaing/modbus_local_gateway/actions/workflows/tests.yml)
[![GitHub stars](https://img.shields.io/github/stars/timlaing/modbus_local_gateway.svg)](https://github.com/timlaing/modbus_local_gateway/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/timlaing/modbus_local_gateway.svg)](https://github.com/timlaing/modbus_local_gateway/issues)
[![GitHub license](https://img.shields.io/github/license/timlaing/modbus_local_gateway.svg)](LICENSE)

[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=timlaing_modbus_local_gateway&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=timlaing_modbus_local_gateway)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=timlaing_modbus_local_gateway&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=timlaing_modbus_local_gateway)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=timlaing_modbus_local_gateway&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=timlaing_modbus_local_gateway)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=timlaing_modbus_local_gateway&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=timlaing_modbus_local_gateway)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=timlaing_modbus_local_gateway&metric=bugs)](https://sonarcloud.io/summary/new_code?id=timlaing_modbus_local_gateway)
[![Lines of Code](https://sonarcloud.io/api/project_badges/measure?project=timlaing_modbus_local_gateway&metric=ncloc)](https://sonarcloud.io/summary/new_code?id=timlaing_modbus_local_gateway)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

## Introduction

This custom Home Assistant integration enables communication with Modbus devices via a Modbus TCP gateway. It uses YAML configuration files to define device registers and coils, mapping them to Home Assistant entities like sensors, switches, numbers, and more. It supports both monitoring (read-only) and control (read/write) operations.

## Installation

[![HACS badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

The easiest way to install this integration is through the [Home Assistant Community Store (HACS)](https://hacs.xyz/). After setting up HACS, you can add this integration as a custom repository:

1. Go to HACS > Integrations.
2. Click the three-dot menu and select "Custom repositories".
3. Add repository:
   `https://github.com/timlaing/modbus_local_gateway`
4. Set category to "Integration" and click "Add".
5. Search for "Modbus Local Gateway" and install.

Or use these buttons (requires *My Home Assistant*):
[![Open HACS Repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=timlaing&repository=modbus_local_gateway&category=integration)

Restart Home Assistant after installation.

For support and discussions, join our Discord community: [Join our Discord community](https://discord.gg/rQ2cZ6K5YY)

## Configuration

### Adding a New Device

Add devices via the Home Assistant UI:
1. Go to **Settings > Devices & Services**.
2. Click **Add Integration**, search for "Modbus Local Gateway".
3. Or use this button:
   [![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=modbus_local_gateway)

#### Step 1: Connection Details
- **Host**: Gateway IP/hostname (e.g., `192.168.1.100`).
- **Port**: TCP port (default: `502`).
- **Device ID**: Modbus device ID (e.g., `1`).
- **Prefix**: Optional device and entity name prefix (e.g., `Device 3`).

#### Step 2: Device Selection
Choose a device type from the dropdown (e.g., `Eastron SDM-230` for `SDM230.yaml`).

### Modifying Existing Devices

Adjust the **update frequency** (default: 30 seconds) via "Configure" at the device in **Devices & Services**.

## Creating YAML Device Configurations

To add support for a new device, create a YAML file in `/config/modbus_local_gateway/`. Each file specifies the Modbus registers/coils for a single device, mapping them to corresponding Home Assistant entities.

Any files in `/config/modbus_local_gateway/` will override those as part of this repo (`custom_components/modbus_local_gateway/device_configs/`).
Once you are happy with your configuration, please consider sharing with others by creating a pull request with your config file.

### Minimal Example
```yaml
device:
  manufacturer: "Dimplex"
  model: "Wärmepumpe SI 11TU"

read_write_word:

  set_water_temp:    # This key must uniquely identify the entity within the config file
    address: 20
    name: "Set Water Temperature"
    multiplier: 0.1
    control: number  # Show a number input field in the Home Assistant UI
    number:
      min: 0
      max: 100
```

### YAML Structure

Each file requires a `device` section and optional register/coil sections:

- **`device` section** (required):
  - `manufacturer` (required): String.
  - `model` (required): String.
  - `max_register_read` (optional): Max registers per read (default: 8).

- **Register/Coil Sections** (optional):
  - `read_write_word`: Holding registers (read/write).
  - `read_only_word`: Input registers (read-only).
  - `read_write_boolean`: Coils (read/write).
  - `read_only_boolean`: Discrete inputs (read-only).

Each register/coil section contains entity definitions, identified by a unique key (e.g., `set_water_temp`), mapping registers/coils to Home Assistant entities.

#### Common Properties

For all entity definitions:
- `address` (required): Modbus address (integer).
- `name` (optional): Friendly name (default: the entity definition's key).
- `size` (optional): Register count (default: 1; use 2 for raw 32-bit `float`, or string length / 2 for `string`; not needed for `sum_scale`).
- `scan_interval` (optional): Override the default update interval for this entity. Used to increase or decrease the frequency of polling.

- **Home Assistant Properties** (see HA documentation for more information):
  - `unit_of_measurement`: E.g., `Volts`, `h`.
  - `device_class`: E.g., `voltage`, `power`.
  - `state_class` (only for register): E.g., `measurement`, `total_increasing`.
  - `entity_category`: `diagnostic` or `config`.
  - `entity_registry_enabled_default: False`.
  - `icon: mdi:thermometer`.

#### Register Properties (`read_write_word`, `read_only_word`)

- **Control Types** (only for `read_write_word`): Allows the user to control the value.
  - `control: number`: Creates a number entity.
    - E.g.:
      ```yaml
      control: number
      number:         # Optional
        min: 10.0     # float
        max: 100.0    # float
        step: 5       # optional (defaults to modbus multiplier or 1.0)
        mode: slider  # optional: slider or box (default)
      ```
  - `control: select`: Creates a select entity.
    - E.g.:
      ```yaml
      control: select
      options:        # Required
        0: "Closed"
        1: "Half-Open"
        2: "Open"
      ```
  - `control: switch`: Creates a switch entity.
    - E.g.:
      ```yaml
      control: switch
      switch:         # Optional
        "on": 1       # default: 1
        "off": 0      # default: 0
      ```
  - `control: text`: Creates a text entity.

- **Data Types**:
  - `signed: true`: Signed integer values rather than the default of unsigned (requires `size: 1`, `size: 2` or `size: 4`).
  - `float: true`: Raw 32-bit float (requires `size: 2` or `size: 4`).
  - `string: true`: String (requires `size:` = length / 2).
    - E.g.
      ```yaml
      string: true
      size: 5       # For a 10 byte string
      ```
- **Math Operations** (applied in order):
  - `swap`: updates the byte ordering of the registers (`byte`, `word` or `word_byte`)
  - `sum_scale`: List of scaling factors applied to consecutive registers.
    - E.g., `sum_scale: [1, 10000]` for two registers starting at `address: 5` uses r1=5, r2=6, calculating r1 * 1 + r2 * 10000.
  - `shift_bits`: Bit shift right (integer).
  - `bits`: Bit mask length (integer).
  - `multiplier`: Scaling factor (float).
  - `offset`: Adds an offset (float).
- **Display**:
  - `precision`: Decimal places (integer). Only valid for `sensor` or `control: number` entities.
  - `map`: Enum mapping.
    - E.g.
      ```yaml
      map:
        0: "Enabled"
        1: "Disabled"
        2: "Auto"
      ```
  - `flags`: Bit flags.
    - E.g.
      ```yaml
      flags:
        1: "Pump active"
        3: "Mill active"
        4: "Heating active"
      ```
- **Behavior**:
  - `never_resets: true`: For non-resetting totals. (E.g. for sensors with `state_class: total_increasing`).

#### Coil Properties (`read_write_boolean`, `read_only_boolean`)
- **Control Types** (only for `read_write_boolean`): Allows the user to control the value.
  - `control: switch`: Creates a switch entity.
    - E.g.:
      ```yaml
      control: switch
      switch:         # Optional
        "on": 1       # default: 1
        "off": 0      # default: 0
      ```
  - `control: binary_sensor`: Creates a binary_sensor entity.
    - E.g.:
      ```yaml
      control: binary_sensor
      "on": False       # Optional - default: True
      "off": True       # Optional - default: False
      ```
### Example YAML

```yaml
device:
  manufacturer: Rekall
  model: MindSync Hub 310

read_write_word:

  baud_rate:
    address: 28
    control: select
    options:
      0: "2400 bps"
      1: "4800 bps"
      2: "9600 bps"

  power_mode:
    address: 30
    control: switch
    switch:
      "on": 1
      "off": 0

  register_1:
    name: "Boolean Register"
    address: 0x0004
    bits: 1
    shift_bits: 4
    device_class: running
    control: binary_sensor

read_only_word:

  voltage:
    address: 0
    precision: 2
    unit_of_measurement: Volts
    device_class: voltage
    state_class: measurement

read_write_boolean:

  power_switch:
    address: 10
    control: switch

read_only_boolean:

  status:
    address: 15
    device_class: power
```
See `custom_components/modbus_local_gateway/device_configs/` for more examples.

## Troubleshooting

- **Logs**: Enable debug logging in `configuration.yaml`:
  ```yaml
  logger:
    default: info
    logs:
      custom_components.modbus_local_gateway: debug
  ```
- **Connection Issues**: Verify gateway IP, port, and device ID.

## Supported Devices

Tested with a [WaveShare Wi-Fi to RS485 Gateway](https://www.waveshare.com/rs485-to-wifi-eth.htm) in Modbus TCP to RTU mode:
- **Settings**: Baud Rate: 9600, Data Bits: 8, Parity: None, Stop Bits: 1, Baudrate Adaptive: Disable, UART AutoFrame: Disable, Modbus Polling: Off, Network A TCP Time out: 5, Network A MAX TCP Num: 24.
- **Tested Slaves**: Eastron SDM230/SDM630, Finder 7M.38/7M.24, Growatt MIN-6000-TL-XH/MOD-6000-TL-X/MIC-2500-TL-X.

Firmware variations may affect compatibility.

## Contributing

We welcome contributions! Please open an issue to discuss your ideas or submit a PR against the `main` branch. Ensure your code follows the existing style, passes the test suite, and update this README with any new instructions.

## License

MIT License. See repository for details.
