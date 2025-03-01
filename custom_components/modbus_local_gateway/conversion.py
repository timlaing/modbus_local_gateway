"""Conversion register functions"""

import logging
from typing import Any, Optional

from pymodbus.pdu import ModbusPDU
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
)
from pymodbus.pdu.bit_message import (
    ReadCoilsResponse,
    ReadDiscreteInputsResponse,
)

from .tcp_client import AsyncModbusTcpClient
from .entity_management.base import ModbusEntityDescription
from .entity_management.const import ModbusDataType

_LOGGER: logging.Logger = logging.getLogger(__name__)


class NotSupportedError(Exception):
    """Unsupported functionality"""


class InvalidDataTypeError(Exception):
    """Invalid data type for conversion"""


class Conversion:
    """Register conversion class"""

    def __init__(self, client: type[AsyncModbusTcpClient]) -> None:
        self.client: type[AsyncModbusTcpClient] = client

    def _convert_to_string(self, registers: list) -> str:
        """Convert to a string type"""
        value: str | int | float | list = self.client.convert_from_registers(
            registers,
            data_type=self.client.DATATYPE.STRING,
        )
        if isinstance(value, str):
            return value.split("\0")[0]
        raise InvalidDataTypeError()

    def _convert_from_string(self, value: str) -> list[int]:
        """Convert from a string type"""
        registers: list[int] = self.client.convert_to_registers(
            value,
            data_type=self.client.DATATYPE.STRING,
        )
        return registers

    def _convert_to_float(self, registers: list) -> float:
        """Convert to a float type"""
        value: str | int | float | list = self.client.convert_from_registers(
            registers,
            data_type=self.client.DATATYPE.FLOAT32,
        )
        if isinstance(value, float):
            return value
        raise InvalidDataTypeError()

    def _convert_from_float(self, value: float) -> list[int]:
        """Convert from a float type"""
        registers: list[int] = self.client.convert_to_registers(
            value,
            data_type=self.client.DATATYPE.FLOAT32,
        )
        return registers

    def _convert_to_enum(
        self, registers: list, desc: ModbusEntityDescription
    ) -> str | None:
        """Convert to an enum type"""
        int_val: int = int(self._convert_to_decimal(registers=registers, desc=desc))
        if desc.conv_map and int_val in desc.conv_map:
            value: str = desc.conv_map[int_val]
            return value

    def _convert_to_flags(
        self, registers: list, desc: ModbusEntityDescription
    ) -> str | None:
        """Convert to a flags type"""
        int_val: int = int(self._convert_to_decimal(registers=registers, desc=desc))
        ret_val: str | None = None
        if desc.conv_flags:
            for key in desc.conv_flags:
                if int_val & (0x1 << (key - 1)) != 0:
                    if ret_val is None:
                        ret_val = desc.conv_flags[key]
                    else:
                        ret_val += f" | {desc.conv_flags[key]}"
            return ret_val

    def _convert_to_decimal(
        self, registers: list, desc: ModbusEntityDescription
    ) -> float:
        """Convert to an int type"""
        num: str | int | float | list = self.client.convert_from_registers(
            registers,
            data_type=(
                self.client.DATATYPE.UINT32
                if desc.register_count == 2
                else self.client.DATATYPE.UINT16
            ),
        )

        if desc.conv_sum_scale is not None:
            num = sum(r * s for r, s in zip(num, desc.conv_sum_scale))

        if isinstance(num, int):
            if desc.conv_shift_bits:
                num = num >> desc.conv_shift_bits
            if desc.conv_bits:
                num = num & int("1" * desc.conv_bits, 2)
        elif desc.conv_shift_bits or desc.conv_bits:
            raise InvalidDataTypeError()

        if isinstance(num, (int, float)):
            if desc.conv_multiplier is not None:
                num = num * desc.conv_multiplier
            if desc.conv_offset:
                num += desc.conv_offset
        elif desc.conv_multiplier is not None or desc.conv_offset:
            raise InvalidDataTypeError()

        return num

    def _convert_from_decimal(
        self, num: float, desc: ModbusEntityDescription
    ) -> list[int]:
        """Convert from a decimal to registers"""
        if desc.conv_offset:
            num -= desc.conv_offset
        if desc.conv_multiplier is not None:
            num = num / desc.conv_multiplier
        if desc.conv_bits:
            raise NotSupportedError("Setting of bit fields is not supported")
        if desc.conv_shift_bits:
            raise NotSupportedError("Setting of bit fields is not supported")
        if desc.conv_sum_scale:
            raise NotSupportedError("Setting of scaled sums is not supported")

        registers: list[int] = self.client.convert_to_registers(
            int(round(num)),
            data_type=(
                self.client.DATATYPE.UINT32
                if desc.register_count == 2
                else self.client.DATATYPE.UINT16
            ),
        )
        return registers

    def convert_from_response(
        self, desc: ModbusEntityDescription, response: ModbusPDU
    ) -> str | float | int | bool | None:
        """Entry point for conversion from response (registers or bits)"""
        if desc.data_type in [ModbusDataType.HOLDING_REGISTER, ModbusDataType.INPUT_REGISTER]:
            if isinstance(response, (ReadHoldingRegistersResponse, ReadInputRegistersResponse)):
                registers = response.registers
                value: Optional[Any] = None
                if desc.is_string:
                    value = self._convert_to_string(registers)
                elif desc.is_float:
                    value = self._convert_to_float(registers)
                elif desc.conv_map:
                    value = self._convert_to_enum(registers, desc)
                elif desc.conv_flags:
                    value = self._convert_to_flags(registers, desc)
                else:
                    value = self._convert_to_decimal(registers, desc)
                return value
            else:
                raise TypeError("Invalid response type for register")
        elif desc.data_type == ModbusDataType.COIL:
            if isinstance(response, ReadCoilsResponse):
                return response.bits[0]  # Single bit for single entity
            else:
                raise TypeError("Invalid response type for coil")
        elif desc.data_type == ModbusDataType.DISCRETE_INPUT:
            if isinstance(response, ReadDiscreteInputsResponse):
                return response.bits[0]  # Single bit for single entity
            else:
                raise TypeError("Invalid response type for discrete input")
        else:
            raise ValueError("Invalid data type")

    def convert_to_registers(
        self, desc: ModbusEntityDescription, value: str | float | int
    ) -> list[int] | int:
        """Entry point for conversion to registers"""
        registers: list[int] | None = None
        if desc.is_string and isinstance(value, str):
            registers = self._convert_from_string(value)
        elif desc.is_float and isinstance(value, float):
            registers = self._convert_from_float(value)
        elif desc.conv_map:
            raise NotSupportedError("Setting of maps is not supported")
        elif desc.conv_flags:
            raise NotSupportedError("Setting of flags is not supported")
        elif isinstance(value, int | float):
            registers = self._convert_from_decimal(value, desc)
        else:
            raise InvalidDataTypeError()
        return registers
