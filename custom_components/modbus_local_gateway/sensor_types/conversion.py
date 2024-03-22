"""Conversion register functions"""

import logging
from typing import Any, Optional

from ..tcp_client import AsyncModbusTcpClient
from .base import ModbusSensorEntityDescription

_LOGGER = logging.getLogger(__name__)


class NotSupportedError(Exception):
    """Unsupported functionality"""


class Conversion:
    """Register conversion class"""

    def __init__(self, client: AsyncModbusTcpClient) -> None:
        self.client: AsyncModbusTcpClient = client

    def _convert_to_string(self, registers: list) -> str:
        """Convert to a string type"""
        value: str = self.client.convert_from_registers(
            registers, data_type=self.client.DATATYPE.STRING
        ).split("\0")[0]
        return value

    def _convert_from_string(self, value: str) -> list[int]:
        """Convert from a string type"""
        registers: list[int] = self.client.convert_to_registers(
            value, data_type=self.client.DATATYPE.STRING
        )
        return registers

    def _convert_to_float(self, registers: list) -> float:
        """Convert to a float type"""
        value: float = self.client.convert_from_registers(
            registers, data_type=self.client.DATATYPE.FLOAT32
        )
        return value

    def _convert_from_float(self, value: float) -> list[int]:
        """Convert from a float type"""
        registers: list[int] = self.client.convert_to_registers(
            value, data_type=self.client.DATATYPE.FLOAT32
        )
        return registers

    def _convert_to_enum(
        self, registers: list, desc: ModbusSensorEntityDescription
    ) -> str | None:
        """Convert to a enum type"""
        int_val: int = int(self._convert_to_decimal(registers=registers, desc=desc))
        if int_val in desc.register_map:
            value: int = desc.register_map[int_val]
            return value

        return None

    def _convert_to_flags(
        self, registers: list, desc: ModbusSensorEntityDescription
    ) -> str | None:
        """Convert to a flags type"""

        int_val: int = int(self._convert_to_decimal(registers=registers, desc=desc))
        ret_val = None

        for key in desc.flags:
            if int_val & (0x1 << (key - 1)) != 0:
                if ret_val is None:
                    ret_val = desc.flags[key]
                else:
                    ret_val += f" | {desc.flags[key]}"

        return ret_val

    def _convert_to_decimal(
        self, registers: list, desc: ModbusSensorEntityDescription
    ) -> float:
        """Convert to a int type"""
        num = self.client.convert_from_registers(
            registers,
            data_type=(
                self.client.DATATYPE.UINT32
                if desc.register_count == 2
                else self.client.DATATYPE.UINT16
            ),
        )

        if desc.bit_shift:
            num = num >> desc.bit_shift

        if desc.bits:
            num = num & int("1" * desc.bits, 2)

        return num * desc.register_multiplier

    def _convert_from_decimal(
        self, num: float, desc: ModbusSensorEntityDescription
    ) -> list[int]:
        """Convert from a decimal to registers"""
        raw_value: float = num / desc.register_multiplier

        if desc.bits:
            raise NotSupportedError("Setting of bit fields is not supported")

        if desc.bit_shift:
            raise NotSupportedError("Setting of bit fields is not supported")

        registers: list[int] = self.client.convert_to_registers(
            int(raw_value),
            data_type=(
                self.client.DATATYPE.UINT32
                if desc.register_count == 2
                else self.client.DATATYPE.UINT16
            ),
        )

        return registers

    def convert_from_registers(
        self, desc: ModbusSensorEntityDescription, registers: list
    ) -> str | float | int:
        """Entry point for conversion from registers"""
        value: Optional[Any] = None

        if desc.string:
            value = self._convert_to_string(registers)
        elif desc.float:
            value = self._convert_to_float(registers)
        elif desc.register_map:
            value = self._convert_to_enum(registers, desc)
        elif desc.flags:
            value = self._convert_to_flags(registers, desc)
        else:
            value = self._convert_to_decimal(registers, desc)

        return value

    def convert_to_registers(
        self, desc: ModbusSensorEntityDescription, value: str | float | int
    ) -> list[int] | int:
        """Entry point for conversion from registers"""
        registers: list[int] | None = None

        if desc.string:
            registers = self._convert_from_string(value)
        elif desc.float:
            registers = self._convert_from_float(value)
        elif desc.register_map:
            raise NotSupportedError("Setting of maps is not supported")
        elif desc.flags:
            raise NotSupportedError("Setting of flags is not supported")
        else:
            registers = self._convert_from_decimal(value, desc)

        return registers
