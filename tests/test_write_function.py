"""Register write function tests.

The setting is per device: a gateway holds several devices and each of them can
be written with a different function, so it is read from the sub-entry of the
device rather than from the gateway.
"""

from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import (
    OPTIONS_WRITE_FUNCTION,
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.modbus_local_gateway.coordinator import ModbusCoordinator
from custom_components.modbus_local_gateway.entity_management.const import (
    WriteFunction,
)


def test_write_function_defaults_to_single(
    mock_config_entry: MockConfigEntry,
) -> None:
    """Entries configured before the option existed keep writing FC 0x06."""
    coordinator = ModbusCoordinator(
        hass=MagicMock(),
        config_entry=mock_config_entry,
        gateway_device=MagicMock(),
        client=MagicMock(),
        gateway="Test",
    )
    assert coordinator.write_function == WriteFunction.SINGLE


def test_write_function_from_the_subentry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The stored setting of the device selects its write function.

    It lives in the sub-entry: a gateway holds several devices, and they can each
    be written with a different function.
    """
    mock_config_entry.add_to_hass(hass)
    subentry = next(
        iter(mock_config_entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE))
    )
    hass.config_entries.async_update_subentry(
        mock_config_entry,
        subentry,
        data={**subentry.data, OPTIONS_WRITE_FUNCTION: WriteFunction.MULTIPLE.value},
    )
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
        gateway_device=MagicMock(),
        client=MagicMock(),
        gateway="Test",
        subentry=next(
            iter(mock_config_entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE))
        ),
    )
    assert coordinator.write_function == WriteFunction.MULTIPLE


def test_write_function_defaults_per_device(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A device that never chose a write function keeps the one it had."""
    mock_config_entry.add_to_hass(hass)
    subentry = next(
        iter(mock_config_entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE))
    )
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
        gateway_device=MagicMock(),
        client=MagicMock(),
        gateway="Test",
        subentry=subentry,
    )
    assert coordinator.write_function == WriteFunction.SINGLE


def test_write_function_unknown_value_falls_back(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """An unrecognised stored value falls back rather than failing the write."""
    mock_config_entry.add_to_hass(hass)
    subentry = next(
        iter(mock_config_entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE))
    )
    hass.config_entries.async_update_subentry(
        mock_config_entry,
        subentry,
        data={**subentry.data, OPTIONS_WRITE_FUNCTION: "nonsense"},
    )
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
        gateway_device=MagicMock(),
        client=MagicMock(),
        gateway="Test",
        subentry=next(
            iter(mock_config_entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE))
        ),
    )
    with patch(
        "custom_components.modbus_local_gateway.coordinator._LOGGER"
    ) as mock_logger:
        assert coordinator.write_function == WriteFunction.SINGLE
        mock_logger.warning.assert_called_once()
