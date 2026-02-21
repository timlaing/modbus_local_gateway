"""Sensor Entity Description for the Modbus Local Gateway integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.number import NumberEntityDescription, NumberMode
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.components.text import TextEntityDescription
from homeassistant.helpers.entity import EntityDescription

from .const import (
    CONV_BITS,
    CONV_MULTIPLIER,
    CONV_OFFSET,
    CONV_SHIFT_BITS,
    CONV_SUM_SCALE,
    CONV_SWAP,
    IS_FLOAT,
    IS_SIGNED,
    IS_STRING,
    MAX_CHANGE,
    PRECISION,
    REGISTER_COUNT,
    ControlType,
    ModbusDataType,
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
    flags: dict[int, str] | None = None  # conv_flags
    string: bool | None = False  # is_string
    float: bool | None = False  # is_float
    signed: bool | None = False  # is_signed
    control: str | None = ControlType.SENSOR  # control_type
    number: dict[str, int] | None = None  # min, max
    switch: dict[str, float] | None = None  # on, off


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
    conv_flags: dict[int, str] | None = None
    is_signed: bool | None = False
    is_string: bool | None = False
    is_float: bool | None = False
    precision: int | None = None
    never_resets: bool = False
    control_type: str | None = ControlType.SENSOR
    max_change: float | None = None
    scan_interval: int | None = None

    def validate(self) -> bool:
        """Validate the entity description"""
        if not self._validate_string_and_float():
            return False
        if not self._validate_string_constraints():
            return False
        if not self._validate_float_constraints():
            return False
        if not self._validate_register_count():
            return False
        if not self._validate_max_change():
            return False
        if not self._validate_scan_interval():
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
        if self.is_string and (
            self.conv_shift_bits
            or self.conv_bits
            or self.precision
            or self.conv_swap
            or self.is_signed
            or (self.conv_multiplier and int(self.conv_multiplier) != 1)
        ):
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
        if self.is_float and (
            self.conv_shift_bits
            or self.conv_bits
            or self.is_signed
            or (self.conv_multiplier is not None and int(self.conv_multiplier) != 1)
        ):
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
                "Unable to create entity for %s: %s outside valid range not valid for %s",
                self.key,
                REGISTER_COUNT,
                IS_FLOAT,
            )
            return False

        if not self.is_string and self.register_count not in (1, 2, 4):
            _LOGGER.warning(
                "Unable to create entity for %s: %s must be 1, 2, or 4 for non-string entities",
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
