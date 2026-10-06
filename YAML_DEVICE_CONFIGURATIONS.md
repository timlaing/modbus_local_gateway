# Creating YAML Device Configurations

To add support for a new device, create a YAML file in `/config/modbus_local_gateway/`. Each file specifies the Modbus registers/coils for a single device, mapping them to corresponding Home Assistant entities.

Any files in `/config/modbus_local_gateway/` will override those as part of this repo (`custom_components/modbus_local_gateway/device_configs/`).
Once you are happy with your configuration, please consider sharing with others by creating a pull request with your config file.

## Minimal Example

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

## YAML Structure

Each file requires a `device` section and optional register/coil sections:

- **`device` section** (required):
  - `manufacturer` (required): String.
  - `model` (required): String.
  - `max_register_read` (optional): Max registers per read (default: 8).
  - `probe_key` (optional): The entity name a
    [recovery probe](README.md#troubleshooting) reads when checking whether the device is back. Use it for
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

### Common Properties

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

### Register Properties (`read_write_word`, `read_only_word`)

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

### Coil Properties (`read_write_boolean`, `read_only_boolean`)

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

## Composite Entities

Some devices split a date, a time or a timestamp across several registers. A
`composite` entity assembles them into a single Home Assistant `time`, `date` or
`datetime` entity, which is writable when its registers are writable:

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

- `type` (required): Which parts the entity carries, and which Home Assistant
  platform the entity is created on: `time` on a `time` entity, `date` on a
  `date` entity and `datetime` on a `datetime` entity.
  - `date`: `year`, `month` and `day` (required).
  - `time`: `hour` and `minute` (required).
  - `datetime`: `year`, `month`, `day`, `hour` and `minute` (required).
  - `second`: Optional for `time` and `datetime`, not allowed for `date`; a
    clock without it reads on the minute.
  - A composite of `date` or `time` used to be created as a `datetime` entity,
    with a date on the value that the device never reported. On upgrade those
    entities move to their own platform, keeping the object id: a
    `datetime.test_period1_end` entity becomes `time.test_period1_end`. The
    recorder holds the history of the old entity id, and automations that name
    the old entity id have to be updated.
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
  not answer FC `0x06` at all. A run of more than one register is always written
  with FC `0x10` unless this says `single`, whatever the connection is set to;
  the connection's own `write_function` decides only for a run of one register.
  Absent, nothing changes, so every other device config is unaffected.
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

## Example YAML

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
