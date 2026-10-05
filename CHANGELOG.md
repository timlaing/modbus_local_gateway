# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

Releases up to `v2.0.0` follow SemVer. From `2025.3.1` on, versions are
CalVer (`YYYY.M.PATCH`) because Home Assistant expects date-based versions for
custom integrations. Pre-releases are not listed here.

## [v2026.10.1] - 2026-10-05

### Added

- **A composite field can read one value and write another**: `offset` is
  applied in both directions, so it cannot describe a register that reports one
  value and takes another. The Growatt clock is such a register: holding
  register 45 (`Sys Year`) reports a four digit year and only accepts a two
  digit one, so every write of the Growatt `current_time` composite was
  refused with an illegal data address. A field can now carry a `write_offset`,
  added to the value on the way out only and leaving the read untouched, and four
  Growatt device configs use it to write `26` for `2026`: `MIC-2500TL-X`,
  `MIN-6000TL-XH`, `MOD-6000TL-X` and `MOD-10KTL3-XH`. `SPH-3600TL-BL_UP` is left
  alone, because a report of a different Growatt family taking the full year
  there suggests it wants the opposite, and it has not been confirmed on
  hardware. A field of more than one register is rejected, since one offset says
  nothing about which of its registers it was meant for, as are `swap` and bit
  fields, which carry no single value to offset.

- **A composite entity can be written register by register**: a run of adjacent
  registers is written with one FC `0x10` request, which keeps a clock from
  being left half updated - but a device that refuses the block write across its
  clock can only be written one register at a time, and every write was
  preceded by a request that came back as an exception. A composite entity can
  now declare `write_function: single`, which writes each register of a run
  with its own FC `0x06` request, each keeping the existing fallback to FC `0x10`
  for a device that does not answer FC `0x06` at all. This is per entity rather
  than a change to the connection-wide option, because on this hardware the
  clock is the exception while the settings registers around it generally need
  the block write. Absent the declaration nothing changes, so every other device
  config is unaffected. Both are documented in the README.

- A composite entity of `type: time` is now created as a `time` entity, and one
  of `type: date` as a `date` entity, instead of both being `datetime` entities.
  A time used to carry today's date, which the device never reported.

### Changed

- **A gateway added from now on names its entities after the gateway**: `legacy_entity_ids` defaulted to on, so a gateway set up from scratch had every entity it would ever create keep an unprefixed name that does not say which gateway it is on — `sensor.pool_temperature` rather than `sensor.shed_pool_temperature`. The setting exists to protect entities that already exist, and a new gateway has none, so the default is now off. Only gateways added from now on are affected, and **nothing is renamed**: entities that already exist keep their IDs whether or not the switch is touched, and a gateway set up before one-entry-per-gateway is migrated onto `legacy_entity_ids: true` explicitly rather than following this default, which is also what keeps it being offered **Restore entity ids of this integration** — the one-click way back to the IDs it had. The setting itself is unchanged and can still be switched on for entities added later.

### Fixed

- **The buttons on the integration page say what they add**: the gateway button said "Add device", the same as the button that adds a device behind a gateway, so it was not possible to tell which was which. The gateway button now says "Add gateway". A Home Assistant release that added device sub-entries to this integration also named it a device itself, which is where the wrong button came from.

- **Devices behind a gateway are named after the device id they answer to**: the list of devices behind a gateway said "slave 2" or "test slave 1", which is the raw id of the device rather than the name it goes by in the rest of Home Assistant. A device is now named "Device ID: 2", with the prefix when it has one: "Device ID: 1 (test)". Reconfiguring a device renames it, so a device that was renamed keeps the name of the settings it has now, and the device registry, its area, its history and the cards pointing at it are untouched. New devices get this name; devices that already exist keep theirs, since the name is only in the list of devices and not in any entity id.

## [v2026.10.0] - 2026-10-04

### Added

- **A device can say it is expected to be offline**: a device that switches itself off - a solar inverter when there is no sun, a heat pump overnight, a device only switched on while a machine is running - is unavailable for a normal reason, and was reported as a fault every time it went away. A device sub-entry now has an **Expected to be offline at times** setting (off by default, so existing devices are unaffected), and with it on the change of state is logged as information instead of a warning: a night of silence is no longer something to be woken up for. Nothing else changes. The device still goes unavailable, is still probed on the backoff above, and its entities still come back by themselves when it does - this only decides how loud a normal absence is. A device config can also name `probe_key`, the entity a recovery probe reads when checking whether the device is back, for a device whose first entity is an expensive read or one it answers slowly while it is waking up; the name has to be an entity of that device, and anything else is logged and ignored rather than leaving the probe reading nothing. Both are documented in the README.

- **A device that is off is found back by its refresh, not by its entities**: a device that stops answering is put on a backoff, but the entities that read on their own `scan_interval` kept reading it anyway, once per entity per timer for as long as it was off - so a device with a dozen such entities cost a dozen reads per timer while nothing was there, and finding it back was left to a read that could not say whether the rest of it was there. Those reads are now left off while the device is away, and the refresh of the whole device asks instead: it covers the entities that have their own timer as well while the device is off, so a device whose entities all poll on their own timers is still found back. Nothing is scheduled to find it: it is the refresh that comes round anyway, and one read of the entity it nominates - `probe_key`, or the first entity - brings the device back and the rest of that same poll is read as normal, so every entity is fresh at once rather than one now and the others whenever their own timer next comes round. An answer that came back but could not be used still does not count as recovery, which is what stops a device that is still waking up from being written off again, and a device that answers the probe and then goes quiet is treated as back - it is on the bus, so the values it answered are kept and it is polled normally from the next cycle. A device read on its own that times out no longer puts the whole device on a backoff over one register, and a protocol error, an illegal address or a failed conversion is still not an outage, because the device is on the bus and talking. The backoff tail is 120 seconds rather than the 300 this was first written with, and a poll that comes round before a deadline reads nothing and returns at once: nothing is queued, no task is left behind for a reload or a disable to clean up, and no device behind the same gateway is held up behind it. What is known about a device lives on the client, keyed by its device id, so it covers every way of asking a device for a value at once - the shared refresh, an entity on its own interval, a recovery probe - and all of them obey the same backoff and say the same thing about it. Documented in the README.

- **A gateway that will not connect is left alone too**: a gateway that could not be reached was retried by every device behind it, on every refresh, which is the same problem as a device that is off one level up. It now backs off to one connection attempt every 2, 5, 15, 30 and then 60 seconds, and the state of it is on the connection, where it can be read. Writes are not held back by either backoff: a write is asked for by a person waiting for it, so it is not gated, and it is told when it did not get through. Nothing written is ever replayed when a device comes back, because a write can be a command.

- **One gateway entry, one sub-entry per device**: a config entry used to be one device on one gateway, so an installation with ten devices behind one gateway had ten config entries to add, reload and remove, ten connections opened to the same host, and ten gateway devices in the UI that were really the same gateway. A config entry is now the gateway (`host`, `port`, `connection type`) and every device behind it is a sub-entry (`device id`, `prefix`, `device config`, `update frequency`, `register write function`), added, changed and removed from the gateway's **Configure** page. Devices keep their own device, their own entities and their own settings, the gateway is their parent device in the UI, and a gateway that several config entries pointed at is set up once: the connection is still shared per `host:port:framer`, and now so is the poll result. Existing installations are migrated on the first start after the upgrade — entities are moved onto the sub-entries and the gateway devices of the group are merged into one — with every entity ID, unique ID, device ID, disabled state, area assignment and dashboard kept as it was, and the update frequency and register write function of each device carried over per device.

- **Composite date, time and datetime entities**: a device that splits a clock across several registers had no way to show it as one value — the date, the time and the year each had to be a separate entity, and none of them could be set. A `composite` entity assembles the registers it declares into a single Home Assistant `datetime` entity, writable when its registers are: `type` says which parts it carries (`date`, `time` or `datetime`), `data_type` says whether those are holding or input registers, and `fields` maps each part to its address. Fields that are not adjacent are grouped into runs of adjacent registers, so each run is read with its own request (the registers in between are never touched) and written in one request per run (FC `0x10`, or FC `0x06` for a run of one register) — a clock in registers 45-50 is always updated as one request instead of leaving the device with half a timestamp. `second` is optional for `time` and `datetime` (a `date` has no seconds), a part the device reports as unavailable or that cannot form a real date makes the entity unavailable rather than publishing an error, and the value is stamped with Home Assistant's local timezone, since a device clock is a wall-clock reading — a value that arrives with an offset, such as the entity's own state in UTC, is converted back to local time before it is written, so the two sides agree. The entity-level options of any other entity work on a composite as well: `scan_interval`, `icon`, `entity_category` and `entity_registry_enabled_default`. Conversion options are per field (`size`, `swap`, `multiplier`, `offset`, `unavailable_values`, `signed`, `bits`, `shift_bits`), so `offset: 2000` on a two-digit year still works, and a device that packs a time into one register next to a mode and an enable flag can show that time as one entity while the other bits stay their own entities: a field may claim part of a register, and the write reads the registers first and merges into them so the bits the composite does not describe survive. Two fields of one composite may not claim the same bits. Documented in the README.
- **Read-modify-write for bit fields**: a register that packs several independent controls could be read with `bits` / `shift_bits` but never written, because Modbus has no bit write for holding registers. Writing such a field now reads the register, replaces only that field and writes it back, inside the same client lock `update_device()` takes, so no poll or other write on that gateway can land in between. No new YAML syntax — `bits` / `shift_bits` already describe the geometry the merge needs. A value that does not fit its mask raises rather than truncating, a failed read aborts the write instead of merging onto a guess, and the field is read in one transaction so a field split across two reads cannot tear. `signed` and `sum_scale` are rejected on writable bit fields because the merge cannot express their arithmetic; coils still reject `bits` entirely. Documented in the README.
- **`unavailable_values` on an entity**: devices publish a sentinel when a sensor is absent or a function is inactive — commonly `0xFFFF`, `0xFF` or `0` — and the integration published it as a real reading. A device config can now declare `unavailable_values`, and the entity goes unavailable while one of them is reported, which keeps the sentinel out of long-term statistics entirely instead of only off a dashboard. Used by the Midea heat-pump config for the curve-setpoint registers that read 255 with the climate curve off.
- **`no_flag_value` on an entity**: a register used as a bit-flag field — typically an error code — had no state of its own for "nothing is flagged", so the sensor reported the raw register value and the fault it had shown before could not be distinguished from a clear reading. A device config can now declare `no_flag_value`, and that value is reported whenever none of the entity's `flags` bits is set, e.g. `no_flag_value: "No error"`. Without the key the raw number is still reported, so existing configs are unaffected. A value a sensor cannot hold (a float, bool, list or mapping) is rejected at load with a warning. Documented in the README.
- **One transaction per register per poll**: entities that read the same register each asked the device for it, so a register several entities share cost one request per entity - the three entities of a Growatt time-of-use window (start time, mode and enable) tripled the traffic of that register, and a poll of the `MOD 6000TL-X` spent 117 transactions where 98 are needed. A poll now asks once per device, register bank and range, and every entity on that register answers from that one answer, which also means they report the same snapshot rather than three readings of a moving value. Nothing is remembered past the poll: the next poll asks the device again, a read that failed is not kept so the next entity tries again instead of inheriting the failure, and a holding register and an input register that happen to share a number are still read separately, because they are different registers.
- **Configurable register write function**: the write function was picked from the value count alone, so a single value always went out as _Preset Single Register_ (FC `0x06`) and a device that only implements _Preset Multiple Registers_ (FC `0x10`) ignored every write to it. The config entry options gain a **Register write function** selector, the counterpart of the official `modbus` integration's `write_registers` option; selecting _Preset Multiple Registers_ sends all holding register writes as FC `0x10`, single values included. It defaults to _Preset Single Register_, so existing entries keep the behaviour they had, and no config entry migration is needed. The selection is read from the config entry on every write rather than stored on the client, because one client is cached per `host:port:framer` and shared by every entry pointing at the same gateway. Coils are unaffected and keep using FC `0x05`. Documented in the README.

### Fixed

- **The Eastron meter's own settings were read and written as if they were floats**: the communicate address, baud rate and energy unit prefix of the SDM630 and SDM230 are single 16-bit registers - a slave id of 1-247, and indexes into small option lists - but were declared as two-register floats, matching the 32-bit measurement registers they sit beside. A write packed the value into two registers and went out as _Preset Multiple Registers_ (FC `0x10`) across the register and the reserved one after it, which these meters refuse, so setting the baud rate or the address failed with no answer from the device; a read spanned the same pair and decoded a float out of a register and a reserved one, so the setting on the device never matched an option either. Each is now declared as the one register it is: a write is FC `0x06` to that register, and a read is that register's own value.

- **An entity could stop updating for the rest of the session, silently**: every entity read guarded itself with a per-entity lock, taken with `asyncio.wait_for(..., 0.1)` so a cycle that arrived while a read was already in progress would give up rather than pile reads up. That wait was not safe. `wait_for` runs the acquisition in a task of its own, and if the deadline cancels the caller in the same event loop iteration in which that task has already taken the lock, the cancellation is raised at the await inside `wait_for` - before the `try` that releases it - and the lock is then held by nobody, with nothing left to release it. Releasing the lock 10 ms before the deadline reproduced that 4 times in 300 attempts on Python 3.14.7. Every later read of that entity then timed out at 0.1 s, and each timeout was swallowed as "already in progress" - so the entity carried its last value for the rest of the session, with one debug line per cycle, until the integration was reloaded. It reached any entity on a `scan_interval` timer, and the read-back after a write. The lock An ordinary entity read no longer waits for the lock at all: a tick that arrives during a read of the same entity is dropped at once, which is what the deadline was for anyway, since the read holding the lock is about to publish the value that read would have fetched. The read-back after a write still waits for a read in flight, because the device has been written by then and the stale value that read fetched must not be the one left in the cache.

- **Entity IDs are never renamed again**: an upgrade turned every entity of this integration into a new entity with the gateway host in front of its ID, so `sensor.modbus_local_gateway_temperature` became `sensor.192_168_1_100_modbus_local_gateway_temperature` and was gone from every dashboard, automation and long-term statistic, with the old ID left behind as a dead entity. Renaming is now a one-time decision at creation: entities that already exist keep their entity ID, unique ID, device and history, entities created from here on are prefixed with the gateway host, and reconfiguration can leave the prefix off for new entities or move the entities of the devices back onto the IDs they had before the prefix existed, which keeps the unique ID and the device intact.

- **Devices hang off the gateway, and only on a Home Assistant that supports it**: a child device links to its parent with `via_device_id`, replacing the deprecated `via_device`; the integration no longer carries the fallback to the old spelling, so the code says what it means instead of probing the installed registry at run time. Core already accepts `via_device_id` and provides the config-subentry and device-registry APIs used here, so the link does not set the version floor: 2026.9.0 stays the tested support minimum, enforced by the version guard, which refuses anything older with a named error naming both the installed and the required version. On a supported release the child hangs off the gateway as before, and devices are matched on their identifiers, so an upgrade reuses the devices and parent links an installation already has: nothing is renamed, re-registered or duplicated, and no config entry or YAML migration is needed.
- **Aborting a flow no longer fails on an older Home Assistant**: the config flow's abort passed `translation_domain` to Home Assistant's `ConfigFlow.async_abort`, an argument that only exists from the Home Assistant release that added it - so on an older HA, which includes the version this repository is developed and tested against, every abort raised `TypeError: ConfigFlow.async_abort() got an unexpected keyword argument 'translation_domain'` and the flow stopped with an error rather than aborting. It reaches the user as a failing config, reauth or options flow, where the underlying cause is not visible at all: the abort is the way a flow says, "nothing to do", and it was raising instead. The handler now forwards whatever the installed Home Assistant hands it rather than naming the arguments itself, so the translation domain is passed on where Home Assistant asks for it - from 2026.10, where an abort can be shown in Home Assistant's own translations instead of the integration's - and no argument is invented where it does not. Nothing else changes for anyone: the abort reason, its placeholders and any next flow are forwarded as before.
- **Writes to devices that only implement preset multiple registers**: a single holding register write always went out as _Preset Single Register_ (FC `0x06`), and some devices only implement _Preset Multiple Registers_ (FC `0x10`). Those devices either answer FC `0x06` with an exception or stay silent, so the write was lost and the entity reported a failure — the reported case is an inverter whose `select` on register 301 failed with "No response received after 5 retries" until it was written by hand with FC `0x10`. A refused single-register write is now retried once with FC `0x10`, mirroring the fallback multi-register writes already take in the other direction, and the retry goes straight to `write_registers` so the function that just failed is not attempted a second time. A write that gets no answer at all is _not_ simply repeated: writing a register can run a command, and a lost response does not mean the device left it alone, so the register is read back first. A read-back that already holds the requested value is treated as done and prevents the retry — it proves the state, not that the write ran. A read-back that still holds the old value leaves it ambiguous: for a device that has never answered FC `0x06` the function is not implemented and the FC `0x10` retry is safe, while a device that does answer `0x06` may have run a command and lost only the response, so its write is reported as failed and not repeated — the shipped Pichler config documents that register 33 (`Reset` / `Snooze`) clears itself again, which would otherwise run the command twice. When the read-back cannot be answered either, the write is reported as failed and nothing is repeated. The log names the failed attempt, its reason and pymodbus' own diagnostics.

- **A device that is switched off no longer holds up Home Assistant's start**: every entity
  of a device used to read itself 100 ms after it was added, and Home Assistant waits for the
  work that setting up an integration starts - so a configured device that is not answering cost
  one timeout sequence per entity before the dashboard came up. Each device behind a gateway is
  now read once, as a whole, and only after Home Assistant has finished starting; entities that
  have their own `scan_interval` are included in that first read instead of waiting for their
  first tick. A poll that meets a device that has stopped answering ends there and reports what
  it had already read, so a silent device costs one timeout per poll rather than one per entity,
  the entities it did not reach go unavailable rather than showing a stale value, and the other
  devices behind the same gateway keep polling. Entities are unavailable until their device has
  been read for the first time, so nothing looks like it is answering before it has. An answer
  that came back wrong - an exception response, a register of the wrong length, a stale answer
  from a gateway that is out of step - is still not treated as an outage: the device is on the
  bus, so the poll carries on with the next entity and the reason is logged at debug. Only a
  read that got no answer at all is an outage, and it says so once per poll. A device that is
  added or reloaded while Home Assistant is already running is read straight away, and a first
  read still pending when the entry is unloaded is dropped. An entity with its own
  `scan_interval` keeps its own reading while the device is answering, and while it is not it
  stays unavailable until the refresh of the whole device finds the device back. A device that
  is off is a state
  rather than an event, so it is logged as one: a warning when it stops answering, an info line
  when it answers again with the time it was gone, and nothing in between however many polls
  pass - unless the device is one that is expected to be off, where the same transition is
  information rather than a fault. A device that answers some of the registers asked for and
  not others is a different thing - it is on the bus, and the values that do come back are worth
  having - so that is warned about on every poll, once per poll and naming the entities that had
  no usable response, rather than once per entity.
- **A `map:` miss no longer freezes an entity**: `_convert_to_enum` returned `None` for an unmapped value and the platforms skip the update on `None`, so the entity silently kept its previous state — no error, no `unknown`, just a stale reading that looks current. The raw number is returned instead, so the state is either a label or a bare number and the reading is never older than the last poll. The miss is logged at debug.
- **Failed register writes are reported to Home Assistant**: the write helpers were annotated `-> None` and never returned the PDU they received, so the `if pdu and pdu.isError()` check in `write_data()` was dead code — a Modbus exception response to a write was reported back as a successful write. The PDU is now returned and `write_data()` raises `ModbusException`, which the coordinator entity wraps into `UpdateFailed`. Behaviour change: writes that previously failed silently now raise.
- **Number writes are read back**: `async_set_native_value` called the client directly, bypassing `ModbusCoordinatorEntity.write_data()` and the re-read that switch, select and text all perform, so the matching sensor stayed stale for a full `scan_interval` after every number write.
- **An empty poll list no longer fails the refresh**: `async_update` polls only entities without a `scan_interval`, so a device config that sets one on every entity left that list empty and raised `UpdateFailed` on every refresh — marking all of the integration's entities unavailable, including the ones their own timers were polling fine. An empty poll list now returns the data the per-entity timers already stored.
- **The client is closed when the last config entry using it unloads**: `async_unload_entry()` unloaded the platforms and dropped the coordinator but never closed the client or evicted it from the cache, so the TCP connection outlived the config entry with pymodbus' retry machinery still running on it. The client is cached per host/port/framer and shared by every entry pointing at the same gateway, so it is closed once no remaining coordinator references it, and `ModbusProtocol.close()` sets `is_closing` so no reconnect task is spawned.
- **Stale frames from a TCP-to-RTU bridge no longer poison the next read**: a gateway that bridges TCP to a shared serial bus answers late under load, and once one request has timed out, its answer is still on the way and the next request collects it before its own - from then on the gateway is permanently one response ahead, which is what the `request ask for transaction_id=27 but got id=26, Skipping` messages and the `extra data` in the log are. The frames that answer a request nobody is waiting for are now counted as they arrive, and a transaction that fails while such frames are in flight is taken as proof that the bridge is out of step: the poll ends there, and the next poll starts on a renewed connection, which drops what the bridge had queued and puts the two back in step. A read that comes back matched clears the count, so a gateway that is merely a moment behind is never disconnected, and a device that simply does not answer is not reconnected either. A match is not proof of which request produced the answer - over RTU-TCP there is no transaction id to match on, so there it means only that the response is the right length - but it is enough to say the gateway is not still answering out of order. The receive buffer is still cleared after a failed or unusable read, but that is not what puts the two back in step - `pdu_send` already clears it before every send, and clearing what has been received cannot unqueue an answer the bridge still owes; only the renewed connection can. A response carrying the wrong number of registers or bits is rejected, as a register response of the wrong length already was, and a coil response is held to the whole bytes it was asked for, so an answer to a larger request is not taken for this one. Nothing changes for a direct Modbus TCP device: requests were already serialised one at a time, and there is a regression test that keeps it that way.
- **The connection reports whether it is in step with the gateway**: an answer that belongs to another request, and an answer that arrives with no request waiting for it, are counted on the connection and reachable from it, so a log that is full of skipped frames can be read against the counts that name the bridge rather than the device. The warning a failed poll writes reports the number of times the connection had to be resynchronised, not those two counts.
- **A device that answers with an exception the config does not explain is named in the log**: the failure carries the device id and the resync count, and the README points at the device documentation for the function and exception codes instead of leaving the raw pymodbus error as the only hint.

### Changed

- **Home Assistant 2026.9 or newer**: the gateway/sub-entry architecture is built on the config sub-entry API as it stands in that release, and the repository is developed and tested against it.
- **The MAC address of a gateway is no longer looked up**: devices used to be linked to the gateway device by its MAC address, which meant a synchronous socket call on every setup and nothing at all for a gateway that does not answer it. The gateway is now the parent through its own device, and a gateway that serves several devices is a single device with the devices behind it as its children, so the lookup has no left to do.
- **Standard names for the connection type**: the two options in the config flow were labelled by how the device is reached — "Via Gateway Device" and "Direct Connection" — which does not say what is on the wire, and neither is the name the protocol carries in a manual or a datasheet. They are now "Modbus TCP" and "Modbus RTU over TCP", matching `FramerType.SOCKET` and `FramerType.RTU`, which is what the selection actually changes. The stored value, and therefore existing config entries, are untouched.

- **Python 3.14 only**: packaging metadata and CI no longer advertise 3.13, and the dev Home Assistant pin follows.
- **Repo tooling and docs**: `prek` hook set (ruff, isort, cspell, yamllint, prettier, mypy, pylint, coverage) plus a dependency sync script, contributor and security docs, a repo-specific PR template, the code-review skill and updated CI workflows. SonarQube scans moved to `workflow_run` with a validated coverage report, keeping the token out of fork-derived code.
- **mypy and pylint run on every commit** instead of on a manual stage; the findings across the integration, tests and test server are fixed (pylint 10.00/10, mypy clean across all 21 source files). The config flow schemas are cast so they type-check against both voluptuous and the `probatio` annotation Home Assistant 2026.10 uses.

### Device configurations

- **Growatt inverters expose a writable clock**: the system time was spread over registers 45-50 as six raw numbers, so a device whose clock ran fast had to be corrected by hand in a vendor tool. The `MIC 2500TL-X`, `MOD 6000TL-X`, `MIN 6000TL-XH`, `MOD 10KTL3-XH` and `SPH3600TL BL_UP` configs now declare a `Current Time` composite `datetime` entity, so the device clock can be read and set from Home Assistant, and a setting is sent as one `write_registers` instead of six separate writes. The `MOD 6000TL-X`, `MIN 6000TL-XH` and `MOD 10KTL3-XH` configs also gain the nine time-of-use windows of the protocol document in `docs`: each is a `time` entity for the start and one for the end, plus a mode select and an enable switch, all on the window's two holding registers - enable, charge mode and start time in the first, end time in the second - so a window is set as one value and writing a time leaves the mode and enable bits of that register alone.
- **Midea-built air-to-water heat pumps** (Kaisai KHA/KMK/KHC controller): 97 entities covering temperatures, refrigerant circuit, electrical values, status and load bitfields, fault history, energy counters and the commissioning parameters. Compatibility follows the wired controller rather than the badge on the outdoor unit; register 131 reports the controller version as a diagnostic. Setpoint ranges are the protocol's, with each unit's own limits exposed as sensors so they can be narrowed. Optional hardware is disabled by default because an unfitted sensor reports a fixed sentinel.
- **Midea heat-pump config**: the curve-setpoint sentinels are declared with `unavailable_values`; the nine remaining register 129 load-output bits are surfaced; and the fault codes in registers 124-127 are now decoded, which is safe because an unmapped `map:` value falls back to the raw number rather than freezing the sensor on the previous fault.
- **Eastron SDM630 demand registers**: `Total System Power demand` and `Total System VA demand` were declared `state_class: total_increasing` with `never_resets: true`, but a demand is a measurement. While the meter exports to the grid both are negative, `total_increasing` cannot hold a negative state — the recorder rejected it and the integration's `never_resets` guard logged "Ignoring device value" and kept the previous import reading, so the sensor froze on the last positive value. Both are now `measurement`, matching the `Total System Power` / `Total System VA` registers they sit beside, and the inert `never_resets` is gone. A test walks the shipped configs so no power device class can be declared as a total again.
- **Schneider Altivar ATV 312**, **Salda RIS 700 PE**, **LAE AC1-27 controller** and **Fröling BWP300PV** configurations.

### Dependencies

- pymodbus `>=3.11.1` → `>=3.13.1`, Home Assistant `>=2026.6.3` → `>=2026.9.0`, setuptools `>=82.0.1,<84.1`, yarl `>=1.24.2`, pycryptodome `>=3.23.0`, tox `4.64.4`, ruff `0.15.20`, prek `>=0.4.5`, isort `>=8.0.1`,
- dropped `getmac`, which was only there for the gateway MAC lookup the sub-entry architecture no longer needs, pytest-asyncio `>=1.4.0`, pytest-cov `>=7.14.3`, pytest-homeassistant-custom-component, coverage `>=7.14.3` and pylint `>=4.0.6`; the dev `requirements_dev.txt` dependency conflicts are fixed and dependabot is set to `increase-if-necessary`.

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
