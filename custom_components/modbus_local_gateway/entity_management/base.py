"""Sensor Entity Description for the Modbus Local Gateway integration."""

from __future__ import annotations

import builtins
from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.date import DateEntityDescription
from homeassistant.components.datetime import (
    DateTimeEntityDescription,
)
from homeassistant.components.number import NumberEntityDescription, NumberMode
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.components.text import TextEntityDescription
from homeassistant.components.time import TimeEntityDescription
from homeassistant.helpers.entity import EntityDescription

from .const import (
    COMPOSITE_TYPE,
    CONV_BITS,
    CONV_MULTIPLIER,
    CONV_OFFSET,
    CONV_SHIFT_BITS,
    CONV_SUM_SCALE,
    CONV_SWAP,
    CONV_UNAVAILABLE_VALUES,
    CONV_WRITE_OFFSET,
    IS_FLOAT,
    IS_SIGNED,
    IS_STRING,
    MAX_CHANGE,
    NO_FLAG_VALUE,
    PRECISION,
    REGISTER_COUNT,
    CompositeType,
    ControlType,
    ModbusDataType,
    WriteFunction,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


@dataclass(kw_only=True, frozen=True)
class UnusedKeysMixin:
    """Mixin for unused but allowed keys."""

    address: int | None = 0  # register_address
    size: int | None = 1  # register_count
    swap: str | None = None  # conv_swap
    sum_scale: list[float] | None = None  # conv_sum_scale
    multiplier: float | None = 1.0  # conv_multiplier
    offset: float | None = None  # conv_offset
    shift_bits: int | None = None  # conv_shift_bits
    bits: int | None = None  # conv_bits
    map: dict[int, str] | None = None  # conv_map
    unavailable_values: list[int] | None = None  # conv_unavailable_values
    flags: dict[int, str] | None = None  # conv_flags
    no_flag_value: str | int | None = None  # conv_no_flag_value
    string: bool | None = False  # is_string
    float: bool | None = False  # is_float
    signed: bool | None = False  # is_signed
    control: str | None = ControlType.SENSOR  # control_type
    number: dict[str, int] | None = None  # min, max
    switch: dict[str, builtins.float] | None = None  # on, off


@dataclass(kw_only=True, frozen=True)
class ModbusRequiredKeysMixin:
    """Mixin for required keys."""

    register_address: int
    data_type: ModbusDataType


@dataclass(kw_only=True, frozen=True)
class ModbusEntityDescription(
    EntityDescription, ModbusRequiredKeysMixin, UnusedKeysMixin
):
    """Describes Modbus sensor entity."""

    register_count: int | None = 1
    conv_swap: str | None = None
    conv_sum_scale: list[float] | None = None
    conv_multiplier: float | None = None
    conv_offset: float | None = None
    conv_shift_bits: int | None = None
    conv_bits: int | None = None
    conv_map: dict[int, str] | None = None
    conv_unavailable_values: list[int] | None = None
    conv_flags: dict[int, str] | None = None
    conv_no_flag_value: str | int | None = None
    is_signed: bool | None = False
    is_string: bool | None = False
    is_float: bool | None = False
    precision: int | None = None
    never_resets: bool = False
    control_type: str | None = ControlType.SENSOR
    max_change: float | None = None
    scan_interval: int | None = None
    write_with: tuple[int, ...] = ()

    def validate(self) -> bool:
        """Validate the entity description"""
        validators: tuple[Callable[[], bool], ...] = (
            self._validate_string_and_float,
            self._validate_string_constraints,
            self._validate_float_constraints,
            self._validate_register_count,
            self._validate_max_change,
            self._validate_scan_interval,
            self._validate_unavailable_values,
            self._validate_no_flag_value,
            self._validate_bitfield,
            self._validate_write_with,
        )
        return all(check() for check in validators)

    @property
    def write_span(self) -> tuple[int, int]:
        """(first, last) register the entity's write must cover.

        Without `write_with` this is the register(s) the entity itself writes.
        With it, the declared registers are rewritten in the same request, and
        the longest run that spans the entity and them is what one request
        covers (a device that wants a window's start and end written together
        refuses a request that only covers one of them). The extra registers
        keep their current values.
        """
        start = self.register_address
        end = self.register_address + (self.register_count or 1) - 1
        if not self.write_with:
            return start, end
        return min(start, *self.write_with), max(end, *self.write_with)

    def _validate_write_with(self) -> bool:
        """Check `write_with` on an entity that is not a composite.

        The registers it names are rewritten together with the entity's own
        in one request, so they must be adjustable holdings and the write must
        not drag registers neither the entity nor `write_with` declared across
        the span: a request that writes more than it was told to could zero a
        value that shares the registers.
        """
        if not self.write_with:
            return True
        if self.control_type not in (
            ControlType.NUMBER,
            ControlType.SWITCH,
            ControlType.SELECT,
        ):
            _LOGGER.warning(
                "Unable to create entity for %s: write_with cannot be used "
                "on a %s, which has nothing to write",
                self.key,
                self.control_type,
            )
            return False
        own_registers = set(
            range(
                self.register_address,
                self.register_address + (self.register_count or 1),
            )
        )
        for address in self.write_with:
            if self.data_type != ModbusDataType.HOLDING_REGISTER:
                _LOGGER.warning(
                    "Unable to create entity for %s: write_with cannot be used "
                    "on register %d, which is read only",
                    self.key,
                    address,
                )
                return False
            if address in own_registers:
                _LOGGER.warning(
                    "Unable to create entity for %s: register %d is already "
                    "the entity's own and cannot be listed in write_with",
                    self.key,
                    address,
                )
                return False
        start, end = self.write_span
        covered = own_registers | set(self.write_with)
        gaps = [
            register for register in range(start, end + 1) if register not in covered
        ]
        if gaps:
            _LOGGER.warning(
                "Unable to create entity for %s: write_with span %d-%d would "
                "also rewrite registers %s, which are neither the entity's own "
                "nor declared in write_with",
                self.key,
                start,
                end,
                ", ".join(str(register) for register in gaps),
            )
            return False
        return True

    def _validate_unavailable_values(self) -> bool:
        """`unavailable_values` must be a list of whole numbers.

        They are matched against the raw register value - after any `bits` /
        `shift_bits` masking, but before `multiplier` and `offset`.
        """
        if self.conv_unavailable_values is None:
            return True
        if not isinstance(self.conv_unavailable_values, list) or not all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in self.conv_unavailable_values
        ):
            _LOGGER.warning(
                "Unable to create entity for %s: %s must be a list of integers",
                self.key,
                CONV_UNAVAILABLE_VALUES,
            )
            return False
        return True

    def _validate_no_flag_value(self) -> bool:
        """`no_flag_value` must be a string or an integer.

        It is the state reported when none of the entity's `flags` bits is set,
        so it must be a type a sensor can hold. Absent, the raw register value
        is reported as before.
        """
        if self.conv_no_flag_value is None:
            return True
        if not isinstance(self.conv_no_flag_value, (str, int)) or isinstance(
            self.conv_no_flag_value, bool
        ):
            _LOGGER.warning(
                "Unable to create entity for %s: %s must be a string or an integer",
                self.key,
                NO_FLAG_VALUE,
            )
            return False
        return True

    def _validate_bitfield(self) -> bool:
        """Check constraints for writable bit fields.

        The merge assumes an unsigned value: a signed field has no well-defined
        representation once masked into part of a register.

        The geometry must also fit the register span, and a coil is already a
        single bit so the options mean nothing there.

        Limited to the number, switch and select controls - applying it to
        sensors would stop already-working entities from being created.
        """
        if self.conv_bits is None and self.conv_shift_bits is None:
            return True
        if self.control_type not in (
            ControlType.NUMBER,
            ControlType.SWITCH,
            ControlType.SELECT,
        ):
            return True

        if self.is_signed:
            _LOGGER.warning(
                "Unable to create entity for %s: %s cannot be combined with "
                "%s or %s on a writable entity",
                self.key,
                IS_SIGNED,
                CONV_BITS,
                CONV_SHIFT_BITS,
            )
            return False
        if self.conv_sum_scale:
            _LOGGER.warning(
                "Unable to create entity for %s: %s cannot be combined with "
                "%s or %s on a writable entity",
                self.key,
                CONV_SUM_SCALE,
                CONV_BITS,
                CONV_SHIFT_BITS,
            )
            return False
        return self.validate_bitfield_geometry()

    def validate_bitfield_geometry(self) -> bool:
        """The field must be a real run of bits inside the registers it names."""
        if self.data_type == ModbusDataType.COIL:
            _LOGGER.warning(
                "Unable to create entity for %s: %s and %s have no meaning on a "
                "coil, which is already a single bit",
                self.key,
                CONV_BITS,
                CONV_SHIFT_BITS,
            )
            return False

        span: int = 16 * (self.register_count or 1)
        shift: int = self.conv_shift_bits or 0
        width: int = self.conv_bits if self.conv_bits is not None else span - shift
        if shift < 0 or width <= 0 or shift + width > span:
            _LOGGER.warning(
                "Unable to create entity for %s: %s %s / %s %s does not fit the "
                "%s bits it addresses",
                self.key,
                CONV_SHIFT_BITS,
                shift,
                CONV_BITS,
                width,
                span,
            )
            return False
        return True

    def _validate_scan_interval(self) -> bool:
        """Validate scan_interval is positive if set."""
        if self.scan_interval is not None and self.scan_interval <= 0:
            _LOGGER.warning(
                "Unable to create entity for %s: scan_interval must be > 0",
                self.key,
            )
            return False
        return True

    def _validate_string_and_float(self) -> bool:
        """Check if both string and float are defined."""
        if self.is_float and self.is_string:
            _LOGGER.warning(
                "Unable to create entity for %s: Both string and float defined",
                self.key,
            )
            return False
        return True

    def _validate_string_constraints(self) -> bool:
        """Check constraints for string entities."""
        string_conflicts: bool = bool(
            self.conv_shift_bits
            or self.conv_bits
            or self.precision
            or self.conv_swap
            or self.is_signed
            or (self.conv_multiplier and int(self.conv_multiplier) != 1)
        )
        if self.is_string and string_conflicts:
            _LOGGER.warning(
                "Unable to create entity for %s: %s, %s, %s, %s, %s, %s, %s, "
                "and %s not valid for %s",
                self.key,
                CONV_SUM_SCALE,
                CONV_SHIFT_BITS,
                CONV_BITS,
                CONV_MULTIPLIER,
                CONV_OFFSET,
                CONV_SWAP,
                IS_SIGNED,
                PRECISION,
                IS_STRING,
            )
            return False
        return True

    def _validate_float_constraints(self) -> bool:
        """Check constraints for float entities."""
        float_conflicts: bool = bool(
            self.conv_shift_bits
            or self.conv_bits
            or self.is_signed
            or (self.conv_multiplier is not None and int(self.conv_multiplier) != 1)
        )
        if self.is_float and float_conflicts:
            _LOGGER.warning(
                "Unable to create entity for %s: %s, %s, %s, and %s not valid for %s",
                self.key,
                CONV_BITS,
                CONV_SHIFT_BITS,
                IS_SIGNED,
                CONV_MULTIPLIER,
                IS_FLOAT,
            )
            return False
        return True

    def _validate_register_count(self) -> bool:
        """Check if register count is valid for float entities."""
        if self.is_float and self.register_count not in (2, 4):
            _LOGGER.warning(
                "Unable to create entity for %s: %s outside valid range "
                "not valid for %s",
                self.key,
                REGISTER_COUNT,
                IS_FLOAT,
            )
            return False

        if not self.is_string and self.register_count not in (1, 2, 4):
            _LOGGER.warning(
                "Unable to create entity for %s: %s must be 1, 2, or 4 for "
                "non-string entities",
                self.key,
                REGISTER_COUNT,
            )
            return False

        return True

    def _validate_max_change(self) -> bool:
        """Check if max_change is valid."""
        if self.max_change is not None:
            if self.is_string:
                _LOGGER.warning(
                    "Unable to create entity for %s: %s not valid for %s",
                    self.key,
                    self.max_change,
                    IS_STRING,
                )
                return False
            if self.max_change < 0:
                _LOGGER.warning(
                    "Unable to create entity for %s: %s must be ≥ 0",
                    self.key,
                    MAX_CHANGE,
                )
                return False
        return True


@dataclass(kw_only=True, frozen=True)
class ModbusSensorEntityDescription(SensorEntityDescription, ModbusEntityDescription):
    """Describes Modbus sensor register entity."""


@dataclass(kw_only=True, frozen=True)
class ModbusSwitchEntityDescription(SwitchEntityDescription, ModbusEntityDescription):
    """Describes Modbus switch holding register entity."""

    on: bool | int | None = None
    off: bool | int | None = None


@dataclass(kw_only=True, frozen=True)
class ModbusSelectEntityDescription(SelectEntityDescription, ModbusEntityDescription):
    """Describes Modbus select holding register entity."""

    select_options: dict[int, str]


@dataclass(kw_only=True, frozen=True)
class ModbusTextEntityDescription(TextEntityDescription, ModbusEntityDescription):
    """Describes Modbus text holding register entity."""


@dataclass(kw_only=True, frozen=True)
class ModbusNumberEntityDescription(NumberEntityDescription, ModbusEntityDescription):
    """Describes Modbus number holding register entity."""

    max: int
    min: int
    mode: NumberMode | None = None


@dataclass(kw_only=True, frozen=True)
class ModbusBinarySensorEntityDescription(
    BinarySensorEntityDescription, ModbusEntityDescription
):
    """Describes Modbus binary sensor entity for Discrete Inputs and Registers."""

    on: bool | int | None = None
    off: bool | int | None = None


@dataclass(kw_only=True, frozen=True)
class ModbusFieldDescription:
    """One register, or run of registers, inside a composite entity.

    A field carries the conversion options a single entity carries, so a device
    that stores and reports a value the same way on both sides is described
    with `offset` and the composite layer only ever sees the real value.

    `write_offset` is for the other kind of device: one that reports a value and
    accepts a different one. Growatt register 45 (`Sys Year`) reports a
    four-digit year and takes a two-digit one, which `offset` cannot express -
    it applies on both sides, so `offset: 2000` would read a raw 2026 back as
    4026. Leaving it unset writes 2026 where the device wants 26.
    """

    key: str
    address: int
    size: int = 1
    conv_swap: str | None = None
    conv_multiplier: float | None = None
    conv_offset: float | None = None
    conv_write_offset: int | None = None
    conv_unavailable_values: list[int] | None = None
    conv_bits: int | None = None
    conv_shift_bits: int | None = None
    is_signed: bool | None = False
    is_float: bool | None = False
    is_string: bool | None = None

    @property
    def is_bitfield(self) -> bool:
        """Whether the field claims part of a register rather than all of it."""
        return self.conv_bits is not None or self.conv_shift_bits is not None

    def validate(self, data_type: ModbusDataType) -> bool:
        """Validate the field as the entity description it converts through.

        A bit field is merged into the register it lives in rather than written
        over it, so the bits it does not cover are left as the device has them:
        a register that packs a time together with a mode and an enable bit can
        be described as one `time` composite plus entities for the other fields.
        """
        entity: ModbusEntityDescription = self.as_entity_description(data_type)
        if not entity.validate():
            return False
        if not self._write_offset_allowed():
            return False
        if not self.is_bitfield:
            return True
        if self.is_signed:
            _LOGGER.warning(
                "Unable to create entity for %s: %s cannot be combined with "
                "%s or %s on a bit field",
                self.key,
                IS_SIGNED,
                CONV_BITS,
                CONV_SHIFT_BITS,
            )
            return False
        return entity.validate_bitfield_geometry()

    def _write_offset_allowed(self) -> bool:
        """Whether a write offset on this field means one thing.

        None of a field of several registers, a bit field or a swapped field
        carries a single value the offset could belong to. A field of several
        registers carries one value per register. A bit field is merged into
        the register it lives in, so the offset would reach the device as a
        shift of the whole register, mode and enable bits included. The offset
        is added to the register the value ends up in, which for a swapped
        field is its bytes the other way round: 2026 would arrive as
        0xEA07 - 2000 rather than as 26 swapped.
        """
        if self.conv_write_offset is None:
            return True
        if self.size > 1:
            _LOGGER.warning(
                "Unable to create entity for %s: %s cannot be used with %s on a "
                "field of %s registers",
                self.key,
                CONV_WRITE_OFFSET,
                REGISTER_COUNT,
                self.size,
            )
            return False
        if self.is_bitfield:
            _LOGGER.warning(
                "Unable to create entity for %s: %s cannot be combined with %s or %s",
                self.key,
                CONV_WRITE_OFFSET,
                CONV_BITS,
                CONV_SHIFT_BITS,
            )
            return False
        if self.conv_swap:
            _LOGGER.warning(
                "Unable to create entity for %s: %s cannot be combined with %s",
                self.key,
                CONV_WRITE_OFFSET,
                CONV_SWAP,
            )
            return False
        return True

    def bit_ranges(self) -> list[tuple[int, int, int]]:
        """The `(address, lowest bit, highest bit)` this field claims.

        A field that is not a bit field claims every bit of every register it
        addresses, which is what makes two of them in one composite an overlap.
        An empty list means the geometry does not fit, and is rejected elsewhere.
        """
        span: int = 16 * max(1, self.size)
        shift: int = self.conv_shift_bits or 0
        width: int = self.conv_bits if self.conv_bits is not None else span - shift
        if width <= 0 or shift < 0 or shift + width > span:
            return []
        if self.is_bitfield:
            return [(self.address + shift // 16, shift % 16, shift % 16 + width - 1)]
        return [(self.address + offset, 0, 15) for offset in range(max(1, self.size))]

    def apply_write_offset(self, registers: list[int]) -> list[int]:
        """Return `registers` with the field's write offset added to them.

        Applied after the value has been descaled and scaled, so it reaches the
        device as the raw register it holds rather than shifting what the
        entity reports. It is deliberately not part of `conv_offset`, which is
        reversed on the way out: a field that reads and writes the same value
        needs neither this nor any change to the read path.
        """
        if self.conv_write_offset is None:
            return registers
        return [register + self.conv_write_offset for register in registers]

    def as_entity_description(
        self, data_type: ModbusDataType
    ) -> ModbusEntityDescription:
        """Return this field as the entity description `Conversion` takes.

        Reusing the entity description is what keeps a field's conversion the
        same code path an ordinary entity goes through.
        """
        # `ModbusEntityDescription` is a dataclass whose `key` comes from the
        # Home Assistant base class, which pylint cannot see as a parameter.
        params: dict[str, Any] = {
            "key": self.key,
            "register_address": self.address,
            "register_count": self.size,
            "data_type": data_type,
            "conv_swap": self.conv_swap,
            "conv_multiplier": self.conv_multiplier,
            "conv_offset": self.conv_offset,
            "conv_unavailable_values": self.conv_unavailable_values,
            "conv_bits": self.conv_bits,
            "conv_shift_bits": self.conv_shift_bits,
            "is_signed": self.is_signed,
            "is_float": self.is_float,
            "is_string": self.is_string,
        }
        return ModbusEntityDescription(**params)  # pylint: disable=unexpected-keyword-arg

    @property
    def end_address(self) -> int:
        """Address just past the last register this field occupies."""
        return self.address + max(1, self.size) - 1


@dataclass(kw_only=True, frozen=True)
class ModbusCompositeEntityDescription(ModbusEntityDescription):
    """Describes an entity assembled from several registers.

    `register_address` and `register_count` describe the whole span the fields
    cover, so an entity reads as one value like any other; `fields` say how the
    registers inside that span turn into a single semantic value.
    """

    composite_type: CompositeType
    fields: tuple[ModbusFieldDescription, ...]
    write_function: WriteFunction | None = None
    write_with: tuple[int, ...] = ()

    @property
    def write_span(self) -> tuple[int, int]:
        """(first, last) register the whole write must cover.

        Without `write_with` this is the span the fields cover. With it, the
        write must also rewrite the declared registers, and the longest run
        that spans the fields and those registers is what one write request
        covers (a device that wants a window's start and end written together
        refuses a request that only covers the end). The extra registers keep
        their current values, they are not fields of this entity.
        """
        start = min(field.address for field in self.fields)
        end = max(field.end_address for field in self.fields)
        if not self.write_with:
            return start, end
        return min(start, *self.write_with), max(end, *self.write_with)

    @property
    def runs(self) -> tuple[tuple[ModbusFieldDescription, ...], ...]:
        """Fields grouped into runs of adjacent registers.

        A run is written with one preset multiple registers request, and read
        with one transaction, so the value on the device is never half updated.
        Two bit fields in the same register are one run, not two: they are
        written in the same request, and each merge keeps the other's bits.

        `write_function` overrides the function the connection writes with, for
        a device that refuses FC 0x10 over the run and takes FC 0x06 only. The
        run is then one request per register, which is the price of a device
        that will not take a whole span in one go.
        """
        ordered: list[ModbusFieldDescription] = sorted(
            self.fields, key=lambda field: field.address
        )
        grouped: list[list[ModbusFieldDescription]] = []
        for field in ordered:
            if grouped and field.address <= grouped[-1][-1].end_address + 1:
                grouped[-1].append(field)
            else:
                grouped.append([field])
        return tuple(tuple(run) for run in grouped)

    def validate(self) -> bool:
        """Validate the composite and every field in it."""
        if not self._validate_scan_interval():
            return False
        if not self.validate_composite():
            return False
        if not self.validate_field_overlap():
            return False
        if not self.validate_write_with():
            return False
        return all(field.validate(self.data_type) for field in self.fields)

    def validate_field_overlap(self) -> bool:
        """Two fields of one composite must not claim the same bits.

        They share the register they live in, so a write would have to decide
        which of them wins - and the loser's value would be overwritten by the
        merge of the other.
        """
        claimed: dict[int, list[tuple[int, int, str]]] = {}
        for field in self.fields:
            for address, low, high in field.bit_ranges():
                for other_low, other_high, other_key in claimed.get(address, []):
                    if low <= other_high and other_low <= high:
                        _LOGGER.warning(
                            "Unable to create entity for %s: field %s and field "
                            "%s both claim bits %d-%d of register %d",
                            self.key,
                            other_key,
                            field.key,
                            max(low, other_low),
                            min(high, other_high),
                            address,
                        )
                        return False
                claimed.setdefault(address, []).append((low, high, field.key))
        return True

    def validate_composite(self) -> bool:
        """Check the field set can form the composite type it declares."""
        declared: set[str] = {field.key for field in self.fields}
        if len(declared) != len(self.fields):
            _LOGGER.warning(
                "Unable to create entity for %s: a field name is declared twice",
                self.key,
            )
            return False

        allowed: set[str] = set(self.composite_type.required_fields) | set(
            self.composite_type.optional_fields
        )
        unknown: set[str] = declared - allowed
        if unknown:
            _LOGGER.warning(
                "Unable to create entity for %s: %s %s is not part of a %s; "
                "allowed fields are %s",
                self.key,
                COMPOSITE_TYPE,
                ", ".join(sorted(unknown)),
                self.composite_type,
                ", ".join(sorted(allowed)),
            )
            return False

        missing: set[str] = set(self.composite_type.required_fields) - declared
        if missing:
            _LOGGER.warning(
                "Unable to create entity for %s: a %s needs %s",
                self.key,
                self.composite_type,
                ", ".join(sorted(missing)),
            )
            return False

        for run in self.runs:
            _LOGGER.debug(
                "Composite %s: run %s covers registers %d-%d",
                self.key,
                ", ".join(field.key for field in run),
                run[0].address,
                run[-1].end_address,
            )
        return True

    def validate_write_with(self) -> bool:
        """The registers `write_with` rewrites are adjustable holdings."""
        if not self.write_with:
            return True
        if self.write_function == WriteFunction.SINGLE:
            _LOGGER.warning(
                "Unable to create entity for %s: write_with cannot combine "
                "with write_function single, which writes registers one at a "
                "time instead of the pair together",
                self.key,
            )
            return False
        field_registers = {
            register
            for field in self.fields
            for register in range(field.address, field.end_address + 1)
        }
        for address in self.write_with:
            if self.data_type != ModbusDataType.HOLDING_REGISTER:
                _LOGGER.warning(
                    "Unable to create entity for %s: write_with cannot be used "
                    "on register %d, which is read only",
                    self.key,
                    address,
                )
                return False
            if address in field_registers:
                _LOGGER.warning(
                    "Unable to create entity for %s: register %d is already a "
                    "field of the composite and cannot be listed in write_with",
                    self.key,
                    address,
                )
                return False
        start, end = self.write_span
        covered = field_registers | set(self.write_with)
        gaps = [
            register for register in range(start, end + 1) if register not in covered
        ]
        if gaps:
            _LOGGER.warning(
                "Unable to create entity for %s: write_with span %d-%d would "
                "also rewrite registers %s, which are neither fields nor "
                "declared in write_with",
                self.key,
                start,
                end,
                ", ".join(str(register) for register in gaps),
            )
            return False
        return True


@dataclass(kw_only=True, frozen=True)
class ModbusDateTimeEntityDescription(
    DateTimeEntityDescription, ModbusCompositeEntityDescription
):
    """Describes a composite entity exposed as a date/time."""


@dataclass(kw_only=True, frozen=True)
class ModbusTimeEntityDescription(
    TimeEntityDescription, ModbusCompositeEntityDescription
):
    """Describes a composite entity exposed as a time."""


@dataclass(kw_only=True, frozen=True)
class ModbusDateEntityDescription(
    DateEntityDescription, ModbusCompositeEntityDescription
):
    """Describes a composite entity exposed as a date."""
