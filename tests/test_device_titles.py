"""Tests for the titles of the devices behind a gateway"""
# pylint: disable=protected-access

from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
import pytest
from pytest_homeassistant_custom_component.common import (
    HomeAssistant,
)

from custom_components.modbus_local_gateway import async_setup
from custom_components.modbus_local_gateway.const import SUBENTRY_TYPE_DEVICE

from .conftest import mock_gateway_entry

CLIENT = (
    "custom_components.modbus_local_gateway.AsyncModbusTcpClientGateway"
    ".async_get_client_connection"
)


async def _setup(hass: HomeAssistant) -> None:
    """Run the integration setup with a gateway that answers."""
    with patch(CLIENT, return_value=MagicMock(connected=True)):
        assert await async_setup(hass, {}) is True
        await hass.async_block_till_done()


def _only_subentry(entry: ConfigEntry) -> ConfigSubentry:
    """Return the one device sub-entry of an entry."""
    return next(iter(entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)))


@pytest.mark.asyncio
async def test_a_device_left_with_the_old_title_is_renamed(
    hass: HomeAssistant,
) -> None:
    """A device created before 2026.10.1 is named by its device id on upgrade.

    The title is only written when a device is created or reconfigured, so one
    set up before the format changed would keep saying "slave 1" in the list of
    devices behind its gateway until the user saved it again.
    """
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)
    # The old format put the prefix in front of "slave <id>".
    object.__setattr__(_only_subentry(entry), "title", "test slave 1")

    await _setup(hass)

    assert _only_subentry(entry).title == "Device ID: 1 (test)"


@pytest.mark.asyncio
async def test_a_device_named_by_the_user_is_left_alone(
    hass: HomeAssistant,
) -> None:
    """A device the user has named keeps the name they gave it."""
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)
    object.__setattr__(_only_subentry(entry), "title", "Inverter")

    await _setup(hass)

    assert _only_subentry(entry).title == "Inverter"


@pytest.mark.asyncio
async def test_the_old_title_is_renamed_whatever_its_casing(
    hass: HomeAssistant,
) -> None:
    """The old title is matched however it is cased.

    A title that differs from the old format only in the case of its words is
    still that title, so matching it exactly would leave the device with it for
    good.
    """
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)
    object.__setattr__(_only_subentry(entry), "title", "Test Slave 1")

    await _setup(hass)

    assert _only_subentry(entry).title == "Device ID: 1 (test)"


@pytest.mark.asyncio
async def test_a_device_created_from_now_on_is_not_renamed_again(
    hass: HomeAssistant,
) -> None:
    """A device already carrying the new title is left as it is.

    `async_update_subentry` reports whether it changed anything, and a change
    reloads the gateway, so a migration that always wrote the title would reload
    every gateway on every start.
    """
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)
    subentry = _only_subentry(entry)
    object.__setattr__(subentry, "title", "Device ID: 1 (test)")
    updated = MagicMock()

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_update_subentry",
        updated,
    ):
        await _setup(hass)

    updated.assert_not_called()
    assert subentry.title == "Device ID: 1 (test)"


@pytest.mark.asyncio
async def test_a_device_with_no_prefix_is_renamed_without_one(
    hass: HomeAssistant,
) -> None:
    """A device with no prefix is named by its id alone.

    The prefix is part of the old title too, so this is the one case where the
    old title has nothing in front of "slave <id>".
    """
    entry = mock_gateway_entry(prefix="")
    entry.add_to_hass(hass)
    object.__setattr__(_only_subentry(entry), "title", "slave 1")

    await _setup(hass)

    assert _only_subentry(entry).title == "Device ID: 1"
