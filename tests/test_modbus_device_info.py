"""Device info Tests"""
# pylint: disable=unexpected-keyword-arg, protected-access

from unittest.mock import patch

from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
import pytest
import yaml

from custom_components.modbus_local_gateway.entity_management import modbus_device_info
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusDateTimeEntityDescription,
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    CompositeType,
    ControlType,
    ModbusDataType,
)
from custom_components.modbus_local_gateway.entity_management.device_loader import (
    load_devices,
)

POWER_DEVICE_CLASSES: frozenset[SensorDeviceClass] = frozenset({
    SensorDeviceClass.POWER,
    SensorDeviceClass.REACTIVE_POWER,
    SensorDeviceClass.APPARENT_POWER,
})


def test_entity_load() -> None:
    """Test device loading"""
    yaml_txt = """device:
        model: Model
        manufacturer: Manufacturer

read_write_word:
  entity_rw:
    name: Read-Write Entity
    address: 1

  entity_bitfield_switch:
    name: Entity Bitfield Switch
    address: 2
    control: switch
    bits: 1
    shift_bits: 4

  entity_shifted_switch:
    name: Entity Shifted Switch
    address: 3
    control: switch
    shift_bits: 1

  entity_invalid_switch:
    name: Entity Invalid Switch
    address: 4
    control: switch
    switch: true

  entity_text:
    name: Entity Text
    address: 5
    control: text

read_only_word:
  entity_ro:
    name: Read-Only Entity
    address: 2

read_write_boolean:
  coil_rw:
    name: Coil RW
    address: 3
    control: switch

read_only_boolean:
  discrete_ro:
    name: Discrete RO
    address: 4"""

    with patch(
        "custom_components.modbus_local_gateway.entity_management."
        "modbus_device_info.load_yaml"
    ) as load_yaml:
        load_yaml.return_value = yaml.full_load(yaml_txt)
        device = modbus_device_info.ModbusDeviceInfo("test.yaml")

        entities = device.entity_descriptions
        assert len(entities) == 7
        assert device.model == "Model"
        assert device.manufacturer == "Manufacturer"
        # A switch on a bit field is valid: writing it is a read-modify-write.
        assert any(
            e.key == "entity_bitfield_switch"
            and e.conv_bits == 1
            and e.conv_shift_bits == 4
            for e in entities
        )
        assert any(e.key == "entity_shifted_switch" for e in entities)
        assert any(
            e.key == "entity_rw" and e.data_type == ModbusDataType.HOLDING_REGISTER
            for e in entities
        )
        assert any(
            e.key == "entity_ro" and e.data_type == ModbusDataType.INPUT_REGISTER
            for e in entities
        )
        assert any(
            e.key == "coil_rw" and e.data_type == ModbusDataType.COIL for e in entities
        )
        assert any(
            e.key == "discrete_ro" and e.data_type == ModbusDataType.DISCRETE_INPUT
            for e in entities
        )
        assert any(
            e.key == "entity_text" and e.data_type == ModbusDataType.HOLDING_REGISTER
            for e in entities
        )
        assert not any(
            e.key == "entity_invalid_bits"
            and e.data_type == ModbusDataType.HOLDING_REGISTER
            for e in entities
        )
        assert not any(
            e.key == "entity_invalid_shift"
            and e.data_type == ModbusDataType.HOLDING_REGISTER
            for e in entities
        )
        assert not any(
            e.key == "entity_invalid_switch"
            and e.data_type == ModbusDataType.HOLDING_REGISTER
            for e in entities
        )


def test_entity_create_basic() -> None:
    """Test basic entity creation for all data types"""

    _config = {
        "device": {"manufacturer": "Test Manufacturer", "model": "Test Model"},
        "read_write_word": {"test_rw": {"name": "Title RW", "address": 1}},
        "read_only_word": {"test_ro": {"name": "Title RO", "address": 2}},
        "read_write_boolean": {
            "test_coil": {"name": "Title Coil", "address": 3, "control": "switch"}
        },
        "read_only_boolean": {
            "test_discrete1": {"name": "Title Discrete 1", "address": 4},
            "test_discrete2": {"name": "Title Discrete 2", "address": 5, "bits": 1},
            "test_discrete3": {
                "name": "Title Discrete 3",
                "address": 6,
                "shift_bits": 1,
            },
        },
    }

    with patch(
        "custom_components.modbus_local_gateway.entity_management."
        "modbus_device_info.load_yaml",
        return_value=_config,
    ):
        device = modbus_device_info.ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        assert len(entities) == 4
        assert any(
            e.name == "Title RW"
            and e.register_address == 1
            and e.data_type == ModbusDataType.HOLDING_REGISTER
            for e in entities
        )
        assert any(
            e.name == "Title RO"
            and e.register_address == 2
            and e.data_type == ModbusDataType.INPUT_REGISTER
            for e in entities
        )
        assert any(
            e.name == "Title Coil"
            and e.register_address == 3
            and e.data_type == ModbusDataType.COIL
            for e in entities
        )
        assert any(
            e.name == "Title Discrete 1"
            and e.register_address == 4
            and e.data_type == ModbusDataType.DISCRETE_INPUT
            for e in entities
        )
        assert not any(
            e.name == "Title Discrete 2"
            and e.register_address == 5
            and e.data_type == ModbusDataType.DISCRETE_INPUT
            for e in entities
        )
        assert not any(
            e.name == "Title Discrete 3"
            and e.register_address == 6
            and e.data_type == ModbusDataType.DISCRETE_INPUT
            for e in entities
        )


def test_entity_create_all_fields() -> None:
    """Test entity creation with all fields for a Holding Register"""

    _config = {
        "device": {"manufacturer": "Test Manufacturer", "model": "Test Model"},
        "read_write_word": {
            "test": {
                "name": "Title",
                "address": 1,
                "float": True,
                "string": False,
                "bits": 8,
                "shift_bits": 2,
                "multiplier": 10,
                "size": 4,
                "icon": "mdi:icon",
                "precision": 2,
                "map": {1: "One"},
                "state_class": "total",
                "device_class": "A",
                "unit_of_measurement": "%",
                "flags": {1: "One"},
                "no_flag_value": "No error",
            },
        },
        "read_only_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    }

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info.load_yaml",
            return_value=_config,
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management.base."
            "ModbusSensorEntityDescription.validate",
            return_value=True,
        ),
    ):
        device = modbus_device_info.ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        assert len(entities) == 1
        assert isinstance(entities[0], ModbusSensorEntityDescription)
        entity: ModbusSensorEntityDescription = entities[0]
        assert entity.name == "Title"
        assert entity.register_address == 1
        assert entity.is_float
        assert not entity.is_string
        assert entity.conv_bits == 8
        assert entity.conv_shift_bits == 2
        assert entity.conv_multiplier == 10
        assert entity.register_count == 4
        assert entity.icon == "mdi:icon"
        assert entity.precision == 2
        assert entity.conv_map == {1: "One"}
        assert entity.state_class == "total"
        assert entity.device_class == "A"
        assert entity.unit_of_measurement == "%"
        assert entity.conv_flags == {1: "One"}
        assert entity.conv_no_flag_value == "No error"
        assert entity.data_type == ModbusDataType.HOLDING_REGISTER


def test_entity_invalid_string_float() -> None:
    """Test invalid entity with both string and float"""

    _config = {
        "device": {"manufacturer": "Test Manufacturer", "model": "Test Model"},
        "read_write_word": {
            "test": {"name": "Title", "address": 1, "string": True, "float": True}
        },
        "read_only_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    }

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info.load_yaml",
            return_value=_config,
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "base._LOGGER.warning"
        ) as log,
    ):
        device = modbus_device_info.ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        log.assert_called_once()
        assert len(entities) == 0


@pytest.mark.parametrize(
    "step",
    ["invalid", 0, -1, float("nan"), float("inf"), float("-inf")],
    ids=["non-numeric", "zero", "negative", "nan", "infinity", "negative-infinity"],
)
def test_entity_invalid_number_step(step: object) -> None:
    """A step that is not a finite positive number skips the entity.

    `float()` accepts zero, negative values and non-finite values, but none of
    them is a usable step, and they must be rejected here rather than reaching
    `ModbusNumberEntity`.
    """

    _config = {
        "device": {"manufacturer": "Test Manufacturer", "model": "Test Model"},
        "read_write_word": {
            "test": {
                "name": "Title",
                "address": 1,
                "control": "number",
                "number": {"min": 0, "max": 10, "step": step},
            }
        },
        "read_only_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    }

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info.load_yaml",
            return_value=_config,
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info._LOGGER.warning"
        ) as log,
    ):
        device = modbus_device_info.ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        log.assert_called_once()
        assert len(entities) == 0


def test_entity_invalid_address() -> None:
    """Test entity missing address"""

    _config = {
        "device": {"manufacturer": "Test Manufacturer", "model": "Test Model"},
        "read_write_word": {"test": {"name": "Test"}},
        "read_only_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    }

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info.load_yaml",
            return_value=_config,
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info._LOGGER.error"
        ) as log,
    ):
        device = modbus_device_info.ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        log.assert_not_called()  # No error logged, just skipped
        assert len(entities) == 0


def test_entity_invalid_control_type() -> None:
    """Test entity with invalid control type for data type"""

    _config = {
        "device": {"manufacturer": "Test Manufacturer", "model": "Test Model"},
        "read_only_word": {"test": {"name": "Test", "address": 1, "control": "switch"}},
        "read_write_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    }

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info.load_yaml",
            return_value=_config,
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info._LOGGER.warning"
        ) as log,
    ):
        device = modbus_device_info.ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        log.assert_called_once()
        assert len(entities) == 0


@pytest.mark.parametrize(
    (
        "scan_interval",
        "num_entities",
        "log_message",
    ),
    [
        (None, 1, None),
        (10, 1, None),
        (0, 0, "scan_interval must be > 0"),
        (-5, 0, "scan_interval must be > 0"),
    ],
)
def test_validate_scan_interval(
    scan_interval: int | None,
    num_entities: int,
    log_message: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test _validate_scan_interval with various scan_interval values."""
    _config = {
        "device": {"manufacturer": "Test Manufacturer", "model": "Test Model"},
        "read_write_word": {
            "test": {"name": "Test", "address": 1, "scan_interval": scan_interval}
        },
        "read_only_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    }
    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info.load_yaml",
            return_value=_config,
        ),
        caplog.at_level("WARNING"),
    ):
        device = modbus_device_info.ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        assert len(entities) == num_entities
        if log_message:
            assert log_message in caplog.text


@pytest.mark.asyncio
async def test_devices_yaml(hass: HomeAssistant) -> None:
    """Validate yaml files with new structure"""
    with patch(
        "custom_components.modbus_local_gateway.entity_management."
        "device_loader._LOGGER.error"
    ) as log:
        devices: dict[str, modbus_device_info.ModbusDeviceInfo] = await load_devices(
            hass=hass
        )
        log.assert_not_called()

    for name in devices:
        with patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info._LOGGER.warning"
        ) as log:
            _ = devices[name].entity_descriptions
            log.assert_not_called()
            _ = devices[name].manufacturer
            log.assert_not_called()
            _ = devices[name].model
            log.assert_not_called()


@pytest.mark.asyncio
async def test_devices_power_entities_are_measurements(hass: HomeAssistant) -> None:
    """A power reading is a measurement, not a total.

    `total_increasing` cannot hold a negative state, so a meter that reports
    export as a negative demand was logged as ignored by `never_resets` and
    rejected by the recorder.
    """
    devices: dict[str, modbus_device_info.ModbusDeviceInfo] = await load_devices(
        hass=hass
    )

    offenders: list[str] = [
        f"{name}: {entity.key}"
        for name, device in devices.items()
        for entity in device.entity_descriptions
        if isinstance(entity, ModbusSensorEntityDescription)
        and entity.device_class in POWER_DEVICE_CLASSES
        and entity.state_class == SensorStateClass.TOTAL_INCREASING
    ]

    assert not offenders, f"power entities declared as totals: {offenders}"


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


def _load_composite(config: dict[str, object]) -> ModbusDateTimeEntityDescription:
    """Load the one composite entity a config describes"""
    entities = _load(config)
    assert len(entities) == 1
    desc = entities[0]
    assert isinstance(desc, ModbusDateTimeEntityDescription)
    return desc


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
    assert desc.fields[1].conv_offset is None
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
            "bad address, size, bits or shift_bits",
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
            "bad address, size, bits or shift_bits",
        ),
        (
            {
                "type": "time",
                "fields": {
                    "hour": {"address": 1, "size": "one"},
                    "minute": {"address": 2},
                },
            },
            "bad address, size, bits or shift_bits",
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
    desc = _load_composite({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {
            "clock": {
                "type": "datetime",
                "scan_interval": 30,
                "icon": "mdi:clock",
                "entity_category": "config",
                "entity_registry_enabled_default": False,
                "fields": {
                    "year": {"address": 1},
                    "month": {"address": 2},
                    "day": {"address": 3},
                    "hour": {"address": 4},
                    "minute": {"address": 5},
                },
            }
        },
    })

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


def test_composite_entity_bad_entity_category(
    caplog: pytest.LogCaptureFixture,
) -> None:
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


def test_composite_entity_bit_fields_load() -> None:
    """A field may claim part of a register"""
    desc = _load_composite({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {
            "period1_end": {
                "name": "Period 1 End Time",
                "type": "time",
                "data_type": "read_write_word",
                "fields": {
                    "minute": {"address": 3038, "bits": 8, "shift_bits": 0},
                    "hour": {"address": 3038, "bits": 5, "shift_bits": 8},
                },
            }
        },
    })

    assert [
        (field.key, field.conv_bits, field.conv_shift_bits) for field in desc.fields
    ] == [("minute", 8, 0), ("hour", 5, 8)]
    assert [[field.key for field in run] for run in desc.runs] == [["minute", "hour"]]


def test_composite_entity_bit_fields_are_shared_with_other_entities() -> None:
    """A packed register can carry a composite and separate entities together"""
    entities = _load({
        "device": {"manufacturer": "Manufacturer", "model": "Model"},
        "composite": {
            "period1_end": {
                "name": "Period 1 End Time",
                "type": "time",
                "data_type": "read_write_word",
                "fields": {
                    "minute": {"address": 3038, "bits": 8, "shift_bits": 0},
                    "hour": {"address": 3038, "bits": 5, "shift_bits": 8},
                },
            }
        },
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
