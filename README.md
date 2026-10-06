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

The full reference - structure, register and coil properties, composite
entities and a worked example - lives in
[YAML_DEVICE_CONFIGURATIONS.md](YAML_DEVICE_CONFIGURATIONS.md).

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

The devices a configuration ships for are listed in
[SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md), together with the file that
describes each one.

### Tested Devices

Tested with a [WaveShare Wi-Fi to RS485 Gateway](https://www.waveshare.com/rs485-to-wifi-eth.htm) in Modbus TCP to RTU mode:

- **Settings**: Baud Rate: 9600, Data Bits: 8, Parity: None, Stop Bits: 1, Baudrate Adaptive: Disable, UART AutoFrame: Disable, Modbus Polling: Off, Network A TCP Time out: 5, Network A MAX TCP Num: 24.
- **Tested Devices**: Eastron SDM-230, Growatt MIC 2500TL-X, Growatt MIN 6000TL-XH.

Firmware variations may affect compatibility.

## Contributing

We welcome contributions! Please open an issue to discuss your ideas or submit a PR against the `main` branch. Ensure your code follows the existing style, passes the test suite, and update this README with any new instructions.

## License

MIT License. See repository for details.
