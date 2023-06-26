"""Config flow for Modbus Local Gateway integration."""
from __future__ import annotations
from collections.abc import Mapping

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.data_entry_flow import FlowResult

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_FILENAME

from .const import (
    DOMAIN,
    CONF_SLAVE_ID,
    CONF_DEFAULT_PORT,
    CONF_DEFAULT_SLAVE_ID,
    OPTIONS_REFRESH,
    OPTIONS_DEFAULT_REFRESH
)

from .helpers import get_gateway_key
from .sensor_types.device_loader import load_devices
from .sensor_types.modbus_device_info import ModbusDeviceInfo
from .coordinator import ModbusCoordinator
from .tcp_client import AsyncModbusTcpClientGateway


_LOGGER = logging.getLogger(__name__)


class OptionsFlowHandler(OptionsFlow):
    """Class to support the options flow"""
    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            coordinator: ModbusCoordinator = self.hass.data[DOMAIN][get_gateway_key(self.config_entry)]
            coordinator.update_interval = user_input.get(OPTIONS_REFRESH, OPTIONS_DEFAULT_REFRESH)

            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        OPTIONS_REFRESH,
                        default=self.config_entry.options.get(OPTIONS_REFRESH, OPTIONS_DEFAULT_REFRESH),
                    ): int
                }
            ),
        )


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Modbus Local Gateway."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise Modbus Local Gateway flow."""
        self.client: AsyncModbusTcpClientGateway = None
        self.data = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        host_opts = {}
        port_opts = {"default": CONF_DEFAULT_PORT}
        slave_opts = {"default": CONF_DEFAULT_SLAVE_ID}

        if user_input is not None:
            self.client = await AsyncModbusTcpClientGateway.async_get_client_connection(self.hass, user_input)
            await self.client.connect()
            if self.client.connected:
                self.client.close()
                self.data = user_input
                return await self.async_step_device_type()

            errors["base"] = "Gateway connection"
            host_opts["default"] = user_input[CONF_HOST]
            port_opts["default"] = user_input[CONF_PORT]
            slave_opts["default"] = user_input[CONF_SLAVE_ID]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, **host_opts): str,
                    vol.Required(CONF_PORT, **port_opts): int,
                    vol.Required(CONF_SLAVE_ID, **slave_opts): int,
                }
            ),
            errors=errors
        )

    async def async_step_device_type(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the device type step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_create()

        devices = await load_devices()
        devices_data = { dev: devices[dev].model for dev in devices }

        return self.async_show_form(step_id="device_type",
                                    data_schema=vol.Schema(
                                        {
                                            vol.Required(CONF_FILENAME): vol.In(devices_data)
                                        }
                                    ),
                                    errors=errors)

    async def async_create(self) -> FlowResult:
        """Create the entry if we can"""
        device_info = ModbusDeviceInfo(self.data[CONF_FILENAME])

        return self.async_create_entry(title=device_info.model, data=self.data)


    def async_abort(self, *, reason: str, description_placeholders: Mapping[str, str] | None = None) -> FlowResult:
        """Aborting the setup"""
        self.client.close()
        return super().async_abort(reason=reason, description_placeholders=description_placeholders)

    def async_show_progress_done(self, *, next_step_id: str) -> FlowResult:
        """Setup complete"""
        self.client.close()
        return super().async_show_progress_done(next_step_id=next_step_id)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options flow callback"""
        return OptionsFlowHandler(config_entry)