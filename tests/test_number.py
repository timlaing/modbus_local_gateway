"""Sensor tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import CONF_DEVICE_ID, DOMAIN
from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.coordinator import ModbusCoordinator
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusDataType,
    ModbusNumberEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.modbus_device_info import (
    ModbusDeviceInfo,
)
from custom_components.modbus_local_gateway.number import (
    ModbusNumberEntity,
    async_setup_entry,
)


@pytest.mark.asyncio
async def test_setup_entry(hass) -> None:
    """Test the HA setup function"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "127.0.0.1",
            "port": "1234",
            CONF_DEVICE_ID: 1,
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
            ModbusNumberEntityDescription(
                key="key1",
                register_address=1,
                data_type=ModbusDataType.INPUT_REGISTER,
                control_type="number",
                min=1,
                max=2,
            ),
        ]
    )

    pm2 = PropertyMock(return_value="")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.modbus_device_info.load_yaml",
            return_value={
                "device": MagicMock(),
                "entities": [],
            },
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
        pm2.assert_called()


@pytest.mark.asyncio
async def test_update_none() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusNumberEntityDescription(
            register_address=1,
            key="key",
            min=1,
            max=2,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusNumberEntity(coordinator=coordinator, ctx=ctx, device=device)

    coordinator.get_data.return_value = None
    entity._handle_coordinator_update()

    coordinator.get_data.assert_called_once_with(ctx)


@pytest.mark.asyncio
async def test_update_exception() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusNumberEntityDescription(
            register_address=1,
            key="key",
            min=1,
            max=2,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusNumberEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    coordinator.get_data.side_effect = Exception()

    with (
        patch(
            "custom_components.modbus_local_gateway.number._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.number._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.number._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        debug.assert_not_called()
        warning.assert_not_called()
        error.assert_called_once()


@pytest.mark.asyncio
async def test_update_value() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusNumberEntityDescription(
            register_address=1,
            key="key",
            min=1,
            max=2,
            control_type="number",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusNumberEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    coordinator.get_data.return_value = 1
    write = MagicMock()
    entity.async_write_ha_state = write

    with (
        patch(
            "custom_components.modbus_local_gateway.number._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.number._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.number._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_called_once()
        warning.assert_not_called()
        write.assert_called_once()


@pytest.mark.asyncio
async def test_update_deviceupdate() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusNumberEntityDescription(
            key="number",
            register_address=1,
            control_type="number",
            min=1,
            max=2,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    hass = MagicMock()
    entity = ModbusNumberEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    type(entity).hass = PropertyMock(return_value=hass)
    type(entity).native_value = PropertyMock(return_value=2)
    write = MagicMock()
    entity.async_write_ha_state = write

    coordinator.get_data.return_value = 1

    with (
        patch(
            "custom_components.modbus_local_gateway.number._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.number._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.number._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_called()
        warning.assert_not_called()
        write.assert_called_once()


@pytest.mark.asyncio
async def test_async_set_native_value_reads_back() -> None:
    """Setting a number must go through the entity's write_data.

    number.py used to call client.write_data() directly, skipping the
    re-read that switch/select/text all get, which left the matching
    sensor stale for a full scan_interval after every write.
    """
    coordinator = MagicMock(spec=ModbusCoordinator)
    coordinator.client = AsyncMock()
    coordinator.config_entry = AsyncMock()
    ctx = ModbusContext(
        1,
        ModbusNumberEntityDescription(
            key="number",
            register_address=1,
            control_type="number",
            min=1,
            max=100,
            data_type=ModbusDataType.HOLDING_REGISTER,
        ),
    )
    entity = ModbusNumberEntity(coordinator=coordinator, ctx=ctx, device=MagicMock())

    with patch.object(coordinator.client, "write_data", AsyncMock()) as write_data:
        await entity.async_set_native_value(42)

        write_data.assert_called_once_with(entity.coordinator_context, 42)
        # the readback is the point of routing through the entity
        coordinator.async_update_entity.assert_awaited_once_with(
            entity.coordinator_context
        )
