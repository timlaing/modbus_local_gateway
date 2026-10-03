"""Fixtures for tests"""
# pylint: disable=unexpected-keyword-arg, protected-access

from typing import Any
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import (
    CONF_DEVICE_ID,
    CONF_LEGACY_ENTITY_IDS,
    CONF_LEGACY_ENTITY_IDS_DEFAULT,
    CONF_PREFIX,
    DOMAIN,
    OPTIONS_DEFAULT_REFRESH,
    OPTIONS_DEFAULT_WRITE_FUNCTION,
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    ModbusDataType,
)
from custom_components.modbus_local_gateway.tcp_client import (
    AsyncModbusTcpClientGateway,
)


def gateway_data(
    host: str = "localhost",
    port: int = 123,
    connection_type: str = "socket",
    **kwargs: Any,
) -> dict[str, Any]:
    """Return the data of a gateway config entry."""
    return {
        "host": host,
        "port": port,
        "connection_type": connection_type,
        CONF_LEGACY_ENTITY_IDS: CONF_LEGACY_ENTITY_IDS_DEFAULT,
        **kwargs,
    }


def device_data(
    slave_id: int = 1, prefix: str = "test", filename: str = "test.yaml", **kwargs: Any
) -> dict[str, Any]:
    """Return the data of a device config sub-entry."""
    return {
        CONF_PREFIX: prefix,
        CONF_DEVICE_ID: slave_id,
        "filename": filename,
        "refresh": OPTIONS_DEFAULT_REFRESH,
        "write_function": OPTIONS_DEFAULT_WRITE_FUNCTION,
        **kwargs,
    }


def device_subentry(
    data: dict[str, Any], unique_id: str, title: str = "slave 1"
) -> dict[str, Any]:
    """Return one device config sub-entry."""
    return {
        "subentry_type": SUBENTRY_TYPE_DEVICE,
        "title": title,
        "unique_id": unique_id,
        "data": data,
    }


def mock_gateway_entry(
    slave_ids: list[int] | None = None,
    prefix: str = "test",
    filename: str = "test.yaml",
    **kwargs: Any,
) -> MockConfigEntry:
    """Return a config entry of a gateway with one sub-entry per slave id."""
    data = gateway_data(**kwargs)
    return MockConfigEntry(
        domain=DOMAIN,
        data=data,
        version=2,
        subentries_data=[
            device_subentry(
                device_data(slave_id, prefix=prefix, filename=filename),
                unique_id=f"{prefix}-{data['host']}:{data['port']}:{slave_id}",
                title=f"slave {slave_id}",
            )
            for slave_id in (slave_ids if slave_ids is not None else [1])
        ],
    )


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """fixture for a mock config entry"""
    return mock_gateway_entry()


@pytest.fixture
def mock_client() -> AsyncMock:
    """fixture for a mock client"""
    client = AsyncMock(spec=AsyncModbusTcpClientGateway)
    client.connected = False
    return client


@pytest.fixture
def valid_entity_description() -> ModbusEntityDescription:
    """Fixture for a valid ModbusEntityDescription."""
    return ModbusEntityDescription(
        key="key",
        register_address=1,
        register_count=2,
        is_float=False,
        is_string=False,
        max_change=None,
        conv_shift_bits=None,
        conv_bits=None,
        conv_multiplier=1.0,
        precision=None,
        data_type=ModbusDataType.HOLDING_REGISTER,
    )
