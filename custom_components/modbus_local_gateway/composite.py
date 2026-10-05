"""Composite register entities - several registers as one semantic value.

Sits above the register conversion layer: a composite assembles the fields it
declares into one value (`from_registers`) and takes one value apart again
(`to_field_values`), while each field converts through the ordinary
`Conversion` code path, so `signed`, `float`, `multiplier`, `offset`, `swap` and
`unavailable_values` keep working per field.
"""

from __future__ import annotations

from datetime import date, datetime, time
import logging
from typing import Any

from homeassistant.util import dt as dt_util
from pymodbus.pdu.pdu import ModbusPDU
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
)

from .conversion import Conversion, ValueUnavailable
from .entity_management.base import (
    ModbusCompositeEntityDescription,
    ModbusFieldDescription,
)
from .entity_management.const import CompositeType, ModbusDataType

_LOGGER: logging.Logger = logging.getLogger(__name__)


class CompositeConversion:
    """Converts between the registers of a composite and its semantic value"""

    @staticmethod
    def from_registers(
        desc: ModbusCompositeEntityDescription,
        response: ModbusPDU,
        conversion: Conversion,
    ) -> date | time | datetime:
        """Assemble the registers read for `desc` into one local value.

        Each composite type gives back what it is: a `date` gives a `date`, a
        `time` gives a `time`, and only a `datetime` gives a `datetime`. There is
        no room for anything else in those two, so a clock no longer has to be
        dressed up as a date and time whose date is today's - which was not a
        reading of the device at all.

        A device clock is a wall-clock reading with no timezone of its own, so a
        `datetime` is stamped with Home Assistant's local timezone - which is
        what the `datetime` platform requires, since it refuses a naive value. A
        `time` or a `date` carries no timezone, so nothing is stamped on it.

        Fields that cannot form a real date or time (a device that reports
        0xFFFF, a clock that has never been set) raise `ValueUnavailable`, so
        the entity goes unavailable instead of raising on every poll.
        """
        registers: list[int] = list(response.registers)
        values: dict[str, int] = {}
        for field in desc.fields:
            start: int = field.address - desc.register_address
            field_registers: list[int] = registers[start : start + max(1, field.size)]
            if len(field_registers) != max(1, field.size):
                raise ValueUnavailable(
                    desc,
                    field.key,
                    f"registers {start}-{start + field.size - 1} of the read span "
                    "are missing",
                )
            values[field.key] = CompositeConversion._field_number(
                desc, field, field_registers, conversion
            )

        value: date | time | datetime = CompositeConversion._assemble(desc, values)
        if isinstance(value, datetime):
            return value.replace(tzinfo=dt_util.get_default_time_zone())
        return value

    @staticmethod
    def _field_number(
        desc: ModbusCompositeEntityDescription,
        field: ModbusFieldDescription,
        registers: list[int],
        conversion: Conversion,
    ) -> int:
        """Convert one field's registers to the whole number the field means"""
        response_class: type[ModbusPDU] = (
            ReadHoldingRegistersResponse
            if desc.data_type == ModbusDataType.HOLDING_REGISTER
            else ReadInputRegistersResponse
        )
        converted: Any = conversion.convert_from_response(
            desc=field.as_entity_description(desc.data_type),
            response=response_class(registers=registers),
        )
        if isinstance(converted, bool) or not isinstance(converted, (int, float)):
            raise ValueUnavailable(
                desc, converted, f"field {field.key} is not a number ({converted})"
            )
        return int(round(converted))

    @staticmethod
    def _assemble(
        desc: ModbusCompositeEntityDescription, values: dict[str, int]
    ) -> date | time | datetime:
        """Combine the field values into the value the composite type declares.

        Parts the config does not declare stay at zero, so a minute-resolution
        clock reads as a value on the minute rather than an error.
        """
        year: int = values.get("year", 1970)
        month: int = values.get("month", 1)
        day: int = values.get("day", 1)
        hour: int = values.get("hour", 0)
        minute: int = values.get("minute", 0)
        second: int = values.get("second", 0)

        try:
            if desc.composite_type is CompositeType.TIME:
                assembled: date | time | datetime = time(hour, minute, second)
            elif desc.composite_type is CompositeType.DATE:
                assembled = date(year, month, day)
            else:
                assembled = datetime(year, month, day, hour, minute, second)
        except ValueError as err:
            raise ValueUnavailable(
                desc,
                {key: values[key] for key in sorted(values)},
                f"{desc.composite_type} fields do not form a real value ({err})",
            ) from err

        _LOGGER.debug("Composite %s: %s", desc.key, assembled)
        return assembled

    @staticmethod
    def to_field_values(
        desc: ModbusCompositeEntityDescription, value: date | time | datetime
    ) -> dict[str, int]:
        """Take one semantic value apart into the fields the config declares.

        Only the declared fields come back, so a `date` composite writes
        year/month/day and leaves the device's clock registers alone.

        A `datetime` that arrives with an offset - the entity's own state, for
        instance, which Home Assistant serialises in UTC - is brought into local
        time first, so the device is set to the wall clock `from_registers`
        reads. A naive value is already the wall clock of the local timezone
        and is taken as it is. A `time` or a `date` carries no offset, so it is
        the wall clock already.
        """
        if isinstance(value, datetime) and value.tzinfo is not None:
            value = dt_util.as_local(value)
        # A date has no clock and a time has no calendar, so only the parts the
        # value actually has are taken. `validate` has already refused a config
        # that asks for a part the type does not have.
        parts: dict[str, Any] = {
            part: getattr(value, part)
            for part in ("year", "month", "day", "hour", "minute", "second")
            if hasattr(value, part)
        }
        declared: dict[str, int] = {
            field.key: parts[field.key] for field in desc.fields if field.key in parts
        }
        _LOGGER.debug("Composite %s: %s -> %s", desc.key, value.isoformat(), declared)
        return declared
