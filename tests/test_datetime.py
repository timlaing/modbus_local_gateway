"""Date time entity tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from datetime import datetime
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import CONF_DEVICE_ID, DOMAIN
from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.coordinator import ModbusCoordinator
from custom_components.modbus_local_gateway.datetime import (
    ModbusDateTimeEntity,
    async_setup_entry,
)
from custom_components.modbus_local_gateway.entity_management import modbus_device_info
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusDateTimeEntityDescription,
    ModbusFieldDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    CompositeType,
    ControlType,
    ModbusDataType,
    WriteFunction,
)

COMPOSITE_DESCRIPTION: ModbusDateTimeEntityDescription = (
    ModbusDateTimeEntityDescription(
        key="current_time",
        register_address=45,
        register_count=6,
        data_type=ModbusDataType.HOLDING_REGISTER,
        control_type=ControlType.DATETIME,
        composite_type=CompositeType.DATETIME,
        fields=tuple(
            ModbusFieldDescription(key=key, address=address)
            for key, address in [
                ("year", 45),
                ("month", 46),
                ("day", 47),
                ("hour", 48),
                ("minute", 49),
                ("second", 50),
            ]
        ),
    )
)


@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant) -> None:
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
    coordinator = MagicMock()
    coordinator.client = AsyncMock()
    gw_dev = MagicMock()
    type(coordinator).gateway_device = PropertyMock(return_value=gw_dev)
    identifiers = PropertyMock()
    identifiers.return_value = ["a"]
    type(gw_dev).identifiers = identifiers
    hass.data[DOMAIN] = {"127.0.0.1:1234:1": coordinator}

    pm1 = PropertyMock(return_value=[COMPOSITE_DESCRIPTION])
    pm2 = PropertyMock(return_value="")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info.load_yaml",
            return_value={
                "device": MagicMock(),
                "entities": [],
            },
        ),
        patch.object(modbus_device_info.ModbusDeviceInfo, "entity_descriptions", pm1),
        patch.object(modbus_device_info.ModbusDeviceInfo, "manufacturer", pm2),
        patch.object(modbus_device_info.ModbusDeviceInfo, "model", pm2),
    ):
        await async_setup_entry(hass, entry, callback.add)

        callback.add.assert_called_once()
        assert len(callback.add.call_args[0][0]) == 1
        assert callback.add.call_args[1] == {"update_before_add": False}
        pm1.assert_called_once()
        pm2.assert_called()


@pytest.mark.asyncio
async def test_update_value() -> None:
    """The coordinator's datetime becomes the entity's native value"""
    coordinator = MagicMock()
    ctx = ModbusContext(1, COMPOSITE_DESCRIPTION)
    device = MagicMock()
    entity = ModbusDateTimeEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    value = datetime(2026, 9, 22, 16, 30, 5, tzinfo=dt_util.get_default_time_zone())
    coordinator.get_data.return_value = value
    write = MagicMock()
    cast(Any, entity).async_write_ha_state = write

    with (
        patch(
            "custom_components.modbus_local_gateway.datetime._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.datetime._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.datetime._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_called_once()
        warning.assert_not_called()
        write.assert_called_once()
        assert entity.native_value == value


@pytest.mark.asyncio
async def test_update_none() -> None:
    """No value leaves the entity without a native value"""
    coordinator = MagicMock()
    ctx = ModbusContext(1, COMPOSITE_DESCRIPTION)
    device = MagicMock()
    entity = ModbusDateTimeEntity(coordinator=coordinator, ctx=ctx, device=device)
    coordinator.get_data.return_value = None

    entity._handle_coordinator_update()

    coordinator.get_data.assert_called_once_with(ctx)
    assert entity.native_value is None


@pytest.mark.asyncio
async def test_update_non_datetime_keeps_previous_value() -> None:
    """A value of another type is not published as a datetime"""
    coordinator = MagicMock()
    ctx = ModbusContext(1, COMPOSITE_DESCRIPTION)
    device = MagicMock()
    entity = ModbusDateTimeEntity(coordinator=coordinator, ctx=ctx, device=device)
    previous = datetime(2026, 9, 22, 16, 30, tzinfo=dt_util.get_default_time_zone())
    entity._attr_native_value = previous
    coordinator.get_data.return_value = "not a datetime"

    entity._handle_coordinator_update()

    assert entity.native_value == previous


@pytest.mark.asyncio
async def test_update_exception() -> None:
    """A failing coordinator is logged instead of raised"""
    coordinator = MagicMock()
    ctx = ModbusContext(1, COMPOSITE_DESCRIPTION)
    device = MagicMock()
    entity = ModbusDateTimeEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    coordinator.get_data.side_effect = Exception()

    with (
        patch(
            "custom_components.modbus_local_gateway.datetime._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.datetime._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.datetime._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        debug.assert_not_called()
        warning.assert_not_called()
        error.assert_called_once()


@pytest.mark.asyncio
async def test_set_value() -> None:
    """Setting a value writes it to the client"""
    coordinator = MagicMock(spec=ModbusCoordinator)
    coordinator.client = AsyncMock()
    coordinator.config_entry = MagicMock()
    coordinator.write_function = WriteFunction.SINGLE

    ctx = ModbusContext(1, COMPOSITE_DESCRIPTION)
    device = MagicMock()
    entity = ModbusDateTimeEntity(coordinator=coordinator, ctx=ctx, device=device)
    value = datetime(2026, 9, 22, 16, 30, 5, tzinfo=dt_util.get_default_time_zone())

    with patch.object(coordinator.client, "write_data", AsyncMock()) as mock_write_data:
        await entity.async_set_value(value)
        mock_write_data.assert_called_once_with(
            entity.coordinator_context, value, write_function=WriteFunction.SINGLE
        )


@pytest.mark.asyncio
async def test_native_value_state_is_timezone_aware() -> None:
    """The datetime platform refuses a naive value, so the entity must not be"""
    coordinator = MagicMock()
    ctx = ModbusContext(1, COMPOSITE_DESCRIPTION)
    device = MagicMock()
    entity = ModbusDateTimeEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).entity_id = PropertyMock(return_value="sensor.clock")
    entity._attr_native_value = datetime(
        2026, 9, 22, 16, 30, tzinfo=dt_util.get_default_time_zone()
    )

    assert entity.state is not None
    assert entity.state.endswith("+00:00") or "+" in entity.state
