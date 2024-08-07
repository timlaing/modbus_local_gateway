"""Config flow for Modbus Local Gateway integration."""

from __future__ import annotations

import datetime
import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_FILENAME, CONF_HOST, CONF_PORT
from homeassistant.core import callback

from .const import (
    CONF_DEFAULT_PORT,
    CONF_DEFAULT_SLAVE_ID,
    CONF_PREFIX,
    CONF_SLAVE_ID,
    DOMAIN,
    OPTIONS_DEFAULT_REFRESH,
    OPTIONS_REFRESH,
)
from .coordinator import ModbusCoordinator
from .helpers import get_gateway_key
from .sensor_types.device_loader import create_device_info, load_devices
from .sensor_types.modbus_device_info import ModbusDeviceInfo
from .tcp_client import AsyncModbusTcpClientGateway

_LOGGER: logging.Logger = logging.getLogger(__name__)


class OptionsFlowHandler(OptionsFlow):
    """Class to support the options flow"""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry: ConfigEntry[Any] = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            coordinator: ModbusCoordinator = self.hass.data[DOMAIN][
                get_gateway_key(self.config_entry)
            ]
            coordinator.update_interval = datetime.timedelta(
                seconds=user_input.get(OPTIONS_REFRESH, OPTIONS_DEFAULT_REFRESH)
            )

            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        OPTIONS_REFRESH,
                        default=self.config_entry.options.get(
                            OPTIONS_REFRESH, OPTIONS_DEFAULT_REFRESH
                        ),
                    ): int
                }
            ),
        )


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Modbus Local Gateway."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise Modbus Local Gateway flow."""
        self.client: AsyncModbusTcpClientGateway
        self.data = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        host_opts: dict[str, str] = {"default": ""}
        port_opts: dict[str, int] = {"default": CONF_DEFAULT_PORT}
        slave_opts: dict[str, int] = {"default": CONF_DEFAULT_SLAVE_ID}
        prefix_opts: dict[str, str] = {"default": ""}

        if user_input is not None:
            self.client = AsyncModbusTcpClientGateway.async_get_client_connection(
                host=user_input[CONF_HOST], port=user_input[CONF_PORT]
            )
            await self.client.connect()
            if self.client.connected:
                self.client.close()
                self.data = user_input
                return await self.async_step_device_type()

            errors["base"] = "Gateway connection"
            host_opts["default"] = user_input[CONF_HOST]
            port_opts["default"] = int(user_input[CONF_PORT])
            slave_opts["default"] = int(user_input[CONF_SLAVE_ID])
            prefix_opts["default"] = user_input[CONF_PREFIX]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, **host_opts): str,
                    vol.Required(CONF_PORT, **port_opts): int,
                    vol.Required(CONF_SLAVE_ID, **slave_opts): int,
                    vol.Optional(CONF_PREFIX, **prefix_opts): str,
                }
            ),
            errors=errors,
        )

    async def async_step_device_type(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the device type step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_create()

        devices: dict[str, ModbusDeviceInfo] = await load_devices(self.hass)
        devices_data: dict[str, str] = {dev: devices[dev].model for dev in devices}

        return self.async_show_form(
            step_id="device_type",
            data_schema=vol.Schema({vol.Required(CONF_FILENAME): vol.In(devices_data)}),
            errors=errors,
        )

    async def async_create(self) -> ConfigFlowResult:
        """Create the entry if we can"""
        device_info: ModbusDeviceInfo = await self.hass.async_add_executor_job(
            create_device_info, self.data[CONF_FILENAME]
        )

        return self.async_create_entry(title=device_info.model, data=self.data)

    def async_abort(
        self, *, reason: str, description_placeholders: Mapping[str, str] | None = None
    ) -> ConfigFlowResult:
        """Aborting the setup"""
        self.client.close()
        return super().async_abort(
            reason=reason, description_placeholders=description_placeholders
        )

    def async_show_progress_done(self, *, next_step_id: str) -> ConfigFlowResult:
        """Setup complete"""
        self.client.close()
        return super().async_show_progress_done(next_step_id=next_step_id)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options flow callback"""
        return OptionsFlowHandler(config_entry)
