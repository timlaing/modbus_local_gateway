"""Conversion Tests"""

import pytest
from pymodbus.pdu.bit_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.pdu.register_message import ReadInputRegistersResponse

from custom_components.modbus_local_gateway.conversion import Conversion
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusDataType,
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.tcp_client import AsyncModbusTcpClient


async def test_int16() -> None:
    """Test int16 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(1, data_type=client.DATATYPE.UINT16)
        ),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert 1 == value


async def test_from_int16() -> None:
    """Test from int16 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    registers = client.convert_to_registers(123, data_type=client.DATATYPE.UINT16)

    value = conversion.convert_to_registers(
        value=123,
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert registers == value


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
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            conv_shift_bits=8,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert 240 == value


async def test_int16_multiplier() -> None:
    """Test int16 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(8, data_type=client.DATATYPE.UINT16)
        ),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            conv_multiplier=0.1,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert value == pytest.approx(0.8, 0.01)


async def test_from_int16_multiplier() -> None:
    """Test from int16 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    registers = client.convert_to_registers(8, data_type=client.DATATYPE.UINT16)

    value = conversion.convert_to_registers(
        value=0.8,
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            conv_multiplier=0.1,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert registers == value


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
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            register_count=2,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert 65537 == value


async def test_from_int32() -> None:
    """Test from int32 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    registers = client.convert_to_registers(123, data_type=client.DATATYPE.UINT32)

    value = conversion.convert_to_registers(
        value=123,
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            register_count=2,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert registers == value


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
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            register_count=2,
            is_float=True,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert value == pytest.approx(1.0, 0.1)


async def test_from_float() -> None:
    """Test from float conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    registers = client.convert_to_registers(123.1, data_type=client.DATATYPE.FLOAT32)

    value = conversion.convert_to_registers(
        value=123.1,
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            register_count=2,
            is_float=True,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert registers == value


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
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            is_string=True,
            register_count=5,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert "HelloWorld" == value


async def test_from_string() -> None:
    """Test from string conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    registers = client.convert_to_registers(
        "HelloWorld", data_type=client.DATATYPE.STRING
    )

    value = conversion.convert_to_registers(
        value="HelloWorld",
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            is_string=True,
            register_count=5,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert registers == value


async def test_enum() -> None:
    """Test enum conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(5, data_type=client.DATATYPE.UINT16)
        ),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            conv_map={1: "One", 3: "three", 4: "Four", 5: "Good"},
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert "Good" == value


async def test_enum_missing() -> None:
    """Test enum conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(7, data_type=client.DATATYPE.UINT16)
        ),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            conv_map={1: "One", 3: "three", 4: "Four", 5: "Good"},
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert value is None


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
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            conv_map={1: "One", 3: "three", 4: "Four", 5: "Good"},
            conv_shift_bits=8,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert "Good" == value


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
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            conv_map={1: "One", 3: "three", 4: "Four", 5: "Good"},
            conv_bits=8,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert "Good" == value


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
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            conv_flags={1: "One", 3: "Good", 4: "Bad"},
            conv_bits=8,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert "Good" == value


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
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            conv_flags={1: "One", 3: "Good", 4: "Bad"},
            conv_bits=8,
            conv_shift_bits=8,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert "Good" == value


async def test_flags_missing() -> None:
    """Test flag conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(32, data_type=client.DATATYPE.UINT16)
        ),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            conv_flags={1: "One", 3: "Good", 4: "Bad"},
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert value is None


async def test_flags_multiple() -> None:
    """Test flag conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadInputRegistersResponse(
            registers=client.convert_to_registers(7, data_type=client.DATATYPE.UINT16)
        ),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            conv_flags={1: "One", 3: "Good", 4: "Bad"},
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert value == "One | Good"


async def test_convert_from_response_coils() -> None:
    """Test convert from response"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadCoilsResponse(
            registers=client.convert_to_registers(1, data_type=client.DATATYPE.UINT16),
            bits=[True],
        ),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            data_type=ModbusDataType.COIL,
        ),
    )

    assert value is True


async def test_convert_from_response_discrete_inputs() -> None:
    """Test convert from response"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_response(
        response=ReadDiscreteInputsResponse(
            registers=client.convert_to_registers(1, data_type=client.DATATYPE.UINT16),
            bits=[False],
        ),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            data_type=ModbusDataType.DISCRETE_INPUT,
        ),
    )

    assert value is False


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
            desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
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
            desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
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
            desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                register_address=1,
                key="test",
                data_type=ModbusDataType.DISCRETE_INPUT,
            ),
        )


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
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
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
