"""Test server for Modbus TCP using pymodbus. Allows to test Modbus TCP clients"""

import argparse
import asyncio
import logging

from pymodbus import __version__ as pymodbus_version
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.framer import FramerType
from pymodbus.server import (
    StartAsyncTcpServer,
)

_logger: logging.Logger = logging.getLogger(__file__)
_logger.setLevel(logging.INFO)


def _server_context(slave_id=1) -> ModbusServerContext:
    """Create a Modbus server context with a single slave."""
    _logger.info("### Create datastore")
    context: dict[int, ModbusSlaveContext] = {}
    context[slave_id] = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0x00, [0] * 100),  # Discrete Inputs
        co=ModbusSequentialDataBlock(0x00, [0] * 100),  # Coils
        hr=ModbusSequentialDataBlock(0x00, [0x1A] * 100),  # Holding Registers
        ir=ModbusSequentialDataBlock(0x00, [13] * 100),  # Input Registers
    )
    return ModbusServerContext(slaves=context, single=False)


def _server_identity() -> ModbusDeviceIdentification:
    """Create a Modbus device identification."""
    identity = ModbusDeviceIdentification(
        info_name={
            "VendorName": "Pymodbus",
            "ProductCode": "PM",
            "VendorUrl": "https://github.com/timlaing/modbus-local-gateway/pymodbus-server/",
            "ProductName": "Pymodbus Server",
            "ModelName": "Pymodbus Server",
            "MajorMinorRevision": pymodbus_version,
        }
    )
    return identity


async def run_async_server(
    host: str = "localhost",
    port: int = 502,
    slave_id: int = 1,
) -> None:
    """Run the Modbus TCP server asynchronously."""
    _logger.info("Starting server, listening on %s:%d", host, port)
    address: tuple[str, int] = (host, port)
    await StartAsyncTcpServer(
        context=_server_context(slave_id=slave_id),  # Data storage
        identity=_server_identity(),  # server identify
        address=address,  # listen address
        # custom_functions=[],  # allow custom handling
        framer=FramerType.SOCKET,  # The framer strategy to use
        # ignore_missing_devices=True,  # ignore request to a missing device
        # broadcast_enable=False,  # treat device 0 as broadcast address,
        # timeout=1,  # waiting time for request to complete
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
        "--slave-id",
        type=int,
        default=1,
        help="Slave ID to use.",
    )
    args: argparse.Namespace = parser.parse_args()

    # Run the server
    asyncio.run(
        run_async_server(host=args.host, port=args.port, slave_id=args.slave_id)
    )
