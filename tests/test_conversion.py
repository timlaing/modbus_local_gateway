"""Conversion Tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
import pytest
from pymodbus.client.mixin import ModbusClientMixin
from pymodbus.pdu.bit_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.pdu.register_message import ReadInputRegistersResponse

from custom_components.modbus_local_gateway.conversion import (
    Conversion,
    InvalidDataTypeError,
)
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusDataType,
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import SwapType
from custom_components.modbus_local_gateway.tcp_client import AsyncModbusTcpClient


@pytest.mark.asyncio
async def test_int16() -> None:
    """Test int16 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(1, data_type=client.DATATYPE.UINT16)
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert 1 == value


@pytest.mark.asyncio
async def test_from_int16() -> None:
    """Test from int16 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    registers = client.convert_to_registers(123, data_type=client.DATATYPE.UINT16)

    value = conversion.convert_to_registers(
        value=123,
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert registers == value


@pytest.mark.asyncio
async def test_int16_bitshift() -> None:
    """Test int16 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(
                0xF000, data_type=client.DATATYPE.UINT16
            )
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            conv_shift_bits=8,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert 240 == value


@pytest.mark.asyncio
async def test_int16_multiplier() -> None:
    """Test int16 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(8, data_type=client.DATATYPE.UINT16)
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            conv_multiplier=0.1,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert value == pytest.approx(0.8, 0.01)


@pytest.mark.asyncio
async def test_from_int16_multiplier() -> None:
    """Test from int16 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    registers = client.convert_to_registers(8, data_type=client.DATATYPE.UINT16)

    value = conversion.convert_to_registers(
        value=0.8,
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            conv_multiplier=0.1,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert registers == value


@pytest.mark.asyncio
async def test_int32() -> None:
    """Test in32 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(
                65537, data_type=client.DATATYPE.UINT32
            )
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            register_count=2,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert 65537 == value


@pytest.mark.asyncio
async def test_from_int32() -> None:
    """Test from int32 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    registers = client.convert_to_registers(123, data_type=client.DATATYPE.UINT32)

    value = conversion.convert_to_registers(
        value=123,
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            register_count=2,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert registers == value


@pytest.mark.asyncio
async def test_float() -> None:
    """Test float conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(
                1.0, data_type=client.DATATYPE.FLOAT32
            )
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            register_count=2,
            is_float=True,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert value == pytest.approx(1.0, 0.1)


@pytest.mark.asyncio
async def test_from_float() -> None:
    """Test from float conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    registers = client.convert_to_registers(123.1, data_type=client.DATATYPE.FLOAT32)

    value = conversion.convert_to_registers(
        value=123.1,
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            register_count=2,
            is_float=True,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert registers == value


@pytest.mark.asyncio
async def test_string() -> None:
    """Test string conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(
                "HelloWorld", data_type=client.DATATYPE.STRING
            )
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            is_string=True,
            register_count=5,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert "HelloWorld" == value


@pytest.mark.asyncio
async def test_from_string() -> None:
    """Test from string conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    registers = client.convert_to_registers(
        "HelloWorld", data_type=client.DATATYPE.STRING
    )

    value = conversion.convert_to_registers(
        value="HelloWorld",
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            is_string=True,
            register_count=5,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert registers == value


@pytest.mark.asyncio
async def test_enum() -> None:
    """Test enum conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(5, data_type=client.DATATYPE.UINT16)
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            conv_map={1: "One", 3: "three", 4: "Four", 5: "Good"},
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert "Good" == value


@pytest.mark.asyncio
async def test_enum_missing() -> None:
    """Test enum conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(7, data_type=client.DATATYPE.UINT16)
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            conv_map={1: "One", 3: "three", 4: "Four", 5: "Good"},
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert value is None


@pytest.mark.asyncio
async def test_enum_bitshift() -> None:
    """Test enum conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(
                0x0500, data_type=client.DATATYPE.UINT16
            )
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            conv_map={1: "One", 3: "three", 4: "Four", 5: "Good"},
            conv_shift_bits=8,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert "Good" == value


@pytest.mark.asyncio
async def test_enum_bits() -> None:
    """Test enum conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(
                0x0505, data_type=client.DATATYPE.UINT16
            )
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            conv_map={1: "One", 3: "three", 4: "Four", 5: "Good"},
            conv_bits=8,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert "Good" == value


@pytest.mark.asyncio
async def test_flags_low() -> None:
    """Test flag conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(
                0x0104, data_type=client.DATATYPE.UINT16
            )
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            conv_flags={1: "One", 3: "Good", 4: "Bad"},
            conv_bits=8,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert "Good" == value


@pytest.mark.asyncio
async def test_flags_high() -> None:
    """Test flag conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(
                0x0401, data_type=client.DATATYPE.UINT16
            )
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            conv_flags={1: "One", 3: "Good", 4: "Bad"},
            conv_bits=8,
            conv_shift_bits=8,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert "Good" == value


@pytest.mark.asyncio
async def test_flags_missing() -> None:
    """Test flag conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(32, data_type=client.DATATYPE.UINT16)
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            conv_flags={1: "One", 3: "Good", 4: "Bad"},
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert value is None


@pytest.mark.asyncio
async def test_flags_multiple() -> None:
    """Test flag conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(7, data_type=client.DATATYPE.UINT16)
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            conv_flags={1: "One", 3: "Good", 4: "Bad"},
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert value == "One | Good"


@pytest.mark.asyncio
async def test_convert_from_response_coils() -> None:
    """Test convert from response"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadCoilsResponse(
            registers=client.convert_to_registers(1, data_type=client.DATATYPE.UINT16),
            bits=[True],
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.COIL,
        ),
    )

    assert value is True


@pytest.mark.asyncio
async def test_convert_from_response_discrete_inputs() -> None:
    """Test convert from response"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadDiscreteInputsResponse(
            registers=client.convert_to_registers(1, data_type=client.DATATYPE.UINT16),
            bits=[False],
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.DISCRETE_INPUT,
        ),
    )

    assert value is False


@pytest.mark.asyncio
async def test_convert_from_response_errors() -> None:
    """Test convert from response"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    with pytest.raises(TypeError):
        conversion.convert_from_response(
            response=ReadDiscreteInputsResponse(
                registers=client.convert_to_registers(
                    1, data_type=client.DATATYPE.UINT16
                ),
            ),
            desc=ModbusSensorEntityDescription(
                register_address=1,
                key="test",
                data_type=ModbusDataType.INPUT_REGISTER,
            ),
        )

    with pytest.raises(TypeError):
        conversion.convert_from_response(
            response=ReadInputRegistersResponse(
                registers=client.convert_to_registers(
                    1, data_type=client.DATATYPE.UINT16
                ),
            ),
            desc=ModbusSensorEntityDescription(
                register_address=1,
                key="test",
                data_type=ModbusDataType.COIL,
            ),
        )

    with pytest.raises(TypeError):
        conversion.convert_from_response(
            response=ReadInputRegistersResponse(
                registers=client.convert_to_registers(
                    1, data_type=client.DATATYPE.UINT16
                ),
            ),
            desc=ModbusSensorEntityDescription(
                register_address=1,
                key="test",
                data_type=ModbusDataType.DISCRETE_INPUT,
            ),
        )


@pytest.mark.asyncio
async def test_float_multiplier() -> None:
    """Test float with multiplier conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(
                7.5, data_type=client.DATATYPE.FLOAT32
            )
        ),
        desc=ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            conv_multiplier=0.001,
            is_float=True,
            register_count=2,
            state_class="total_increasing",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert value == pytest.approx(0.0075, 0.0001)


@pytest.mark.parametrize(
    "registers,swap_type,expected",
    [
        # NONE: no change
        ([0x1234, 0x5678], None, [0x1234, 0x5678]),
        # BYTE: swap bytes in each register
        ([0x1234, 0x5678], SwapType.BYTE, [0x3412, 0x7856]),
        # WORD: reverse register order
        ([0x1234, 0x5678], SwapType.WORD, [0x5678, 0x1234]),
        # WORD_BYTE: reverse order and swap bytes in each
        ([0x1234, 0x5678], SwapType.WORD_BYTE, [0x7856, 0x3412]),
        # Single register, BYTE
        ([0x1234], SwapType.BYTE, [0x3412]),
        # Single register, WORD (should be same as input)
        ([0x1234], SwapType.WORD, [0x1234]),
        # Single register, WORD_BYTE (should swap bytes)
        ([0x1234], SwapType.WORD_BYTE, [0x3412]),
    ],
)
def test_swap_registers(
    registers: list[int], swap_type: None | SwapType, expected: list[int]
) -> None:
    """Test _swap_registers with various swap types."""
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = ModbusSensorEntityDescription(
        register_address=1,
        key="test",
        conv_swap=swap_type,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    result: list[int] = conversion._swap_registers(registers, desc)
    assert result == expected


def test_swap_registers_does_not_modify_input() -> None:
    """Test that _swap_registers does not modify the input list."""
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = ModbusSensorEntityDescription(
        register_address=1,
        key="test",
        conv_swap=SwapType.WORD_BYTE,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    original: list[int] = [0x1234, 0x5678]
    input_copy: list[int] = original.copy()
    _: list[int] = conversion._swap_registers(original, desc)
    assert original == input_copy


@pytest.mark.parametrize(
    "signed,size,expected",
    [
        (False, 1, ModbusClientMixin.DATATYPE.UINT16),
        (False, 2, ModbusClientMixin.DATATYPE.UINT32),
        (False, 4, ModbusClientMixin.DATATYPE.UINT64),
        (True, 1, ModbusClientMixin.DATATYPE.INT16),
        (True, 2, ModbusClientMixin.DATATYPE.INT32),
        (True, 4, ModbusClientMixin.DATATYPE.INT64),
        (False, 3, None),  # Invalid size
        (True, 3, None),  # Invalid size
    ],
)
def test_get_number_type(
    signed: bool, size: int, expected: ModbusClientMixin.DATATYPE
) -> None:
    """Test _get_number_data_type with various signed and size combinations."""
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = ModbusSensorEntityDescription(
        register_address=1,
        key="test",
        is_float=False,
        is_signed=signed,
        register_count=size,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    if expected is None:
        with pytest.raises(InvalidDataTypeError):
            conversion._get_number_data_type(desc)
    else:
        result: ModbusClientMixin.DATATYPE = conversion._get_number_data_type(desc)
        assert result == expected


@pytest.mark.parametrize(
    "size,expected",
    [
        (2, ModbusClientMixin.DATATYPE.FLOAT32),
        (4, ModbusClientMixin.DATATYPE.FLOAT64),
        (3, None),  # Invalid size for float
        (1, None),  # Invalid size for float
    ],
)
def test_get_float_type(size: int, expected: ModbusClientMixin.DATATYPE) -> None:
    """Test _get_float_data_type with various sizes."""
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = ModbusSensorEntityDescription(
        register_address=1,
        key="test",
        is_float=True,
        register_count=size,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    if expected is None:
        with pytest.raises(InvalidDataTypeError):
            conversion._get_float_data_type(desc)
    else:
        result: ModbusClientMixin.DATATYPE = conversion._get_float_data_type(desc)
        assert result == expected
