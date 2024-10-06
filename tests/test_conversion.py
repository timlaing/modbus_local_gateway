"""Conversion Tests"""

from custom_components.modbus_local_gateway.sensor_types.base import (
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.sensor_types.conversion import Conversion
from custom_components.modbus_local_gateway.tcp_client import AsyncModbusTcpClient


async def test_int16() -> None:
    """Test int16 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(1, data_type=client.DATATYPE.UINT16),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
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
        ),
    )

    assert registers == value


async def test_int16_bitshift() -> None:
    """Test int16 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(0xF000, data_type=client.DATATYPE.UINT16),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            bit_shift=8,
        ),
    )

    assert 240 == value


async def test_int16_multiplier() -> None:
    """Test int16 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(8, data_type=client.DATATYPE.UINT16),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            register_multiplier=0.1,
        ),
    )

    assert 0.8 == value


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
            register_multiplier=0.1,
        ),
    )

    assert registers == value


async def test_int32() -> None:
    """Test in32 conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(65537, data_type=client.DATATYPE.UINT32),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            register_count=2,
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
        ),
    )

    assert registers == value


async def test_float() -> None:
    """Test float conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(1.0, data_type=client.DATATYPE.FLOAT32),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            register_count=2,
            float=True,
        ),
    )

    assert 1.0 == value


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
            float=True,
        ),
    )

    assert registers == value


async def test_string() -> None:
    """Test string conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(
            "HelloWorld", data_type=client.DATATYPE.STRING
        ),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            string=True,
            register_count=5,
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
            string=True,
            register_count=5,
        ),
    )

    assert registers == value


async def test_enum() -> None:
    """Test enum conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(5, data_type=client.DATATYPE.UINT16),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            register_map={1: "One", 3: "three", 4: "Four", 5: "Good"},
        ),
    )

    assert "Good" == value


async def test_enum_missing() -> None:
    """Test enum conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(7, data_type=client.DATATYPE.UINT16),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            register_map={1: "One", 3: "three", 4: "Four", 5: "Good"},
        ),
    )

    assert value is None


async def test_enum_bitshift() -> None:
    """Test enum conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(0x0500, data_type=client.DATATYPE.UINT16),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            register_map={1: "One", 3: "three", 4: "Four", 5: "Good"},
            bit_shift=8,
        ),
    )

    assert "Good" == value


async def test_enum_bits() -> None:
    """Test enum conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(0x0505, data_type=client.DATATYPE.UINT16),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            register_map={1: "One", 3: "three", 4: "Four", 5: "Good"},
            bits=8,
        ),
    )

    assert "Good" == value


async def test_flags_low() -> None:
    """Test flag conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(0x0104, data_type=client.DATATYPE.UINT16),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            flags={1: "One", 3: "Good", 4: "Bad"},
            bits=8,
        ),
    )

    assert "Good" == value


async def test_flags_high() -> None:
    """Test flag conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(0x0401, data_type=client.DATATYPE.UINT16),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            flags={1: "One", 3: "Good", 4: "Bad"},
            bits=8,
            bit_shift=8,
        ),
    )

    assert "Good" == value


async def test_flags_missing() -> None:
    """Test flag conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(32, data_type=client.DATATYPE.UINT16),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            flags={1: "One", 3: "Good", 4: "Bad"},
        ),
    )

    assert value is None


async def test_flags_multiple() -> None:
    """Test flag conversion"""
    client = AsyncModbusTcpClient
    conversion = Conversion(client=client)

    value = conversion.convert_from_registers(
        registers=client.convert_to_registers(7, data_type=client.DATATYPE.UINT16),
        desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="test",
            flags={1: "One", 3: "Good", 4: "Bad"},
        ),
    )

    assert value == "One | Good"
