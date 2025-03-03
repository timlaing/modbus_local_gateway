import asyncio
import logging
from pymodbus.client import AsyncModbusTcpClient

# Constants
MODBUS_HOST = '10.0.0.60'
MODBUS_PORT = 502
SLAVE_ID = 20

REGISTER_ADDRESS = 1
REGISTER_COUNT = 1

ENABLE_WRITE = False
WRITE_VALUE_SINGLE = 2
WRITE_VALUE_MULTIPLE = 5

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def modbus_operations():
    logger.debug("Creating Modbus TCP client for %s:%d", MODBUS_HOST, MODBUS_PORT)

    async with AsyncModbusTcpClient(host=MODBUS_HOST, port=MODBUS_PORT) as client:
        try:
            logger.debug("Attempting to connect to device")
            connected = await client.connect()

            if connected:
                logger.info("Successfully connected to device")

                # Read operation
                logger.debug("Reading %d register(s) from address %d, slave %d", REGISTER_COUNT, REGISTER_ADDRESS, SLAVE_ID)
                result = await client.read_holding_registers(address=REGISTER_ADDRESS, count=REGISTER_COUNT, slave=SLAVE_ID)

                if result.isError():
                    logger.error("Error reading register: %s", result)
                else:
                    logger.info("Successfully read register value: %s", result.registers[0])
                    print(result.registers[0])

                if ENABLE_WRITE:

                    # Write operation using write_register (function code 6)
                    logger.debug("Writing value %d to register at address %d, slave %d using write_register", WRITE_VALUE_SINGLE, REGISTER_ADDRESS, SLAVE_ID)
                    result = await client.write_register(address=REGISTER_ADDRESS, value=WRITE_VALUE_SINGLE, slave=SLAVE_ID)

                    if result.isError():
                        logger.error("Error writing register with write_register: %s", result)
                    else:
                        logger.info("Successfully wrote register with write_register")

                    # Write operation using write_registers (function code 16)
                    logger.debug("Writing value %d to %d register(s) at address %d, slave %d using write_registers", WRITE_VALUE_MULTIPLE, REGISTER_COUNT, REGISTER_ADDRESS, SLAVE_ID)
                    result = await client.write_registers(address=REGISTER_ADDRESS, values=[WRITE_VALUE_MULTIPLE], slave=SLAVE_ID)

                    if result.isError():
                        logger.error("Error writing register with write_registers: %s", result)
                    else:
                        logger.info("Successfully wrote register with write_registers")

            else:
                logger.error("Failed to connect to device")

        except Exception as e:
            logger.exception("An error occurred: %s", str(e))
            raise

    logger.info("Connection closed automatically by context manager")

if __name__ == "__main__":
    logger.info("Starting Modbus operations")
    try:
        asyncio.run(modbus_operations())
        logger.info("Modbus operations completed successfully")
    except Exception as e:
        logger.error("Program terminated with error: %s", str(e))
