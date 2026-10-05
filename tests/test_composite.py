"""Composite register entity conversion tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from datetime import date, datetime, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

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
    """A date composite reads as that day, and nothing else"""
    desc = make_description(
        composite_type=CompositeType.DATE,
        fields=(("year", 45), ("month", 46), ("day", 47)),
    )

    value = CompositeConversion.from_registers(
        desc,
        ReadHoldingRegistersResponse(registers=[26, 9, 22]),
        conversion,
    )

    assert value == date(2026, 9, 22)
    assert not isinstance(value, datetime)


def test_from_registers_time(conversion: Conversion) -> None:
    """A time composite reads as that time, and no date with it"""
    desc = make_description(
        composite_type=CompositeType.TIME,
        fields=(("hour", 45), ("minute", 46), ("second", 47)),
        offset=None,
    )

    value = CompositeConversion.from_registers(
        desc, ReadHoldingRegistersResponse(registers=[16, 30, 5]), conversion
    )

    assert value == time(16, 30, 5)
    assert not isinstance(value, datetime)


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


def test_to_field_values_converts_aware_value_to_local_time() -> None:
    """A value that arrives with an offset is written as the local wall clock.

    Home Assistant serialises the state of a datetime entity in UTC, so a value
    that comes back that way is converted before it is split: the device is set
    to the clock `from_registers` reads, not to its UTC equivalent.
    """
    desc = make_description()

    with patch.object(dt_util, "DEFAULT_TIME_ZONE", ZoneInfo("Europe/Berlin")):
        assert CompositeConversion.to_field_values(
            desc, datetime(2026, 9, 22, 14, 30, 5, tzinfo=ZoneInfo("UTC"))
        ) == {
            "year": 2026,
            "month": 9,
            "day": 22,
            "hour": 16,
            "minute": 30,
            "second": 5,
        }


def test_to_field_values_keeps_naive_value_as_it_is() -> None:
    """A naive value is already a local wall clock and is taken as it is"""
    desc = make_description()

    with patch.object(dt_util, "DEFAULT_TIME_ZONE", ZoneInfo("Europe/Berlin")):
        assert CompositeConversion.to_field_values(
            desc, datetime(2026, 9, 22, 16, 30)
        ) == {
            "year": 2026,
            "month": 9,
            "day": 22,
            "hour": 16,
            "minute": 30,
            "second": 0,
        }


def _packed_time_description(
    address: int = 3038,
    data_type: ModbusDataType = ModbusDataType.HOLDING_REGISTER,
) -> ModbusDateTimeEntityDescription:
    """Build the Growatt period 1 word: minute bits 0-7, hour bits 8-12.

    Bits 13-14 are the charge mode and bit 15 the enable, which this composite
    does not describe.
    """
    return ModbusDateTimeEntityDescription(
        key="period1",
        register_address=address,
        register_count=1,
        data_type=data_type,
        composite_type=CompositeType.TIME,
        fields=(
            ModbusFieldDescription(
                key="minute", address=address, conv_bits=8, conv_shift_bits=0
            ),
            ModbusFieldDescription(
                key="hour", address=address, conv_bits=5, conv_shift_bits=8
            ),
        ),
    )


def test_from_registers_bit_fields(conversion: Conversion) -> None:
    """A time packed into one register is read out of its bits"""
    desc = _packed_time_description()

    value = CompositeConversion.from_registers(
        desc,
        ReadHoldingRegistersResponse(registers=[(9 << 8) | 0]),
        conversion,
    )

    assert isinstance(value, time)
    assert (value.hour, value.minute) == (9, 0)


def test_from_registers_bit_fields_keep_mode_and_enable(conversion: Conversion) -> None:
    """The bits the composite does not describe do not disturb the value"""
    desc = _packed_time_description()
    word = (1 << 15) | (2 << 13) | (22 << 8) | 45

    value = CompositeConversion.from_registers(
        desc, ReadHoldingRegistersResponse(registers=[word]), conversion
    )

    assert isinstance(value, time)
    assert (value.hour, value.minute) == (22, 45)


def test_from_registers_bit_field_unavailable(conversion: Conversion) -> None:
    """A sentinel inside the bits makes the whole composite unavailable"""
    desc = _packed_time_description()

    response = ReadHoldingRegistersResponse(registers=[(9 << 8) | 0x3C])

    with pytest.raises(ValueUnavailable):
        CompositeConversion.from_registers(desc, response, conversion)


def test_from_registers_bit_field_with_offset(conversion: Conversion) -> None:
    """A bit field converts through the same path, offset included"""
    desc = ModbusDateTimeEntityDescription(
        key="clock",
        register_address=45,
        register_count=1,
        data_type=ModbusDataType.HOLDING_REGISTER,
        composite_type=CompositeType.DATE,
        fields=(
            ModbusFieldDescription(
                key="year", address=45, conv_bits=8, conv_offset=2000
            ),
            ModbusFieldDescription(key="month", address=46),
            ModbusFieldDescription(key="day", address=47),
        ),
    )

    value = CompositeConversion.from_registers(
        desc, ReadHoldingRegistersResponse(registers=[26, 9, 22]), conversion
    )

    assert isinstance(value, date)
    assert value.year == 2026


def test_bit_fields_share_one_run() -> None:
    """Two bit fields in one register are written in one request"""
    desc = _packed_time_description()

    assert desc.runs == (desc.fields,)


def test_bit_field_next_to_a_plain_field_is_one_run() -> None:
    """A bit field and the register beside it are written in one request"""
    desc = ModbusDateTimeEntityDescription(
        key="clock",
        register_address=45,
        register_count=2,
        data_type=ModbusDataType.HOLDING_REGISTER,
        composite_type=CompositeType.TIME,
        fields=(
            ModbusFieldDescription(
                key="hour", address=45, conv_bits=5, conv_shift_bits=8
            ),
            ModbusFieldDescription(key="minute", address=46),
        ),
    )

    assert [[field.key for field in run] for run in desc.runs] == [
        ["hour", "minute"],
    ]


def test_fields_with_a_gap_stay_separate() -> None:
    """Fields that are not adjacent still need a request of their own"""
    desc = ModbusDateTimeEntityDescription(
        key="clock",
        register_address=45,
        register_count=3,
        data_type=ModbusDataType.HOLDING_REGISTER,
        composite_type=CompositeType.TIME,
        fields=(
            ModbusFieldDescription(
                key="hour", address=45, conv_bits=5, conv_shift_bits=8
            ),
            ModbusFieldDescription(key="minute", address=47),
        ),
    )

    assert [[field.key for field in run] for run in desc.runs] == [["hour"], ["minute"]]


def test_overlapping_bit_fields_rejected() -> None:
    """Two fields cannot claim the same bits"""
    desc = ModbusDateTimeEntityDescription(
        key="clock",
        register_address=45,
        register_count=1,
        data_type=ModbusDataType.HOLDING_REGISTER,
        composite_type=CompositeType.TIME,
        fields=(
            ModbusFieldDescription(
                key="hour", address=45, conv_bits=5, conv_shift_bits=8
            ),
            ModbusFieldDescription(
                key="minute", address=45, conv_bits=8, conv_shift_bits=4
            ),
        ),
    )

    with patch(
        "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
    ) as log:
        assert not desc.validate()

    assert "both claim bits 8-11" in log.call_args.args[0] % log.call_args.args[1:]


def test_bit_field_geometry_rejected() -> None:
    """Bits that do not fit the register are rejected"""
    desc = ModbusDateTimeEntityDescription(
        key="clock",
        register_address=45,
        register_count=1,
        data_type=ModbusDataType.HOLDING_REGISTER,
        composite_type=CompositeType.TIME,
        fields=(
            ModbusFieldDescription(
                key="hour", address=45, conv_bits=20, conv_shift_bits=0
            ),
            ModbusFieldDescription(key="minute", address=46),
        ),
    )

    with patch(
        "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
    ) as log:
        assert not desc.validate()

    assert (
        "does not fit the 16 bits it addresses"
        in log.call_args.args[0] % log.call_args.args[1:]
    )


def test_signed_bit_field_rejected() -> None:
    """`signed` has no meaning for a field masked out of a register"""
    desc = ModbusDateTimeEntityDescription(
        key="clock",
        register_address=45,
        register_count=1,
        data_type=ModbusDataType.HOLDING_REGISTER,
        composite_type=CompositeType.TIME,
        fields=(
            ModbusFieldDescription(
                key="hour", address=45, conv_bits=5, conv_shift_bits=8, is_signed=True
            ),
            ModbusFieldDescription(key="minute", address=46),
        ),
    )

    with patch(
        "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
    ) as log:
        assert not desc.validate()

    assert "signed cannot be combined" in log.call_args.args[0] % log.call_args.args[1:]
