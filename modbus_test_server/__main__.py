"""Test server for Modbus TCP using pymodbus. Allows to test Modbus TCP clients"""

import argparse
import asyncio
import json
import logging

from pymodbus import __version__ as pymodbus_version
from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusSequentialDataBlock,
    ModbusServerContext,
)
from pymodbus.framer import FramerType
from pymodbus.pdu.device import ModbusDeviceIdentification
from pymodbus.server import (
    StartAsyncTcpServer,
)

_logger: logging.Logger = logging.getLogger(__file__)
_logger.setLevel(logging.INFO)


class CallbackDataBlock(ModbusSequentialDataBlock):
    """A datablock that stores the new value in memory,.

    and passes the operation to a message queue for further processing.
    """

    def setValues(self, address, values) -> None:
        """Set the requested values of the datastore."""
        super().setValues(address, values)
        txt = f"Callback from setValues with address {address}, value {values}"
        _logger.info(txt)

    def getValues(self, address, count=1):
        """Return the requested values from the datastore."""
        result = super().getValues(address, count=count)
        txt = f"Callback from getValues with address {address}, count {count}, data {result}"
        _logger.debug(txt)
        return result


ADDRESS_TYPE_MAP: dict[str, int] = {
    "coils": 0x1,  # Coils
    "discrete_inputs": 0x2,  # Discrete Inputs
    "holding_registers": 0x3,  # Holding Registers
    "input_registers": 0x4,  # Input Registers
}


def _server_context(
    data_file,
    device_id: int = 1,
) -> ModbusServerContext:
    """Create a Modbus server context with a single device."""
    _logger.info("### Create datastore")
    context: dict[int, ModbusDeviceContext] = {}
    context[device_id] = ModbusDeviceContext(
        di=CallbackDataBlock(0x00, [0] * 65536),  # Discrete Inputs
        co=CallbackDataBlock(0x00, [0] * 65536),  # Coils
        hr=CallbackDataBlock(0x00, [0] * 65536),  # Holding Registers
        ir=CallbackDataBlock(0x00, [0] * 65536),  # Input Registers
    )

    # Load initial data from file
    _logger.info("### Load initial data from file %s", data_file.name)
    data: dict = json.load(data_file)
    for block_type, block_data in data.items():
        for address_str, value in block_data.items():
            address: int = int(address_str, 16)
            context[device_id].setValues(ADDRESS_TYPE_MAP[block_type], address, [value])

    return ModbusServerContext(devices=context, single=False)


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
    data_file,
    host: str = "localhost",
    port: int = 502,
    device_id: int = 1,
) -> None:
    """Run the Modbus TCP server asynchronously."""
    _logger.info("Starting server, listening on %s:%d", host, port)
    address: tuple[str, int] = (host, port)
    await StartAsyncTcpServer(
        context=_server_context(
            device_id=device_id,
            data_file=data_file,
        ),  # Data storage
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
        "datafile",
        type=argparse.FileType("r", encoding="utf-8"),
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
    print(args)

    # Run the server
    asyncio.run(
        run_async_server(
            host=args.host,
            port=args.port,
            device_id=args.device_id,
            data_file=args.datafile,
        )
    )
