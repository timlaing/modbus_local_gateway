"""Sensor tests"""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from homeassistant.components.sensor.const import SensorStateClass
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import DOMAIN
from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusDataType,
    ModbusEntityDescription,
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.modbus_device_info import (
    ModbusDeviceInfo,
)
from custom_components.modbus_local_gateway.sensor import (
    ModbusSensorEntity,
    async_setup_entry,
)


@pytest.mark.nohomeassistant
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
            ModbusSensorEntityDescription(
                key="key1", register_address=1, data_type="input_register"
            ),
            ModbusSensorEntityDescription(
                key="key2", register_address=2, data_type="holding_register"
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
        assert (
            len(callback.add.call_args[0][0]) == 2
        )  # Both input and holding registers
        assert callback.add.call_args[1] == {"update_before_add": False}
        pm1.assert_called_once()


async def test_update_none() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)

    coordinator.get_data.return_value = None
    entity._handle_coordinator_update()  # pylint: disable=protected-access

    coordinator.get_data.assert_called_once_with(ctx)


async def test_update_exception() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    coordinator.get_data.side_effect = Exception()

    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()  # pylint: disable=protected-access

        coordinator.get_data.assert_called_once_with(ctx)

        debug.assert_not_called()
        warning.assert_not_called()
        error.assert_called_once()


async def test_update_value() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = {"identifiers": "ABC"}
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)  # type: ignore
    type(entity).name = PropertyMock(return_value="Test")
    type(entity).entity_description = PropertyMock(
        return_value=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            key="key",
            register_address=1,
            data_type=ModbusDataType.INPUT_REGISTER,
        )
    )
    coordinator.get_data.return_value = 1
    write = MagicMock()
    entity.async_write_ha_state = write

    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()  # pylint: disable=protected-access

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_not_called()
        warning.assert_not_called()
        write.assert_called_once()


async def test_update_reset() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    type(entity).native_value = PropertyMock(return_value=2)  # type: ignore
    type(entity).state_class = PropertyMock(
        return_value=SensorStateClass.TOTAL_INCREASING
    )
    type(entity).entity_description = PropertyMock(
        return_value=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            key="key",
            register_address=1,
            data_type=ModbusDataType.INPUT_REGISTER,
        )
    )

    reset = PropertyMock()
    type(entity).last_reset = reset
    write = MagicMock()
    entity.async_write_ha_state = write

    coordinator.get_data.return_value = 1

    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()  # pylint: disable=protected-access

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_not_called()
        warning.assert_not_called()
        write.assert_called_once()
        reset.assert_called_once()


async def test_update_never_reset() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    type(entity).name = PropertyMock(return_value="Test")
    type(entity).native_value = PropertyMock(return_value=2)  # type: ignore
    type(entity).state_class = PropertyMock(
        return_value=SensorStateClass.TOTAL_INCREASING
    )
    type(entity).entity_description = PropertyMock(
        return_value=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            key="key",
            register_address=1,
            never_resets=True,
            data_type=ModbusDataType.INPUT_REGISTER,
        )
    )

    reset = PropertyMock()
    type(entity).last_reset = reset
    write = MagicMock()
    entity.async_write_ha_state = write

    coordinator.get_data.return_value = 1

    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.error") as error,
    ):
        entity._handle_coordinator_update()  # pylint: disable=protected-access

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_not_called()
        warning.assert_not_called()
        write.assert_not_called()
        reset.assert_not_called()


async def test_update_deviceupdate() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = {"identifiers": "ABC"}
    hass = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)  # type: ignore
    type(entity).name = PropertyMock(return_value="Test")
    type(entity).hass = PropertyMock(return_value=hass)
    type(entity).native_value = PropertyMock(return_value=2)  # type: ignore
    type(entity).state_class = PropertyMock(
        return_value=SensorStateClass.TOTAL_INCREASING
    )
    type(entity).entity_description = PropertyMock(
        return_value=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            key="hw_version",
            register_address=1,
            data_type=ModbusDataType.INPUT_REGISTER,
        )
    )

    reset = PropertyMock()
    type(entity).last_reset = reset
    write = MagicMock()
    entity.async_write_ha_state = write

    coordinator.get_data.return_value = 1

    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.error") as error,
        patch("custom_components.modbus_local_gateway.sensor.dr.async_get") as dr,
    ):
        dr.return_value = MagicMock()

        entity._handle_coordinator_update()  # pylint: disable=protected-access

        coordinator.get_data.assert_called_once_with(ctx)

        dr.assert_called_once_with(entity.hass)
        error.assert_not_called()
        debug.assert_called()
        warning.assert_not_called()
        write.assert_called_once()
        reset.assert_called_once()
