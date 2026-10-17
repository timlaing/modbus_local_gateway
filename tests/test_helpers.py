"""Test the keys that identify gateway connections and devices."""
# pylint: disable=unexpected-keyword-arg, protected-access

from custom_components.modbus_local_gateway.helpers import (
    get_connection_key,
    get_device_key,
    get_gateway_device_identifier,
    get_transport,
)

from .conftest import gateway_data, serial_gateway_data


def test_network_is_the_transport_of_an_entry_that_says_nothing() -> None:
    """An entry written before AUX-2 support is a network gateway."""
    assert get_transport(gateway_data()) == "network"
    assert get_transport(serial_gateway_data()) == "serial_proxy"


def test_network_connection_key_is_host_and_port() -> None:
    """A network gateway keeps the connection key it has always had."""
    assert get_connection_key(gateway_data(host="192.168.1.5", port=502)) == (
        "192.168.1.5:502"
    )


def test_proxy_port_connection_key_is_the_serial_number() -> None:
    """A proxy port is keyed by what survives a Home Assistant reinstallation.

    Its URL carries the ESPHome config entry id, which is not the same thing
    next time around, so identifiers built from this key must not use it.
    """
    assert get_connection_key(serial_gateway_data(serial_number="001122-uart1")) == (
        "001122-uart1"
    )


def test_network_device_key_carries_prefix_connection_and_slave_id() -> None:
    """A device behind a network gateway keeps its unique id."""
    config = {
        **gateway_data(host="192.168.1.5", port=502),
        "prefix": "inv",
        "slave_id": 2,
    }
    assert get_device_key(config) == "inv-192.168.1.5:502:2"


def test_proxy_port_device_key_carries_prefix_connection_and_slave_id() -> None:
    """A device behind a proxy port is keyed by the port it talks to."""
    config = {
        **serial_gateway_data(serial_number="001122-uart1"),
        "prefix": "inv",
        "slave_id": 2,
    }
    assert get_device_key(config) == "inv-001122-uart1:2"


def test_proxy_port_device_key_without_a_prefix() -> None:
    """A device with no prefix is keyed by the connection alone."""
    config = {**serial_gateway_data(), "prefix": "", "slave_id": 1}
    assert get_device_key(config) == "aabbccddeeff-uart0:1"


def test_gateway_device_identifier_follows_the_connection_key() -> None:
    """The gateway device of a connection is identified by its connection key."""
    assert get_gateway_device_identifier(gateway_data()) == (
        "ModbusGateway-localhost:123"
    )
    assert get_gateway_device_identifier(serial_gateway_data()) == (
        "ModbusGateway-aabbccddeeff-uart0"
    )
