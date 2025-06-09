"""Conversion register functions"""

import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.client.mixin import ModbusClientMixin
from pymodbus.pdu import ModbusPDU
from pymodbus.pdu.bit_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
)

from .entity_management.base import (
    ModbusEntityDescription,
)
from .entity_management.const import ModbusDataType, SwapType

_LOGGER: logging.Logger = logging.getLogger(__name__)


class NotSupportedError(Exception):
    """Unsupported functionality"""


class InvalidDataTypeError(Exception):
    """Invalid data type for conversion"""


class Conversion:
    """Register conversion class"""

    def __init__(self, client: type[AsyncModbusTcpClient]) -> None:
        self.client: type[AsyncModbusTcpClient] = client

    def _swap_registers(
        self, registers: list[int], desc: ModbusEntityDescription
    ) -> list[int]:
        """Do swap as needed."""
        _registers: list[int] = registers.copy()
        if desc.conv_swap in (SwapType.BYTE, SwapType.WORD_BYTE):
            # convert [12][34] --> [21][43]
            for i, register in enumerate(_registers):
                _registers[i] = int.from_bytes(
                    register.to_bytes(2, byteorder="little"),
                    byteorder="big",
                    signed=False,
                )
        if desc.conv_swap in (SwapType.WORD, SwapType.WORD_BYTE):
            # convert [12][34] ==> [34][12]
            _registers.reverse()
        return _registers

    def _get_number_data_type(
        self, desc: ModbusEntityDescription
    ) -> ModbusClientMixin.DATATYPE:
        """Get the data type for integer conversion"""
        if desc.register_count == 4:
            return (
                ModbusClientMixin.DATATYPE.INT64
                if desc.is_signed
                else ModbusClientMixin.DATATYPE.UINT64
            )
        if desc.register_count == 2:
            return (
                ModbusClientMixin.DATATYPE.INT32
                if desc.is_signed
                else ModbusClientMixin.DATATYPE.UINT32
            )
        if desc.register_count == 1:
            return (
                ModbusClientMixin.DATATYPE.INT16
                if desc.is_signed
                else ModbusClientMixin.DATATYPE.UINT16
            )
        raise InvalidDataTypeError(
            f"Invalid register count for integer conversion: {desc.register_count}"
        )

    def _get_float_data_type(
        self, desc: ModbusEntityDescription
    ) -> ModbusClientMixin.DATATYPE:
        """Get the data type for float conversion"""
        if desc.register_count == 4:
            return ModbusClientMixin.DATATYPE.FLOAT64
        if desc.register_count == 2:
            return ModbusClientMixin.DATATYPE.FLOAT32
        raise InvalidDataTypeError(
            f"Invalid register count for float conversion: {desc.register_count}"
        )

    def _convert_to_string(self, registers: list[int]) -> str:
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

    def _convert_to_float(
        self, registers: list, desc: ModbusEntityDescription
    ) -> float:
        """Convert to a float type"""
        value: str | int | float | list = self.client.convert_from_registers(
            registers,
            data_type=self._get_float_data_type(desc),
        )
        if isinstance(value, float):
            value = self._apply_conversion_operations(value, desc)
            return value
        raise InvalidDataTypeError()

    def _convert_from_float(
        self, value: float, desc: ModbusEntityDescription
    ) -> list[int]:
        """Convert from a float type"""
        registers: list[int] = self.client.convert_to_registers(
            value,
            data_type=self._get_float_data_type(desc),
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
        self, registers: list[int], desc: ModbusEntityDescription
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
        self, registers: list[int], desc: ModbusEntityDescription
    ) -> float | int:
        """Convert to a float type"""
        num: int | float = self._convert_registers_to_number(registers, desc)
        num = self._apply_conversion_operations(num, desc)
        return num

    def _convert_registers_to_number(
        self, registers: list[int], desc: ModbusEntityDescription
    ) -> int | float:
        """Convert registers to a number based on data type"""
        num: str | int | float | list = self.client.convert_from_registers(
            registers, data_type=self._get_number_data_type(desc)
        )

        if desc.conv_sum_scale is not None and isinstance(num, list):
            num = sum(r * s for r, s in zip(num, desc.conv_sum_scale))

        if isinstance(num, float):
            return num

        if isinstance(num, int):
            if desc.conv_shift_bits:
                num = num >> desc.conv_shift_bits
            if desc.conv_bits:
                num = num & int("1" * desc.conv_bits, 2)
            return num
        raise InvalidDataTypeError(
            f"Invalid data type for conversion: {type(num).__name__}"
        )

    def _apply_conversion_operations(
        self, num: int | float, desc: ModbusEntityDescription
    ) -> float:
        """Apply multiplier and offset to the number"""
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
            data_type=self._get_number_data_type(desc),
        )
        return registers

    def convert_from_response(
        self, desc: ModbusEntityDescription, response: ModbusPDU
    ) -> str | float | int | bool | None:
        """Entry point for conversion from response (registers or bits)"""
        if desc.data_type in [
            ModbusDataType.HOLDING_REGISTER,
            ModbusDataType.INPUT_REGISTER,
        ]:
            return self._convert_from_register_response(desc, response)
        elif desc.data_type == ModbusDataType.COIL:
            return self._convert_from_coil_response(response)
        elif desc.data_type == ModbusDataType.DISCRETE_INPUT:
            return self._convert_from_discrete_input_response(response)
        else:
            raise ValueError("Invalid data type")

    def _convert_from_register_response(
        self, desc: ModbusEntityDescription, response: ModbusPDU
    ) -> str | float | int | None:
        """Convert from register response"""
        if not isinstance(
            response, (ReadHoldingRegistersResponse, ReadInputRegistersResponse)
        ):
            raise TypeError("Invalid response type for register")

        registers: list[int] = self._swap_registers(response.registers, desc)
        if desc.is_string:
            return self._convert_to_string(registers)
        if desc.is_float:
            return self._convert_to_float(registers, desc)
        if desc.conv_map:
            return self._convert_to_enum(registers, desc)
        if desc.conv_flags:
            return self._convert_to_flags(registers, desc)

        return self._convert_to_decimal(registers, desc)

    def _convert_from_coil_response(self, response: ModbusPDU) -> bool:
        """Convert from coil response"""
        if not isinstance(response, ReadCoilsResponse):
            raise TypeError("Invalid response type for coil")
        return response.bits[0]  # Single bit for single entity

    def _convert_from_discrete_input_response(self, response: ModbusPDU) -> bool:
        """Convert from discrete input response"""
        if not isinstance(response, ReadDiscreteInputsResponse):
            raise TypeError("Invalid response type for discrete input")
        return response.bits[0]  # Single bit for single entity

    def convert_to_registers(
        self, desc: ModbusEntityDescription, value: str | float | int
    ) -> list[int]:
        """Entry point for conversion to registers"""
        registers: list[int] | None = None
        if desc.is_string and isinstance(value, str):
            registers = self._convert_from_string(value)
        elif desc.is_float and isinstance(value, (float, int)):
            registers = self._convert_from_float(value, desc)
        elif desc.conv_map:
            raise NotSupportedError("Setting of maps is not supported")
        elif desc.conv_flags:
            raise NotSupportedError("Setting of flags is not supported")
        elif isinstance(value, (int, float)):
            registers = self._convert_from_decimal(value, desc)
        else:
            raise InvalidDataTypeError()
        return self._swap_registers(registers, desc)
