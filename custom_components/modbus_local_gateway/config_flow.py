"""Config flow for Modbus Local Gateway integration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import logging
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentry,
    ConfigSubentryFlow,
    FlowType,
    SubentryFlowContext,
    SubentryFlowResult,
)
from homeassistant.const import CONF_FILENAME, CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
import voluptuous as vol

from .const import (
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CONNECTION_TYPE,
    CONF_CONNECTION_TYPES,
    CONF_DEFAULT_CONNECTION_TYPE,
    CONF_DEFAULT_DEVICE_ID,
    CONF_DEFAULT_PORT,
    CONF_DEVICE,
    CONF_DEVICE_ID,
    CONF_GATEWAY_TYPE,
    CONF_LEGACY_ENTITY_IDS,
    CONF_LEGACY_ENTITY_IDS_DEFAULT,
    CONF_PARITY,
    CONF_PREFIX,
    CONF_PROXY_DEVICE,
    CONF_RESTORE_ENTITY_IDS,
    CONF_SERIAL_NUMBER,
    CONF_STOPBITS,
    CONF_TRANSPORT,
    CONF_WRITE_FUNCTION_TYPES,
    DOMAIN,
    GATEWAY_TYPES,
    OPTIONS_DEFAULT_EXPECTED_OFFLINE,
    OPTIONS_DEFAULT_REFRESH,
    OPTIONS_DEFAULT_WRITE_FUNCTION,
    OPTIONS_EXPECTED_OFFLINE,
    OPTIONS_REFRESH,
    OPTIONS_WRITE_FUNCTION,
    SERIAL_CONNECTION_TYPE,
    SERIAL_DEFAULT_BAUDRATE,
    SERIAL_DEFAULT_BYTESIZE,
    SERIAL_DEFAULT_PARITY,
    SERIAL_DEFAULT_STOPBITS,
    SUBENTRY_TYPE_DEVICE,
    TRANSPORT_SERIAL_PROXY,
)
from .coordinator import async_restore_legacy_entity_ids
from .entity_management.device_loader import create_device_info, load_devices
from .entity_management.modbus_device_info import ModbusDeviceInfo
from .helpers import (
    get_connection_key,
    get_connection_type,
    get_device_config,
    get_device_identifiers,
    get_device_key,
    get_device_title,
    get_transport,
    is_supported_home_assistant,
)
from .serial_proxy import (
    ProxyPort,
    SerialSupportUnavailable,
    async_get_proxy_ports,
    async_validate_port,
)
from .tcp_client import AsyncModbusTcpClientGateway

_LOGGER: logging.Logger = logging.getLogger(__name__)

# What the parity of a serial line is offered as: the letter the entry
# stores, under the name it is known by.
_SERIAL_PARITY: dict[str, str] = {"N": "None", "E": "Even", "O": "Odd"}


def _number(minimum: float, maximum: float) -> NumberSelector:
    """Return a selector for a whole number in a range."""
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum, max=maximum, step=1, mode=NumberSelectorMode.BOX
        )
    )


def _dropdown(options: Mapping[str, str]) -> SelectSelector:
    """Return a selector for a choice of options.

    What is stored identifies a device or a connection, so it cannot be what a
    user reads: `socket` and `rtu` mean nothing outside the code. Each option
    therefore carries the name to show, as the enumeration it replaces did.
    """
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(value=value, label=label)
                for value, label in options.items()
            ],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


class DeviceSubentryFlowHandler(ConfigSubentryFlow):
    """Handle the sub-entry flow for adding and modifying a device."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a device behind the gateway of this config entry."""
        return await self._async_step_device(user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change the settings of a device behind the gateway.

        The name of this step is what puts the reconfigure button on a device, so
        a device can be moved to another slave id without losing its entity ids,
        unique ids, device id or history.
        """
        return await self._async_step_device(
            user_input, subentry=self._get_reconfigure_subentry()
        )

    async def _async_step_device(
        self,
        user_input: dict[str, Any] | None,
        subentry: ConfigSubentry | None = None,
    ) -> SubentryFlowResult:
        """Ask for, validate and store the settings of one device."""
        entry: ConfigEntry = self._get_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            data: dict[str, Any] = _normalise_device_data(user_input)
            config: dict[str, Any] = get_device_config(entry, _as_subentry(data))
            device_key: str = get_device_key(config)

            if device_key in _device_keys(entry, skip=subentry):
                errors[CONF_DEVICE_ID] = "device_id_taken"
            else:
                try:
                    await self.hass.async_add_executor_job(
                        create_device_info, self.hass, data[CONF_FILENAME]
                    )
                except FileNotFoundError, KeyError:
                    errors[CONF_FILENAME] = "file_not_found"
                else:
                    return self._async_store_device(entry, subentry, data, config)

        devices: dict[str, ModbusDeviceInfo] = await load_devices(self.hass)
        devices_data: dict[str, str] = {
            item[0]: f"{item[1].manufacturer or 'Unknown'} {item[1].model or 'Unknown'}"
            for item in sorted(
                devices.items(),
                key=lambda item: (
                    f"{item[1].manufacturer or 'Unknown'} {item[1].model or 'Unknown'}"
                ),
            )
        }

        return self.async_show_form(
            step_id=str(self.source),
            data_schema=self.add_suggested_values_to_schema(  # type: ignore[arg-type,unused-ignore]
                data_schema=_device_schema(devices_data),  # type: ignore[arg-type,unused-ignore]
                suggested_values=dict(subentry.data) if subentry else None,
            ),
            errors=errors,
            description_placeholders={"gateway": entry.title},
        )

    def _async_store_device(
        self,
        entry: ConfigEntry,
        subentry: ConfigSubentry | None,
        data: dict[str, Any],
        config: Mapping[str, Any],
    ) -> SubentryFlowResult:
        """Store the settings of a device as a new or updated sub-entry."""
        if subentry is None:
            return self.async_create_entry(
                title=get_device_title(config),
                data=data,
                unique_id=get_device_key(config),
            )

        # Changing the prefix or the slave id changes the key of the device, and
        # with it its registry identifiers. Renaming them in place keeps the
        # device - and its history, area and dashboard cards - where it was.
        _async_move_device(
            hass=self.hass, entry=entry, subentry=subentry, config=config
        )

        # The title is the device's name in the list of devices behind the
        # gateway, and it is built from the id and the prefix. Those are editable,
        # so the title is refreshed with them: a device keeps the name of the
        # settings it was created with otherwise.
        self.hass.config_entries.async_update_subentry(
            entry,
            subentry,
            data=data,
            title=get_device_title(config),
            unique_id=get_device_key(config),
        )
        # The devices and entities of this entry are built from its sub-entries,
        # so they have to be rebuilt when one of them changed.
        self.hass.config_entries.async_schedule_reload(entry.entry_id)
        return self.async_abort(
            reason="reconfigure_successful",
            description_placeholders={
                "device": get_device_title(config),
                "gateway": entry.title,
            },
        )


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Modbus Local Gateway."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialise Modbus Local Gateway flow."""
        self.client: AsyncModbusTcpClientGateway | None = None
        # What kind of connection the flow is building: a framer for a
        # network gateway, or TRANSPORT_SERIAL_PROXY for an AUX-2.
        self._gateway_type: str = CONF_DEFAULT_CONNECTION_TYPE
        # What the AUX-2 steps know so far: the ports Home Assistant can
        # see, the device chosen among them, and the entry - if any - this
        # flow is reconfiguring rather than adding.
        self._proxy_ports: list[ProxyPort] = []
        self._proxy_device: str = ""
        self._reconfiguring: ConfigEntry | None = None

    def is_matching(self, other_flow: ConfigFlowHandler) -> bool:
        """Check if the other flow matches this one."""
        return (
            self.client is not None
            and other_flow.client is not None
            and self.client == other_flow.client
        )

    @staticmethod
    @callback
    def async_get_supported_subentry_types(
        config_entry: ConfigEntry,
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return the kinds of sub-entry a gateway can hold.

        A gateway is a connection, so what can be added behind it is what that
        connection speaks to: devices. The device flow is the only one there is,
        and it is reached by name from the device page and by source from the
        gateway flow.
        """
        return {SUBENTRY_TYPE_DEVICE: DeviceSubentryFlowHandler}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask what kind of gateway connection this is.

        The kind comes first because everything after it depends on it: a
        network gateway is asked for a host and a port, an AUX-2 for the
        device and port to open. Whether an AUX-2 can be asked for at all
        is checked here, so a missing device or library is said where the
        choice is made rather than on a form that has nothing to offer.
        """
        if not is_supported_home_assistant():
            return self.async_abort(reason="unsupported_home_assistant_version")

        errors: dict[str, str] = {}
        if user_input is not None:
            self._gateway_type = str(user_input[CONF_GATEWAY_TYPE])
            if self._gateway_type == TRANSPORT_SERIAL_PROXY:
                errors = await self._async_proxy_ports()
                if not errors:
                    return await self.async_step_aux2()
            else:
                return await self.async_step_network()

        return self.async_show_form(
            step_id="user",
            data_schema=_gateway_type_schema(  # type: ignore[arg-type,unused-ignore]
                self._gateway_type
            ),
            errors=errors,
        )

    async def async_step_network(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a gateway reached over the network.

        The connection type starts on the kind chosen at the gateway step,
        so the framer of that choice carries over and is still offered
        here - a network gateway is one of the two framers, never an AUX-2.
        """
        errors: dict[str, str] = {}
        host: Any = ""
        port: Any = CONF_DEFAULT_PORT
        connection_type: Any = (
            self._gateway_type
            if self._gateway_type in CONF_CONNECTION_TYPES
            else CONF_DEFAULT_CONNECTION_TYPE
        )

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = int(user_input[CONF_PORT])
            connection_type = user_input.get(
                CONF_CONNECTION_TYPE, CONF_DEFAULT_CONNECTION_TYPE
            )
            if self._async_gateway_exists(host, port, connection_type):
                return self.async_abort(reason="already_configured")

            if await self._async_gateway_reachable(host, port, connection_type):
                data: dict[str, Any] = {
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_CONNECTION_TYPE: connection_type,
                    CONF_LEGACY_ENTITY_IDS: user_input.get(
                        CONF_LEGACY_ENTITY_IDS, CONF_LEGACY_ENTITY_IDS_DEFAULT
                    ),
                }
                return self.async_create_entry(title=_gateway_title(data), data=data)

            errors["base"] = "Gateway connection"

        return self.async_show_form(
            step_id="network",
            data_schema=_gateway_schema(host, port, connection_type),  # type: ignore[arg-type,unused-ignore]
            errors=errors,
        )

    async def async_step_aux2(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask which AUX-2 the gateway connects through.

        A port only means something next to the device it is on, so device
        and port are asked one after the other rather than as one long
        list. An entry being reconfigured starts here too, opened on the
        device it already has, so its port can be moved - or another AUX-2
        chosen - exactly the way it was added.
        """
        errors: dict[str, str] = {}
        if not self._proxy_ports:
            # Reconfiguring reaches this step without passing the gateway
            # step, so the ports may not have been read yet.
            errors = await self._async_proxy_ports()

        devices: dict[str, str] = {
            port.entry_id: port.device_name for port in self._proxy_ports
        }

        if user_input is not None and not errors:
            device: str = str(user_input[CONF_PROXY_DEVICE])
            if device in devices:
                self._proxy_device = device
                return await self.async_step_aux2_port()
            errors[CONF_PROXY_DEVICE] = "no_proxy_ports"

        return self.async_show_form(
            step_id="aux2",
            data_schema=vol.Schema({  # type: ignore[arg-type,unused-ignore]
                vol.Required(
                    CONF_PROXY_DEVICE, default=_prefill(self._proxy_device, devices)
                ): _dropdown(devices),
            }),
            errors=errors,
        )

    async def async_step_aux2_port(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask which port of the AUX-2 to open, and how to talk on it.

        The settings are stored only once the port has taken them: a baud
        rate the device cannot do, or a port somebody else is holding, is
        refused on this form rather than by every read afterwards - a proxy
        port only reports those when it is opened, so this probe is the one
        honest place to ask.
        """
        errors: dict[str, str] = {}
        ports: list[ProxyPort] = [
            port for port in self._proxy_ports if port.entry_id == self._proxy_device
        ]

        if user_input is not None:
            port = next(
                (known for known in ports if known.url == user_input[CONF_DEVICE]),
                None,
            )
            if port is None:
                # The port was gone from the list before it was submitted.
                errors[CONF_DEVICE] = "no_proxy_ports"
            else:
                data: dict[str, Any] = _serial_data(port, user_input)
                failure: str | None = await self._async_port_error(port, data)
                if failure == "already_configured" and self._reconfiguring is None:
                    # A port belongs to one entry: while adding, this is not
                    # a setting to change but nowhere to go. Reconfiguring
                    # keeps the form, as it does for a network gateway.
                    return self.async_abort(reason="already_configured")
                if failure is not None:
                    errors["base"] = failure
                else:
                    return self._async_store_serial(data)

        reconfiguring = (
            self._reconfiguring.data if self._reconfiguring is not None else {}
        )
        last: dict[str, Any] = dict(user_input) if user_input else dict(reconfiguring)
        return self.async_show_form(
            step_id="aux2_port",
            data_schema=_serial_schema(  # type: ignore[arg-type,unused-ignore]
                ports, last
            ),
            errors=errors,
        )

    async def _async_proxy_ports(self) -> dict[str, str]:
        """Read the proxy ports Home Assistant can see, as form errors.

        Whether AUX-2 can be configured at all is only known by looking:
        the library may be missing, and ports only exist once a device has
        been adopted. Both are returned as errors rather than raised, so
        the form can be submitted again once things are in place. When the
        flow is a reconfiguration, the device already stored is picked so
        the form opens on it.
        """
        try:
            self._proxy_ports = await async_get_proxy_ports(self.hass)
        except SerialSupportUnavailable as err:
            self._proxy_ports = []
            return {"base": err.reason}

        if not self._proxy_ports:
            return {"base": "no_proxy_ports"}

        if self._reconfiguring is not None and not self._proxy_device:
            current = self._reconfiguring.data.get(CONF_DEVICE)
            known = next(
                (port for port in self._proxy_ports if port.url == current), None
            )
            if known is not None:
                self._proxy_device = known.entry_id
        return {}

    async def _async_port_error(
        self, port: ProxyPort, data: Mapping[str, Any]
    ) -> str | None:
        """Return what stops `port` being stored as this connection, if any.

        Another entry on the same URL is refused before the port is probed:
        the probe would open a port the other entry is entitled to hold.
        """
        entry = self._reconfiguring
        if self._serial_port_taken(
            str(data[CONF_DEVICE]), skip=entry.entry_id if entry is not None else None
        ):
            return "already_configured"
        return await async_validate_port(
            self.hass,
            port,
            baudrate=int(data[CONF_BAUDRATE]),
            bytesize=int(data[CONF_BYTESIZE]),
            parity=str(data[CONF_PARITY]),
            stopbits=int(data[CONF_STOPBITS]),
        )

    def _async_store_serial(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Store the AUX-2 connection: a new entry, or the changed one.

        An entry that now points at another port is reloaded, because its
        client, its gateway device and every read behind it belong to the
        connection and have to follow it.
        """
        entry = self._reconfiguring
        if entry is None:
            return self.async_create_entry(title=_gateway_title(data), data=data)

        stored: dict[str, Any] = {**entry.data, **data}
        self.hass.config_entries.async_update_entry(
            entry, data=stored, title=_gateway_title(stored)
        )
        self.hass.config_entries.async_schedule_reload(entry.entry_id)
        return self.async_abort(reason="reconfigure_successful")

    def _serial_port_taken(self, url: str, skip: str | None = None) -> bool:
        """Return whether a config entry already points at this proxy port.

        One port is one connection with one set of UART settings, so two
        entries on one URL would fight over a port that can be held only
        once, and would share the serial number their gateway device is
        keyed by.
        """
        return any(
            entry.entry_id != skip
            and get_transport(entry.data) == TRANSPORT_SERIAL_PROXY
            and entry.data.get(CONF_DEVICE) == url
            for entry in self.hass.config_entries.async_entries(DOMAIN)
        )

    async def _async_gateway_reachable(
        self, host: str, port: int, connection_type: str
    ) -> bool:
        """Report whether a gateway answers on the given connection.

        A gateway that cannot be reached is not worth storing: reconfiguring to
        it would take every device behind the current connection down.
        """
        self.client = AsyncModbusTcpClientGateway.async_get_client_connection(
            host=host,
            port=port,
            connection_type=connection_type,
        )
        await self.client.connect()
        if self.client.connected:
            self.client.close()
            return True
        return False

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the gateway connection.

        Devices behind the gateway keep their entity ids, unique ids and device
        ids while this changes, so the connection can be moved to another host
        or port without anybody having to rename anything.
        """
        entry: ConfigEntry = self._get_reconfigure_entry()
        if get_transport(entry.data) == TRANSPORT_SERIAL_PROXY:
            # The AUX-2 forms are the same ones the entry was added with, so
            # the port can be moved - or another AUX-2 chosen - without the
            # devices behind it being touched either.
            self._reconfiguring = entry
            return await self.async_step_aux2(user_input)

        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = int(user_input[CONF_PORT])
            connection_type = user_input.get(
                CONF_CONNECTION_TYPE, CONF_DEFAULT_CONNECTION_TYPE
            )
            if self._async_gateway_exists(
                host, port, connection_type, skip=entry.entry_id
            ):
                errors["base"] = "already_configured"
            elif await self._async_gateway_reachable(host, port, connection_type):
                if user_input.get(CONF_RESTORE_ENTITY_IDS, False):
                    await async_restore_legacy_entity_ids(self.hass, entry)

                data: dict[str, Any] = {
                    **entry.data,
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_CONNECTION_TYPE: connection_type,
                    CONF_LEGACY_ENTITY_IDS: user_input.get(
                        CONF_LEGACY_ENTITY_IDS, CONF_LEGACY_ENTITY_IDS_DEFAULT
                    ),
                }
                self.hass.config_entries.async_update_entry(
                    entry,
                    data=data,
                    title=_gateway_title(data),
                )
                # The client and the gateway device belong to the connection.
                self.hass.config_entries.async_schedule_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")
            else:
                errors["base"] = "Gateway connection"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(  # type: ignore[arg-type,unused-ignore]
                data_schema=_gateway_schema(  # type: ignore[arg-type,unused-ignore]
                    entry.data[CONF_HOST],
                    entry.data[CONF_PORT],
                    get_connection_type(entry.data),
                    restore=bool(
                        entry.data.get(
                            CONF_LEGACY_ENTITY_IDS, CONF_LEGACY_ENTITY_IDS_DEFAULT
                        )
                    ),
                ),
                suggested_values={**entry.data, CONF_RESTORE_ENTITY_IDS: False},
            ),
            errors=errors,
        )

    def _async_gateway_exists(
        self,
        host: str,
        port: int,
        connection_type: str,
        skip: str | None = None,
    ) -> bool:
        """Return whether a config entry already points at this gateway.

        Entries that predate sub-entries count too: they are migrated into a
        gateway config entry of their own, which would leave two config entries
        for one connection.
        """
        return any(
            entry.entry_id != skip
            and entry.data.get(CONF_HOST) == host
            and int(entry.data.get(CONF_PORT, 0)) == port
            and get_connection_type(entry.data) == connection_type
            for entry in self.hass.config_entries.async_entries(DOMAIN)
        )

    def async_abort(
        self,
        *,
        reason: str,
        description_placeholders: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> ConfigFlowResult:
        """Aborting the setup"""
        if self.client:
            self.client.close()
        return super().async_abort(
            reason=reason,
            description_placeholders=description_placeholders,
            **kwargs,
        )

    def async_show_progress_done(self, *, next_step_id: str) -> ConfigFlowResult:
        """Setup complete"""
        if self.client:
            self.client.close()
        return super().async_show_progress_done(next_step_id=next_step_id)

    async def async_on_create_entry(self, result: ConfigFlowResult) -> ConfigFlowResult:
        """Ask for the first device as soon as a gateway is configured."""
        subentry_result = await self.hass.config_entries.subentries.async_init(
            (result["result"].entry_id, SUBENTRY_TYPE_DEVICE),
            context=SubentryFlowContext(source=SOURCE_USER),
        )
        result["next_flow"] = (
            FlowType.CONFIG_SUBENTRIES_FLOW,
            subentry_result["flow_id"],
        )
        return result


def _normalise_device_data(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Return the settings of a device as they are stored."""
    return {
        CONF_PREFIX: str(user_input.get(CONF_PREFIX) or ""),
        CONF_DEVICE_ID: int(user_input[CONF_DEVICE_ID]),
        CONF_FILENAME: str(user_input[CONF_FILENAME]),
        OPTIONS_REFRESH: int(user_input[OPTIONS_REFRESH]),
        OPTIONS_WRITE_FUNCTION: str(user_input[OPTIONS_WRITE_FUNCTION]),
        OPTIONS_EXPECTED_OFFLINE: bool(
            user_input.get(OPTIONS_EXPECTED_OFFLINE, OPTIONS_DEFAULT_EXPECTED_OFFLINE)
        ),
    }


def _as_subentry(data: Mapping[str, Any]) -> ConfigSubentry:
    """Return settings of a device as a sub-entry would hold them.

    Only used to read a reconfigure form back: a sub-entry added for real goes
    through `hass.config_entries`, which stores the mapping itself.
    """
    return ConfigSubentry(
        data=MappingProxyType(dict(data)),
        subentry_type=SUBENTRY_TYPE_DEVICE,
        title="",
        unique_id=None,
    )


def _device_keys(entry: ConfigEntry, skip: ConfigSubentry | None = None) -> set[str]:
    """Return the keys of the devices already behind this gateway."""
    return {
        get_device_key(get_device_config(entry, known))
        for known in entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)
        if skip is None or known.subentry_id != skip.subentry_id
    }


def _async_move_device(
    hass: Any, entry: ConfigEntry, subentry: ConfigSubentry, config: Mapping[str, Any]
) -> None:
    """Give the device of a sub-entry the identifiers of its new settings.

    The entities of the device follow: their unique ids carry the prefix and the
    slave id of the device, so leaving them behind would make Home Assistant
    create a second set of entities instead of keeping these ones.
    """
    device_registry: dr.DeviceRegistry = dr.async_get(hass)
    identifiers: set[tuple[str, str]] = get_device_identifiers(config)

    device: dr.DeviceEntry | None = None
    for known in get_device_identifiers(get_device_config(entry, subentry)):
        device = device_registry.async_get_device_by_identifier(known, entry.entry_id)
        if device is not None:
            break

    if device is None or set(device.identifiers) == identifiers:
        return

    device_registry.async_update_device(device.id, new_identifiers=identifiers)
    _async_move_entity_unique_ids(
        hass=hass,
        device=device,
        old=_unique_id_head(get_device_config(entry, subentry)),
        new=_unique_id_head(config),
    )


def _unique_id_head(config: Mapping[str, Any]) -> str:
    """Return the prefix and slave id an entity unique id starts with."""
    prefix: str = config.get(CONF_PREFIX) or ""
    return f"{prefix + '-' if prefix else ''}{config[CONF_DEVICE_ID]}"


def _async_move_entity_unique_ids(
    hass: Any, device: dr.DeviceEntry, old: str, new: str
) -> None:
    """Rename the unique ids of the entities of a moved device.

    An entity keeps its entity id and its history: only the part of the unique
    id that names the device changes, so the registry entry the entity was
    created under stays the one it is matched against.
    """
    entity_registry: er.EntityRegistry = er.async_get(hass)
    for entity_entry in er.async_entries_for_device(entity_registry, device.id):
        unique_id: str = entity_entry.unique_id
        if not unique_id.startswith(f"{old}-"):
            # Not one of ours, or from a release that named unique ids
            # differently. Home Assistant mints a new entity for it, which is
            # what happened to those entities already.
            continue
        entity_registry.async_update_entity(
            entity_entry.entity_id, new_unique_id=f"{new}{unique_id[len(old) :]}"
        )


def _device_schema(devices_data: Mapping[str, str]) -> vol.Schema:
    """Return the form asking for the settings of one device."""
    return vol.Schema({
        vol.Required(CONF_DEVICE_ID, default=CONF_DEFAULT_DEVICE_ID): _number(0, 247),
        vol.Required(CONF_FILENAME): _dropdown(devices_data),
        vol.Optional(CONF_PREFIX, default=""): TextSelector(),
        vol.Required(OPTIONS_REFRESH, default=OPTIONS_DEFAULT_REFRESH): _number(0, 900),
        vol.Required(
            OPTIONS_WRITE_FUNCTION, default=OPTIONS_DEFAULT_WRITE_FUNCTION
        ): _dropdown(CONF_WRITE_FUNCTION_TYPES),
        vol.Required(
            OPTIONS_EXPECTED_OFFLINE, default=OPTIONS_DEFAULT_EXPECTED_OFFLINE
        ): BooleanSelector(),
    })


def _gateway_type_schema(gateway_type: Any) -> vol.Schema:
    """Return the form asking what kind of gateway connection this is.

    The two network kinds are the framers the gateway speaks, so the choice
    *is* the connection type and carries on to the network step as it; the
    AUX-2 is a device rather than a framer, and carries on to the steps
    that ask which one instead.
    """
    return vol.Schema({
        vol.Required(CONF_GATEWAY_TYPE, default=gateway_type): _dropdown(GATEWAY_TYPES),
    })


def _gateway_schema(
    host: Any, port: Any, connection_type: Any, restore: bool = False
) -> vol.Schema:
    """Return the form asking for a gateway connection.

    Restoring the pre-2026.02 entity ids is only offered when there is something
    to restore, on the gateway that has the entity ids in question.
    """
    schema: dict[Any, Any] = {
        vol.Required(CONF_HOST, default=host): TextSelector(),
        vol.Required(CONF_PORT, default=port): _number(1, 65535),
        vol.Required(CONF_CONNECTION_TYPE, default=connection_type): _dropdown(
            CONF_CONNECTION_TYPES
        ),
        vol.Required(
            CONF_LEGACY_ENTITY_IDS, default=CONF_LEGACY_ENTITY_IDS_DEFAULT
        ): BooleanSelector(),
    }
    if restore:
        schema[vol.Required(CONF_RESTORE_ENTITY_IDS, default=False)] = BooleanSelector()
    return vol.Schema(schema)


def _gateway_title(data: Mapping[str, Any]) -> str:
    """Return what the config entry for this gateway connection is called."""
    return f"Modbus Gateway ({get_connection_key(data)})"


def _serial_data(port: ProxyPort, settings: Mapping[str, Any]) -> dict[str, Any]:
    """Return the settings of a gateway on one AUX-2 port, as stored.

    Transport and connection type are not asked for: a proxy port is
    reached over one scheme and speaks one framer, so what is asked for is
    the port itself and the UART settings of the line behind it. The serial
    number keys the connection, because the URL names the ESPHome config
    entry that adopts the device, which is not the same thing.
    """
    return {
        CONF_TRANSPORT: TRANSPORT_SERIAL_PROXY,
        CONF_CONNECTION_TYPE: SERIAL_CONNECTION_TYPE,
        CONF_DEVICE: port.url,
        CONF_SERIAL_NUMBER: port.serial_number,
        CONF_BAUDRATE: int(settings[CONF_BAUDRATE]),
        CONF_BYTESIZE: int(settings[CONF_BYTESIZE]),
        CONF_PARITY: str(settings[CONF_PARITY]),
        CONF_STOPBITS: int(settings[CONF_STOPBITS]),
    }


def _serial_schema(ports: Sequence[ProxyPort], last: Mapping[str, Any]) -> vol.Schema:
    """Return the form asking for the port to open and how to talk on it.

    `last` is whatever is already known: what was submitted when the form
    comes back with an error, the entry's own settings when it is being
    reconfigured, and the usual serial defaults when there is neither.
    What a device does or does not take is deliberately not asked here:
    that is only reported when a port is opened, which is what the probe
    of the chosen port is for.
    """
    options: dict[str, str] = {port.url: port.port_label for port in ports}
    return vol.Schema({
        vol.Required(
            CONF_DEVICE, default=_prefill(str(last.get(CONF_DEVICE, "")), options)
        ): _dropdown(options),
        vol.Required(
            CONF_BAUDRATE,
            default=int(last.get(CONF_BAUDRATE, SERIAL_DEFAULT_BAUDRATE)),
        ): _number(300, 921600),
        vol.Required(
            CONF_BYTESIZE,
            default=int(last.get(CONF_BYTESIZE, SERIAL_DEFAULT_BYTESIZE)),
        ): _number(5, 8),
        vol.Required(
            CONF_PARITY, default=str(last.get(CONF_PARITY, SERIAL_DEFAULT_PARITY))
        ): _dropdown(_SERIAL_PARITY),
        vol.Required(
            CONF_STOPBITS,
            default=int(last.get(CONF_STOPBITS, SERIAL_DEFAULT_STOPBITS)),
        ): _number(1, 2),
    })


def _prefill(value: str, options: Mapping[str, str]) -> str:
    """Return `value` when the form offers it, else the first option it does.

    The device or port an entry already points at is what its form should
    open on, but that may have been unplugged or renamed meanwhile: the
    form still has to show something that can be submitted.
    """
    return value if value in options else next(iter(options), "")
