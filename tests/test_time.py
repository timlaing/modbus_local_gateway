"""Time entity tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from datetime import time
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.modbus_local_gateway.const import (
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.coordinator import ModbusCoordinator
from custom_components.modbus_local_gateway.entity_management import modbus_device_info
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusFieldDescription,
    ModbusTimeEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    CompositeType,
    ControlType,
    ModbusDataType,
    WriteFunction,
)
from custom_components.modbus_local_gateway.time import (
    ModbusTimeEntity,
    async_setup_entry,
)

from .conftest import mock_gateway_entry, mock_runtime

COMPOSITE_DESCRIPTION: ModbusTimeEntityDescription = ModbusTimeEntityDescription(
    key="period1_end",
    register_address=45,
    register_count=3,
    data_type=ModbusDataType.HOLDING_REGISTER,
    control_type=ControlType.TIME,
    composite_type=CompositeType.TIME,
    fields=tuple(
        ModbusFieldDescription(key=key, address=address)
        for key, address in [
            ("hour", 45),
            ("minute", 46),
            ("second", 47),
        ]
    ),
)


@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test the HA setup function"""

    entry = mock_gateway_entry(host="127.0.0.1", port=1234, filename="test.yaml")
    callback = MagicMock()
    coordinator = MagicMock()
    coordinator.client = AsyncMock()
    gw_dev = MagicMock()
    type(coordinator).gateway_device = PropertyMock(return_value=gw_dev)
    identifiers = PropertyMock()
    identifiers.return_value = ["a"]
    type(gw_dev).identifiers = identifiers
    subentry_id = next(
        iter(entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE))
    ).subentry_id
    entry.runtime_data = mock_runtime({subentry_id: coordinator})

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
        coordinator.device_info = modbus_device_info.ModbusDeviceInfo("test.yaml")
        await async_setup_entry(hass, entry, callback.add)

        callback.add.assert_called_once()
        assert len(callback.add.call_args[0][0]) == 1
        assert callback.add.call_args[1] == {
            "update_before_add": False,
            "config_subentry_id": subentry_id,
        }
        pm1.assert_called_once()
        pm2.assert_called()


@pytest.mark.asyncio
async def test_update_value() -> None:
    """The coordinator's time becomes the entity's native value"""
    coordinator = MagicMock()
    ctx = ModbusContext(1, COMPOSITE_DESCRIPTION)
    device = MagicMock()
    entity = ModbusTimeEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    value = time(16, 30, 5)
    coordinator.get_data.return_value = value
    write = MagicMock()
    cast(Any, entity).async_write_ha_state = write

    with (
        patch("custom_components.modbus_local_gateway.time._LOGGER.warning") as warning,
        patch("custom_components.modbus_local_gateway.time._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.time._LOGGER.error") as error,
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
    entity = ModbusTimeEntity(coordinator=coordinator, ctx=ctx, device=device)
    coordinator.get_data.return_value = None

    entity._handle_coordinator_update()

    coordinator.get_data.assert_called_once_with(ctx)
    assert entity.native_value is None


@pytest.mark.asyncio
async def test_update_non_time_keeps_previous_value() -> None:
    """A value of another type is not published as a time

    A datetime used to arrive here - the value had today's date on it - so this
    is the guard that keeps a date out of the time platform again.
    """
    coordinator = MagicMock()
    ctx = ModbusContext(1, COMPOSITE_DESCRIPTION)
    device = MagicMock()
    entity = ModbusTimeEntity(coordinator=coordinator, ctx=ctx, device=device)
    previous = time(16, 30)
    entity._attr_native_value = previous
    coordinator.get_data.return_value = "not a time"

    entity._handle_coordinator_update()

    assert entity.native_value == previous


@pytest.mark.asyncio
async def test_update_exception() -> None:
    """A failing coordinator is logged instead of raised"""
    coordinator = MagicMock()
    ctx = ModbusContext(1, COMPOSITE_DESCRIPTION)
    device = MagicMock()
    entity = ModbusTimeEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    coordinator.get_data.side_effect = Exception()

    with (
        patch("custom_components.modbus_local_gateway.time._LOGGER.warning") as warning,
        patch("custom_components.modbus_local_gateway.time._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.time._LOGGER.error") as error,
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
    entity = ModbusTimeEntity(coordinator=coordinator, ctx=ctx, device=device)
    value = time(16, 30, 5)

    with patch.object(coordinator.client, "write_data", AsyncMock()) as mock_write_data:
        await entity.async_set_value(value)
        mock_write_data.assert_called_once_with(
            entity.coordinator_context, value, write_function=WriteFunction.SINGLE
        )


@pytest.mark.asyncio
async def test_set_value_synchronously_is_not_supported() -> None:
    """Writes go through the coordinator, not straight to the client"""
    entity = ModbusTimeEntity(
        coordinator=MagicMock(),
        ctx=ModbusContext(1, COMPOSITE_DESCRIPTION),
        device=MagicMock(),
    )

    with pytest.raises(NotImplementedError):
        entity.set_value(time(1, 2, 3))


def test_native_value_has_no_date() -> None:
    """A time entity's state is a time, not a date and time"""
    coordinator = MagicMock()
    ctx = ModbusContext(1, COMPOSITE_DESCRIPTION)
    entity = ModbusTimeEntity(coordinator=coordinator, ctx=ctx, device=MagicMock())
    cast(Any, type(entity)).entity_id = PropertyMock(return_value="time.clock")
    entity._attr_native_value = time(16, 30, 5)

    assert entity.state == "16:30:05"
