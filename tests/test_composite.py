"""Composite register entity conversion tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from datetime import datetime

from homeassistant.util import dt as dt_util
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
)
import pytest

from custom_components.modbus_local_gateway.composite import CompositeConversion
from custom_components.modbus_local_gateway.conversion import (
    Conversion,
    ValueUnavailable,
)
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusDateTimeEntityDescription,
    ModbusFieldDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    CompositeType,
    ModbusDataType,
)


def make_description(
    composite_type: CompositeType = CompositeType.DATETIME,
    data_type: ModbusDataType = ModbusDataType.HOLDING_REGISTER,
    fields: tuple[tuple[str, int], ...] = (
        ("year", 45),
        ("month", 46),
        ("day", 47),
        ("hour", 48),
        ("minute", 49),
        ("second", 50),
    ),
    offset: int | None = 2000,
) -> ModbusDateTimeEntityDescription:
    """Build a composite description from (field name, address) pairs"""
    return ModbusDateTimeEntityDescription(
        key="clock",
        register_address=min(address for _, address in fields),
        register_count=max(address for _, address in fields)
        - min(address for _, address in fields)
        + 1,
        data_type=data_type,
        composite_type=composite_type,
        fields=tuple(
            ModbusFieldDescription(
                key=name,
                address=address,
                conv_offset=offset if name == "year" else None,
            )
            for name, address in fields
        ),
    )


@pytest.fixture(name="conversion")
def conversion_fixture() -> Conversion:
    """Conversion bound to the pymodbus client that decodes the registers"""
    return Conversion(AsyncModbusTcpClient)


def test_from_registers_datetime(conversion: Conversion) -> None:
    """Registers holding a date and time become one local datetime"""
    desc = make_description()

    value = CompositeConversion.from_registers(
        desc,
        ReadHoldingRegistersResponse(registers=[26, 9, 22, 16, 30, 5]),
        conversion,
    )

    assert value == datetime(
        2026, 9, 22, 16, 30, 5, tzinfo=dt_util.get_default_time_zone()
    )


def test_from_registers_without_second(conversion: Conversion) -> None:
    """A clock without seconds reads as a value on the minute"""
    desc = make_description(
        fields=(("year", 45), ("month", 46), ("day", 47), ("hour", 48), ("minute", 49))
    )

    value = CompositeConversion.from_registers(
        desc,
        ReadHoldingRegistersResponse(registers=[26, 9, 22, 16, 30]),
        conversion,
    )

    assert value == datetime(
        2026, 9, 22, 16, 30, 0, tzinfo=dt_util.get_default_time_zone()
    )


def test_from_registers_with_gap(conversion: Conversion) -> None:
    """Fields that are not adjacent are read from their own registers"""
    desc = make_description(
        fields=(
            ("year", 45),
            ("month", 46),
            ("day", 47),
            ("hour", 60),
            ("minute", 61),
            ("second", 62),
        )
    )

    value = CompositeConversion.from_registers(
        desc,
        ReadHoldingRegistersResponse(registers=[26, 9, 22] + [0] * 12 + [16, 30, 5]),
        conversion,
    )

    assert value == datetime(
        2026, 9, 22, 16, 30, 5, tzinfo=dt_util.get_default_time_zone()
    )


def test_from_registers_input_register(conversion: Conversion) -> None:
    """An input register composite is converted with the input response type"""
    desc = make_description(data_type=ModbusDataType.INPUT_REGISTER)

    value = CompositeConversion.from_registers(
        desc,
        ReadInputRegistersResponse(registers=[26, 9, 22, 16, 30, 5]),
        conversion,
    )

    assert value == datetime(
        2026, 9, 22, 16, 30, 5, tzinfo=dt_util.get_default_time_zone()
    )


def test_from_registers_date(conversion: Conversion) -> None:
    """A date composite reads as midnight of that day"""
    desc = make_description(
        composite_type=CompositeType.DATE,
        fields=(("year", 45), ("month", 46), ("day", 47)),
    )

    value = CompositeConversion.from_registers(
        desc,
        ReadHoldingRegistersResponse(registers=[26, 9, 22]),
        conversion,
    )

    assert value == datetime(2026, 9, 22, tzinfo=dt_util.get_default_time_zone())


def test_from_registers_time(conversion: Conversion) -> None:
    """A time composite reads as that time today"""
    desc = make_description(
        composite_type=CompositeType.TIME,
        fields=(("hour", 45), ("minute", 46), ("second", 47)),
        offset=None,
    )
    today = dt_util.now().date()

    value = CompositeConversion.from_registers(
        desc, ReadHoldingRegistersResponse(registers=[16, 30, 5]), conversion
    )

    assert value == datetime.combine(
        today,
        datetime.min.time().replace(hour=16, minute=30, second=5),
        dt_util.get_default_time_zone(),
    )


def test_from_registers_unavailable_value(conversion: Conversion) -> None:
    """A field the device marks unavailable leaves the entity unavailable"""
    desc = make_description(fields=(("year", 45), ("month", 46), ("day", 47)))

    response = ReadHoldingRegistersResponse(registers=[26, 65535, 47])

    with pytest.raises(ValueUnavailable):
        CompositeConversion.from_registers(desc, response, conversion)


def test_from_registers_impossible_value(conversion: Conversion) -> None:
    """Fields that cannot form a real date leave the entity unavailable"""
    desc = make_description(fields=(("year", 45), ("month", 46), ("day", 47)))

    response = ReadHoldingRegistersResponse(registers=[26, 13, 47])

    with pytest.raises(ValueUnavailable):
        CompositeConversion.from_registers(desc, response, conversion)


def test_from_registers_missing_registers(conversion: Conversion) -> None:
    """A response too short for a field leaves the entity unavailable"""
    desc = make_description(fields=(("year", 45), ("month", 46), ("day", 47)))

    response = ReadHoldingRegistersResponse(registers=[26, 9])

    with pytest.raises(ValueUnavailable):
        CompositeConversion.from_registers(desc, response, conversion)


def test_from_registers_string_field(conversion: Conversion) -> None:
    """A field that converts to text cannot be part of a date"""
    desc = ModbusDateTimeEntityDescription(
        key="clock",
        register_address=45,
        register_count=2,
        data_type=ModbusDataType.HOLDING_REGISTER,
        composite_type=CompositeType.DATE,
        fields=(
            ModbusFieldDescription(key="year", address=45, size=2, is_string=True),
        ),
    )

    response = ReadHoldingRegistersResponse(registers=[0x3031, 0x3233])

    with pytest.raises(ValueUnavailable):
        CompositeConversion.from_registers(desc, response, conversion)


def test_to_field_values_datetime() -> None:
    """One datetime is taken apart into the declared fields"""
    desc = make_description()

    assert CompositeConversion.to_field_values(
        desc, datetime(2026, 9, 22, 16, 30, 5)
    ) == {
        "year": 2026,
        "month": 9,
        "day": 22,
        "hour": 16,
        "minute": 30,
        "second": 5,
    }


def test_to_field_values_declared_fields_only() -> None:
    """A date composite only writes the fields it declares"""
    desc = make_description(
        composite_type=CompositeType.DATE,
        fields=(("year", 45), ("month", 46), ("day", 47)),
    )

    assert CompositeConversion.to_field_values(desc, datetime(2026, 9, 22, 16, 30)) == {
        "year": 2026,
        "month": 9,
        "day": 22,
    }
