"""Sensor tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.modbus_local_gateway.const import (
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.entity_management import modbus_device_info
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusEntityDescription,
    ModbusSelectEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    ModbusDataType,
)
from custom_components.modbus_local_gateway.select import (
    ModbusSelectEntity,
    async_setup_entry,
)

from .conftest import mock_gateway_entry, mock_runtime


@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test the HA setup function"""

    entry = mock_gateway_entry(host="127.0.0.1", port=1234, filename="test.yaml")
    callback = MagicMock()
    coordinator = AsyncMock()
    gw_dev = MagicMock()
    type(coordinator).gateway_device = PropertyMock(return_value=gw_dev)
    identifiers = PropertyMock()
    identifiers.return_value = ["a"]
    type(gw_dev).identifiers = identifiers
    subentry_id = next(
        iter(entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE))
    ).subentry_id
    entry.runtime_data = mock_runtime({subentry_id: coordinator})

    pm1 = PropertyMock(
        return_value=[
            ModbusSelectEntityDescription(
                key="key1",
                register_address=1,
                select_options={1: "A", 2: "B"},
                data_type=ModbusDataType.INPUT_REGISTER,
                control_type="select",
            ),
        ]
    )

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
async def test_update_none() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusSelectEntity(coordinator=coordinator, ctx=ctx, device=device)

    coordinator.get_data.return_value = None
    entity._handle_coordinator_update()

    coordinator.get_data.assert_called_once_with(ctx)


@pytest.mark.asyncio
async def test_update_exception() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusSelectEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    coordinator.get_data.side_effect = Exception()

    with (
        patch(
            "custom_components.modbus_local_gateway.select._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.select._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.select._LOGGER.error") as error,
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
        ModbusSelectEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
            select_options={1: "A", 2: "B"},
            control_type="select",
        ),
    )
    device = MagicMock()
    entity = ModbusSelectEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    coordinator.get_data.return_value = 1
    write = MagicMock()
    cast(Any, entity).async_write_ha_state = write

    with (
        patch(
            "custom_components.modbus_local_gateway.select._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.select._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.select._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_called_once()
        warning.assert_not_called()
        write.assert_called_once()


@pytest.mark.asyncio
async def test_update_unmapped_value_keeps_current_option() -> None:
    """A value with no select option keeps the current option instead of raising."""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusSelectEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
            select_options={1: "A", 2: "B"},
            control_type="select",
        ),
    )
    device = MagicMock()
    entity = ModbusSelectEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    entity._attr_current_option = "B"
    coordinator.get_data.return_value = 3
    write = MagicMock()
    cast(Any, entity).async_write_ha_state = write

    with (
        patch(
            "custom_components.modbus_local_gateway.select._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.select._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.select._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_not_called()
        warning.assert_not_called()
        write.assert_called_once()
        assert entity._attr_current_option == "B"


@pytest.mark.asyncio
async def test_update_float_value_matches_int_option() -> None:
    """A whole float from a `float: true` select still maps to its option.

    The Eastron meters keep their baud rate and unit prefix as 32 bit floats,
    so the coordinator hands over `2.0` where the option is keyed `2`. The
    select must still show it rather than leaving `current_option` unset.
    """
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusSelectEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
            select_options={1: "A", 2: "B"},
            control_type="select",
        ),
    )
    device = MagicMock()
    entity = ModbusSelectEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    coordinator.get_data.return_value = 2.0
    write = MagicMock()
    cast(Any, entity).async_write_ha_state = write

    with (
        patch(
            "custom_components.modbus_local_gateway.select._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.select._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.select._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()

        error.assert_not_called()
        debug.assert_called_once()
        warning.assert_not_called()
        write.assert_called_once()
        assert entity._attr_current_option == "B"


@pytest.mark.asyncio
async def test_update_fractional_float_keeps_current_option() -> None:
    """A float that matches no option leaves the current option alone."""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusSelectEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
            select_options={1: "A", 2: "B"},
            control_type="select",
        ),
    )
    device = MagicMock()
    entity = ModbusSelectEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    entity._attr_current_option = "B"
    coordinator.get_data.return_value = 2.5
    write = MagicMock()
    cast(Any, entity).async_write_ha_state = write

    with (
        patch(
            "custom_components.modbus_local_gateway.select._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.select._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.select._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()

        error.assert_not_called()
        debug.assert_not_called()
        warning.assert_not_called()
        write.assert_called_once()
        assert entity._attr_current_option == "B"


@pytest.mark.asyncio
async def test_update_deviceupdate() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusSelectEntityDescription(
            key="select",
            register_address=1,
            control_type="select",
            select_options={1: "A", 2: "B"},
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    hass = MagicMock()
    entity = ModbusSelectEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    type(entity).hass = PropertyMock(return_value=hass)
    cast(Any, type(entity)).native_value = PropertyMock(return_value=2)

    write = MagicMock()
    cast(Any, entity).async_write_ha_state = write

    coordinator.get_data.return_value = 1

    with (
        patch(
            "custom_components.modbus_local_gateway.select._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.select._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.select._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_called()
        warning.assert_not_called()
        write.assert_called_once()
