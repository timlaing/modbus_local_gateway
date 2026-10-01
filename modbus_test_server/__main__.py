"""Test server for Modbus TCP using pymodbus. Allows to test Modbus TCP clients"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from pymodbus import __version__ as pymodbus_version
from pymodbus.framer import FramerType
from pymodbus.pdu.device import ModbusDeviceIdentification
from pymodbus.server import StartAsyncTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

_logger: logging.Logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)


_BLOCK_TYPES: list[str] = [
    "coils",
    "discrete_inputs",
    "holding_registers",
    "input_registers",
]


def _write_logging_action() -> Any:
    """Return an action logging incoming writes."""

    async def action(
        function_code: int,
        start_address: int,
        address: int,
        count: int,
        current_registers: list[int],
        set_values: list[int] | list[bool] | None,
    ) -> None:
        """Log incoming writes."""
        if set_values is not None:
            _logger.info(
                "Write to address %s, value %s",
                address,
                set_values,
            )

    return action


def _simdata_for(block_type: str, items: dict[str, Any]) -> SimData:
    """Create a SimData block covering the addresses given in ``items``."""
    data_type = (
        DataType.BITS
        if block_type in ("coils", "discrete_inputs")
        else DataType.REGISTERS
    )
    if not items:
        return SimData(1, count=1, values=[False], datatype=data_type)
    ordered = sorted((int(address, 16), value) for address, value in items.items())
    start = ordered[0][0]
    int_values: list[int] = []
    previous = start
    for address, value in ordered:
        int_values.extend([0] * (address - previous))
        int_values.append(int(value))
        previous = address + 1
    if data_type == DataType.BITS:
        return SimData(
            start,
            count=1,
            values=[bool(value) for value in int_values],
            datatype=data_type,
        )
    return SimData(start, count=1, values=int_values, datatype=data_type)


def _server_device(data_file: Path, device_id: int) -> SimDevice:
    """Create a SimDevice with the data from the given file."""
    _logger.info("### Create datastore")
    with data_file.open("r", encoding="utf-8") as file:
        data: dict[str, dict[str, Any]] = json.load(file)

    blocks: list[list[SimData]] = []
    for block_type in _BLOCK_TYPES:
        items = data.get(block_type, {})
        blocks.append([_simdata_for(block_type, items)])

    return SimDevice(
        id=device_id,
        simdata=(blocks[0], blocks[1], blocks[2], blocks[3]),
        action=_write_logging_action(),
    )


def _server_identity() -> ModbusDeviceIdentification:
    """Create a Modbus device identification."""
    info_name: dict[str, str] = {
        "VendorName": "Pymodbus",
        "ProductCode": "PM",
        "VendorUrl": (
            "https://github.com/timlaing/modbus-local-gateway/pymodbus-server/"
        ),
        "ProductName": "Pymodbus Server",
        "ModelName": "Pymodbus Server",
        "MajorMinorRevision": pymodbus_version,
    }
    identity = _device_identity(info_name)
    return identity


class _TypedModbusDeviceIdentification(ModbusDeviceIdentification):
    """Typed wrapper for the untyped pymodbus constructor."""

    def __init__(self, info_name: dict[str, str]) -> None:
        """Create a Modbus device identification."""
        super().__init__()  # type: ignore[no-untyped-call]
        name_attr = "_ModbusDeviceIdentification__names"
        names: list[str] = getattr(self, name_attr)
        for name, value in info_name.items():
            self.stat_data[names.index(name)] = value


def _device_identity(info_name: dict[str, str]) -> ModbusDeviceIdentification:
    """Build a Modbus device identification."""
    return _TypedModbusDeviceIdentification(info_name)


async def run_async_server(
    data_file: Path,
    host: str = "localhost",
    port: int = 502,
    device_id: int = 1,
) -> None:
    """Run the Modbus TCP server asynchronously."""
    _logger.info("Starting server, listening on %s:%d", host, port)
    address: tuple[str, int] = (host, port)
    await StartAsyncTcpServer(
        context=_server_device(data_file=data_file, device_id=device_id),
        address=address,  # listen address
        identity=_server_identity(),
        framer=FramerType.SOCKET,  # The framer strategy to use
    )


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run a Modbus TCP server.")
    parser.add_argument(
        "datafile",
        type=Path,
        help="Data file to use.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host to bind the server to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5020,
        help="Port to bind the server to.",
    )
    parser.add_argument(
        "--device-id",
        type=int,
        default=1,
        help="Device ID to use.",
    )
    args: argparse.Namespace = parser.parse_args()
    _logger.debug("Parsed arguments: %s", args)

    # Run the server
    asyncio.run(
        run_async_server(
            host=args.host,
            port=args.port,
            device_id=args.device_id,
            data_file=args.datafile,
        )
    )
