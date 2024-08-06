"""Sensor tests"""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry
import pytest
from custom_components.modbus_local_gateway.const import DOMAIN
from custom_components.modbus_local_gateway.sensor_types.base import (
    ModbusTextEntityDescription,
)
from custom_components.modbus_local_gateway.sensor_types.modbus_device_info import (
    ModbusDeviceInfo,
)
from custom_components.modbus_local_gateway.text import (
    ModbusTextEntity,
    async_setup_entry,
)


@pytest.mark.nohomeassistant
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
            ModbusTextEntityDescription(key="key1", register_address=1),
        ]
    )
    pm2 = PropertyMock(
        return_value=[
            ModbusTextEntityDescription(
                key="key2",
                register_address=2,
                control_type="text",
            ),
        ]
    )

    pm3 = PropertyMock(return_value="")

    with patch(
        "custom_components.modbus_local_gateway.sensor_types.modbus_device_info.load_yaml",
        return_value={
            "device": MagicMock(),
            "entities": [],
        },
    ), patch.object(ModbusDeviceInfo, "entity_desciptions", pm1), patch.object(
        ModbusDeviceInfo, "properties", pm2
    ), patch.object(
        ModbusDeviceInfo, "manufacturer", pm3
    ), patch.object(
        ModbusDeviceInfo, "model", pm3
    ):
        await async_setup_entry(hass, entry, callback.add)

        callback.add.assert_called_once()
        assert len(callback.add.call_args[0][0]) == 1
        assert callback.add.call_args[1] == {"update_before_add": False}
        pm1.assert_called_once()
        pm2.assert_called_once()


async def test_update_none():
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = MagicMock()
    device = MagicMock()
    entity = ModbusTextEntity(coordinator=coordinator, ctx=ctx, device=device)

    coordinator.get_data.return_value = None
    entity._handle_coordinator_update()  # pylint: disable=protected-access

    coordinator.get_data.assert_called_once_with(ctx)


async def test_update_exception():
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = MagicMock()
    device = MagicMock()
    entity = ModbusTextEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    coordinator.get_data.side_effect = Exception()

    with patch(
        "custom_components.modbus_local_gateway.text._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.text._LOGGER.debug"
    ) as debug, patch(
        "custom_components.modbus_local_gateway.text._LOGGER.error"
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
    entity = ModbusTextEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    type(entity).entity_description = PropertyMock(
        return_value=ModbusTextEntityDescription(
            key="key",
            register_address=1,
            control_type="text",
        )
    )
    coordinator.get_data.return_value = 1
    write = MagicMock()
    entity.async_write_ha_state = write

    with patch(
        "custom_components.modbus_local_gateway.text._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.text._LOGGER.debug"
    ) as debug, patch(
        "custom_components.modbus_local_gateway.text._LOGGER.error"
    ) as error:
        entity._handle_coordinator_update()  # pylint: disable=protected-access

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_called_once()
        warning.assert_not_called()
        write.assert_called_once()


async def test_update_deviceupdate():
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = MagicMock()
    device = MagicMock()
    hass = MagicMock()
    entity = ModbusTextEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    type(entity).hass = PropertyMock(return_value=hass)
    type(entity).native_value = PropertyMock(return_value=2)
    type(entity).entity_description = PropertyMock(
        return_value=ModbusTextEntityDescription(
            key="text",
            register_address=1,
            control_type="text",
        )
    )

    write = MagicMock()
    entity.async_write_ha_state = write

    coordinator.get_data.return_value = 1

    with patch(
        "custom_components.modbus_local_gateway.text._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.text._LOGGER.debug"
    ) as debug, patch(
        "custom_components.modbus_local_gateway.text._LOGGER.error"
    ) as error:

        entity._handle_coordinator_update()  # pylint: disable=protected-access

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_called()
        warning.assert_not_called()
        write.assert_called_once()
