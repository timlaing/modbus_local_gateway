"""Sensor Entity Description for the Modbus Local Gateway integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.number import NumberEntityDescription
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
    IS_FLOAT,
    IS_STRING,
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
    sum_scale: list[float] | None = None  # conv_sum_scale
    multiplier: float | None = 1.0  # conv_multiplier
    offset: float | None = None  # conv_offset
    shift_bits: int | None = None  # conv_shift_bits
    bits: int | None = None  # conv_bits
    map: dict[int, str] | None = None  # conv_map
    flags: dict[int, str] | None = None  # conv_flags
    string: bool | None = False  # is_string
    float: bool | None = False  # is_float
    control: str | None = ControlType.SENSOR  # control_type
    number: dict[str, int] | None = None  # min, max
    options: dict[int, str] | None = None  # select_options
    switch: dict[str, float] | None = None  # on, off


@dataclass(kw_only=True, frozen=True)
class ModbusRequiredKeysMixin:
    """Mixin for required keys."""

    register_address: int


@dataclass(kw_only=True, frozen=True)
class ModbusEntityDescription(
    EntityDescription, ModbusRequiredKeysMixin, UnusedKeysMixin
):
    """Describes Modbus sensor entity."""

    register_count: int | None = 1
    conv_sum_scale: list[float] | None = None
    conv_multiplier: float | None = 1.0
    conv_offset: float | None = None
    conv_shift_bits: int | None = None
    conv_bits: int | None = None
    conv_map: dict[int, str] | None = None
    conv_flags: dict[int, str] | None = None
    is_string: bool | None = False
    is_float: bool | None = False
    precision: int | None = None
    never_resets: bool = False
    control_type: str | None = ControlType.SENSOR
    data_type: ModbusDataType

    def validate(self) -> bool:
        """Validate the entity description"""
        valid = True
        if self.is_float and self.is_string:
            _LOGGER.warning(
                "Unable to create entity for %s: Both string and float defined",
                self.key,
            )
            valid = False
        elif (
            self.conv_shift_bits
            or self.conv_bits
            or self.precision
            or (self.conv_multiplier and int(self.conv_multiplier) != 1)
        ) and self.is_string:
            _LOGGER.warning(
                "Unable to create entity for %s: %s, %s, %s, %s, %s, and %s not valid for %s",
                self.key,
                CONV_SUM_SCALE,
                CONV_SHIFT_BITS,
                CONV_BITS,
                CONV_MULTIPLIER,
                CONV_OFFSET,
                PRECISION,
                IS_STRING,
            )
            valid = False
        elif (
            self.conv_shift_bits
            or self.conv_bits
            or (self.conv_multiplier is not None and self.conv_multiplier != 1.0)
        ) and self.is_float:
            _LOGGER.warning(
                "Unable to create entity for %s: %s, %s, and %s not valid for %s",
                self.key,
                CONV_BITS,
                CONV_SHIFT_BITS,
                CONV_MULTIPLIER,
                IS_FLOAT,
            )
            valid = False
        elif self.register_count != 2 and self.is_float:
            _LOGGER.warning(
                "Unable to create entity for %s: %s outside valid range not valid for %s",
                self.key,
                REGISTER_COUNT,
                IS_FLOAT,
            )
            valid = False
        return valid


@dataclass(kw_only=True, frozen=True)
class ModbusSensorEntityDescription(SensorEntityDescription, ModbusEntityDescription):
    """Describes Modbus sensor register entity."""


@dataclass(kw_only=True, frozen=True)
class ModbusSwitchEntityDescription(SwitchEntityDescription, ModbusEntityDescription):
    """Describes Modbus switch holding register entity."""

    on: int | None = None
    off: int | None = None


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


@dataclass(kw_only=True, frozen=True)
class ModbusBinarySensorEntityDescription(
    BinarySensorEntityDescription, ModbusEntityDescription
):
    """Describes Modbus binary sensor entity for Discrete Inputs."""
