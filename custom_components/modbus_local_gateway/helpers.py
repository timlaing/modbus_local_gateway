"""Helper functions for Modbus Local Gateway integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from packaging.version import Version

from .const import (
    CONF_CONNECTION_TYPE,
    CONF_DEFAULT_CONNECTION_TYPE,
    CONF_DEVICE_ID,
    CONF_PREFIX,
    DOMAIN,
    MIN_HOMEASSISTANT_VERSION,
    SUBENTRY_TYPE_DEVICE,
)
from .coordinator import (
    ModbusContext,
    ModbusCoordinator,
    ModbusCoordinatorEntity,
)
from .entity_management.const import ControlType
from .entity_management.modbus_device_info import ModbusDeviceInfo

_LOGGER: logging.Logger = logging.getLogger(__name__)

GATEWAY_DEVICE_KEY = "ModbusGateway"


def is_supported_home_assistant() -> bool:
    """Return whether the running Home Assistant can run this integration.

    `loader.py` does not enforce the `homeassistant` key of a custom
    integration's manifest, so the floor has to be checked here. Config
    sub-entries, and the registry calls used to move devices and entities into
    them, do not exist before 2026.9.
    """
    return Version(HA_VERSION) >= Version(MIN_HOMEASSISTANT_VERSION)


def get_connection_key(config: Mapping[str, Any]) -> str:
    """Return the key of the gateway connection itself.

    This identifies the gateway device and titles the config entry. It carries no
    prefix: the prefix is a per-device setting, so it belongs to the device
    sub-entries and their unique ids, never to the connection.
    """
    return f"{config[CONF_HOST]}:{config[CONF_PORT]}"


def get_gateway_device_identifier(config: Mapping[str, Any]) -> str:
    """Return the registry identifier of the gateway device."""
    return f"{GATEWAY_DEVICE_KEY}-{get_connection_key(config)}"


def get_device_key(config: Mapping[str, Any]) -> str:
    """Return the key of one device behind a gateway.

    This is the device's first registry identifier and the unique id of its
    config sub-entry, so a gateway cannot end up with two devices claiming the
    same slave id.
    """
    prefix: str = config.get(CONF_PREFIX) or ""
    return (
        f"{prefix + '-' if prefix else ''}"
        f"{config[CONF_HOST]}:{config[CONF_PORT]}:{config[CONF_DEVICE_ID]}"
    )


def get_device_identifiers(config: Mapping[str, Any]) -> set[tuple[str, str]]:
    """Return the registry identifiers of one device behind a gateway."""
    key = get_device_key(config)
    return {(DOMAIN, key), (DOMAIN, f"{key}-{config[CONF_DEVICE_ID]}")}


def get_device_config(entry: ConfigEntry, subentry: ConfigSubentry) -> dict[str, Any]:
    """Return the settings of one device, gateway settings included."""
    return {**entry.data, **subentry.data}


def get_connection_type(config: Mapping[str, Any]) -> str:
    """Return the configured connection type, defaulting to Modbus TCP."""
    return str(config.get(CONF_CONNECTION_TYPE, CONF_DEFAULT_CONNECTION_TYPE))


def async_setup_entities(
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    control: ControlType,
    entity_class: type[ModbusCoordinatorEntity],
) -> None:
    """Set up the entities of every device sub-entry."""
    for subentry in config_entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE):
        coordinator: ModbusCoordinator | None = config_entry.runtime_data.get(
            subentry.subentry_id
        )
        if coordinator is None:
            # The sub-entry was added while the entry was loading; its update
            # listener reloads the entry, which sets this up properly.
            _LOGGER.debug(
                "No coordinator for sub-entry %s, skipping", subentry.subentry_id
            )
            continue

        config: dict[str, Any] = get_device_config(config_entry, subentry)
        _LOGGER.debug(
            "Setting up entities for config: %s, platform: %s", config, control
        )
        device_info: ModbusDeviceInfo = coordinator.device_info

        async_add_entities(
            [
                entity_class(
                    coordinator=coordinator,
                    ctx=ModbusContext(device_id=config[CONF_DEVICE_ID], desc=desc),
                    device=_device_info(config, device_info),
                )
                for desc in device_info.entity_descriptions
                if desc.control_type == control
            ],
            update_before_add=False,
            config_subentry_id=subentry.subentry_id,
        )


def _device_info(config: dict[str, Any], device_info: ModbusDeviceInfo) -> DeviceInfo:
    """Return the device info of a device behind a gateway.

    The device itself is created by `async_setup_entry` so that it belongs to its
    sub-entry: a `DeviceInfo` cannot say which sub-entry a device belongs to, so
    an entity can only point at an existing device by its identifiers.
    """
    return DeviceInfo(
        identifiers=get_device_identifiers(config),
        name=" ".join([
            part
            for part in [
                config.get(CONF_PREFIX),
                device_info.manufacturer,
                device_info.model,
            ]
            if part
        ]),
        manufacturer=device_info.manufacturer,
        model=device_info.model,
    )
