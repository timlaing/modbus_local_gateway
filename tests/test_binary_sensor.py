"""Binary Sensor tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.binary_sensor import (
    ModbusBinarySensorEntity,
    async_setup_entry,
)
from custom_components.modbus_local_gateway.const import DOMAIN
from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusBinarySensorEntityDescription,
    ModbusDataType,
)
from custom_components.modbus_local_gateway.entity_management.modbus_device_info import (
    ModbusDeviceInfo,
)


async def test_setup_entry(hass) -> None:
    """Test the HA setup function"""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "127.0.0.1",
            "port": "1234",
            "slave_id": 1,
            "filename": "test.yaml",
        },
    )
    callback = MagicMock()
    coordinator = AsyncMock()
    gw_dev = MagicMock()
    type(coordinator).gateway_device = PropertyMock(return_value=gw_dev)
    identifiers = PropertyMock()
    identifiers.return_value = ["a"]
    type(gw_dev).identifiers = identifiers
    hass.data[DOMAIN] = {"127.0.0.1:1234:1": coordinator}

    pm1 = PropertyMock(
        return_value=[
            ModbusBinarySensorEntityDescription(
                key="discrete_ro",
                register_address=1,
                data_type=ModbusDataType.DISCRETE_INPUT,
                control_type="binary_sensor",
            ),
        ]
    )
    pm2 = PropertyMock(return_value="")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.modbus_device_info.load_yaml",
            return_value={"device": MagicMock()},
        ),
        patch.object(ModbusDeviceInfo, "entity_descriptions", pm1),
        patch.object(ModbusDeviceInfo, "manufacturer", pm2),
        patch.object(ModbusDeviceInfo, "model", pm2),
    ):
        await async_setup_entry(hass, entry, callback.add)

        callback.add.assert_called_once()
        assert len(callback.add.call_args[0][0]) == 1
        assert callback.add.call_args[1] == {"update_before_add": False}
        pm1.assert_called_once()


async def test_update_none() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusBinarySensorEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.DISCRETE_INPUT,
            control_type="binary_sensor",
        ),
    )
    device = MagicMock()
    entity = ModbusBinarySensorEntity(coordinator=coordinator, ctx=ctx, device=device)

    coordinator.get_data.return_value = None
    entity._handle_coordinator_update()

    coordinator.get_data.assert_called_once_with(ctx)


async def test_update_exception() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusBinarySensorEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.DISCRETE_INPUT,
            control_type="binary_sensor",
        ),
    )
    device = MagicMock()
    entity = ModbusBinarySensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    coordinator.get_data.side_effect = Exception()

    with patch(
        "custom_components.modbus_local_gateway.binary_sensor._LOGGER.error"
    ) as error:
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)
        error.assert_called_once()


async def test_update_value_bool() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusBinarySensorEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.DISCRETE_INPUT,
            control_type="binary_sensor",
            on=True,
        ),
    )
    device = MagicMock()
    entity = ModbusBinarySensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    coordinator.get_data.return_value = True
    write = MagicMock()
    entity.async_write_ha_state = write

    with patch(
        "custom_components.modbus_local_gateway.binary_sensor._LOGGER.error"
    ) as error:
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)
        error.assert_not_called()
        write.assert_called_once()
        assert entity.is_on is True


async def test_update_value_int() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusBinarySensorEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.DISCRETE_INPUT,
            control_type="binary_sensor",
            on=10,
        ),
    )
    device = MagicMock()
    entity = ModbusBinarySensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    coordinator.get_data.return_value = 10
    write = MagicMock()
    entity.async_write_ha_state = write

    with patch(
        "custom_components.modbus_local_gateway.binary_sensor._LOGGER.error"
    ) as error:
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)
        error.assert_not_called()
        write.assert_called_once()
        assert entity.is_on is True
