"""Sensor tests"""
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.components.sensor.const import STATE_CLASS_TOTAL_INCREASING
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import DOMAIN
from custom_components.modbus_local_gateway.sensor import (
    ModbusSensorEntity,
    async_setup_entry,
)
from custom_components.modbus_local_gateway.sensor_types.base import (
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.sensor_types.modbus_device_info import (
    ModbusDeviceInfo,
)


async def test_setup_entry(hass):
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
            ModbusSensorEntityDescription(key="key1", register_address=1),
        ]
    )
    pm2 = PropertyMock(
        return_value=[
            ModbusSensorEntityDescription(key="key2", register_address=2),
        ]
    )

    with patch(
        "custom_components.modbus_local_gateway.sensor_types.modbus_device_info.load_yaml",
        return_value={
            "device": MagicMock(),
            "entities": [],
        },
    ), patch.object(ModbusDeviceInfo, "entity_desciptions", pm1), patch.object(
        ModbusDeviceInfo, "properties", pm2
    ):
        await async_setup_entry(hass, entry, callback.add)

        callback.add.assert_called_once()
        assert len(callback.add.call_args[0][0]) == 2
        assert callback.add.call_args[1] == {"update_before_add": False}
        pm1.assert_called_once()
        pm2.assert_called_once()


async def test_update_none():
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = MagicMock()
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)

    coordinator.get_data.return_value = None
    entity._handle_coordinator_update()  # pylint: disable=protected-access

    coordinator.get_data.assert_called_once_with(ctx)


async def test_update_exception():
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = MagicMock()
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    coordinator.get_data.side_effect = Exception()

    with patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.debug"
    ) as debug, patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.error"
    ) as error:
        entity._handle_coordinator_update()  # pylint: disable=protected-access

        coordinator.get_data.assert_called_once_with(ctx)

        debug.assert_not_called()
        warning.assert_not_called()
        error.assert_called_once()


async def test_update_value():
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = MagicMock()
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    type(entity).entity_description = PropertyMock(
        return_value=ModbusSensorEntityDescription(key="key", register_address=1)
    )
    coordinator.get_data.return_value = 1
    write = MagicMock()
    entity.async_write_ha_state = write

    with patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.debug"
    ) as debug, patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.error"
    ) as error:
        entity._handle_coordinator_update()  # pylint: disable=protected-access

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_not_called()
        warning.assert_not_called()
        write.assert_called_once()


async def test_update_reset():
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = MagicMock()
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    type(entity).native_value = PropertyMock(return_value=2)
    type(entity).state_class = PropertyMock(return_value=STATE_CLASS_TOTAL_INCREASING)
    type(entity).entity_description = PropertyMock(
        return_value=ModbusSensorEntityDescription(key="key", register_address=1)
    )

    reset = PropertyMock()
    type(entity).last_reset = reset
    write = MagicMock()
    entity.async_write_ha_state = write

    coordinator.get_data.return_value = 1

    with patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.debug"
    ) as debug, patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.error"
    ) as error:
        entity._handle_coordinator_update()  # pylint: disable=protected-access

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_not_called()
        warning.assert_not_called()
        write.assert_called_once()
        reset.assert_called_once()


async def test_update_never_reset():
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = MagicMock()
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    type(entity).native_value = PropertyMock(return_value=2)
    type(entity).state_class = PropertyMock(return_value=STATE_CLASS_TOTAL_INCREASING)
    type(entity).entity_description = PropertyMock(
        return_value=ModbusSensorEntityDescription(
            key="key", register_address=1, never_resets=True
        )
    )

    reset = PropertyMock()
    type(entity).last_reset = reset
    write = MagicMock()
    entity.async_write_ha_state = write

    coordinator.get_data.return_value = 1

    with patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.debug"
    ) as debug, patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.error"
    ) as error:
        entity._handle_coordinator_update()  # pylint: disable=protected-access

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_not_called()
        warning.assert_not_called()
        write.assert_not_called()
        reset.assert_not_called()


async def test_update_deviceupdate():
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = MagicMock()
    device = MagicMock()
    hass = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    type(entity).hass = PropertyMock(return_value=hass)
    type(entity).native_value = PropertyMock(return_value=2)
    type(entity).state_class = PropertyMock(return_value=STATE_CLASS_TOTAL_INCREASING)
    type(entity).entity_description = PropertyMock(
        return_value=ModbusSensorEntityDescription(key="hw_version", register_address=1)
    )

    reset = PropertyMock()
    type(entity).last_reset = reset
    write = MagicMock()
    entity.async_write_ha_state = write

    coordinator.get_data.return_value = 1

    with patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.debug"
    ) as debug, patch(
        "custom_components.modbus_local_gateway.sensor._LOGGER.error"
    ) as error, patch(
        "custom_components.modbus_local_gateway.sensor.dr.async_get"
    ) as dr:
        dr.return_value = MagicMock()

        entity._handle_coordinator_update()  # pylint: disable=protected-access

        coordinator.get_data.assert_called_once_with(ctx)

        dr.assert_called_once_with(entity.hass)
        error.assert_not_called()
        debug.assert_called()
        warning.assert_not_called()
        write.assert_called_once()
        reset.assert_called_once()
