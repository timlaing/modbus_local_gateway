"""Device info composite entity tests"""
# pylint: disable=unexpected-keyword-arg, protected-access

from unittest.mock import patch

from homeassistant.const import EntityCategory
import pytest
import yaml

from custom_components.modbus_local_gateway.entity_management import modbus_device_info
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusCompositeEntityDescription,
    ModbusDateEntityDescription,
    ModbusDateTimeEntityDescription,
    ModbusTimeEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    CompositeType,
    ControlType,
    ModbusDataType,
    WriteFunction,
)

COMPOSITE_YAML = """device:
        model: Model
        manufacturer: Manufacturer

composite:
  current_time:
    name: Current Time
    type: datetime
    fields:
      year: {address: 45, offset: 2000}
      month: {address: 46}
      day: {address: 47}
      hour: {address: 48}
      minute: {address: 49}
      second: {address: 50}"""


def _load(config: dict[str, object]) -> list[modbus_device_info.DESCRIPTION_TYPE]:
    """Load a device description from a config dict"""
    with patch(
        "custom_components.modbus_local_gateway.entity_management."
        "modbus_device_info.load_yaml",
        return_value=config,
    ):
        device = modbus_device_info.ModbusDeviceInfo("test.yaml")
        return list(device.entity_descriptions)


def _load_composite(config: dict[str, object]) -> ModbusCompositeEntityDescription:
    """Load the one composite entity a config describes"""
    entities = _load(config)
    assert len(entities) == 1
    desc = entities[0]
    assert isinstance(desc, ModbusCompositeEntityDescription)
    return desc


# The parts each composite type carries, and the register each one is read from.
# `year` carries 2000, as it does in a real device config.
_COMPOSITE_FIELDS: dict[str, tuple[tuple[str, int], ...]] = {
    "datetime": (
        ("year", 45),
        ("month", 46),
        ("day", 47),
        ("hour", 48),
        ("minute", 49),
        ("second", 50),
    ),  # noqa: E501
    "time": (("hour", 45), ("minute", 46), ("second", 47)),
    "date": (("year", 45), ("month", 46), ("day", 47)),
}


def _composite_config(composite_type: str, **extra: object) -> dict[str, object]:
    """A config describing one composite entity of the given type"""
    fields: dict[str, dict[str, int]] = {
        part: {"address": address, **({"offset": 2000} if part == "year" else {})}
        for part, address in _COMPOSITE_FIELDS[composite_type]
    }
    return {
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {"clock": {"type": composite_type, "fields": fields, **extra}},
    }


@pytest.mark.parametrize(
    ("composite_type", "expected_class", "expected_control"),
    [
        ("datetime", ModbusDateTimeEntityDescription, ControlType.DATETIME),
        ("time", ModbusTimeEntityDescription, ControlType.TIME),
        ("date", ModbusDateEntityDescription, ControlType.DATE),
    ],
)
def test_each_composite_type_gets_its_own_platform(
    composite_type: str,
    expected_class: type[ModbusCompositeEntityDescription],
    expected_control: ControlType,
) -> None:
    """A composite is exposed on the platform of the value it is.

    A `time` used to be built as a `datetime` entity, so a clock read as a date
    and a time whose date was the day it was read - and the entity id said
    `datetime` for a value that is only a time.
    """
    desc = _load_composite(_composite_config(composite_type))

    assert isinstance(desc, expected_class)
    assert desc.control_type == expected_control
    assert desc.composite_type == composite_type


def test_composite_entity_load() -> None:
    """Test composite entity creation"""
    desc = _load_composite(yaml.full_load(COMPOSITE_YAML))
    assert desc.key == "current_time"
    assert desc.name == "Current Time"
    assert desc.data_type == ModbusDataType.HOLDING_REGISTER
    assert desc.control_type == ControlType.DATETIME
    assert desc.composite_type == CompositeType.DATETIME
    assert desc.register_address == 45
    assert desc.register_count == 6
    assert [field.key for field in desc.fields] == [
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "second",
    ]
    assert desc.fields[0].conv_offset == 2000
    assert desc.fields[0].conv_write_offset is None
    assert desc.fields[1].conv_offset is None
    assert desc.write_function is None
    # one run of adjacent fields, so one read and one write
    assert desc.runs == (desc.fields,)


def test_composite_entity_data_type() -> None:
    """A composite entity declares the data type its fields live in"""
    assert (
        _load_composite({
            "device": {"manufacturer": "Manufacturer", "model": "Model"},
            "composite": {
                "clock": {
                    "type": "datetime",
                    "data_type": "read_only_word",
                    "fields": {
                        "year": {"address": 1},
                        "month": {"address": 2},
                        "day": {"address": 3},
                        "hour": {"address": 4},
                        "minute": {"address": 5},
                    },
                }
            },
        }).data_type
        == ModbusDataType.INPUT_REGISTER
    )


def test_composite_entity_gapped_fields_group_runs() -> None:
    """Fields that are not adjacent are grouped into separate runs"""
    desc = _load_composite({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {
            "clock": {
                "type": "time",
                "fields": {
                    "hour": {"address": 10},
                    "minute": {"address": 11},
                    "second": {"address": 20},
                },
            }
        },
    })
    assert desc.composite_type == CompositeType.TIME
    assert desc.register_address == 10
    assert desc.register_count == 11
    assert [[field.key for field in run] for run in desc.runs] == [
        ["hour", "minute"],
        ["second"],
    ]


def test_composite_entity_field_conversion() -> None:
    """Field conversion options are taken from the field mapping"""
    fields = _load_composite({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {
            "clock": {
                "type": "time",
                "fields": {
                    "hour": {"address": 10, "multiplier": 0.1},
                    "minute": {
                        "address": 11,
                        "signed": True,
                        "swap": True,
                        "unavailable_values": [999],
                    },
                },
            }
        },
    }).fields
    assert fields[0].conv_multiplier == 0.1
    assert fields[1].is_signed
    assert fields[1].conv_swap
    assert fields[1].conv_unavailable_values == [999]


def test_composite_entity_field_write_offset() -> None:
    """A field keeps a write offset apart from the offset it reads with"""
    fields = _load_composite({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {
            "clock": {
                "type": "datetime",
                "fields": {
                    "year": {"address": 45, "write_offset": -2000},
                    "month": {"address": 46},
                    "day": {"address": 47},
                    "hour": {"address": 48},
                    "minute": {"address": 49},
                    "second": {"address": 50},
                },
            }
        },
    }).fields
    assert fields[0].conv_write_offset == -2000
    # the read path is untouched: only the write is offset
    assert fields[0].conv_offset is None
    assert fields[1].conv_write_offset is None


def test_composite_entity_write_offset_accepts_a_big_integer() -> None:
    """A big integer is an integer, and must not abort loading the config

    Checking it went through `float()`, which raises OverflowError on a value
    too large for one, escaping the field parser instead of warning.
    """
    fields = _load_composite({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {
            "clock": {
                "type": "datetime",
                "fields": {
                    "year": {"address": 45, "write_offset": 10**400},
                    "month": {"address": 46},
                    "day": {"address": 47},
                    "hour": {"address": 48},
                    "minute": {"address": 49},
                    "second": {"address": 50},
                },
            }
        },
    }).fields
    assert fields[0].conv_write_offset == 10**400


def test_composite_entity_write_function() -> None:
    """A composite can ask to be written register by register"""
    desc = _load_composite({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {
            "clock": {
                "type": "datetime",
                "write_function": "single",
                "fields": {
                    "year": {"address": 45},
                    "month": {"address": 46},
                    "day": {"address": 47},
                    "hour": {"address": 48},
                    "minute": {"address": 49},
                    "second": {"address": 50},
                },
            }
        },
    })
    assert desc.write_function == WriteFunction.SINGLE


def test_composite_entity_write_with() -> None:
    """A composite can declare registers to rewrite together with its fields"""
    desc = _load_composite({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {
            "clock": {
                "type": "time",
                "write_with": 3038,
                "fields": {"hour": {"address": 3039}, "minute": {"address": 3040}},
            }
        },
    })
    assert desc.write_with == (3038,)


def test_composite_entity_write_with_list() -> None:
    """write_with accepts a list of register addresses"""
    desc = _load_composite({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {
            "clock": {
                "type": "time",
                "write_with": [3038, 3041],
                "fields": {"hour": {"address": 3039}, "minute": {"address": 3040}},
            }
        },
    })
    assert desc.write_with == (3038, 3041)


def test_composite_entity_write_with_keeps_span() -> None:
    """write_with does not move the entity's own read span"""
    desc = _load_composite({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {
            "clock": {
                "type": "time",
                "write_with": 3038,
                "fields": {"hour": {"address": 3039}, "minute": {"address": 3040}},
            }
        },
    })
    assert desc.register_address == 3039
    assert desc.register_count == 2
    assert desc.write_span == (3038, 3040)


@pytest.mark.parametrize(
    ("entity", "expected_log"),
    [
        # a packed register is described as separate entities at one address
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "bits": 4, "signed": True},
                    "minute": {"address": 2},
                },
            },
            "signed cannot be combined",
        ),
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "bits": 20},
                    "minute": {"address": 2},
                },
            },
            "does not fit the 16 bits it addresses",
        ),
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "shift_bits": 4},
                    "minute": {"address": 1, "bits": 8},
                },
            },
            "both claim bits",
        ),
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "bits": "four"},
                    "minute": {"address": 2},
                },
            },
            "bad address, size, bits, shift_bits or write_offset",
        ),
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "map": {1: "a"}},
                    "minute": {"address": 2},
                },
            },
            "cannot use map",
        ),
        # a field is not a part of a date or time
        (
            {
                "type": "time",
                "fields": {"hour": {"address": 1}, "weekday": {"address": 2}},
            },
            "is not part of a time",
        ),
        # a type that is not a date or time
        (
            {
                "type": "weekday",
                "fields": {"hour": {"address": 1}, "minute": {"address": 2}},
            },
            "type must be one of",
        ),
        (
            {"type": 3, "fields": {"hour": {"address": 1}, "minute": {"address": 2}}},
            "type must be one of",
        ),
        # no type at all
        (
            {"fields": {"hour": {"address": 1}, "minute": {"address": 2}}},
            "type must be one of",
        ),
        # missing fields, or fields that are not a mapping
        ({"type": "time"}, "needs a fields mapping"),
        ({"type": "time", "fields": {}}, "needs a fields mapping"),
        ({"type": "time", "fields": []}, "needs a fields mapping"),
        (
            {"type": "time", "fields": {"hour": 1, "minute": 2}},
            "should be a dictionary",
        ),
        # a field without an address
        (
            {
                "type": "time",
                "fields": {"hour": {"offset": 1}, "minute": {"address": 2}},
            },
            "is missing address",
        ),
        # an address or size that is not a number
        (
            {
                "type": "time",
                "fields": {"hour": {"address": "first"}, "minute": {"address": 2}},
            },
            "bad address, size, bits, shift_bits or write_offset",
        ),
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "size": "one"},
                    "minute": {"address": 2},
                },
            },
            "bad address, size, bits, shift_bits or write_offset",
        ),
        # a write offset on a field of more than one register
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "size": 2, "write_offset": -2000},
                    "minute": {"address": 2},
                },
            },
            "cannot be used with size",
        ),
        # a write offset where there is no single value to offset
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "bits": 5, "write_offset": -2000},
                    "minute": {"address": 2},
                },
            },
            "cannot be combined with bits or shift_bits",
        ),
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "swap": "byte", "write_offset": -2000},
                    "minute": {"address": 2},
                },
            },
            "cannot be combined with swap",
        ),
        # a write offset that is not a whole number, and a bool, which is an int
        # in Python
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "write_offset": -1999.5},
                    "minute": {"address": 2},
                },
            },
            "bad address, size, bits, shift_bits or write_offset",
        ),
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "write_offset": True},
                    "minute": {"address": 2},
                },
            },
            "bad address, size, bits, shift_bits or write_offset",
        ),
        # a write function that is neither single nor multiple
        (
            {
                "type": "time",
                "write_function": "preset",
                "fields": {"hour": {"address": 1}, "minute": {"address": 2}},
            },
            "write_function must be one of single, multiple",
        ),
        # a write_with address that is stripped off whatever holds it
        (
            {
                "type": "time",
                "write_with": "3038",
                "fields": {"hour": {"address": 1}, "minute": {"address": 2}},
            },
            "write_with must be a register address",
        ),
        (
            {
                "type": "time",
                "write_with": [True],
                "fields": {"hour": {"address": 1}, "minute": {"address": 2}},
            },
            "write_with must be a register address",
        ),
        (
            {
                "type": "time",
                "write_with": [],
                "fields": {"hour": {"address": 1}, "minute": {"address": 2}},
            },
            "write_with must be a register address",
        ),
        # a write_with address that is already a field
        (
            {
                "type": "time",
                "write_with": 1,
                "fields": {"hour": {"address": 1}, "minute": {"address": 2}},
            },
            "already a field of the composite",
        ),
        # write_with needs registers that can be written
        (
            {
                "type": "time",
                "write_with": 3038,
                "data_type": "read_only_word",
                "fields": {"hour": {"address": 1}, "minute": {"address": 2}},
            },
            "write_with cannot be used on",
        ),
        # write_with defeats write_function single
        (
            {
                "type": "time",
                "write_with": 3038,
                "write_function": "single",
                "fields": {"hour": {"address": 1}, "minute": {"address": 2}},
            },
            "write_with cannot combine with write_function single",
        ),
        # write_with that would drag gap registers into the write span
        (
            {
                "type": "time",
                "write_with": 3038,
                "fields": {"hour": {"address": 3040}, "minute": {"address": 3041}},
            },
            "would also rewrite registers",
        ),
        # a key that no field understands
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "description": 1},
                    "minute": {"address": 2},
                },
            },
            "unknown keys description",
        ),
        # a field that cannot hold the value
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "float": True},
                    "minute": {"address": 2},
                },
            },
            "hour",
        ),
        # coils cannot hold a date
        (
            {
                "type": "time",
                "data_type": "read_write_boolean",
                "fields": {"hour": {"address": 1}, "minute": {"address": 2}},
            },
            "data_type must be",
        ),
        (
            {
                "type": "time",
                "data_type": "read_only_boolean",
                "fields": {"hour": {"address": 1}, "minute": {"address": 2}},
            },
            "data_type must be",
        ),
    ],
)
def test_composite_entity_invalid(
    entity: dict[str, object], expected_log: str, caplog: pytest.LogCaptureFixture
) -> None:
    """Test invalid composite entities"""

    with patch(
        "custom_components.modbus_local_gateway.entity_management."
        "modbus_device_info.load_yaml",
        return_value={
            "device": {"manufacturer": "Manufacturer", "model": "Model"},
            "composite": {"clock": entity},
        },
    ):
        device = modbus_device_info.ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions

    assert len(entities) == 0
    assert expected_log in caplog.text


def test_composite_entity_keeps_entity_level_options() -> None:
    """A composite takes the entity-level options any other entity takes"""
    desc = _load_composite(
        _composite_config(
            "datetime",
            scan_interval=30,
            icon="mdi:clock",
            entity_category="config",
            entity_registry_enabled_default=False,
        )
    )

    assert desc.scan_interval == 30
    assert desc.icon == "mdi:clock"
    assert desc.entity_category == EntityCategory.CONFIG
    assert desc.entity_registry_enabled_default is False


def test_composite_entity_without_entity_level_options() -> None:
    """The entity-level options are optional"""
    desc = _load_composite(yaml.full_load(COMPOSITE_YAML))

    assert desc.scan_interval is None
    assert desc.icon is None
    assert desc.entity_registry_enabled_default is True


@pytest.mark.parametrize(
    ("scan_interval", "num_entities", "log_message"),
    [
        (10, 1, None),
        (0, 0, "scan_interval must be > 0"),
        (-5, 0, "scan_interval must be > 0"),
    ],
)
def test_composite_entity_scan_interval(
    scan_interval: int,
    num_entities: int,
    log_message: str | None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A composite honours and validates the scan_interval of any other entity"""
    config = yaml.full_load(COMPOSITE_YAML)
    config["composite"]["current_time"]["scan_interval"] = scan_interval
    with caplog.at_level("WARNING"):
        entities = _load(config)

    assert len(entities) == num_entities
    if log_message:
        assert log_message in caplog.text


def test_composite_entity_bad_entity_category(caplog: pytest.LogCaptureFixture) -> None:
    """An unusable entity_category warns and is left out"""
    config = yaml.full_load(COMPOSITE_YAML)
    config["composite"]["current_time"]["entity_category"] = "nonsense"
    with caplog.at_level("WARNING"):
        entities = _load(config)

    assert len(entities) == 1
    assert entities[0].entity_category is None
    assert "Invalid entity_category nonsense" in caplog.text


def test_composite_entity_missing_required_field() -> None:
    """A date needs a year, a month and a day"""

    entities = _load({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {
            "date": {
                "type": "date",
                "fields": {"year": {"address": 1}, "month": {"address": 2}},
            }
        },
    })

    assert not entities


def test_composite_entity_alongside_other_entities() -> None:
    """Composite entities are loaded next to the ordinary ones"""
    entities = _load(
        yaml.full_load(
            COMPOSITE_YAML
            + """

read_write_word:
  entity_rw:
    name: Read-Write Entity
    address: 1

read_only_word: {}
read_write_boolean: {}
read_only_boolean: {}"""
        )
    )

    assert len(entities) == 2
    assert {desc.key for desc in entities} == {"current_time", "entity_rw"}


# The Growatt period 1 word: minute in bits 0-7, hour in bits 8-12. Bits 13-14
# are the charge mode and bit 15 the enable, which this composite leaves alone.
_PACKED_TIME: dict[str, object] = {
    "name": "Period 1 End Time",
    "type": "time",
    "data_type": "read_write_word",
    "fields": {
        "minute": {"address": 3038, "bits": 8, "shift_bits": 0},
        "hour": {"address": 3038, "bits": 5, "shift_bits": 8},
    },
}


def test_composite_entity_bit_fields_load() -> None:
    """A field may claim part of a register"""
    desc = _load_composite({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {"period1_end": _PACKED_TIME},
    })

    assert [
        (field.key, field.conv_bits, field.conv_shift_bits) for field in desc.fields
    ] == [("minute", 8, 0), ("hour", 5, 8)]
    assert [[field.key for field in run] for run in desc.runs] == [["minute", "hour"]]


def test_composite_entity_bit_fields_are_shared_with_other_entities() -> None:
    """A packed register can carry a composite and separate entities together"""
    entities = _load({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {"period1_end": _PACKED_TIME},
        "read_write_word": {
            "period1_enable": {
                "name": "Period 1 Enable",
                "address": 3038,
                "control": "switch",
                "bits": 1,
                "shift_bits": 15,
            }
        },
        "read_only_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    })

    assert {desc.key for desc in entities} == {"period1_end", "period1_enable"}
