"""Conversion Tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
import pytest
from pymodbus.client.mixin import ModbusClientMixin
from pymodbus.pdu.bit_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
)

from custom_components.modbus_local_gateway.conversion import (
    Conversion,
    InvalidDataTypeError,
    NotSupportedError,
)
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusDataType,
    ModbusNumberEntityDescription,
    ModbusSensorEntityDescription,
    ModbusSwitchEntityDescription,
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


def _switch_desc(**kwargs) -> ModbusSwitchEntityDescription:
    """A writable bit-field switch description."""
    return ModbusSwitchEntityDescription(
        register_address=1,
        key="test",
        control_type="switch",
        data_type=ModbusDataType.HOLDING_REGISTER,
        **kwargs,
    )


def _number_desc(**kwargs) -> ModbusNumberEntityDescription:
    """A writable bit-field number description."""
    return ModbusNumberEntityDescription(
        register_address=1,
        key="test",
        control_type="number",
        data_type=ModbusDataType.HOLDING_REGISTER,
        min=0,
        max=255,
        **kwargs,
    )


@pytest.mark.parametrize(
    ("current", "value", "expected"),
    [
        (0b0000_0000_0001_0011, 1, 0b0000_0000_0001_0011),  # already set, no change
        (0b0000_0000_0000_0011, 1, 0b0000_0000_0001_0011),  # set, neighbours kept
        (0b1111_1111_1111_1111, 0, 0b1111_1111_1110_1111),  # clear, neighbours kept
        (0b0000_0000_0001_0000, 0, 0b0000_0000_0000_0000),  # clear the only bit
    ],
)
def test_merge_single_bit(current: int, value: int, expected: int) -> None:
    """Setting or clearing one bit must leave every other bit untouched."""
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = _switch_desc(conv_bits=1, conv_shift_bits=4, on=1, off=0)

    assert conversion.merge_into_registers(desc, value, [current]) == [expected]


def test_merge_low_byte_preserves_high_byte() -> None:
    """Two 8-bit fields in one register: writing the low byte must not zero the high byte.

    A register holding 30 in the high byte and 6 in the low byte; writing 45
    to the low byte must leave the high byte at 30.
    """
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = _number_desc(conv_bits=8, conv_shift_bits=0)

    result = conversion.merge_into_registers(desc, 45, [(30 << 8) | 6])

    assert result == [(30 << 8) | 45]
    assert result[0] >> 8 == 30


def test_merge_high_byte_preserves_low_byte() -> None:
    """The mirror case: writing the high byte must not disturb the low byte."""
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = _number_desc(conv_bits=8, conv_shift_bits=8)

    result = conversion.merge_into_registers(desc, 30, [(12 << 8) | 45])

    assert result == [(30 << 8) | 45]
    assert result[0] & 0xFF == 45


def test_merge_across_two_registers() -> None:
    """A field straddling the boundary between the two registers of a 32-bit entity."""
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = _number_desc(register_count=2, conv_bits=8, conv_shift_bits=12)

    current = AsyncModbusTcpClient.convert_to_registers(
        0xABCD_1234, data_type=AsyncModbusTcpClient.DATATYPE.UINT32
    )
    result = conversion.merge_into_registers(desc, 0xFF, current)

    merged = AsyncModbusTcpClient.convert_from_registers(
        result, data_type=AsyncModbusTcpClient.DATATYPE.UINT32
    )
    assert merged == 0xABCF_F234


@pytest.mark.parametrize(
    "swap", [None, SwapType.BYTE, SwapType.WORD, SwapType.WORD_BYTE]
)
def test_merge_round_trips_through_swap(swap) -> None:
    """Merging then reading back must return the value that was written.

    `_swap_registers` is its own inverse, which is what lets the merge use the
    same call to un-swap and re-swap.
    """
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = _number_desc(
        register_count=2, conv_bits=8, conv_shift_bits=8, conv_swap=swap
    )

    current = AsyncModbusTcpClient.convert_to_registers(
        0x0000_0000, data_type=AsyncModbusTcpClient.DATATYPE.UINT32
    )
    merged = conversion.merge_into_registers(desc, 0x5A, current)

    read_back = conversion.convert_from_response(
        desc=desc,
        response=ReadHoldingRegistersResponse(registers=merged),
    )
    assert read_back == 0x5A


def test_merge_applies_multiplier_and_offset() -> None:
    """A scaled bit field descales before it is packed."""
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = _number_desc(conv_bits=8, conv_shift_bits=0, conv_multiplier=0.5)

    # 21.5 degrees / 0.5 == 43 raw, merged into the low byte
    assert conversion.merge_into_registers(desc, 21.5, [0xFF00]) == [0xFF00 | 43]


@pytest.mark.parametrize("value", [256, -1])
def test_merge_rejects_value_that_does_not_fit(value: int) -> None:
    """Overflowing the field would corrupt the neighbouring controls."""
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = _number_desc(conv_bits=8, conv_shift_bits=0)

    with pytest.raises(ValueError, match="does not fit"):
        conversion.merge_into_registers(desc, value, [0x1234])


def test_merge_width_defaults_to_top_of_register() -> None:
    """With `shift_bits` but no `bits`, the field runs to the top of the span."""
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = _number_desc(conv_shift_bits=12)

    assert conversion.field_geometry(desc) == (12, 0xF)
    assert conversion.merge_into_registers(desc, 0xA, [0x5678]) == [0xA678]


def test_convert_to_registers_still_refuses_bit_fields() -> None:
    """The plain (non read-modify-write) path must not silently zero a field."""
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = _number_desc(conv_bits=8, conv_shift_bits=0)

    with pytest.raises(NotSupportedError, match="merge_into_registers"):
        conversion.convert_to_registers(desc, 5)


def test_merge_refuses_sum_scale() -> None:
    """`sum_scale` has no inverse. Validation rejects it at load, but
    merge_into_registers is public, so it guards too."""
    conversion = Conversion(client=AsyncModbusTcpClient)
    desc = _number_desc(conv_bits=8, conv_sum_scale=[1.0, 0.1])

    with pytest.raises(NotSupportedError, match="scaled sums"):
        conversion.merge_into_registers(desc, 5, [0x1234])
