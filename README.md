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

Or use these buttons (requires _My Home Assistant_):
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

#### Step 1: Gateway Connection Details

A config entry is a gateway: the Modbus TCP server itself.

- **Host**: Gateway IP/hostname (e.g., `192.168.1.100`).
- **Port**: TCP port (default: `502`).
- **Connection type**: `Modbus TCP` or `Modbus RTU over TCP`.

#### Step 2: Add the Devices Behind the Gateway

A gateway usually serves more than one device, so the devices are added to a gateway instead of each becoming a config entry of its own. Open the gateway's **Configure** page, choose **Add device**, and fill in:

- **Device ID**: Modbus device ID (e.g., `1`).
- **Prefix**: Optional device and entity name prefix (e.g., `Device 3`).
- **Device config**: the YAML file describing the model (e.g., `Eastron SDM-230` for `SDM230.yaml`).
- **Expected to be offline at times** (optional): for a device that switches itself off, such as a
  solar inverter after dark (default: off). See
  [Devices that are off at times](#devices-that-are-off-at-times).

Every device becomes a device of its own in Home Assistant, with the gateway as its parent, and can be reconfigured, reloaded or removed on its own. Devices that report the same model twice, on the same gateway, are refused: add the second one with a different prefix instead.

#### Entity IDs

Entities are created once and keep their entity ID from then on: the integration never renames an entity that already exists, so dashboards, automations and history survive an upgrade. Entities created from here on are named with the gateway host in front of the name, so that two gateways on one network cannot hand out the same entity ID. Reconfiguring a gateway can turn that prefix off for entities added later and, if asked for, move the entities of the devices back onto the entity IDs they had before the prefix existed — again by keeping the unique ID and the device, so nothing is re-registered and no history is lost.

### Modifying Existing Devices

Use **Configure** on the gateway to add, edit or remove the devices behind it, and **Configure** on a device to change the **update frequency** (default: 30 seconds) or the **register write function** of that device alone.

#### Devices that are off at times

Some devices are not always there to be read. A solar inverter shuts itself down when there is no
sun and comes back on its own when there is; a heat pump stops for the night; a device that is only
switched on while a machine is running is silent for the same reason. For those, a device being
unavailable is a normal part of its day rather than a fault, so **Expected to be offline at times**
is set on the device and:

- the change of state is logged as information rather than as a warning, so a night of silence does
  not wake anybody up for;
- everything else is unchanged. The device still goes unavailable, is still probed, and its entities
  still become available again by themselves when it comes back.

Nothing needs to be scheduled or automated around this; the setting only changes how quiet a normal
absence is.

#### Register Write Function

Holding register writes normally use _Preset Single Register_ (FC `0x06`). Some devices only implement _Preset Multiple Registers_ (FC `0x10`) and silently ignore FC `0x06`, so every write to them fails. In that case set **Register write function** to _Preset Multiple Registers_; the value count no longer matters and single values are sent as FC `0x10` too.

Coil writes always use _Force Single Coil_ (FC `0x05`) and are unaffected by this option.

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
  set_water_temp: # This key must uniquely identify the entity within the config file
    address: 20
    name: "Set Water Temperature"
    multiplier: 0.1
    control: number # Show a number input field in the Home Assistant UI
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
  - `probe_key` (optional): The entity name a
    [recovery probe](#troubleshooting) reads when checking whether the device is back. Use it for
    a device whose first entity is an expensive read, or one that answers slowly while it is
    waking up: name an entity the device answers as long as it is powered at all, such as a status
    word. The name has to be an entity of that device; anything else is logged and the first entity
    is used.

- **Register/Coil Sections** (optional):
  - `read_write_word`: Holding registers (read/write).
  - `read_only_word`: Input registers (read-only).
  - `read_write_boolean`: Coils (read/write).
  - `read_only_boolean`: Discrete inputs (read-only).

- **`composite` Section** (optional):
  - `composite`: Entities assembled from several registers (see
    [Composite Entities](#composite-entities)).

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
      number: # Optional
        min: 10.0 # float
        max: 100.0 # float
        step: 5 # optional (defaults to modbus multiplier or 1.0)
        mode: slider # optional: slider or box (default)
      ```
  - `control: select`: Creates a select entity.
    - E.g.:
      ```yaml
      control: select
      options: # Required
        0: "Closed"
        1: "Half-Open"
        2: "Open"
      ```
  - `control: switch`: Creates a switch entity.
    - E.g.:
      ```yaml
      control: switch
      switch: # Optional
        "on": 1 # default: 1
        "off": 0 # default: 0
      ```
  - `control: text`: Creates a text entity.

- **Data Types**:
  - `signed: true`: Signed integer values rather than the default of unsigned (requires `size: 1`, `size: 2` or `size: 4`).
  - `float: true`: Raw 32-bit float (requires `size: 2` or `size: 4`).
  - `string: true`: String (requires `size:` = length / 2).
    - E.g.
      ```yaml
      string: true
      size: 5 # For a 10 byte string
      ```
- **Math Operations** (applied in order):
  - `swap`: updates the byte ordering of the registers (`byte`, `word` or `word_byte`)
  - `sum_scale`: List of scaling factors applied to consecutive registers.
    - E.g., `sum_scale: [1, 10000]` for two registers starting at `address: 5` uses r1=5, r2=6, calculating r1 * 1 + r2 * 10000.
  - `shift_bits`: Bit shift right (integer).
  - `bits`: Bit mask length (integer).
    - On a **writable** entity (`control: number`, `control: select` or `control: switch`),
      `bits` and `shift_bits` make the entity address a _bit field_: the write becomes a
      read-modify-write, so the other bits of the register keep their values. The read and the
      write are issued under the client lock, so a poll cannot interleave between them.
    - This lets several independent controls share one register. E.g. two switches in register 0,
      one on bit 1 and one on bit 2, where toggling either leaves the other untouched:
      ```yaml
      heating:
        address: 0
        bits: 1
        shift_bits: 1
        control: switch
      hot_water:
        address: 0
        bits: 1
        shift_bits: 2
        control: switch
      ```
    - `signed` and `sum_scale` are rejected on a _writable_ bit field — neither has a meaningful
      inverse when merging a value back into part of a register. They remain valid on read-only
      entities.
  - `multiplier`: Scaling factor (float).
  - `offset`: Adds an offset (float).
- **Display**:
  - `precision`: Decimal places (integer). Only valid for `sensor` or `control: number` entities.
  - `map`: Enum mapping. A value with no entry falls back to the converted number (after
    `multiplier`, `offset`, `bits` and `shift_bits`), so the state is either a label or a number.
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
  - `no_flag_value`: State to report when none of the `flags` bits is set (string or
    integer). Without it, the converted number is reported, which is the raw register
    value on a fault register nothing is flagged for. Useful where the register is an
    error code and "no error" needs its own state.
    - E.g.
      ```yaml
      flags:
        1: "Sensor fault"
        2: "Communication fault"
      no_flag_value: "No error"
      ```
- **Behavior**:
  - `never_resets: true`: For non-resetting totals. (E.g. for sensors with `state_class: total_increasing`).
  - `unavailable_values`: Register values that mean "no reading" - the sentinel many devices publish
    (commonly `0xFFFF`, `0xFF` or `0`) when a sensor is absent or a function is inactive. The entity
    goes **unavailable** while one is reported, which also keeps it out of long-term statistics.
    Matched against the **raw register value**: after `bits` / `shift_bits`, before `multiplier` and
    `offset`.
    - E.g.
      ```yaml
      unavailable_values: [255, 0]
      ```

#### Coil Properties (`read_write_boolean`, `read_only_boolean`)

- **Control Types** (only for `read_write_boolean`): Allows the user to control the value.
  - `control: switch`: Creates a switch entity.
    - E.g.:
      ```yaml
      control: switch
      switch: # Optional
        "on": 1 # default: 1
        "off": 0 # default: 0
      ```
  - `control: binary_sensor`: Creates a binary_sensor entity.
    - E.g.:
      ```yaml
      control: binary_sensor
      "on": False # Optional - default: True
      "off": True # Optional - default: False
      ```

### Composite Entities

Some devices split a date, a time or a timestamp across several registers. A
`composite` entity assembles them into a single Home Assistant `datetime`
entity, which is writable when its registers are writable:

```yaml
composite:
  current_time:
    name: Current Time
    type: datetime
    data_type: read_write_word # default: read_write_word
    fields:
      year: { address: 45, offset: 2000 }
      month: { address: 46 }
      day: { address: 47 }
      hour: { address: 48 }
      minute: { address: 49 }
      second: { address: 50 }
```

- `type` (required): Which parts the entity carries.
  - `date`: `year`, `month` and `day` (required).
  - `time`: `hour` and `minute` (required).
  - `datetime`: `year`, `month`, `day`, `hour` and `minute` (required).
  - `second`: Optional for `time` and `datetime`, not allowed for `date`; a
    clock without it reads on the minute.
- `data_type` (optional): `read_write_word` (default, writable) or
  `read_only_word` (read-only). A coil cannot hold a composite.
- `fields` (required): One entry per part, each an `address` and any of
  `size`, `swap`, `multiplier`, `offset`, `write_offset`, `unavailable_values`,
  `bits`, `shift_bits`, `signed`, `float` and `string`, exactly as for a
  register entity. A field name that is not a part of `type`, an unknown key,
  `map` or `flags` is rejected with a warning and the entity is skipped.
- `write_offset` (optional, field): Added to the value on the way out only, for
  a device that reads one value and writes another: `offset` is applied in both
  directions, so it cannot describe a register that reports a four digit year
  and takes a two digit one. It is rejected on a field of more than one
  register, on a bit field and on a `swap` field, since none of them carries a
  single value the offset could belong to.
- Fields that are **not adjacent** are grouped: each run of adjacent registers
  is read with its own request, so the registers in between are never touched,
  and written in one request per run (FC `0x10`, or FC `0x06` for a run of one
  register). A clock in registers 45-50 is therefore read in one request and
  written in one request per run, unless it sets `write_function: single`.
- `write_function` (optional): `single` writes each register of a run with its
  own FC `0x06` request instead of one FC `0x10` over the run, for a device that
  refuses the block write across a clock. The request then costs one round trip
  per register, and each keeps the fallback to FC `0x10` for a device that does
  not answer FC `0x06` at all. Absent, the connection's own `write_function`
  decides, so every other device config is unaffected.
- The entity-level options of any other entity work here too: `scan_interval`,
  `icon`, `entity_category` and `entity_registry_enabled_default`.
- A field may claim **part of a register** with `bits` / `shift_bits`, which is
  how some devices pack a time together with a mode and an enable flag:

  ```yaml
  composite:
    period1_start:
      name: Period 1 Start Time
      type: time
      fields:
        minute: { address: 3038, bits: 8, shift_bits: 0 }
        hour: { address: 3038, bits: 5, shift_bits: 8 }

  read_write_word:
    period1_mode: # the same register, other bits, as its own entity
      name: Period 1 Mode
      address: 3038
      control: select
      bits: 2
      shift_bits: 13
      options: { 0: Load, 1: Battery, 2: Grid }
  ```

  The bits the composite does not describe are left as the device has them: a
  write reads the registers first and merges its fields into them, inside the
  same lock a poll takes, so the enable and mode bits survive. Two fields of one
  composite must not claim the same bits, and `signed` is rejected on a bit
  field.

- Several entities on **one register** are read from a single transaction when
  the read succeeds: a poll asks the device once for a register, however many
  of the device's entities read it, and they all report that one snapshot. A
  read that failed is not kept, so a later entity on that register asks again
  rather than reporting the failure of someone else's read. Entities that
  share a register but not its register bank are still read separately.

- A part the device reports as unavailable - or one that cannot form a real
  date or time - makes the entity **unavailable**, rather than publishing an
  error.
- The value is stamped with Home Assistant's local timezone, since a device
  clock is a wall-clock reading, and a value that arrives with an offset is
  brought into local time before it is written back, so the two sides agree.

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
- **A device that is not answering at start-up**: a device behind a gateway is read once after
  Home Assistant has finished starting, so a device that is switched off costs one timeout, not
  one per entity, and it never holds up the start. Its entities show as unavailable until it
  answers, the other devices behind the same gateway are unaffected, and a poll that meets a
  device that has gone quiet keeps the values it had already read.
- **A device that is off says so once**: the log gets one warning when a device stops answering
  and one info line when it answers again, with how long it was gone, and nothing in between
  however many polls pass. A device that answers some of the registers asked for and not others
  is a different thing and is warned about every poll, naming the entities that had no usable
  response.
- **A device that is off is not polled every cycle**: a device that stops answering is put on a
  backoff of 5, 10, 20, 40, 80 and then 120 seconds, so an inverter that is off for a ten-hour night
  costs about three hundred reads instead of thousands. Nothing is queued up or timed in the
  background: each poll that comes round while the device is backing off reads nothing at all and
  returns immediately, so the other devices behind the same gateway are not held up, and no task is
  left running to clean up on unload. Entities that read on their own `scan_interval` do not read
  a device that is off either, for the same reason: the refresh of the whole device is what asks
  whether it is back, and one read per entity per timer is how a device that is off for the night
  would fill the bus and the log. So that refresh is what finds it back, and while a device is off
  it reads the whole device, including the entities that have their own timer - otherwise a device
  whose entities all poll on their own timers would have nothing left to ask it with.
- **One answer brings a device back, and the rest of it comes with it**: the refresh after a
  deadline reads one entity to ask whether the device is back - the entity named by `probe_key`, or
  the device's first entity - and one usable answer is enough to bring its entities back. The rest
  of the poll carries on in that same read, so everything the device does answer is fresh at once
  rather than one entity now and the others whenever their own timer next comes round. An answer
  that came back but could not be used does not count as recovery, which is what stops a device that
  wakes up mid-read from being written off again. A device that answers the probe and then goes quiet
  again is on the bus, so it is treated as back: the values it did answer are kept, the entities
  that had no usable response are warned about as usual, and it is polled normally from the next
  cycle.
- **A gateway that will not connect is left alone too**: a gateway that cannot be reached is
  retried after 2, 5, 15, 30 and then 60 seconds rather than once per device per refresh. Writes
  are not held back by either backoff: a write is asked for by a person waiting for it, and is
  told when it did not get through. Nothing written is ever replayed when a device comes back,
  because a write can be a command.
- **A device that is expected to be off** (see
  [Devices that are off at times](#devices-that-are-off-at-times)): with the setting on, the same
  transitions are logged as information instead of as warnings, so a device that switches itself off
  is not reported as a fault.
- **Writes Fail with "No response received after 5 retries"**: some devices only implement
  _Preset Multiple Registers_ (FC `0x10`). A single-value write to them now falls back to
  FC `0x10` on its own, and the log says which attempt failed and why.
- **A write that never got an answer is not repeated blindly**: because writing a holding
  register can run a command, a write whose response went missing is read back first. If the
  register already holds the value the write is treated as done and nothing is written again;
  if it still holds its old value, the FC `0x10` fallback only runs for devices that have
  never answered a preset single register write, since for those the function is unimplemented
  rather than the response lost. When the read-back cannot be answered, the write is reported
  as failed and nothing is repeated.
- **"request ask for transaction_id ... but got id ..." or "extra data" in the logs**: this is
  the bridge, not the integration. A gateway that bridges TCP to a shared serial bus answers late
  when the bus is busy, and once a request has timed out its answer is still on the way, so the
  next request collects it before its own: from then on, the gateway is one response ahead for good.
  The integration counts the answers that belong to a request nobody is waiting for, and when a
  read fails while such answers are in flight it treats the bridge as out of step — the poll ends
  there and the next poll starts on a renewed connection, which drops what the bridge had queued.
  A read that comes back matched clears the count, so a gateway that is only a moment behind is
  never disconnected. The warning for a failed poll carries the number of times the connection had to be resynchronised; the count of out-of-order answers is on the connection. Devices behind one
  gateway are polled one request at a time and each device keeps its own update frequency. If the
  messages persist, reduce how often the devices are polled, check the bridge's TCP time-out and
  max-connection settings, or update its firmware; a serial bus shared with another master (a
  second integration, or the vendor's own tool) produces the same symptom.
- **A device answers with an exception the config does not explain**: check the device's own
  documentation for the function code and exception code in the log. Some devices answer a
  function they do not implement with an exception whose code is `0`, which the device reports
  as a failure rather than an error in the configuration.
- **RTU over TCP cannot tell responses apart**: with the RTU connection type the answer to a
  request carries no transaction id, so a gateway that answers one request late can hand back the
  previous answer for a _different register of the same device_. A response with the wrong number
  of registers or bits is detected and rejected, but two reads of the same length cannot be told
  apart from the bytes alone. If a device only speaks RTU over TCP, keep its update frequency
  generous; a gateway that answers in Modbus TCP is matched on the transaction id and is not
  affected.

## Supported Devices

Tested with a [WaveShare Wi-Fi to RS485 Gateway](https://www.waveshare.com/rs485-to-wifi-eth.htm) in Modbus TCP to RTU mode:

- **Settings**: Baud Rate: 9600, Data Bits: 8, Parity: None, Stop Bits: 1, Baudrate Adaptive: Disable, UART AutoFrame: Disable, Modbus Polling: Off, Network A TCP Time out: 5, Network A MAX TCP Num: 24.
- **Tested Slaves**: Eastron SDM230/SDM630, Finder 7M.38/7M.24, Growatt MIN-6000-TL-XH/MOD-6000-TL-X/MIC-2500-TL-X.

Firmware variations may affect compatibility.

## Contributing

We welcome contributions! Please open an issue to discuss your ideas or submit a PR against the `main` branch. Ensure your code follows the existing style, passes the test suite, and update this README with any new instructions.

## License

MIT License. See repository for details.
